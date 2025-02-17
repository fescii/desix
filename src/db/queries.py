# db/queries.py
from sqlalchemy.orm import Session
from .models import User, MonitoredAccount, AccessRequest

class UserQueries:
	def __init__(self, session: Session, config):
		self.session = session
		# create an initial user using config.SUPER_ADMIN_ID
		user = self.get_user(telegram_id=config.SUPER_ADMIN_ID)
		if not user:
			user = self.create_user(
				telegram_id=config.SUPER_ADMIN_ID,
				username='admin',
				role='super_admin'
			)
			print(f'Created super admin: {user.username}')
		print(f'Super admin already exists: \n - username: {user.username} \n - telegram_id: {user.telegram_id}\n - role: {user.role}')
		

	def get_user(self, telegram_id: str):
		return self.session.query(User).filter_by(telegram_id=telegram_id).first()

	def create_user(self, telegram_id: str, username: str, role: str):
		user = User(telegram_id=telegram_id, username=username, role=role)
		self.session.add(user)
		self.session.commit()
		return user

	def create_access_request(self, user_id: int):
		if self.session.query(AccessRequest).filter_by(
				user_id=user_id,
				status='pending'
		).first():
			self.session.query(AccessRequest).filter_by(
				user_id=user_id,
				status='pending'
			).delete()

		request = AccessRequest(user_id=user_id, status='pending')
		self.session.add(request)
		self.session.commit()
		return True
	def get_admin_chat_ids(self):
		admins = self.session.query(User).filter(
			User.role.in_(['admin', 'super_admin'])
		).all()
		return [admin.telegram_id for admin in admins]

	def get_super_admin_chat_ids(self):
		admins = self.session.query(User).filter(
			User.role.in_(['super_admin'])
		).all()
		return [admin.telegram_id for admin in admins]

class AccountQueries:
	def __init__(self, session: Session):
		self.session = session
	
	def add_account(self, username: str, twitter_id: str, added_by: int):
		account = MonitoredAccount(
			twitter_username=username,
			twitter_id=twitter_id,
			added_by=added_by
		)
		self.session.add(account)
		self.session.commit()
		return account
	
	def get_account_by_username(self, twitter_username: str):
		return self.session.query(MonitoredAccount).filter_by(
			twitter_username=twitter_username
		).first()
	
	def get_account_by_twitter_id(self, twitter_id: str):
		return self.session.query(MonitoredAccount).filter_by(
			twitter_id=twitter_id
		).first()
	
	def get_all_accounts(self):
		return self.session.query(MonitoredAccount).all()
	
	def update_webhook_id(self, account_id: int, webhook_id: str):
		account = self.session.query(MonitoredAccount).get(account_id)
		if account:
			account.webhook_id = webhook_id
			self.session.commit()
			return True
		return False
	
	def get_admin_ids(self):
		admins = self.session.query(User).filter(
			User.role.in_(['admin', 'super_admin'])
		).all()
		return [admin.telegram_id for admin in admins]
	
	def get_accounts_by_admin(self, admin_id: int):
		return self.session.query(MonitoredAccount).filter_by(
			added_by=admin_id
		).all()

	def get_admin_chat_ids(self):
		admins = self.session.query(User).filter(
			User.role.in_(['admin', 'super_admin'])
		).all()
		return [admin.telegram_id for admin in admins]
	
	def get_super_admin_chat_ids(self):
		admins = self.session.query(User).filter(
			User.role.in_(['super_admin'])
		).all()
		return [admin.telegram_id for admin in admins]
