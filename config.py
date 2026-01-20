import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'pa-k-secret-key-2024-mku'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///data/members.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False