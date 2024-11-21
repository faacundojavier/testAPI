from functools import wraps
from flask import request
from jose import jwt
from jose.exceptions import JWTError, ExpiredSignatureError
from models.user import User
from config import Config
import json
import requests

class AuthError(Exception):
    """Una clase personalizada para manejar errores de autenticación"""
    def __init__(self, error, status_code):
        super().__init__()
        self.error = {
            'message': error['description']
        }
        self.status_code = status_code

def get_token_auth_header():
    """Obtiene el token de autorización del header"""
    auth = request.headers.get("Authorization", None)
    if not auth:
        raise AuthError({
            "code": "authorization_header_missing",
            "description": "Se requiere el header de autorización"
        }, 401)
    
    parts = auth.split()

    if parts[0].lower() != "bearer":
        raise AuthError({
            "code": "invalid_header",
            "description": "El header de autorización debe comenzar con Bearer"
        }, 401)
    elif len(parts) == 1:
        raise AuthError({
            "code": "invalid_header",
            "description": "Token no encontrado"
        }, 401)
    elif len(parts) > 2:
        raise AuthError({
            "code": "invalid_header",
            "description": "El header de autorización debe ser Bearer token"
        }, 401)

    token = parts[1]
    return token

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            token = get_token_auth_header()
            
            # Obtener las claves JWKS de Auth0
            jwks = requests.get(f'https://{Config.AUTH0_DOMAIN}/.well-known/jwks.json').json()
            unverified_header = jwt.get_unverified_header(token)
            
            rsa_key = {}
            for key in jwks['keys']:
                if key['kid'] == unverified_header['kid']:
                    rsa_key = {
                        'kty': key['kty'],
                        'kid': key['kid'],
                        'n': key['n'],
                        'e': key['e']
                    }
                    break
       
            if not rsa_key:
                raise AuthError({
                    'code': 'invalid_header',
                    'description': 'No se pudo encontrar la clave apropiada'
                }, 401)

            try:
                # Verificar el token
                payload = jwt.decode(
                    token,
                    rsa_key,
                    algorithms=['RS256'],
                    audience=Config.AUTH0_AUDIENCE,
                    issuer=f'https://{Config.AUTH0_DOMAIN}/'
                )
            except ExpiredSignatureError:
                raise AuthError({
                    'code': 'token_expired',
                    'description': 'El token ha expirado'
                }, 401)
            except JWTError as e:
                raise AuthError({
                    'code': 'invalid_token',
                    'description': f'Token inválido: {str(e)}'
                }, 401)

            # Debug: Imprimir el payload completo
            print("Token payload:", json.dumps(payload, indent=2))
            
            # Buscar el email en el payload
            email = payload.get('email')
            if not email:
                raise AuthError({
                    'code': 'invalid_claims',
                    'description': 'No se encontró el email en el token'
                }, 401)

            user = User.query.filter_by(email=email).first()
            if not user:
                raise AuthError({
                    'code': 'invalid_user',
                    'description': f'Usuario no encontrado para el email: {email}'
                }, 401)
              
            if not user.has_role(Config.ADMIN_ROLE):
                raise AuthError({
                    'code': 'insufficient_permissions',
                    'description': f'El usuario {email} no tiene rol de administrador'
                }, 403)

            return f(*args, **kwargs)

        except AuthError as e:
            # Retornar directamente el diccionario y el código de estado
            return e.error, e.status_code
        except Exception as e:
            # Retornar directamente el diccionario y el código de estado
            return {'message': f'Error inesperado: {str(e)}'}, 500

    return decorated