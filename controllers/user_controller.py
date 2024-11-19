from flask import Blueprint, request, jsonify
from models.user import User
from models.role import Role
from models import db
from uuid import uuid4
from datadog import statsd
from auth.auth_middleware import requires_auth
import json

user_bp = Blueprint('user', __name__)

# Endpoint para crear un usuario
@user_bp.route('/users', methods=['POST'])
@requires_auth
def create_user():
    data = request.get_json()
    
    # Verificar campos requeridos
    if not all(key in data for key in ("name", "email", "userType", "status")):
        return jsonify({"error": "Faltan campos requeridos"}), 400
    
    existing_user = User.query.filter_by(email=data["email"]).first()
    if existing_user:
        return jsonify({"error": "El correo electrónico ya está en uso."}), 409

    try:
        with db.session.begin_nested():
            new_user = User(
                id=str(uuid4()),
                name=data["name"],
                email=data["email"],
                userType=data["userType"],
                status=data["status"],
                roles=json.dumps([])
            )
            db.session.add(new_user)
        
        db.session.commit()
        
        return jsonify({
            "id": new_user.id,
            "name": new_user.name,
            "email": new_user.email
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# Endpoint para eliminar un usuario
@user_bp.route('/users/<string:id>', methods=['DELETE'])
def delete_user(id):
    user = User.query.get(id)  # Buscar el usuario por ID
    
    if user is None:
        return jsonify({"error": "Usuario no encontrado"}), 404
    
    db.session.delete(user)     # Eliminar el usuario de la sesión
    db.session.commit()          # Guardar cambios en la base de datos
    
    return jsonify({"message": "Usuario eliminado exitosamente"}), 200

# Endpoint para obtener todos los usuarios
@user_bp.route('/users', methods=['GET'])
def get_users():
    users = User.query.all()  # Obtener todos los usuarios de la base de datos
    result = []
    
    for user in users:
        result.append({
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "userType": user.userType,
            "status": user.status,
            "roles": user.roles  # Incluir roles como cadena
        })
    
    return jsonify(result), 200  # Retornar lista en formato JSON

# Endpoint para asignar roles a un usuario
@user_bp.route('/users/assignRole', methods=['POST'])
def assignRole():
    data = request.get_json()
    
    # Verificar que se hayan proporcionado el ID del usuario y el rol
    if not all(key in data for key in ("email", "role")):
        return jsonify({"error": "Faltan campos requeridos"}), 400
    
    user = User.query.get(data["email"])
    
    if user is None:
        return jsonify({"error": "Usuario no encontrado"}), 404
    
    # Verificar si el rol existe
    role = Role.query.filter_by(name=data['role']).first()
    
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
@user_bp.route('/users/removeRole', methods=['POST'])
def removeRole():
    data = request.get_json()
    
    # Verificar que se hayan proporcionado el ID del usuario y el rol
    if not all(key in data for key in ("email", "role")):
        return jsonify({"error": "Faltan campos requeridos"}), 400
    
    user = User.query.get(data["email"])
    
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