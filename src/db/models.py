# db/models.py
from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class User(Base):
	__tablename__ = 'users'

	id = Column(Integer, primary_key=True)
	telegram_id = Column(String, unique=True)
	username = Column(String)
	role = Column(String)  # super_admin, admin, user, pending


class MonitoredAccount(Base):
	__tablename__ = 'monitored_accounts'

	id = Column(Integer, primary_key=True)
	twitter_username = Column(String, unique=True)
	twitter_id = Column(String, unique=True)
	added_by = Column(Integer, ForeignKey('users.id'))
	webhook_id = Column(String)


class AccessRequest(Base):
	__tablename__ = 'access_requests'

	id = Column(Integer, primary_key=True)
	user_id = Column(Integer, ForeignKey('users.id'))
	status = Column(String)  # pending, approved, denied
	processed_by = Column(Integer, ForeignKey('users.id'))