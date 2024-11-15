import asyncio
import tweepy
from config import Config
import datetime
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

logger = logging.getLogger(__name__)

class TwitterManager:
    def __init__(self, config: Config, telegram_bot, user_queries, account_queries):
        self.client_dy = tweepy.Client(
            bearer_token=config.DY_TWITTER_BEARER_TOKEN,
            consumer_key=config.DY_TWITTER_API_KEY,
            consumer_secret=config.DY_TWITTER_API_KEY_SECRET,
            access_token=config.DY_TWITTER_ACCESS_TOKEN,
            access_token_secret=config.DY_TWITTER_ACCESS_SECRET,
        )
        self.client_dx = tweepy.Client(
            bearer_token=config.DX_TWITTER_BEARER_TOKEN,
            consumer_key=config.DX_TWITTER_API_KEY,
            consumer_secret=config.DX_TWITTER_API_KEY_SECRET,
            access_token=config.DX_TWITTER_ACCESS_TOKEN,
            access_token_secret=config.DX_TWITTER_ACCESS_SECRET,
        )
        self.poll_interval = config.TWITTER_POLL_INTERVAL
        self.monitoring = False
        self.monitored_users = []
        self.last_tweets = {}
        self.telegram_bot = telegram_bot
        self.user_queries = user_queries
        self.account_queries = account_queries
        self.monitor_task = None

    def create_tweet_url(self, username: str, tweet_id: str) -> str:
        """Create the URL for a tweet"""
        return f"https://twitter.com/{username}/status/{tweet_id}"

    def create_telegram_keyboard(self, tweet_url: str) -> InlineKeyboardMarkup:
        """Create an inline keyboard with a button to view the tweet"""
        keyboard = [[InlineKeyboardButton("View on X", url=tweet_url)]]
        return InlineKeyboardMarkup(keyboard)

    async def send_to_telegram(self, chat_id: int, message: str, tweet_url: str = None):
        """Send a message to Telegram with an inline button"""
        try:
            kwargs = {
                'chat_id': chat_id,
                'text': message,
                'parse_mode': 'HTML'
            }
            
            if tweet_url:
                kwargs['reply_markup'] = self.create_telegram_keyboard(tweet_url)
            
            await self.telegram_bot.bot.send_message(**kwargs)
        except Exception as e:
            logger.error(f"Error sending message to Telegram: {e}")

    def format_tweet_message(self, username: str, tweet) -> str:
        """Format the tweet message for Telegram"""
        created_at = tweet.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')
        return (
            f"📱 New tweet from <b>@{username}</b>\n\n"
            f"{tweet.text}\n\n"
            f"🕒 {created_at}"
        )

    async def fetch_user_tweets(self, username: str, client, since_id=None):
        """Fetch tweets for a user with error handling"""
        try:
            user = await asyncio.get_event_loop().run_in_executor(
                None, lambda: client.get_user(username=username)
            )
            tweets = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: client.get_users_tweets(
                    id=user.data.id,
                    since_id=since_id,
                    max_results=5,
                    tweet_fields=["created_at", "text"]
                )
            )
            return user, tweets
        except Exception as e:
            logger.error(f"Error fetching tweets for @{username}: {e}")
            return None, None

    async def initialize_monitoring(self, usernames: list[str]):
        """Initialize monitoring for new users"""
        for username in usernames:
            if username not in self.last_tweets:
                user, tweets = await self.fetch_user_tweets(username, self.client_dy)
                if tweets and tweets.data:
                    self.last_tweets[username] = tweets.data[0].id

    async def monitor_loop(self):
        """The main monitoring loop"""
        current_client = self.client_dy
        
        while self.monitoring:
            try:
                for username in self.monitored_users:
                    user, tweets = await self.fetch_user_tweets(
                        username,
                        current_client,
                        self.last_tweets.get(username)
                    )
                    
                    if tweets and tweets.data:
                        self.last_tweets[username] = tweets.data[0].id
                        
                        for tweet in reversed(tweets.data):
                            message = self.format_tweet_message(username, tweet)
                            tweet_url = self.create_tweet_url(username, tweet.id)
                            
                            chat_ids = self.user_queries.get_authorized_chat_ids()
                            for chat_id in chat_ids:
                                await self.send_to_telegram(chat_id, message, tweet_url)
                            
                            logger.info(f"Sent new tweet from @{username} to Telegram")
                
                # Alternate the client
                current_client = self.client_dx if current_client == self.client_dy else self.client_dy
                
                # Async sleep
                await asyncio.sleep(self.poll_interval)
            
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
                await asyncio.sleep(self.poll_interval)

    async def monitor(self, usernames: list[str]):
        """Start monitoring tweets from the given usernames"""
        if self.monitor_task and not self.monitor_task.done():
            return
        
        self.monitoring = True
        self.monitored_users = usernames
        logger.info(f"Started monitoring: {', '.join(usernames)}")
        
        # Send startup notification
        admin_chat_ids = self.account_queries.get_admin_chat_ids()
        if admin_chat_ids:
            await asyncio.gather(*[
                self.send_to_telegram(
                    chat_id=admin_chat_id,
                    message=f"🔔 Started monitoring tweets from: {', '.join(usernames)}"
                )
                for admin_chat_id in admin_chat_ids
            ])
        
        # Initialize monitoring
        await self.initialize_monitoring(usernames)
        
        # Start the monitoring loop as a background task
        self.monitor_task = asyncio.create_task(self.monitor_loop())

    async def stop_monitoring(self):
        """Stop monitoring tweets"""
        self.monitoring = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
            self.monitor_task = None
        
        logger.info("Stopped monitoring.")
        
        # Send shutdown notification
        admin_chat_id = self.account_queries.get_admin_chat_id()
        if admin_chat_id:
            await self.send_to_telegram(
                chat_id=admin_chat_id,
                message="🔔 Stopped monitoring tweets"
            )

    async def add_monitored_user(self, username: str):
        """Add a new user to the monitored list"""
        if username not in self.monitored_users:
            self.monitored_users.append(username)
            await self.initialize_monitoring([username])
            logger.info(f"Added @{username} to the monitored list.")

    async def remove_monitored_user(self, username: str):
        """Remove a user from the monitored list"""
        if username in self.monitored_users:
            self.monitored_users.remove(username)
            if username in self.last_tweets:
                del self.last_tweets[username]
            logger.info(f"Removed @{username} from the monitored list.")
        else:
            logger.info(f"@{username} is not in the monitored list.")
    async def get_user_id(self, username: str):
        """Get the user ID for a given username"""
        user = await asyncio.get_event_loop().run_in_executor(
            None, lambda: self.client_dy.get_user(username=username)
        )
        return user.data.id