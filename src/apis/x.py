import asyncio
import requests
import datetime
import pytz
import logging
from config import Config
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

logger = logging.getLogger(__name__)

class TwitterManager:
    def __init__(self, config: Config, telegram_bot, user_queries, account_queries):
        self.base_url = "https://api.twitter.com/2"
        self.headers_dx = {
            "Authorization": f"Bearer {config.DX_TWITTER_BEARER_TOKEN}"
        }
        self.headers_dy = {
            "Authorization": f"Bearer {config.DY_TWITTER_BEARER_TOKEN}"
        }
        
        self.poll_interval = config.TWITTER_POLL_INTERVAL
        self.monitoring = False
        self.monitored_users = []
        self.last_tweets = {}
        self.telegram_bot = telegram_bot
        self.user_queries = user_queries
        self.account_queries = account_queries
        self.monitor_task = None
        
        # Token status tracking
        self.token_status = {
            'dy': {'authorized': True, 'rate_limit_remaining': None, 'rate_limit_reset': None},
            'dx': {'authorized': True, 'rate_limit_remaining': None, 'rate_limit_reset': None}
        }
        self.current_token = 'dy'  # Start with dy token
        self.rate_limit_warning_threshold = 10

    def get_next_token(self):
        """Get the next available token for API requests"""
        tokens = ['dy', 'dx']
        if all(self.token_status[t]['authorized'] for t in tokens):
            # If both tokens are authorized, alternate between them
            self.current_token = 'dx' if self.current_token == 'dy' else 'dy'
        else:
            # If only one token is authorized, use that one
            self.current_token = next(
                (t for t in tokens if self.token_status[t]['authorized']),
                None
            )
        return self.current_token
    
    def get_current_headers(self):
        """Get the headers for the current token"""
        token = self.get_next_token()
        return self.headers_dy if token == 'dy' else self.headers_dx

    def create_tweet_url(self, username: str, tweet_id: str) -> str:
        """Create the URL for a tweet"""
        return f"https://twitter.com/{username}/status/{tweet_id}"

    @staticmethod
    def convert_to_new_york_time(utc_time):
        utc_zone = pytz.utc
        ny_zone = pytz.timezone('America/New_York')
        utc_time = utc_zone.localize(utc_time)
        ny_time = utc_time.astimezone(ny_zone)
        return ny_time.strftime("%I:%M %p")

    @staticmethod
    def shorten_text(text: str, max_length: int = 200) -> str:
        """Shorten the text to a maximum length"""
        if len(text) > max_length:
            return text[:max_length - 3] + "..."
        return text

    def format_reply_message(self, username: str, tweet) -> tuple[str, InlineKeyboardMarkup]:
        """Format the reply message for Telegram with inline keyboard buttons"""
        text = self.shorten_text(tweet['text'])
        tweet_link = self.create_tweet_url(username, tweet['id'])
        utc_time = datetime.datetime.utcnow()
        timestamp = self.convert_to_new_york_time(utc_time)
        
        # Create inline keyboard with buttons
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("💬 View Reply", url=tweet_link),
                InlineKeyboardButton("👤 View Profile", url=f"https://twitter.com/{username}")
            ]
        ])
        
        message = (
            f"<b>Reply | @{username}</b>\n\n"
            f"{text}\n\n"
            f"🕒 {timestamp}"
        )
        
        return message, keyboard

    def format_tweet_message(self, username: str, tweet) -> tuple[str, InlineKeyboardMarkup]:
        """Format the tweet message for Telegram with inline keyboard buttons"""
        text = self.shorten_text(tweet['text'])
        tweet_link = self.create_tweet_url(username, tweet['id'])
        utc_time = datetime.datetime.utcnow()
        timestamp = self.convert_to_new_york_time(utc_time)
        
        # Create inline keyboard with buttons
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔗 View Tweet", url=tweet_link),
                InlineKeyboardButton("👤 View Profile", url=f"https://twitter.com/{username}")
            ]
        ])
        
        message = (
            f"<b>Tweet | @{username}</b>\n\n"
            f"{text}\n\n"
            f"🕒 {timestamp}"
        )
        
        return message, keyboard

    async def send_to_telegram(self, chat_id: int, message: str, tweet_url: str = None, reply_markup: InlineKeyboardMarkup = None):
        """Send a message to Telegram with inline keyboard buttons"""
        try:
            kwargs = {
                'chat_id': chat_id,
                'text': message,
                'parse_mode': 'HTML',
                'disable_web_page_preview': True  # Prevent URL preview for cleaner look
            }
            
            if reply_markup:
                kwargs['reply_markup'] = reply_markup
                
            await self.telegram_bot.bot.send_message(**kwargs)
        except Exception as e:
            logger.error(f"Error sending message to Telegram: {e}")

    async def fetch_latest_activity(self, user: set, headers) -> tuple[str, str]:
        """
        Fetch the most recent tweet and reply for a user
        Returns tuple of (latest_tweet_id, latest_reply_id)
        """
        try:
            username, user_id = user
            params = {
                "max_results": 5,  # Increase to better chance of finding both tweet and reply
                "tweet.fields": "created_at,text,conversation_id,in_reply_to_user_id",
                "exclude": "retweets"
            }
            
            endpoint = f"users/{user_id}/tweets"
            response = await self.make_request(endpoint, params, headers)
            
            if response and 'data' in response:
                tweets = response['data']
                
                # Find latest regular tweet and reply
                latest_tweet = None
                latest_reply = None
                latest_tweet_data = None
                latest_reply_data = None
                
                for tweet in tweets:
                    is_reply = tweet.get('in_reply_to_user_id') is not None
                    
                    if is_reply and latest_reply is None:
                        latest_reply = tweet['id']
                        latest_reply_data = tweet
                    elif not is_reply and latest_tweet is None:
                        latest_tweet = tweet['id']
                        latest_tweet_data = tweet
                    
                    # Break if we found both
                    if latest_tweet and latest_reply:
                        break
                
                logger.info(
                    f"Fetched initial tweets for @{username} - "
                    f"Latest tweet: {latest_tweet}, Latest reply: {latest_reply}"
                )
                
                # Send the latest tweet or reply to telegram with inline keyboard
                chat_ids = self.user_queries.get_admin_chat_ids()
                
                if latest_tweet_data:
                    message, keyboard = self.format_tweet_message(user[0], latest_tweet_data)
                    for chat_id in chat_ids:
                        await self.send_to_telegram(
                            chat_id=chat_id,
                            message=message,
                            reply_markup=keyboard
                        )
                
                if latest_reply_data:
                    message, keyboard = self.format_reply_message(user[0], latest_reply_data)
                    for chat_id in chat_ids:
                        await self.send_to_telegram(
                            chat_id=chat_id,
                            message=message,
                            reply_markup=keyboard
                        )
                
                # Return the most recent ID between tweet and reply
                if latest_tweet and latest_reply:
                    return max(int(latest_tweet), int(latest_reply))
                return latest_tweet or latest_reply or None
            
            return None
            
        except Exception as e:
            logger.error(f"Error fetching initial tweets for @{username}: {e}")
            return None
    
    async def make_request(self, endpoint: str, params: dict, headers: dict):
        """Make an async request to the Twitter API with authorization and rate limit handling"""
        try:
            token_type = 'dy' if headers == self.headers_dy else 'dx'
            
            # Skip request if token is unauthorized
            if not self.token_status[token_type]['authorized']:
                logger.warning(f"Skipping request with unauthorized {token_type.upper()} token")
                return None
            
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: requests.get(
                    f"{self.base_url}/{endpoint}",
                    params=params,
                    headers=headers
                )
            )
            
            if response.status_code == 401:  # Unauthorized
                await self.handle_unauthorized_token(token_type)
                return None
            
            # Only process rate limits for authorized requests
            if response.status_code == 200:
                self.token_status[token_type]['rate_limit_remaining'] = int(response.headers.get('x-rate-limit-remaining', 0))
                reset_time = int(response.headers.get('x-rate-limit-reset', 0))
                self.token_status[token_type]['rate_limit_reset'] = datetime.datetime.fromtimestamp(reset_time)
                
                if self.token_status[token_type]['rate_limit_remaining'] <= self.rate_limit_warning_threshold:
                    await self.notify_rate_limit_warning(token_type)
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:  # Rate limit exceeded
                await self.handle_rate_limit_exceeded(token_type)
            logger.error(f"Twitter API request failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Twitter API request failed: {e}")
            return None

    async def handle_unauthorized_token(self, token_type: str):
        """Handle unauthorized token scenario with clear messaging"""
        self.token_status[token_type]['authorized'] = False
        
        message = f"⚠️ {token_type.upper()} token unauthorized - switching to alternate token"
        logger.error(f"Token {token_type.upper()} unauthorized")
        
        # Only notify if all tokens become unauthorized
        if not any(status['authorized'] for status in self.token_status.values()):
            message = "🚫 All tokens unauthorized - monitoring stopped"
            admin_chat_ids = self.account_queries.get_super_admin_chat_ids()
            for admin_chat_id in admin_chat_ids:
                await self.send_to_telegram(chat_id=admin_chat_id, message=message)
            await self.stop_monitoring()

    async def handle_rate_limit_exceeded(self, token_type: str):
        """Handle rate limit exceeded with clear messaging"""
        reset_time = self.token_status[token_type]['rate_limit_reset']
        if reset_time:
            reset_in = (reset_time - datetime.datetime.now()).total_seconds() / 60
            message = f"⚠️ {token_type.upper()} rate limit reached - reset in {reset_in:.0f}min"
        else:
            message = f"⚠️ {token_type.upper()} rate limit reached - switching tokens"
        
        admin_chat_ids = self.account_queries.get_super_admin_chat_ids()
        for admin_chat_id in admin_chat_ids:
            await self.send_to_telegram(chat_id=admin_chat_id, message=message)
        
        # If both tokens are rate limited, pause monitoring
        if (self.token_status['dy']['rate_limit_remaining'] == 0 and
            self.token_status['dx']['rate_limit_remaining'] == 0):
            await self.pause_monitoring_until_reset()

    async def handle_all_tokens_unauthorized(self):
        """Handle scenario where all tokens are unauthorized"""
        message = (
            "🔴 CRITICAL: All API tokens are unauthorized!\n"
            "Monitoring will be stopped until tokens are updated.\n"
            "Please update the configuration with valid tokens."
        )
        
        admin_chat_ids = self.account_queries.get_super_admin_chat_ids()
        if admin_chat_ids:
            for admin_chat_id in admin_chat_ids:
                await self.send_to_telegram(chat_id=admin_chat_id, message=message)
        
        await self.stop_monitoring()

    async def fetch_user_tweets(self, user: set, headers, since_id=None):
        """Fetch tweets for a user without sending to Telegram"""
        try:
            username, user_id = user
            params = {
                "max_results": 10,
                "tweet.fields": "created_at,text,conversation_id,in_reply_to_user_id",
                "exclude": "retweets"
            }
            
            if since_id:
                params["since_id"] = since_id

            endpoint = f"users/{user_id}/tweets"
            response = await self.make_request(endpoint, params, headers)

            if response and 'data' in response:
                all_tweets = []
                for tweet_data in response['data']:
                    tweet_dict = {
                        'id': tweet_data['id'],
                        'text': tweet_data['text'],
                        'created_at': tweet_data['created_at'],
                        'is_reply': tweet_data.get('in_reply_to_user_id') is not None
                    }
                    all_tweets.append(tweet_dict)

                sorted_tweets = sorted(
                    all_tweets,
                    key=lambda x: x['created_at'],
                    reverse=True
                )

                if since_id:
                    sorted_tweets = [
                        tweet for tweet in sorted_tweets 
                        if int(tweet['id']) > int(since_id)
                    ]

                logger.info(f"Fetched {len(sorted_tweets)} tweets for @{username}")
                return username, sorted_tweets

            return username, None

        except Exception as e:
            logger.error(f"Error fetching tweets for @{username}: {e}")
            return None, None

    async def notify_rate_limit_warning(self, token_type: str):
        """Notify admins about approaching rate limit for authorized tokens"""
        if not self.token_status[token_type]['authorized']:
            return
            
        reset_time = self.token_status[token_type]['rate_limit_reset']
        remaining = self.token_status[token_type]['rate_limit_remaining']
        reset_in = (reset_time - datetime.datetime.now()).total_seconds() / 60
        
        message = (
            f"⚠️ Rate Limit Warning for {token_type.upper()} token:\n"
            f"Remaining requests: {remaining}\n"
            f"Reset in: {reset_in:.1f} minutes\n"
            f"Reset time: {reset_time.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        admin_chat_ids = self.account_queries.get_super_admin_chat_ids()
        if admin_chat_ids:
            for admin_chat_id in admin_chat_ids:
                await self.send_to_telegram(chat_id=admin_chat_id, message=message)

    async def handle_rate_limit_exceeded(self, token_type: str):
        """Handle rate limit exceeded scenario"""
        try:
            reset_time = self.token_status[token_type]['rate_limit_reset']
            # Check if reset_time is None before calculation
            if reset_time is None:
                reset_in = 0
                reset_time_str = "Unknown"
            else:
                reset_in = (reset_time - datetime.datetime.now()).total_seconds() / 60  # minutes
                reset_time_str = reset_time.strftime('%Y-%m-%d %H:%M:%S')
            
            message = (
                f"🚫 Rate Limit Exceeded for {token_type.upper()} token!\n"
                f"Rate limit will reset in: {reset_in:.1f} minutes\n"
                f"Reset time: {reset_time_str}"
            )
            
            admin_chat_ids = self.account_queries.get_super_admin_chat_ids()
            if admin_chat_ids:
                for admin_chat_id in admin_chat_ids:
                    await self.send_to_telegram(chat_id=admin_chat_id, message=message)
            
            # If both tokens are rate limited, pause monitoring temporarily
            if (self.token_status['dy']['rate_limit_remaining'] == 0 and
                self.token_status['dx']['rate_limit_remaining'] == 0):
                await self.pause_monitoring_until_reset()
                
        except Exception as e:
            logger.error(f"Error in handle_rate_limit_exceeded: {e}")
            # Fallback message in case of error
            message = f"🚫 Rate Limit Exceeded for {token_type.upper()} token! Unable to determine reset time."
            admin_chat_ids = self.account_queries.get_admin_chat_ids()
            if admin_chat_ids:
                for admin_chat_id in admin_chat_ids:
                    await self.send_to_telegram(chat_id=admin_chat_id, message=message)

    async def pause_monitoring_until_reset(self):
        """Temporarily pause monitoring until rate limits reset"""
        try:
            message = "⏸️ Monitoring temporarily paused due to rate limits on both tokens"
            
            admin_chat_ids = self.account_queries.get_super_admin_chat_ids()
            if admin_chat_ids:
                for admin_chat_id in admin_chat_ids:
                    await self.send_to_telegram(chat_id=admin_chat_id, message=message)
            
            # Calculate shortest reset time, handling None values
            dy_reset = self.token_status['dy']['rate_limit_reset']
            dx_reset = self.token_status['dx']['rate_limit_reset']
            
            if dy_reset is None and dx_reset is None:
                wait_time = 900  # 15 minutes default wait if both reset times are None
            elif dy_reset is None:
                wait_time = (dx_reset - datetime.datetime.now()).total_seconds()
            elif dx_reset is None:
                wait_time = (dy_reset - datetime.datetime.now()).total_seconds()
            else:
                reset_time = min(dy_reset, dx_reset)
                wait_time = (reset_time - datetime.datetime.now()).total_seconds()
            
            # Ensure wait_time is positive and reasonable
            wait_time = max(min(wait_time, 3600), 300)  # Between 5 minutes and 1 hour
            
            await asyncio.sleep(wait_time + 5)  # Add 5 seconds buffer
            
            # Resume monitoring
            message = "▶️ Resuming monitoring after rate limit reset"
            for admin_chat_id in admin_chat_ids:
                await self.send_to_telegram(chat_id=admin_chat_id, message=message)
                
        except Exception as e:
            logger.error(f"Error in pause_monitoring_until_reset: {e}")
            # Default fallback behavior
            await asyncio.sleep(900)  # 15 minutes default wait
            message = "▶️ Resuming monitoring after default wait period"
            if admin_chat_ids:
                for admin_chat_id in admin_chat_ids:
                    await self.send_to_telegram(chat_id=admin_chat_id, message=message)

    async def initialize_monitoring(self, users: list[set]):
        """Initialize monitoring for new users with latest tweet/reply IDs"""
        admin_chat_ids = self.account_queries.get_admin_chat_ids()
        initialization_messages = []

        for user in users:
            if user not in self.last_tweets:
                latest_id = await self.fetch_latest_activity(user, self.headers_dy)
                
                if latest_id:
                    self.last_tweets[user] = str(latest_id)
                    msg = f"✅ Initialized monitoring for @{user[0]} - Latest activity ID: {latest_id}"
                else:
                    msg = f"⚠️ Could not fetch initial tweets for @{user[0]}"
                
                initialization_messages.append(msg)
                logger.info(msg)

    async def monitor_loop(self):
        """Improved monitor loop with token switching and centralized message sending"""
        while self.monitoring:
            try:
                current_headers = self.get_current_headers()
                if not current_headers:
                    logger.error("No authorized tokens available")
                    await self.handle_all_tokens_unauthorized()
                    break
                
                for user in self.monitored_users:
                    username, tweets = await self.fetch_user_tweets(
                        user,
                        current_headers,
                        self.last_tweets.get(user)
                    )
                    
                    if tweets and len(tweets) > 0:
                        self.last_tweets[user] = tweets[0]['id']
                        # Send tweets to Telegram here
                        chat_ids = self.user_queries.get_admin_chat_ids()
                        for tweet in reversed(tweets):
                            if tweet['is_reply']:
                                message, keyboard = self.format_reply_message(username, tweet)
                            else:
                                message, keyboard = self.format_tweet_message(username, tweet)
                            
                            for chat_id in chat_ids:
                                await self.send_to_telegram(
                                    chat_id=chat_id,
                                    message=message,
                                    reply_markup=keyboard
                                )
                
                await asyncio.sleep(self.poll_interval)
            
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
                await asyncio.sleep(self.poll_interval)    

    async def monitor(self, users: list[set]):
        """Start monitoring tweets from the given usernames"""
        if self.monitor_task and not self.monitor_task.done():
            return
        
        self.monitoring = True
        self.monitored_users = users
        logger.info(f"Started monitoring: {', '.join([user[0] for user in users])}")
        
        # Send startup notification
        admin_chat_ids = self.account_queries.get_admin_chat_ids()
        if admin_chat_ids:
            for admin_chat_id in admin_chat_ids:
                await self.send_to_telegram(
                    chat_id=admin_chat_id,
                    message=f"🔔 Starting tweet monitoring process..."
                )
        
        # Initialize with latest tweets
        await self.initialize_monitoring(users)
        
        # Send confirmation of initialization
        if admin_chat_ids:
            status_message = (
                "📊 Monitoring Status:\n"
                f"Users being monitored: {', '.join([f'@{user[0]}' for user in users])}\n"
                f"Poll interval: {self.poll_interval} seconds\n"
                "Monitoring loop starting..."
            )
            for admin_chat_id in admin_chat_ids:
                await self.send_to_telegram(
                    chat_id=admin_chat_id,
                    message=status_message
                )
        
        # Start the monitoring loop
        self.monitor_task = asyncio.create_task(self.monitor_loop())

    async def stop_monitoring(self):
        """Stop monitoring tweets"""
        self.monitoring = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                logger.info("Monitoring task cancelled.")
            self.monitor_task = None
        
        logger.info("Stopped monitoring.")
        
        admin_chat_ids = self.account_queries.get_admin_chat_ids()
        if admin_chat_ids:
            for admin_chat_id in admin_chat_ids:
                await self.send_to_telegram(
                    chat_id=admin_chat_id,
                    message="🔕 Monitoring has been stopped."
                )

    async def add_monitored_user(self, user: set):
        """Add a new user to the monitored list"""
        if user not in self.monitored_users:
            self.monitored_users.append(user)
            await self.initialize_monitoring([user])
            logger.info(f"Added @{user[0]} to the monitored list.")

    async def remove_monitored_user(self, user: set):
        """Remove a user from the monitored list"""
        if user in self.monitored_users:
            self.monitored_users.remove(user)
            if user in self.last_tweets:
                del self.last_tweets[user]
            logger.info(f"Removed @{user[0]} from the monitored list.")
        else:
            logger.info(f"@{user[0]} is not in the monitored list.")
            
    async def get_user_id(self, username: str):
        """Get user information from username"""
        params = {
            "usernames": username,
            "user.fields": "id,username"
        }
        response = await self.make_request("users/by", params, self.headers_dy)
        
        if response and 'data' in response:
            user_data = response['data'][0]
            logger.info(f"User ID for @{username}: {user_data['id']}")
            return user_data['id']
        return None