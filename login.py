from flask.ext.login import LoginManager

from realm import app
from .database import session
from .models import WebUser

login_manager = LoginManager()
login_manager.init_app(app)

login_manager.login_view = "login"
login_manager.login_message_category = "danger"

@login_manager.user_loader
def load_user(id):
    return session.query(WebUser).get(int(id))
