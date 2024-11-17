# main.py
import asyncio
import logging
from contextlib import asynccontextmanager
import uvicorn
from fastapi import FastAPI, Request
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from telegram.ext import ApplicationBuilder

from config import Config
from bot.commands import Commands
from bot.handlers import BotHandlers
from db.queries import UserQueries, AccountQueries
from apis.x import TwitterManager
from db.models import Base

logging.basicConfig(
	level=logging.INFO,
	format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def setup_commands(app):
	"""Set up bot commands after the bot is fully initialized"""
	try:
		commands = [
			("start", "Start the bot"),
			("request_access", "Request access"),
			("approve_user", "Approve a user"),
			("deny_user", "Deny a user"),
			("promote_admin", "Promote a user to admin"),
			("revoke_admin", "Revoke admin rights from a user"),
			("add_account", "Add a Twitter account to monitor"),
			("remove_account", "Remove a Twitter account from monitoring"),
			("list_accounts", "List all monitored Twitter accounts"),
			("start_monitoring", "Start monitoring Twitter accounts"),
			("stop_monitoring", "Stop monitoring Twitter accounts"),
			("help", "Show help message")
		]
		await app.bot.set_my_commands(commands)
		logger.info("Bot commands setup completed")
	except Exception as e:
		logger.error(f"Error setting up commands: {e}")
		raise


@asynccontextmanager
async def lifespan(app: FastAPI):
	"""Manage application lifespan"""
	try:
		if hasattr(app.state, 'telegram_bot'):
			await app.state.telegram_bot.initialize()
			await app.state.telegram_bot.start()
			await setup_commands(app.state.telegram_bot)
			
			# Start polling in a background task
			app.state.polling_task = asyncio.create_task(
				app.state.telegram_bot.updater.start_polling()
			)
			logger.info("Started polling for updates")
		
		yield
	finally:
		if hasattr(app.state, 'telegram_bot'):
			if hasattr(app.state, 'polling_task'):
				app.state.polling_task.cancel()
				try:
					await app.state.polling_task
				except asyncio.CancelledError:
					pass
			await app.state.telegram_bot.stop()


async def create_app(app_config: Config):
	"""Create and configure the application"""
	fastapi_app = FastAPI(lifespan=lifespan)
	
	try:
		# Setup database
		engine = create_engine(app_config.DATABASE_URL)
		Base.metadata.create_all(engine)
		Session = sessionmaker(bind=engine)
		session = Session()
		
		# Initialize the telegram bot application with polling
		telegram_app = (
			ApplicationBuilder()
			.token(app_config.TELEGRAM_TOKEN)
			.build()
		)
		
		# Initialize queries
		user_queries = UserQueries(session, config=app_config)
		account_queries = AccountQueries(session)
		
		#initialize Twitter API
		twitter_api = TwitterManager(
			config=app_config,
			account_queries=account_queries,
			telegram_bot=telegram_app,
			user_queries=user_queries
		)
	
		# Initialize bot components
		commands = Commands(telegram_app, user_queries, account_queries, twitter_api)
		handlers = BotHandlers(commands)
		
		# Register handlers
		handlers.register_handlers(telegram_app)
		
		# Store telegram bot in-app state
		fastapi_app.state.telegram_bot = telegram_app
		fastapi_app.state.twitter_monitor = twitter_api
		
		return fastapi_app
	
	except Exception as exception:
		logger.error(f"Error creating application: {str(exception)}")
		raise

def run_app():
	try:
		config = Config.load_config()
		logger.info("Configuration loaded successfully")
		
		app = asyncio.run(create_app(config))
		
		logger.info("Starting application...")
		uvicorn.run(
			app,
			host="0.0.0.0",
			port=8000,
			log_level="info"
		)
	except Exception as e:
		logger.error(f"Application failed to start: {str(e)}")
		raise

if __name__ == "__main__":
	run_app()