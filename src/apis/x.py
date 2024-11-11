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