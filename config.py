import os

class DevelopmentConfig(object):
    SQLALCHEMY_DATABASE_URI = "postgresql://postgres:postgres@localhost:5432/realm"
    DEBUG = True
    SECRET_KEY = "77a61869bc93b509efe6db6b282b19f6"
