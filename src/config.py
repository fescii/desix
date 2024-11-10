import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
from dotenv import load_dotenv

@dataclass
class Config:
	TELEGRAM_TOKEN: str
	TWITTER_API_KEY: str
	TWITTER_API_SECRET: str
	TWITTER_ACCESS_TOKEN: str
	TWITTER_ACCESS_SECRET: str
	TWITTER_WEBHOOK_SECRET: str
	DATABASE_URL: str
	WEBHOOK_URL: str
	SUPER_ADMIN_ID: str

	@classmethod
	def load_config(cls) -> 'Config':
		"""Load configuration from environment file"""
		# Load environment variables from .env file
		env_path = Path('.') / '.env'
		load_dotenv(dotenv_path=env_path)


		# Required environment variables
		required_vars = [
			'TELEGRAM_TOKEN',
			'TWITTER_API_KEY',
			'TWITTER_API_SECRET',
			'TWITTER_ACCESS_TOKEN',
			'TWITTER_ACCESS_SECRET',
			'TWITTER_WEBHOOK_SECRET',
			'WEBHOOK_URL',
			'SUPER_ADMIN_ID'
		]

		missing_vars = [
			var for var in required_vars
			if not os.getenv(var)
		]

		if missing_vars:
			raise EnvironmentError(
				f"Missing required environment variables: {', '.join(missing_vars)}"
			)

		# Database URL defaults to SQLite if not provided
		database_url = os.getenv(
			'DATABASE_URL',
			f"sqlite:///{os.path.expanduser('~/.twitter-monitor.db')}"
		)

		return cls(
			TELEGRAM_TOKEN=os.getenv('TELEGRAM_TOKEN'),
			TWITTER_API_KEY=os.getenv('TWITTER_API_KEY'),
			TWITTER_API_SECRET=os.getenv('TWITTER_API_SECRET'),
			TWITTER_ACCESS_TOKEN=os.getenv('TWITTER_ACCESS_TOKEN'),
			TWITTER_ACCESS_SECRET=os.getenv('TWITTER_ACCESS_SECRET'),
			TWITTER_WEBHOOK_SECRET=os.getenv('TWITTER_WEBHOOK_SECRET'),
			DATABASE_URL=database_url,
			WEBHOOK_URL=os.getenv('WEBHOOK_URL'),
			SUPER_ADMIN_ID=os.getenv('SUPER_ADMIN_ID')
		)