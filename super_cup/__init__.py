from flask import Blueprint

bp = Blueprint("super_cup", __name__)

from super_cup import routes
