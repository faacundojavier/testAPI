from flask import Flask, request, jsonify, redirect, session, url_for
from flask_restx import Api, Resource
from requests_oauthlib import OAuth2Session
from authlib.integrations.flask_client import OAuth
from config import Config
from models import db
from models.user import User
from models.role import Role
from controllers.user_controller import user_bp
from controllers.role_controller import role_bp
from controllers.role_controller import role_api
from controllers.user_controller import user_api
from auth.auth_middleware import AuthError
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

api = Api(app,
    version='1.0',
    title='User Management API',
    description='API para gestión de usuarios y roles',
    doc='/swagger',
    prefix='/api'
)

# Registrar namespaces
api.add_namespace(role_api)
api.add_namespace(user_api)

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
        "message": "Test API REST.",
        "login_url": "/login",
        "api_docs": "/swagger"
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

@app.errorhandler(AuthError)
def handle_auth_error(ex):
    response = jsonify(ex.error)
    response.status_code = ex.status_code
    return response

if __name__ == '__main__':
    app.run(debug=True)