from flask import Blueprint

main = Blueprint('main', __name__)

from . import errors  # noqa E402, F401
