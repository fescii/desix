# bot/handlers.py
from telegram.ext import (
    CommandHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler
)
import logging

logger = logging.getLogger(__name__)

class BotHandlers:
    def __init__(self, commands):
        self.commands = commands

    def register_handlers(self, app):
        """Register all command and message handlers"""
        try:
            # Existing command handlers
            app.add_handler(CommandHandler("start", self.commands.start))
            app.add_handler(CommandHandler("help", self.commands.help))
            app.add_handler(CommandHandler("request_access", self.commands.request_access))
            app.add_handler(CommandHandler("approve_user", self.commands.approve_user))
            app.add_handler(CommandHandler("deny_user", self.commands.deny_user))
            app.add_handler(CommandHandler("promote_admin", self.commands.promote_admin))
            app.add_handler(CommandHandler("revoke_admin", self.commands.revoke_admin))

            # New account management handlers
            app.add_handler(CommandHandler("add_account", self.commands.add_account))
            app.add_handler(CommandHandler("remove_account", self.commands.remove_account))
            app.add_handler(CommandHandler("list_accounts", self.commands.list_accounts))

            # Start/stop monitoring commands
            app.add_handler(CommandHandler("start_monitoring", self.commands.start_monitoring))
            app.add_handler(CommandHandler("stop_monitoring", self.commands.stop_monitoring))

            # Handle unknown commands
            app.add_handler(MessageHandler(
                filters.COMMAND & ~filters.UpdateType.EDITED_MESSAGE,
                self.commands.unknown
            ))

            logger.info("All handlers registered successfully")
        except Exception as e:
            logger.error(f"Error registering handlers: {e}")
            raise