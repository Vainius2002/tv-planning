from flask import Blueprint

bp = Blueprint("contacts", __name__)

from . import routes