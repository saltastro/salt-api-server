import os

# Adapted from Miguel Grinberg: Flask Web Development, Second Edition (O'Reilly).

class Config:
    DEBUG = False
    TESTING = False
    JWT_SECRET_KEY = os.environ['JWT_SECRET_KEY']
    LOG_FILE_PATH = os.environ['LOG_FILE_PATH']
    SENTRY_DSN = os.getenv('SENTRY_DSN')

    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ['DEV_DATABASE_URI']


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ['TEST_DATABASE_URI']


class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.environ['DATABASE_URI']


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,

    'default': DevelopmentConfig
}
