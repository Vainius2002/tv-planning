# app/campaigns/__init__.py
from flask import Blueprint
bp = Blueprint("campaigns", __name__)
from . import routes
