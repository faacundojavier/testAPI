from flask import Flask, request, jsonify, redirect, session, url_for
from requests_oauthlib import OAuth2Session
from datadog import initialize, statsd
from config import Config
from models import db
from models.user import User
from models.role import Role
from routes.user_routes import user_bp
from routes.role_routes import role_bp
from uuid import uuid4
import logging

app = Flask(__name__)
app.config.from_object(Config)

# Inicializar DB
db.init_app(app)

# Inicializar integración Datadog
options = {
    'api_key': '4ca9b95447eb0d7b3f9ae8a271816db9',
    'app_key': 'fc7802f55f214723b0f11b138463030788cfcd68'
}

initialize(**options)

# Crear las tablas en la base de datos sólo si no existen
with app.app_context():
    db.create_all()

# Registrar los Blueprints para las rutas de usuario y rol
app.register_blueprint(user_bp)
app.register_blueprint(role_bp)

# Configuración de OAuth (GitHub)
GITHUB_CLIENT_ID = "Ov23lijiz4UwwYWeED8A"
GITHUB_CLIENT_SECRET = "26dedd471513cf44a7d1f51b08084c2f67237740"
GITHUB_OAUTH_URL = "https://github.com/login/oauth"
GITHUB_API_URL = "https://api.github.com/user"

# Ruta raíz
@app.route('/')
def home():
    return "Probando API REST."

@app.route('/login')
def login():
    github = OAuth2Session(GITHUB_CLIENT_ID)
    authorization_url, state = github.authorization_url(f"{GITHUB_OAUTH_URL}/authorize")
    session['oauth_state'] = state
    print("OAuth State:", session['oauth_state'])  # Mensaje de depuración
    return redirect(authorization_url)
@app.route('/callback')
def callback():
    if 'oauth_state' not in session:
        return jsonify({"error": "Estado OAuth no encontrado en la sesión."}), 400

    github = OAuth2Session(GITHUB_CLIENT_ID, state=session['oauth_state'])

    try:
        token = github.fetch_token(
            f"{GITHUB_OAUTH_URL}/access_token",
            client_secret=GITHUB_CLIENT_SECRET,
            authorization_response = request.url.replace("http://", "https://") # Forzar el uso de HTTPS
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    # Tomando user info
    user_info = github.get(GITHUB_API_URL).json()

    # Verificar si hay un error en la respuesta
    if 'message' in user_info and user_info['message'] == 'Requires authentication':
        return jsonify({"error": "No se pudo obtener información del usuario. Asegúrate de que el token es válido."}), 401

    user_name = user_info.get("login")  # Nombre de usuario en GitHub

    # Verifica si el usuario ya existe en la base de datos
    user = User.query.filter_by(name=user_name).first()

    if not user:
        # Si no existe, crear un nuevo usuario
        new_user = User(
            id=str(uuid4()),  # Genera UUID
            name=user_name,
            userType="Federated",
            status="Active",
            roles=""
        )
        db.session.add(new_user)
        db.session.commit()
        user_id = new_user.id
    else:
        user_id = user.id

    return jsonify({"message": "Inicio de sesion exitoso", "user_id": user_id})

@app.errorhandler(Exception)
def handle_exception(e):
    # Registrar el error usando logging
    logging.error(f"Error occurred: {str(e)}")
    return jsonify({"error": str(e)}), 500

# Métricas Datadog
statsd.increment('app.start')
statsd.increment('app.page_views', tags=["page:home"])
statsd.event('User Signup', 'A new user has signed up.', alert_type='success', tags=['user:signup'])
statsd.increment('app.errors', tags=["error_type:validation"])

if __name__ == '__main__':
    app.run(debug=True)