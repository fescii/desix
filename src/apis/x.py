import tweepy
from src.config import Config

class TwitterAPI:
	def __init__(self, config: Config):
		self.client = tweepy.Client(
			# consumer_key=config.TWITTER_API_KEY,
			# consumer_secret=config.TWITTER_API_SECRET,
			# access_token=config.TWITTER_ACCESS_TOKEN,
			bearer_token=config.TWITTER_BEARER_TOKEN,
			# access_token_secret=config.TWITTER_ACCESS_SECRET
		)
		
		# check if a client is authenticated
		if not self.client:
			raise Exception("Failed to authenticate Twitter API client")

	def get_client(self):
		return self.client
	
	def get_user_id(self, username):
		try:
			# Fetch user details
			user = self.client.get_user(username=username)
			# Extract and return the user ID
			return user.data.id
		except Exception as e:
			print(f"Error: {e}")
			print(e.response.text)
			return None


class TwitterAPIv2:
	def __init__(self, config):
		self.config = config
		self.client = self._authenticate()
	
	def _authenticate(self):
		"""Authenticate with Twitter API v2"""
		auth = tweepy.Client(
			bearer_token=self.config.TWITTER_BEARER_TOKEN
		)
		
		if not auth:
			raise Exception("Failed to authenticate Twitter API client")
		return auth
	
	def get_user_id(self, username):
		try:
			# Fetch user details
			user = self.client.get_user(username=username)
			# Extract and return the user ID
			return user.data.id
		except Exception as e:
			print(f"Error: {e}")
			print(e.response.text)
			return None
	
	def fetch_user_tweets(self, username: str, since_id: str = None):
		"""
		Fetch tweets for a given user, starting from the provided since_id (if given).
		Returns a list of tweepy.Status objects.
		"""
		try:
			user = self.client.get_user(screen_name=username)
			tweets = self.client.user_timeline(
				user_id=user.id,
				since_id=since_id,
				tweet_mode='extended',
				count=10
			)
			return tweets
		except tweepy.TweepyException as e:
			logger.error(f"Error fetching tweets for @{username}: {str(e)}")
			return []
	
	def process_tweets(self, tweets, account):
		"""Process a list of tweets and forward them to Telegram"""
		for tweet in tweets:
			message = self._format_tweet_message(tweet, account)
			self._send_tweet_to_telegram(message, account.added_by)
	
	def _format_tweet_message(self, tweet, account):
		"""Format tweet data into a readable message"""
		username = tweet.user.screen_name
		text = tweet.full_text
		tweet_url = f"https://twitter.com/{username}/status/{tweet.id_str}"
		
		return (
			f"🐦 New tweet from @{username}\n\n"
			f"{text}\n\n"
			f"🔗 {tweet_url}"
		)
	
	def _send_tweet_to_telegram(self, message, chat_id):
		"""Send formatted tweet to Telegram chat"""
		try:
			# Send a message to Telegram
			pass  # Implement Telegram message sending logic here
			logger.info(f"Tweet forwarded to Telegram chat {chat_id}")
		except Exception as e:
			logger.error(f"Error sending tweet to Telegram: {str(e)}")