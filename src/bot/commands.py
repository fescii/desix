# bot/commands.py
# from telegram import Update
# from telegram import BotCommand
# from telegram.ext import ContextTypes, Application
# from src.db.queries import UserQueries, AccountQueries
from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes
import logging

logger = logging.getLogger(__name__)

def admin_only(func):
    """Decorator to restrict commands to admin users only"""
    @wraps(func)
    async def wrapped(self, update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = self.user_queries.get_user(str(update.effective_user.id))
        if not user or user.role not in ['admin', 'super_admin']:
            await update.message.reply_text("This command is restricted to administrators.")
            return
        return await func(self, update, context, *args, **kwargs)
    return wrapped

class Commands:
  def __init__(self, app, user_queries, account_queries, twitter_webhook, twitter_api):
    self.app = app
    self.user_queries = user_queries
    self.account_queries = account_queries
    self.twitter_webhook = twitter_webhook
    self.twitter_api = twitter_api
  
  async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /start command"""
    try:
      logger.info(f"Start command received from user {update.effective_user.id}")
      user = update.effective_user
      if not self.user_queries.get_user(user.id):
        self.user_queries.create_user(user.id, user.username, 'pending')
        await update.message.reply_text(
          "Welcome! Please request access using /request_access"
        )
        logger.info(f"New user {user.id} created")
        return
      
      await update.message.reply_text(
        "Welcome back! Use /help to see available commands"
      )
      logger.info(f"Existing user {user.id} welcomed back")
    except Exception as e:
      logger.error(f"Error in start command: {e}")
      await update.message.reply_text(
        "Sorry, there was an error processing your command. Please try again."
      )
  
  async def request_access(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /request_access command"""
    try:
      logger.info(f"Request access command received from user {update.effective_user.id}")
      user_id = update.effective_user.id
      if self.user_queries.create_access_request(user_id):
        await update.message.reply_text(
          "Access request submitted. An admin will review it."
        )
        # Notify admins
        await self.notify_admins(f"New access request from {user_id}")
        logger.info(f"Access request created for user {user_id}")
      else:
        await update.message.reply_text(
          "You already have an active access request."
        )
        logger.info(f"Duplicate access request from user {user_id}")
    except Exception as e:
      logger.error(f"Error in request_access command: {e}")
      await update.message.reply_text(
        "Sorry, there was an error processing your request. Please try again."
      )
  
  async def approve_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /approve_user command"""
    try:
      logger.info(f"Approve user command received from user {update.effective_user.id}")
      args = context.args
      if not args:
        await update.message.reply_text("Please provide a user ID to approve.")
        return

      user_id = args[0]
      user = self.user_queries.get_user(user_id)
      if not user:
        await update.message.reply_text("User not found.")
        return

      user.role = 'user'
      self.user_queries.session.commit()
      await update.message.reply_text(f"User {user_id} has been approved.")
      await self._send_message(user_id, "Your access request has been approved.")
      logger.info(f"User {user_id} approved")
    except Exception as e:
      logger.error(f"Error in approve_user command: {e}")
      await update.message.reply_text(
        "Sorry, there was an error processing your request. Please try again."
      )
      
  async def notify_admins(self, message: str):
    """Notify all admins with a message"""
    # Notify admins
    admin_ids = self.account_queries.get_admin_ids()
    for admin_id in admin_ids:
      await self._send_message(admin_id, message)
      
  async def _send_message(self, user_id: int, message: str):
    """Send a message to a specific user"""
    await self.app.bot.send_message(chat_id=user_id, text=message)
    
  async def deny_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /deny_user command"""
    try:
      logger.info(f"Deny user command received from user {update.effective_user.id}")
      args = context.args
      if not args:
        await update.message.reply_text("Please provide a user ID to deny.")
        return

      user_id = args[0]
      user = self.user_queries.get_user(user_id)
      if not user:
        await update.message.reply_text("User not found.")
        return

      self.user_queries.session.delete(user)
      self.user_queries.session.commit()
      await update.message.reply_text(f"User {user_id} has been denied.")
      await self._send_message(user_id, "Your access request has been denied.")
      logger.info(f"User {user_id} denied")
    except Exception as e:
      logger.error(f"Error in deny_user command: {e}")
      await update.message.reply_text(
        "Sorry, there was an error processing your request. Please try again."
      )
      
  async def promote_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /promote_admin command"""
    try:
      logger.info(f"Promote admin command received from user {update.effective_user.id}")
      args = context.args
      if not args:
        await update.message.reply_text("Please provide a user ID to promote.")
        return

      user_id = args[0]
      user = self.user_queries.get_user(user_id)
      if not user:
        await update.message.reply_text("User not found.")
        return

      user.role = 'admin'
      self.user_queries.session.commit()
      await update.message.reply_text(f"User {user_id} has been promoted to admin.")
      await self._send_message(user_id, "You have been promoted to admin.")
      logger.info(f"User {user_id} promoted to admin")
    except Exception as e:
      logger.error(f"Error in promote_admin command: {e}")
      await update.message.reply_text(
        "Sorry, there was an error processing your request. Please try again."
      )
      
  async def revoke_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /revoke_admin command"""
    try:
      logger.info(f"Revoke admin command received from user {update.effective_user.id}")
      args = context.args
      if not args:
        await update.message.reply_text("Please provide a user ID to revoke.")
        return

      user_id = args[0]
      user = self.user_queries.get_user(user_id)
      if not user:
        await update.message.reply_text("User not found.")
        return

      user.role = 'user'
      self.user_queries.session.commit()
      await update.message.reply_text(f"User {user_id} has been revoked from admin.")
      await self._send_message(user_id, "You have been revoked from admin.")
      logger.info(f"Admin rights revoked from user {user_id}")
    except Exception as e:
      logger.error(f"Error in revoke_admin command: {e}")
      await update.message.reply_text(
        "Sorry, there was an error processing your request. Please try again."
      )
  
  @staticmethod
  async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /help command"""
    try:
      logger.info(f"Help command received from user {update.effective_user.id}")
      await update.message.reply_text(
        "Available commands:\n"
        "/start - Start the bot\n"
        "/request_access - Request access\n"
        "/approve_user - Approve a user (admin only)\n"
        "/deny_user - Deny a user (admin only)\n"
        "/promote_admin - Promote a user to admin (admin only)\n"
        "/revoke_admin - Revoke admin status from a user (admin only)"
      )
      logger.info("Help message sent successfully")
    except Exception as e:
      logger.error(f"Error in help command: {e}")
      await update.message.reply_text(
        "Sorry, there was an error showing the help message. Please try again."
      )
      
  @staticmethod
  async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle unknown commands"""
    try:
      logger.info(f"Unknown command received from user {update.effective_user.id}")
      await update.message.reply_text("Sorry, I don't understand that command.")
      logger.info("Unknown command response sent")
    except Exception as e:
      logger.error(f"Error in unknown command: {e}")
      await update.message.reply_text(
        "Sorry, there was an error processing your command. Please try again."
      )
  
  @admin_only
  async def add_account(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /add_account command"""
    try:
      logger.info(f"Add account command received from user {update.effective_user.id}")
      
      if not context.args or len(context.args) != 1:
        await update.message.reply_text(
          "Please provide both Twitter username.\n"
          "Usage: /add_account <@username>"
        )
        return
      
      username = context.args
      twitter_id = self.twitter_api.get_user_id(username)
      username = username.strip('@')  # Remove @ if provided
      
      # if id is None, user does not exist
      if not twitter_id:
        await update.message.reply_text(
          f"User @{username} does not exist."
        )
        return
      
      # Check if an account already exists
      existing_account = self.account_queries.get_account_by_username(username)
      if existing_account:
        await update.message.reply_text(
          f"Account @{username} is already being monitored."
        )
        return
      
      # Add an account to a database
      account = self.account_queries.add_account(
        username=username,
        twitter_id=twitter_id,
        added_by=update.effective_user.id
      )
      
      # Subscribe to user's tweets via webhook
      subscription_success = await self.twitter_webhook.subscribe_to_user_events(twitter_id)
      
      if subscription_success:
        account.webhook_id = self.twitter_webhook.config.WEBHOOK_ID
        self.account_queries.session.commit()
        
        await update.message.reply_text(
          f"Successfully added @{username} to monitored accounts."
        )
        logger.info(f"Account @{username} added successfully by {update.effective_user.id}")
      else:
        # Rollback account creation if webhook subscription fails
        self.account_queries.session.delete(account)
        self.account_queries.session.commit()
        await update.message.reply_text(
          f"Failed to subscribe to @{username}'s tweets. Please try again."
        )
    
    except Exception as e:
      logger.error(f"Error in add_account command: {e}")
      await update.message.reply_text(
        "Sorry, there was an error adding the account. Please try again."
      )
  
  @admin_only
  async def remove_account(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /remove_account command"""
    try:
      logger.info(f"Remove account command received from user {update.effective_user.id}")
      
      if not context.args:
        await update.message.reply_text(
          "Please provide the Twitter username to remove.\n"
          "Usage: /remove_account <username>"
        )
        return
      
      username = context.args[0].strip('@')
      account = self.account_queries.get_account_by_username(username)
      
      if not account:
        await update.message.reply_text(
          f"Account @{username} is not currently monitored."
        )
        return
      
      # Unsubscribe from user's tweets
      if account.webhook_id:
        success = await self.twitter_webhook.unsubscribe_from_user_events(
          account.twitter_id
        )
        if not success:
          await update.message.reply_text(
            "Warning: Failed to unsubscribe from tweets, but removing from database."
          )
      
      # Remove from database
      self.account_queries.session.delete(account)
      self.account_queries.session.commit()
      
      await update.message.reply_text(
        f"Successfully removed @{username} from monitored accounts."
      )
      logger.info(f"Account @{username} removed by {update.effective_user.id}")
    
    except Exception as e:
      logger.error(f"Error in remove_account command: {e}")
      await update.message.reply_text(
        "Sorry, there was an error removing the account. Please try again."
      )
  
  @admin_only
  async def list_accounts(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /list_accounts command"""
    try:
      logger.info(f"List accounts command received from user {update.effective_user.id}")
      
      accounts = self.account_queries.get_all_accounts()
      
      if not accounts:
        await update.message.reply_text("No accounts are currently being monitored.")
        return
      
      message = "Monitored Twitter Accounts:\n\n"
      for account in accounts:
        message += f"• @{account.twitter_username}\n"
        message += f"  ID: {account.twitter_id}\n"
        message += f"  Added by: {account.added_by}\n\n"
      
      await update.message.reply_text(message)
      logger.info("Account list sent successfully")
    
    except Exception as e:
      logger.error(f"Error in list_accounts command: {e}")
      await update.message.reply_text(
        "Sorry, there was an error listing the accounts. Please try again."
      )
  
  async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /help command"""
    try:
      logger.info(f"Help command received from user {update.effective_user.id}")
      
      # Get user role
      user = self.user_queries.get_user(str(update.effective_user.id))
      is_admin = user and user.role in ['admin', 'super_admin']
      
      base_commands = (
        "Available commands:\n"
        "/start - Start the bot\n"
        "/request_access - Request access\n"
        "/help - Show help message"
      )
      
      admin_commands = (
        "\nAdmin commands:\n"
        "/approve_user - Approve a user\n"
        "/deny_user - Deny a user\n"
        "/promote_admin - Promote a user to admin\n"
        "/revoke_admin - Revoke admin status\n"
        "/add_account - Add Twitter account to monitor\n"
        "/remove_account - Remove monitored Twitter account\n"
        "/list_accounts - List all monitored accounts"
      ) if is_admin else ""
      
      await update.message.reply_text(base_commands + admin_commands)
      logger.info("Help message sent successfully")
    
    except Exception as e:
      logger.error(f"Error in help command: {e}")
      await update.message.reply_text(
        "Sorry, there was an error showing the help message. Please try again."
      )