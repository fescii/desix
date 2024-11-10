# hooks/twitter_webhook.py
from fastapi import Request, HTTPException
import hmac
import hashlib
import json
import logging
import base64
import requests
from typing import Optional

logger = logging.getLogger(__name__)

class TwitterWebhook:
	def __init__(self, account_queries, config, telegram_bot):
		self.account_queries = account_queries
		self.config = config
		self.telegram_bot = telegram_bot
		self.api_base = "https://api.twitter.com/1.1"
	
	async def register_webhook(self) -> bool:
		"""Register the webhook URL with Twitter"""
		try:
			url = f"{self.api_base}/account_activity/webhooks.json"
			webhook_url = f"{self.config.WEBHOOK_URL}/twitter"
			
			headers = self._get_auth_headers()
			response = requests.post(
				url,
				headers=headers,
				params={"url": webhook_url}
			)
			
			if response.status_code == 200:
				webhook_id = response.json()["id"]
				logger.info(f"Successfully registered webhook with ID: {webhook_id}")
				return webhook_id
			else:
				logger.error(f"Failed to register webhook: {response.text}")
				return None
		
		except Exception as e:
			logger.error(f"Error registering webhook: {str(e)}")
			return None
	
	async def subscribe_to_user_events(self, user_id: str) -> bool:
		"""Subscribe to a user's tweet events"""
		try:
			url = f"{self.api_base}/account_activity/webhooks/{self.config.WEBHOOK_ID}/subscriptions.json"
			headers = self._get_auth_headers()
			
			response = requests.post(url, headers=headers)
			
			if response.status_code == 204:
				logger.info(f"Successfully subscribed to events for user {user_id}")
				return True
			else:
				logger.error(f"Failed to subscribe to user events: {response.text}")
				return False
		
		except Exception as e:
			logger.error(f"Error subscribing to user events: {str(e)}")
			return False
	
	async def handle_crc_check(self, request: Request):
		"""Handle Twitter's CRC (Challenge-Response Check)"""
		try:
			crc_token = request.query_params.get('crc_token')
			if not crc_token:
				raise HTTPException(status_code=400, detail="Missing crc_token")
			
			validation = self._generate_crc_response(crc_token)
			return {"response_token": f"sha256={validation}"}
		
		except Exception as e:
			logger.error(f"Error handling CRC check: {str(e)}")
			raise HTTPException(status_code=500, detail="Error processing CRC check")
	
	async def handle_webhook(self, request: Request):
		"""Handle incoming webhook events from Twitter"""
		try:
			# Validate Twitter signature
			signature = request.headers.get("x-twitter-webhooks-signature")
			body = await request.body()
			
			if not signature or not self._validate_signature(signature, body):
				raise HTTPException(status_code=400, detail="Invalid signature")
			
			# Parse and process the webhook data
			data = json.loads(body)
			await self._process_event(data)
			return {"status": "ok"}
		
		except Exception as e:
			logger.error(f"Error handling webhook: {str(e)}")
			raise HTTPException(status_code=500, detail="Error processing webhook")
	
	def _validate_signature(self, signature: str, body: bytes) -> bool:
		"""Validate the webhook signature from Twitter"""
		expected = hmac.new(
			self.config.TWITTER_WEBHOOK_SECRET.encode(),
			body,
			hashlib.sha256
		).hexdigest()
		return hmac.compare_digest(signature, f"sha256={expected}")
	
	def _generate_crc_response(self, crc_token: str) -> str:
		"""Generate the response for Twitter's CRC check"""
		hmac_digest = hmac.new(
			self.config.TWITTER_WEBHOOK_SECRET.encode(),
			crc_token.encode(),
			hashlib.sha256
		).digest()
		return base64.b64encode(hmac_digest).decode()
	
	def _get_auth_headers(self) -> dict:
		"""Generate authentication headers for Twitter API requests"""
		return {
			"Authorization": f"Bearer {self.config.TWITTER_BEARER_TOKEN}",
			"Content-Type": "application/json"
		}
	
	async def _process_event(self, data: dict):
		"""Process incoming webhook events"""
		try:
			if 'tweet_create_events' in data:
				for tweet in data['tweet_create_events']:
					twitter_username = tweet['user']['screen_name']
					account = self.account_queries.get_account_by_username(twitter_username)
					
					if account:
						# Format and send tweet to Telegram
						message = self._format_tweet_message(tweet)
						await self._send_tweet_to_telegram(message, account.added_by)
		
		except Exception as e:
			logger.error(f"Error processing webhook event: {str(e)}")
	
	def _format_tweet_message(self, tweet: dict) -> str:
		"""Format tweet data into a readable message"""
		username = tweet['user']['screen_name']
		text = tweet['text']
		tweet_id = tweet['id_str']
		tweet_url = f"https://twitter.com/{username}/status/{tweet_id}"
		
		return (
			f"🐦 New tweet from @{username}\n\n"
			f"{text}\n\n"
			f"🔗 {tweet_url}"
		)
	
	async def _send_tweet_to_telegram(self, message: str, chat_id: int):
		"""Send formatted tweet to Telegram chat"""
		try:
			await self.telegram_bot.bot.send_message(
				chat_id=chat_id,
				text=message,
				disable_web_page_preview=True
			)
			logger.info(f"Tweet forwarded to Telegram chat {chat_id}")
		except Exception as e:
			logger.error(f"Error sending tweet to Telegram: {str(e)}")