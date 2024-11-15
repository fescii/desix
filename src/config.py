import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
from dotenv import load_dotenv

@dataclass
class Config:
	TELEGRAM_TOKEN: str
	DATABASE_URL: str
	TWITTER_POLL_INTERVAL: int
	SUPER_ADMIN_ID: str

	# Describefy
	DY_TWITTER_BEARER_TOKEN: str
	DY_TWITTER_API_KEY: str
	DY_TWITTER_API_KEY_SECRET: str
	DY_TWITTER_ACCESS_TOKEN: str
	DY_TWITTER_ACCESS_SECRET: str
	DY_TWITTER_CLIENT_ID: str
	DY_TWITTER_CLIENT_SECRET: str

	# Desix
	DX_TWITTER_BEARER_TOKEN: str
	DX_TWITTER_API_KEY: str
	DX_TWITTER_API_KEY_SECRET: str
	DX_TWITTER_CLIENT_ID: str
	DX_TWITTER_CLIENT_SECRET: str
	DX_TWITTER_ACCESS_TOKEN: str
	DX_TWITTER_ACCESS_SECRET: str

	@classmethod
	def load_config(cls) -> 'Config':
		"""Load configuration from environment file"""
		# Load environment variables from .env file
		env_path = Path('.') / '.env'
		load_dotenv(dotenv_path=env_path)


		# Required environment variables
		required_vars = [
			'TELEGRAM_TOKEN',

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
			DY_TWITTER_API_KEY=os.getenv('DY_TWITTER_API_KEY'),
			DY_TWITTER_API_KEY_SECRET=os.getenv('DY_TWITTER_API_KEY_SECRET'),
			DY_TWITTER_ACCESS_TOKEN=os.getenv('DY_TWITTER_ACCESS_TOKEN'),
			DY_TWITTER_ACCESS_SECRET=os.getenv('DY_TWITTER_ACCESS_SECRET'),
			DY_TWITTER_BEARER_TOKEN=os.getenv('DY_TWITTER_BEARER_TOKEN'),
			DY_TWITTER_CLIENT_ID=os.getenv('DY_TWITTER_CLIENT_ID'),
			DY_TWITTER_CLIENT_SECRET=os.getenv('DY_TWITTER_CLIENT_SECRET'),
			DX_TWITTER_API_KEY=os.getenv('DX_TWITTER_API_KEY'),
			DX_TWITTER_API_KEY_SECRET=os.getenv('DX_TWITTER_API_KEY_SECRET'),
			DX_TWITTER_ACCESS_TOKEN=os.getenv('DX_TWITTER_ACCESS_TOKEN'),
			DX_TWITTER_ACCESS_SECRET=os.getenv('DX_TWITTER_ACCESS_SECRET'),
			DX_TWITTER_BEARER_TOKEN=os.getenv('DX_TWITTER_BEARER_TOKEN'),
			DX_TWITTER_CLIENT_ID=os.getenv('DX_TWITTER_CLIENT_ID'),
			DX_TWITTER_CLIENT_SECRET=os.getenv('DX_TWITTER_CLIENT_SECRET'),
			TWITTER_POLL_INTERVAL=int(os.getenv('TWITTER_POLL_INTERVAL')),
			DATABASE_URL=database_url,
			SUPER_ADMIN_ID=os.getenv('SUPER_ADMIN_ID')
		)