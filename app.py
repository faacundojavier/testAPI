from flask import Flask, request, jsonify, redirect, session, url_for
from requests_oauthlib import OAuth2Session
from authlib.integrations.flask_client import OAuth
from datadog import initialize, statsd
from config import Config
from models import db
from models.user import User
from models.role import Role
from controllers.user_controller import user_bp
from controllers.role_controller import role_bp
from uuid import uuid4
import json
import jwt
import requests
import logging
import os

app = Flask(__name__)
app.secret_key = Config.SECRET_KEY
app.config.from_object(Config)
# Inicializar DB
db.init_app(app)

def create_admin_user(app):
    with app.app_context():
        try:
            # Crear rol de administrador si no existe
            admin_role = Role.query.filter_by(name=Config.ADMIN_ROLE).first()
            if not admin_role:
                admin_role = Role(
                    id=str(uuid4()),
                    name=Config.ADMIN_ROLE,
                    description="Administrator role with full access",
                    roleType="admin",
                    scope="global",
                    permissions=json.dumps(['all'])
                )
                db.session.add(admin_role)
                db.session.flush()  # Asegurar que el rol se cree antes de crear el usuario

            # Crear usuario administrador si no existe
            admin_user = User.query.filter_by(email=Config.ADMIN_EMAIL).first()
            if not admin_user:
                admin_user = User(
                    id=str(uuid4()),
                    name="Admin",
                    email=Config.ADMIN_EMAIL,
                    userType="Admin",
                    status="Active",
                    roles=json.dumps([Config.ADMIN_ROLE])
                )
                db.session.add(admin_user)
            
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"Error creating admin user: {str(e)}")
            raise

# Crear las tablas sólo si no existen
with app.app_context():
    db.create_all()
    create_admin_user(app)

# Inicializar integración Datadog
options = {
    'api_key': '4ca9b95447eb0d7b3f9ae8a271816db9',
    'app_key': 'fc7802f55f214723b0f11b138463030788cfcd68',
    'host': os.getenv('HOSTNAME', 'my-api-service'),
    'statsd_host': 'dd-agent',
    'statsd_port': 8125
}

initialize(**options)

# Registrar los Blueprints para las rutas de usuario y rol
app.register_blueprint(user_bp)
app.register_blueprint(role_bp)

# Configuración de OAuth (Auth0)
oauth = OAuth(app)
auth0 = oauth.register(
    'auth0',
    client_id=Config.AUTH0_CLIENT_ID,
    client_secret=Config.AUTH0_CLIENT_SECRET,
    api_base_url=f'https://{Config.AUTH0_DOMAIN}',
    access_token_url=f'https://{Config.AUTH0_DOMAIN}/oauth/token',
    authorize_url=f'https://{Config.AUTH0_DOMAIN}/authorize',
    client_kwargs={
        'scope': 'openid profile email'
    },
    server_metadata_url=f'https://{Config.AUTH0_DOMAIN}/.well-known/openid-configuration'
)

# Ruta raíz
@app.route('/')
def home():
    return jsonify({
        "message": "Probando API REST.",
        "login_url": "/login"
    })

@app.route('/login')
def login():
    try:
        return auth0.authorize_redirect(
            redirect_uri=Config.AUTH0_CALLBACK_URL,
            audience=Config.AUTH0_AUDIENCE
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/callback')
def callback():
    try:
        token = auth0.authorize_access_token()
        user_info = auth0.get('userinfo').json()
        
        email = user_info.get('email')
        name = user_info.get('name') or email
        
        with db.session.begin_nested():  # Crear un savepoint
            user = User.query.filter_by(email=email).first()
            if not user:
                new_user = User(
                    id=str(uuid4()),
                    name=name,
                    email=email,
                    userType="Federated",
                    status="Active",
                    roles=json.dumps([])
                )
                db.session.add(new_user)
        
        db.session.commit()  # Commit final
            
        return jsonify({
            "message": "Login successful",
            "access_token": token['access_token']
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400

@app.errorhandler(Exception)
def handle_exception(e):
    statsd.increment('flask.error_count',
                    tags=['error_type:{}'.format(type(e).__name__),
                          'service:my-api-service',
                          'env:development'])
    return jsonify({"error": str(e)}), 500

# Métricas Datadog
statsd.increment('app.start')
statsd.increment('app.page_views', tags=["page:home"])
statsd.event('User Signup', 'A new user has signed up.', alert_type='success', tags=['user:signup'])
statsd.increment('app.errors', tags=["error_type:validation"])

if __name__ == '__main__':
    app.run(debug=True)