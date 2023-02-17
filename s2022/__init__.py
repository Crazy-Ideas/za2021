from flask import Blueprint

bp = Blueprint("s2022", __name__)

from s2022 import routes
