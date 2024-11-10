from telegram.ext import ApplicationBuilder
from sqlalchemy.orm import Session
from src.config import Config

class TelegramAPI:
	def __init__(self, config: Config, session: Session):
		self.config = config
		self.session = session
		self._app = None
	
	def get_app(self):
		if not self._app:
			self._app = (
				ApplicationBuilder()
				.token(self.config.TELEGRAM_TOKEN)
				.build()
			)
		return self._app