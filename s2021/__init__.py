from flask import Blueprint

bp = Blueprint("s2021", __name__)

from s2021 import routes
