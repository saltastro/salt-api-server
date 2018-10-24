"""Top-level package for SALT API Server."""

__author__ = """SALT Astronomy"""
__version__ = "0.1.0"

import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, current_app
from flask_sqlalchemy import SQLAlchemy
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from config import config


def log_exception(e):
    """
    Log an exception to Flask's logger and Sentry.

    Parameters
    ----------
    e : Exception
        The exception to log.

    """

    current_app.logger.exception(e)
    sentry_sdk.capture_exception(e)


db = SQLAlchemy()

from app.dataloader import ObservationLoader, ProposalLoader, BlockLoader  # noqa E402

loaders = {"proposal_loader": ProposalLoader(), 'observation_loader': ObservationLoader(),
           'block_loader': BlockLoader()}

# these imports can only happen here as otherwise there might be import errors
from app.auth import verify_token  # noqa E402
from app.main import main  # noqa E402
from app.graphql import graphql  # noqa E402


def create_app(config_name):
    app = Flask("__name__")
    app.config.from_object(config[config_name])

    db.init_app(app)

    # logging to file
    log_file_path = app.config["LOG_FILE_PATH"]
    if not log_file_path:
        raise Exception("The environment variable LOG_FILE_PATH is not defined")
    handler = RotatingFileHandler(log_file_path, maxBytes=1000000, backupCount=10)
    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s in %(module)s: %(" "message)s"
    )
    handler.setFormatter(formatter)
    app.logger.addHandler(handler)

    # setting up Sentry
    sentry_dsn = app.config["SENTRY_DSN"]
    if not sentry_dsn:
        app.logger.info(
            "No value is defined for SENTRY_DSN. Have you defined an "
            "environment variable with this name?"
        )
    sentry_sdk.init(dsn=sentry_dsn, integrations=[FlaskIntegration()])

    app.register_blueprint(graphql)
    app.register_blueprint(main)

    app.before_request(verify_token)

    return app
