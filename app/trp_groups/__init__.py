from flask import Blueprint

bp = Blueprint("trp_groups", __name__)

from . import routes