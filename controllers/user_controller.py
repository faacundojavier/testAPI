from flask import Blueprint, request, jsonify
from flask_restx import Namespace, Resource, fields, abort
from models.user import User
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

user_bp = Blueprint('user', __name__)
user_api = Namespace('users', description='Operaciones con usuarios')

# Swagger models
user_model = user_api.model('User', {
    'name': fields.String(required=True, description='Nombre del usuario'),
    'email': fields.String(required=True, description='Email del usuario'),
    'userType': fields.String(required=True, description='Tipo de usuario'),
    'status': fields.String(required=True, description='Estado del usuario')
})

user_response = user_api.model('UserResponse', {
    'id': fields.String(description='ID del usuario'),
    'name': fields.String(description='Nombre del usuario'),
    'email': fields.String(description='Email del usuario'),
    'userType': fields.String(description='Tipo de usuario'),
    'status': fields.String(description='Estado del usuario'),
    'roles': fields.List(fields.String, description='Lista de roles del usuario')
})

error_model = user_api.model('Error', {
    'message': fields.String(description='Mensaje de error')
})

role_assignment_model = user_api.model('RoleAssignment', {
    'email': fields.String(required=True, description='Email del usuario'),
    'role': fields.String(required=True, description='Nombre del rol a asignar/remover')
})

role_response_model = user_api.model('RoleResponse', {
    'message': fields.String(description='Mensaje de resultado'),
    'current_roles': fields.List(fields.String, description='Lista actualizada de roles')
})

# Flask-RESTX routes (Swagger API)
@user_api.route('')
class UserList(Resource):
    @user_api.doc('list_users')
    @user_api.marshal_list_with(user_response)
    def get(self):
        """Lista todos los usuarios"""
        try:
            logger.info('Iniciando obtención de todos los usuarios')
            users = User.query.all()
            return [user.to_dict() for user in users]
        except Exception as e:
            logger.error(f'Error al obtener usuarios: {str(e)}')
            return user_api.abort(500, {'message': f"Error al obtener usuarios: {str(e)}"})

    @user_api.doc('create_user')
    @user_api.expect(user_model)
    @user_api.response(201, 'Usuario creado exitosamente', user_response)
    @user_api.response(409, 'Email ya existe', error_model)
    @user_api.response(400, 'Datos inválidos', error_model)
    @user_api.response(500, 'Error interno del servidor', error_model)
    #@requires_auth
    def post(self):
        """Crea un nuevo usuario"""
        try:
            data = user_api.payload
            logger.info(f'Intento de creación de nuevo usuario con email: {data.get("email")}')
            
            # Verificar campos requeridos
            required_fields = ["name", "email", "userType", "status"]
            if not all(key in data for key in required_fields):
                logger.warning('Intento de creación de usuario con campos faltantes')
                return {'message': 'Faltan campos requeridos'}, 400
            
            # Verificar si el email ya existe
            existing_user = User.query.filter_by(email=data["email"]).first()
            if existing_user:
                logger.warning(f'Intento de creación usuario con email duplicado: {data["email"]}')
                return {'message': 'El correo electrónico ya está en uso'}, 409

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
            logger.info(f'Usuario creado exitosamente: {new_user.id}')

            return new_user.to_dict(), 201
            
        except Exception as e:
            db.session.rollback()
            logger.error(f'Error al crear usuario: {str(e)}')
            return {'message': f"Error al crear usuario: {str(e)}"}, 500

@user_api.route('/<string:id>')
@user_api.param('id', 'ID del usuario')
class UserResource(Resource):
    @user_api.doc('delete_user')
    @user_api.response(200, 'Usuario eliminado exitosamente')
    @user_api.response(404, 'Usuario no encontrado', error_model)
    @user_api.response(500, 'Error interno del servidor', error_model)
    @requires_auth
    def delete(self, id):
        """Eliminar un usuario"""
        try:
            logger.info(f'Intento de eliminación de usuario: {id}')
            user = User.query.get(id)
            if not user:
                logger.warning(f'Intento de eliminación de usuario inexistente: {id}')
                return {'message': 'Usuario no encontrado'}, 404
            
            db.session.delete(user)
            db.session.commit()
            
            logger.info(f'Usuario eliminado exitosamente: {id}')
            return {'message': 'Usuario eliminado exitosamente'}, 200
            
        except Exception as e:
            db.session.rollback()
            logger.error(f'Error al eliminar usuario: {str(e)}')
            return {'message': f"Error al eliminar usuario: {str(e)}"}, 500

@user_api.route('/role')
class UserRoleManagement(Resource):
    @user_api.doc('assign_role')
    @user_api.expect(role_assignment_model)
    @user_api.response(200, 'Rol asignado o ya existente', role_response_model)
    @user_api.response(400, 'Datos inválidos', error_model)
    @user_api.response(404, 'Usuario o rol no encontrado', error_model)
    @user_api.response(500, 'Error interno del servidor', error_model)
    #@requires_auth
    def post(self):
        """Asignar un rol a un usuario"""
        try:
            data = user_api.payload
            logger.info(f'Intento de asignar rol a usuario: {data.get("email")}')

            # Verificar campos requeridos
            if not all(key in data for key in ("email", "role")):
                logger.warning('Intento de asignar rol con campos faltantes')
                return {'message': 'Faltan campos requeridos'}, 400
            
            # Buscar usuario
            user = User.query.filter_by(email=data["email"]).first()
            if not user:
                logger.warning(f'Intento de asignar rol a usuario inexistente: {data["email"]}')
                return {'message': 'Usuario no encontrado'}, 404
            
            # Verificar si el rol existe
            role = Role.query.filter_by(name=data['role']).first()
            if not role:
                logger.warning(f'Intento de asignar rol inexistente: {data["role"]}')
                return {'message': 'Este rol no existe'}, 404
            
            # Manejar la conversión de roles con try-except específico
            try:
                current_roles = json.loads(user.roles) if isinstance(user.roles, str) else []
            except (json.JSONDecodeError, TypeError):
                logger.warning(f'Error al decodificar roles actuales para usuario: {user.email}')
                current_roles = user.roles.split(",") if user.roles else []
            except Exception as e:
                return {'message': f'Error al procesar roles actuales: {str(e)}'}, 500
            
            if data['role'] not in current_roles:
                current_roles.append(data['role'])
                user.roles = json.dumps(current_roles)
                
                try:
                    db.session.commit()
                    logger.info(f'Rol {data["role"]} asignado exitosamente a usuario {user.email}')
                    return {
                        'message': f"Rol '{data['role']}' asignado a {user.name}",
                        'current_roles': current_roles
                    }, 200
                except Exception as e:
                    db.session.rollback()
                    logger.error(f'Error al actualizar roles: {str(e)}')
                    return {'message': f"Error al actualizar roles: {str(e)}"}, 500
            
            logger.info(f'Rol {data["role"]} ya estaba asignado a usuario {user.email}')
            return {
                                'message': "El rol ya está asignado a este usuario",
                'current_roles': current_roles
            }, 200
            
        except Exception as e:
            db.session.rollback()
            return {'message': f"Error inesperado: {str(e)}"}, 500
            
    @user_api.doc('remove_role')
    @user_api.expect(role_assignment_model)
    @user_api.response(200, 'Rol removido o no existente', role_response_model)
    @user_api.response(400, 'Datos inválidos', error_model)
    @user_api.response(404, 'Usuario no encontrado', error_model)
    @user_api.response(500, 'Error interno del servidor', error_model)
    #@requires_auth
    def delete(self):
        """Remover un rol de un usuario"""
        try:
            data = user_api.payload
            logger.info(f'Intento de remover rol de usuario: {data.get("email")}')

            if not all(key in data for key in ("email", "role")):
                logger.warning('Intento de remover rol con campos faltantes')
                return {'message': 'Faltan campos requeridos'}, 400
            
            user = User.query.filter_by(email=data["email"]).first()
            if not user:
                logger.warning(f'Intento de remover rol de usuario inexistente: {data["email"]}')
                return {'message': 'Usuario no encontrado'}, 404
            
            # Manejar la conversión de roles con try-except específico
            try:
                current_roles = json.loads(user.roles) if isinstance(user.roles, str) else []
            except (json.JSONDecodeError, TypeError):
                logger.warning(f'Error al decodificar roles actuales para usuario: {user.email}')
                current_roles = user.roles.split(",") if user.roles else []
            except Exception as e:
                return {'message': f'Error al procesar roles actuales: {str(e)}'}, 500
            
            if data['role'] in current_roles:
                current_roles.remove(data['role'])
                user.roles = json.dumps(current_roles)
                
                try:
                    db.session.commit()
                    logger.info(f'Rol {data["role"]} removido exitosamente de usuario {user.email}')
                    return {
                        'message': f"Rol '{data['role']}' removido de {user.name}",
                        'current_roles': current_roles
                    }, 200
                except Exception as e:
                    db.session.rollback()
                    logger.error(f'Error al actualizar roles: {str(e)}')
                    return {'message': f"Error al actualizar roles: {str(e)}"}, 500
            
            logger.info(f'Rol {data["role"]} no estaba asignado a usuario {user.email}')
            return {
                'message': "El rol no está asignado a este usuario",
                'current_roles': current_roles
            }, 200
            
        except Exception as e:
            db.session.rollback()
            return {'message': f"Error inesperado: {str(e)}"}, 500

# Blueprint routes (legacy API)
@user_bp.route('/api/users', methods=['POST'])
#@requires_auth
def create_user_legacy():
    try:
        data = request.get_json()
        
        # Verificar campos requeridos
        required_fields = ["name", "email", "userType", "status"]
        if not all(key in data for key in required_fields):
            return jsonify({"message": "Faltan campos requeridos"}), 400
        
        # Verificar si el email ya existe
        if User.query.filter_by(email=data["email"]).first():
            return jsonify({"message": "El correo electrónico ya está en uso"}), 409

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
        
        return jsonify(new_user.to_dict()), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": str(e)}), 500

@user_bp.route('/api/users', methods=['GET'])
def get_users_legacy():
    try:
        users = User.query.all()
        return jsonify([user.to_dict() for user in users]), 200
    except Exception as e:
        return jsonify({"message": str(e)}), 500

@user_bp.route('/api/users/<string:id>', methods=['DELETE'])
#@requires_auth
def delete_user_legacy(id):
    try:
        user = User.query.get(id)
        if not user:
            return jsonify({"message": "Usuario no encontrado"}), 404
        
        db.session.delete(user)
        db.session.commit()
        
        return jsonify({"message": "Usuario eliminado exitosamente"}), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": str(e)}), 500

@user_bp.route('/api/users/assignRole', methods=['POST'])
#@requires_auth
def assign_role_legacy():
    """Legacy route for assigning role"""
    return UserRoleManagement().post()

@user_bp.route('/api/users/removeRole', methods=['POST'])
#@requires_auth
def remove_role_legacy():
    """Legacy route for removing role"""
    return UserRoleManagement().delete()