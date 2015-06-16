from datetime import date, datetime

from flask.ext.login import UserMixin
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects import postgresql
from sqlalchemy import Column, Boolean, Integer, String, Text, ForeignKey
from sqlalchemy import Date, DateTime

from realm.database import Base, engine


class Domain(Base):
    __tablename__ = "domains"

    id = Column(Integer, primary_key=True)
    domain_name = Column(String(48), nullable=False, unique=True)
    ip = Column(postgresql.INET, nullable=False)
    category = relationship('Category', backref='domain', uselist=False)
    status = relationship('Status', backref='domain')
    provider_id = Column(Integer, ForeignKey('providers.id'))
    exp_date = Column(Date, default=date(2020, 1, 1))
    is_monitored = Column(Boolean)
    is_active = Column(Boolean)
    whois_info_id = Column(Integer, ForeignKey('whois_info.id'))

    def as_dictionary(self):
        domain = {
            "id": self.id,
            "category": self.category.category_name.name,
            "domain_name": self.domain_name,
            "ip": self.ip,
            "provider": self.provider.provider_url,
            "status_type": self.status[-1].status_type,
            "status_time": str(self.status[-1].status_time),
            "is_monitored": self.is_monitored,
            "is_active": self.is_active
        }
        return domain


class Provider(Base):
    __tablename__ = "providers"

    id = Column(Integer, primary_key=True)
    provider_url = Column(String(64), nullable=False)
    domains = relationship('Domain', backref='provider')


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True)
    category_name_id = Column(Integer, ForeignKey('category_names.id'))
    domain_id = Column(Integer, ForeignKey('domains.id'))


class CategoryName(Base):
    __tablename__ = "category_names"

    id = Column(Integer, primary_key=True)
    name = Column(String(16))
    category = relationship('Category', backref='category_name')


class Status(Base):
    __tablename__ = "status"

    id = Column(Integer, primary_key=True)
    status_type = Column(String(32), nullable=False)
    status_time = Column(DateTime, default=datetime.now())
    domain_id = Column(Integer, ForeignKey('domains.id'))


class WhoisInfo(Base):
    __tablename__ = "whois_info"

    id = Column(Integer, primary_key=True)
    text = Column(Text)
    domain = relationship('Domain', backref='whois_info', uselist=False)
    lookup_time = Column(DateTime, default=datetime.now())


class WebUser(Base, UserMixin):
    __tablename__ = "web_users"

    id = Column(Integer, primary_key=True)
    username = Column(String(32), unique=True)
    password = Column(String(128))

Base.metadata.create_all(engine)
