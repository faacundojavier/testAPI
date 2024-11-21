from flask import Blueprint, request, jsonify
from flask_restx import Namespace, Resource, fields
from models.role import Role
from models import db
from uuid import uuid4
from auth.auth_middleware import requires_auth
import json
import logging

# Configurar logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Handler para consola
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

role_bp = Blueprint('role', __name__)
role_api = Namespace('roles', description='Operaciones con roles')

# Swagger models
role_model = role_api.model('Role', {
    'name': fields.String(required=True, description='Nombre del rol'),
    'description': fields.String(required=True, description='Descripción del rol'),
    'roleType': fields.String(required=True, description='Tipo de rol (ej: admin, user)'),
    'scope': fields.String(required=True, description='Alcance del rol (ej: global, limited)'),
    'permissions': fields.List(fields.String, required=True, description='Lista de permisos del rol')
})

role_response = role_api.model('RoleResponse', {
    'id': fields.String(description='ID del rol'),
    'name': fields.String(description='Nombre del rol'),
    'description': fields.String(description='Descripción del rol'),
    'roleType': fields.String(description='Tipo de rol'),
    'scope': fields.String(description='Alcance del rol'),
    'permissions': fields.List(fields.String, description='Lista de permisos')
})

error_model = role_api.model('Error', {
    'message': fields.String(description='Mensaje de error')
})

# Flask-RESTX routes (Swagger API)
@role_api.route('')
class RoleList(Resource):
    @role_api.doc('list_roles')
    @role_api.response(200, 'Lista de roles obtenida exitosamente', [role_response])
    @role_api.response(500, 'Error interno del servidor', error_model)
    def get(self):
        """Obtener todos los roles"""
        try:
            logger.info('Iniciando obtención de todos los roles')
            roles = Role.query.all()
            role_list = []
            
            for role in roles:
                try:
                    permissions = role.permissions
                    if isinstance(permissions, str):
                        try:
                            permissions = json.loads(permissions)
                        except json.JSONDecodeError:
                            permissions = [permissions] if permissions else []
                    
                    role_dict = {
                        'id': role.id,
                        'name': role.name,
                        'description': role.description,
                        'roleType': role.roleType,
                        'scope': role.scope,
                        'permissions': permissions
                    }
                    role_list.append(role_dict)
                except Exception as e:
                    logger.error(f'Error al procesar rol {role.id}: {str(e)}')
                    return {'message': f'Error al procesar rol {role.id}: {str(e)}'}, 500
            
            logger.info(f'Se obtuvieron {len(role_list)} roles exitosamente')
            return role_list, 200
        except Exception as e:
            logger.error(f'Error al obtener roles: {str(e)}')
            return {'message': f'Error al obtener roles: {str(e)}'}, 500

    @role_api.doc('create_role')
    @role_api.expect(role_model)
    @role_api.response(201, 'Rol creado exitosamente', role_response)
    @role_api.response(400, 'Datos inválidos', error_model)
    @role_api.response(409, 'El rol ya existe', error_model)
    @role_api.response(500, 'Error interno del servidor', error_model)
    #@requires_auth
    def post(self):
        """Crear un nuevo rol"""
        try:
            data = role_api.payload
            logger.info(f'Intento de crear nuevo rol: {data.get("name")}')
            
            # Verificar campos requeridos
            required_fields = ["name", "description", "roleType", "scope", "permissions"]
            if not all(key in data for key in required_fields):
                logger.warning('Intento de crear rol con campos faltantes')
                return {'message': 'Faltan campos requeridos'}, 400
                
            # Verificar si el rol ya existe
            if Role.query.filter_by(name=data["name"]).first():
                logger.warning(f'Intento de crear rol con nombre duplicado: {data["name"]}')
                return {'message': 'Ya existe un rol con ese nombre'}, 409

            new_role = Role(
                id=str(uuid4()),
                name=data["name"],
                description=data["description"],
                roleType=data["roleType"],
                scope=data["scope"],
                permissions=json.dumps(data["permissions"])
            )
            
            db.session.add(new_role)
            db.session.commit()
            
            logger.info(f'Rol creado exitosamente: {new_role.id}')
            return {
                'id': new_role.id,
                'name': new_role.name,
                'description': new_role.description,
                'roleType': new_role.roleType,
                'scope': new_role.scope,
                'permissions': data["permissions"]
            }, 201
            
        except Exception as e:
            db.session.rollback()
            logger.error(f'Error al crear rol: {str(e)}')
            return {'message': f'Error al crear rol: {str(e)}'}, 500

@role_api.route('/<string:id>')
@role_api.param('id', 'ID del rol')
class RoleResource(Resource):
    @role_api.doc('modify_role')
    @role_api.expect(role_model)
    @role_api.response(200, 'Rol modificado exitosamente', role_response)
    @role_api.response(404, 'Rol no encontrado', error_model)
    @role_api.response(409, 'El nombre del rol ya existe', error_model)
    @role_api.response(500, 'Error interno del servidor', error_model)
    #@requires_auth
    def put(self, id):
        """Modificar un rol existente"""
        try:
            logger.info(f'Intento de modificar rol: {id}')
            role = Role.query.get(id)
            if not role:
                logger.warning(f'Intento de modificar rol inexistente: {id}')
                return {'message': 'Rol no encontrado'}, 404
                
            data = role_api.payload
            
            # Verificar si el nuevo nombre ya existe en otro rol
            existing_role = Role.query.filter_by(name=data["name"]).first()
            if existing_role and existing_role.id != id:
                logger.warning(f'Intento de modificar rol con nombre duplicado: {data["name"]}')
                return {'message': 'Ya existe un rol con ese nombre'}, 409

            # Actualizar campos
            updated = False
            for field in ['name', 'description', 'roleType', 'scope']:
                if field in data:
                    setattr(role, field, data[field])
                    updated = True
            
            if 'permissions' in data:
                role.permissions = json.dumps(data['permissions'])
                updated = True
                
            if updated:
                try:
                    db.session.commit()
                    logger.info(f'Rol modificado exitosamente: {id}')
                    return {
                        'id': role.id,
                        'name': role.name,
                        'description': role.description,
                        'roleType': role.roleType,
                        'scope': role.scope,
                        'permissions': json.loads(role.permissions)
                    }, 200
                except Exception as e:
                    db.session.rollback()
                    logger.error(f'Error al guardar modificaciones del rol: {str(e)}')
                    return {'message': f'Error al modificar el rol: {str(e)}'}, 500
            
            logger.info(f'No se realizaron cambios en el rol: {id}')
            return {'message': 'No se realizaron cambios'}, 200
            
        except Exception as e:
            db.session.rollback()
            logger.error(f'Error al modificar rol: {str(e)}')
            return {'message': f'Error al modificar rol: {str(e)}'}, 500

    @role_api.doc('delete_role')
    @role_api.response(200, 'Rol eliminado exitosamente')
    @role_api.response(404, 'Rol no encontrado', error_model)
    @role_api.response(500, 'Error interno del servidor', error_model)
    @requires_auth
    def delete(self, id):
        """Eliminar un rol"""
        try:
            logger.info(f'Intento de eliminar rol: {id}')
            role = Role.query.get(id)
            if not role:
                logger.warning(f'Intento de eliminar rol inexistente: {id}')
                return {'message': 'Rol no encontrado'}, 404
            
            db.session.delete(role)
            db.session.commit()
            
            logger.info(f'Rol eliminado exitosamente: {id}')
            return {'message': 'Rol eliminado exitosamente'}, 200
            
        except Exception as e:
            db.session.rollback()
            logger.error(f'Error al eliminar rol: {str(e)}')
            return {'message': f'Error al eliminar rol: {str(e)}'}, 500

# Blueprint routes (legacy API)
@role_bp.route('/api/roles', methods=['GET'])
def get_roles_legacy():
    """Legacy route for getting all roles"""
    return RoleList().get()

@role_bp.route('/api/roles', methods=['POST'])
#@requires_auth
def create_role_legacy():
    """Legacy route for creating a role"""
    return RoleList().post()

@role_bp.route('/api/roles/<string:id>', methods=['PUT'])
#@requires_auth
def modify_role_legacy(id):
    """Legacy route for modifying a role"""
    return RoleResource().put(id)

@role_bp.route('/api/roles/<string:id>', methods=['DELETE'])
#@requires_auth
def delete_role_legacy(id):
    """Legacy route for deleting a role"""
    return RoleResource().delete(id)