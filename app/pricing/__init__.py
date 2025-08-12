from flask import Blueprint

bp = Blueprint("pricing_lists", __name__)

from . import routes