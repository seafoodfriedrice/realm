from os import environ
from flask import Flask

app = Flask(__name__)
config_path = environ.get("CONFIG_PATH", "realm.config.DevelopmentConfig")
app.config.from_object(config_path)

from . import views
from . import filters
from . import api
from . import login
