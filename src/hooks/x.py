import tweepy
import logging
import asyncio
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class TwitterMonitor:
  def __init__(self, twitter_api, account_queries, telegram_bot):
    self.is_monitoring = False
    self.account_queries = account_queries
    self.telegram_bot = telegram_bot
    self.twitter_api = twitter_api
  
  async def monitor(self):
    """Start monitoring Twitter accounts and forwarding new tweets to Telegram"""
    while self.is_monitoring:
      # Fetch monitored accounts
      accounts = self.account_queries.get_all_accounts()
      
      #if no accounts are found, send a text to telegram
      
      for account in accounts:
        tweets = self.twitter_api.fetch_user_tweets(
          account.twitter_username,
          since_id=account.last_checked_tweet_id
        )
        
        if tweets:
          self.twitter_api.process_tweets(tweets, account)
          account.last_checked_tweet_id = tweets[0].id_str
          self.account_queries.session.commit()
      
      # Wait before checking again
      await asyncio.sleep(self.config.TWITTER_POLL_INTERVAL)
      
  async def stop_monitoring(self, value):
    """Stop monitoring Twitter accounts"""
    self.is_monitoring = value
    