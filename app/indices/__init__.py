from flask import Blueprint

bp = Blueprint('indices', __name__, url_prefix='/indices')

from . import routes