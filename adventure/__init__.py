from flask import Blueprint

bp = Blueprint("adventure", __name__)

from adventure import routes
