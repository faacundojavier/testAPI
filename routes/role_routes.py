from flask import Blueprint, request, jsonify
from models.role import Role
from models import db, session_scope
from uuid import uuid4
from datadog import statsd

role_bp = Blueprint('role', __name__)

# Endpoint para crear un rol
@role_bp.route('/roles', methods=['POST'])
def create_rol():
    data = request.get_json()
    
    # Verificar campos requeridos
    if not all(key in data for key in ("name", "description", "roleType", "scope")):
        statsd.increment('roles.create.failure')
        return jsonify({"error": "Faltan campos requeridos"}), 400
    
    new_role = Role(
        id=str(uuid4()),
        name=data["name"],
        description=data["description"],
        roleType=data["roleType"],
        scope=data["scope"]
    )
    
    db.session.add(new_role)  # Agregar nuevo rol a la sesión
    db.session.commit()       # Guardar rol en la base de datos
    statsd.increment('roles.create.success')
    
    return jsonify({"id": new_role.id, "name": new_role.name}), 201

# Endpoint para modificar un rol
@role_bp.route('/roles/<string:id>', methods=['PUT'])
def modify_rol(id):
    role = Role.query.get(id)
    
    if role is None:
        statsd.increment('roles.modify.failure')
        return jsonify({"error": "Rol no encontrado"}), 404
    
    data = request.get_json()
    
    # Actualizar los campos del rol
    updated = False
    if 'name' in data:
        role.name = data['name']
        updated = True
    if 'description' in data:
        role.description = data['description']
        updated = True
    if 'roleType' in data:
        role.roleType = data['roleType']
        updated = True
    if 'scope' in data:
        role.scope = data['scope']
        updated = True
    
    if updated:
        try:
            db.session.commit()  # Guardar cambios en la base de datos
            statsd.increment('roles.modify.success')
            return jsonify({"id": role.id, "name": role.name}), 200
        except Exception as e:
            db.session.rollback()  # Revertir cambios en caso de error
            statsd.increment('roles.modify.failure')
            return jsonify({"error": "Error al modificar el rol: " + str(e)}), 500
    else:
        return jsonify({"message": "No se realizaron cambios."}), 204

# Endpoint para borrar un rol
@role_bp.route('/roles/<string:id>', methods=['DELETE'])
def delete_role(id):
    with session_scope() as session:
        role = Role.query.get(id)
        if role is None:
            statsd.increment('roles.delete.failure')
            return jsonify({"error": "Rol no encontrado"}), 404
        
        session.delete(role)
        statsd.increment('roles.delete.success')
        return jsonify({"message": "Rol eliminado exitosamente"}), 200

# Endpoint para obtener todos los roles
@role_bp.route('/roles', methods=['GET'])
def get_roles():
    roles = Role.query.all()  # Obtener todos los roles de la base de datos
    result = []
    
    for role in roles:
        result.append({
            "id": role.id,
            "name": role.name,
            "description": role.description,
            "roleType": role.roleType,
            "scope": role.scope
        })
    
    return jsonify(result), 200  # Retornar lista en formato JSON