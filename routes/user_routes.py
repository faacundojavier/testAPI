from flask import Blueprint, request, jsonify
from models.user import User
from models.role import Role
from models import db
from uuid import uuid4
from datadog import statsd

user_bp = Blueprint('user', __name__)

# Endpoint para crear un usuario
@user_bp.route('/users', methods=['POST'])
def create_user():
    data = request.get_json()
    
    # Verificar campos requeridos
    if not all(key in data for key in ("name", "userType", "status")):
        return jsonify({"error": "Faltan campos requeridos"}), 400
    
    new_user = User(
        id=str(uuid4()),
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
    if not all(key in data for key in ("user_id", "role")):
        return jsonify({"error": "Faltan campos requeridos"}), 400
    
    user = User.query.get(data["user_id"])
    
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