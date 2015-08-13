'''
    Modified version of HTTP Basic Auth from Flask Snippets
    shown at http://flask.pocoo.org/snippets/8/
'''

from functools import wraps

from flask import request, Response
from werkzeug.security import check_password_hash

from realm.database import session
from realm.models import WebUser


def check_auth(username, password):
    """This function is called to check if a username /
    password combination is valid.
    """
    web_user = session.query(WebUser).filter_by(username=username).first()
    if web_user and check_password_hash(web_user.password, password):
        return True

def authenticate():
    """Sends a 401 response that enables basic auth"""
    return Response(
        'Could not verify your access level for that URL.\n'
        'You have to login with proper credentials', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'}
    )

def http_basic_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated
