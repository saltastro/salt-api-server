import os
from flask_cors import CORS
from app import create_app


app = create_app(os.getenv('FLASK_CONFIG') or 'default')
CORS(app)
