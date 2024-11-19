import os

class Config:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{os.path.join(BASE_DIR, "roles.db")}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    AUTH0_DOMAIN = 'dev-0768cjysl3zah84i.us.auth0.com'
    AUTH0_CLIENT_ID = 'OQpi36UI3pkaQp43RiNUw5U2LBZJLA9r'
    AUTH0_CLIENT_SECRET = 'XOwz78vBznfpDUkSY9KwwTgWtDiDXzvVxiFahBxv0YP5mW4GIh1k2mqI2ucNaaED'
    AUTH0_CALLBACK_URL = 'https://flask-app-1082402879404.us-central1.run.app/callback'
    AUTH0_AUDIENCE = 'https://flask-app-1082402879404.us-central1.run.app'
    SECRET_KEY = 'S3cR3tK3yT35t4p1'
    ADMIN_EMAIL = 'faacundojavier@gmail.com'
    ADMIN_ROLE = 'admin'