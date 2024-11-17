from flask import Flask, request, jsonify, redirect, session, url_for
from flask_sqlalchemy import SQLAlchemy
from requests_oauthlib import OAuth2Session
from datadog import initialize, statsd
from uuid import uuid4
import uuid
import os

app = Flask(__name__)

# Inicializar integración Datadog
options = {
    'api_key': '4ca9b95447eb0d7b3f9ae8a271816db9',
    'app_key': 'fc7802f55f214723b0f11b138463030788cfcd68'
}

initialize(**options)

# Configuración de la base de datos
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///roles.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = "S3cR3tK3yT35t4p1"

# Inicializar SQLAlchemy
db = SQLAlchemy(app)

# Modelo para los roles
class Rol(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(200), nullable=False)
    roleType = db.Column(db.String(50), nullable=False)
    scope = db.Column(db.String(50), nullable=False)

# Modelo para los usuarios
class User(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    userType = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(50), nullable=False)
    roles = db.Column(db.String(200), nullable=True)  # Almacena roles como un string

# Crear las tablas en la base de datos
with app.app_context():
    db.create_all()

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
            id=str(uuid.uuid4()),  # Genera UUID
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

# Endpoint para crear un rol
@app.route('/roles', methods=['POST'])
def create_rol():
    data = request.get_json()
    
    # Verificar campos requeridos
    if not all(key in data for key in ("name", "description", "roleType", "scope")):
        statsd.increment('roles.create.failure')
        return jsonify({"error": "Faltan campos requeridos"}), 400
    
    new_rol = Rol(
        id=str(uuid4()),
        name=data["name"],
        description=data["description"],
        roleType=data["roleType"],
        scope=data["scope"]
    )
    
    db.session.add(new_rol)  # Agregar nuevo rol a la sesión
    db.session.commit()       # Guardar rol en la base de datos
    statsd.increment('roles.create.success')
    
    return jsonify({"id": new_rol.id, "name": new_rol.name}), 201

# Endpoint para modificar un rol
@app.route('/roles/<string:id>', methods=['PUT'])
def modify_rol(id):
    rol = Rol.query.get(id)
    
    if rol is None:
        statsd.increment('roles.modify.failure')
        return jsonify({"error": "Rol no encontrado"}), 404
    
    data = request.get_json()
    
    # Actualizar los campos del rol
    if 'name' in data:
        rol.name = data['name']
    if 'description' in data:
        rol.description = data['description']
    if 'roleType' in data:
        rol.roleType = data['roleType']
    if 'scope' in data:
        rol.scope = data['scope']
    
    db.session.commit()  # Guardar cambios en la base de datos
    
    statsd.increment('roles.modify.success')
    return jsonify({"id": rol.id, "name": rol.name}), 200

# Endpoint para borrar un rol
@app.route('/roles/<string:id>', methods=['DELETE'])
def delete_rol(id):
    rol = Rol.query.get(id)  # Buscar el rol por ID
    
    if rol is None:
        statsd.increment('roles.delete.failure')
        return jsonify({"error": "Rol no encontrado"}), 404
    
    db.session.delete(rol)   # Eliminar el rol de la sesión
    db.session.commit()       # Guardar los cambios en la base de datos
    
    statsd.increment('roles.delete.success')
    return jsonify({"message": "Rol eliminado exitosamente"}), 200

# Endpoint para obtener todos los roles
@app.route('/roles', methods=['GET'])
def get_roles():
    roles = Rol.query.all()  # Obtener todos los roles de la base de datos
    result = []
    
    for rol in roles:
        result.append({
            "id": rol.id,
            "name": rol.name,
            "description": rol.description,
            "roleType": rol.roleType,
            "scope": rol.scope
        })
    
    return jsonify(result), 200  # Retornar lista en formato JSON

# Endpoint para crear un usuario
@app.route('/users', methods=['POST'])
def create_user():
    data = request.get_json()
    
    # Verificar campos requeridos
    if not all(key in data for key in ("name", "userType", "status")):
        return jsonify({"error": "Faltan campos requeridos"}), 400
    
    user_id = str(uuid.uuid4())  # Genera un UUID aleatorio
    
    new_user = User(
        id=user_id,
        name=data["name"],
        userType=data["userType"],
        status=data["status"],
        roles=""  # Inicialmente sin roles asignados
    )
    
    try:
        db.session.add(new_user)  # Agregar nuevo usuario a la sesión
        db.session.commit()        # Guardar usuario en la base de datos
    except Exception as e:
        db.session.rollback()      # Revertir cambios si ocurre un error
        return jsonify({"error": "Error al crear el usuario: " + str(e)}), 500
    
    return jsonify({"id": new_user.id, "name": new_user.name}), 201

# Endpoint para eliminar un usuario
@app.route('/users/<string:id>', methods=['DELETE'])
def delete_user(id):
    user = User.query.get(id)  # Buscar el usuario por ID
    
    if user is None:
        return jsonify({"error": "Usuario no encontrado"}), 404
    
    db.session.delete(user)     # Eliminar el usuario de la sesión
    db.session.commit()          # Guardar cambios en la base de datos
    
    return jsonify({"message": "Usuario eliminado exitosamente"}), 200

# Endpoint para obtener todos los usuarios
@app.route('/users', methods=['GET'])
def get_users():
    users = User.query.all()  # Obtener todos los usuarios de la base de datos
    result = []
    
    for user in users:
        result.append({
            "id": user.id,
            "name": user.name,
            "userType": user.userType,
            "status": user.status,
            "roles": user.roles  # Incluir roles como cadena
        })
    
    return jsonify(result), 200  # Retornar lista en formato JSON

# Endpoint para asignar roles a un usuario
@app.route('/users/assignRole', methods=['POST'])
def assignRole():
    data = request.get_json()
    
    # Verificar que se hayan proporcionado el ID del usuario y el rol
    if not all(key in data for key in ("user_id", "role")):
        return jsonify({"error": "Faltan campos requeridos"}), 400
    
    user = User.query.get(data["user_id"])
    
    if user is None:
        return jsonify({"error": "Usuario no encontrado"}), 404
    
    # Verificar si el rol existe
    role = Rol.query.filter_by(name=data['role']).first()
    
    if role is None:
        return jsonify({"error": "Este rol no existe"}), 404
    
    current_roles = user.roles.split(",") if user.roles else []
    
    if data['role'] not in current_roles:
        current_roles.append(data['role'])
        user.roles = ",".join(current_roles)  
        
        db.session.commit()  
        
        return jsonify({"message": f"Rol '{data['role']}' asignado a {user.name}."}), 200
    else:
        return jsonify({"message": "El rol ya está asignado a este usuario."}), 200

# Endpoint para desasignar roles de un usuario
@app.route('/users/removeRole', methods=['POST'])
def removeRole():
    data = request.get_json()
    
    # Verificar que se hayan proporcionado el ID del usuario y el rol
    if not all(key in data for key in ("user_id", "role")):
        return jsonify({"error": "Faltan campos requeridos"}), 400
    
    user = User.query.get(data["user_id"])
    
    if user is None:
        return jsonify({"error": "Usuario no encontrado"}), 404
    
    current_roles = user.roles.split(",") if user.roles else []
    
    if data['role'] in current_roles:
        current_roles.remove(data['role'])
        user.roles = ",".join(current_roles)  
        
        db.session.commit()  
        
        return jsonify({"message": f"Rol '{data['role']}' desasignado de {user.name}."}), 200
    else:
        return jsonify({"message": "El rol no está asignado a este usuario."}), 200

@app.errorhandler(Exception)
def handle_exception(e):
    # Registrar el error usando logging
    return jsonify({"error": str(e)}), 500

# Métricas Datadog
statsd.increment('app.start')
statsd.increment('app.page_views', tags=["page:home"])
statsd.event('User Signup', 'A new user has signed up.', alert_type='success', tags=['user:signup'])
statsd.increment('app.errors', tags=["error_type:validation"])

if __name__ == '__main__':
    app.run(debug=True)