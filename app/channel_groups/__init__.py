from flask import Blueprint

bp = Blueprint("channel_groups", __name__)

from . import routes