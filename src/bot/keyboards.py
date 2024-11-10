# bot/keyboards.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

class Keyboards:
  @staticmethod
  def get_admin_keyboard():
    keyboard = [
      [
        InlineKeyboardButton("Add Account", callback_data='add_account'),
        InlineKeyboardButton("Remove Account", callback_data='remove_account')
      ],
      [
        InlineKeyboardButton("Manage Users", callback_data='manage_users'),
        InlineKeyboardButton("View Requests", callback_data='view_requests')
      ],
      [
        InlineKeyboardButton("Approve User", callback_data='approve_user'),
        InlineKeyboardButton("Deny User", callback_data='deny_user')
      ],
      [
        InlineKeyboardButton("Promote Admin", callback_data='promote_admin'),
        InlineKeyboardButton("Revoke Admin", callback_data='revoke_admin')
      ],
      [
        InlineKeyboardButton("Back", callback_data='back'),
        # add help button
        InlineKeyboardButton("Help", callback_data='help')
      ],

    ]
    return InlineKeyboardMarkup(keyboard)