from functools import wraps
from flask import request, jsonify
import json
import requests
from jose import jwt
from jose.exceptions import JWTError, ExpiredSignatureError
from models.user import User
from config import Config

def get_token_auth_header():
    """Obtiene el token de autorización del header"""
    auth = request.headers.get("Authorization", None)
    if not auth:
        raise Exception({"code": "authorization_header_missing",
                        "description": "Authorization header is expected"})
    
    parts = auth.split()

    if parts[0].lower() != "bearer":
        raise Exception({"code": "invalid_header",
                        "description": "Authorization header must start with Bearer"})
    elif len(parts) == 1:
        raise Exception({"code": "invalid_header",
                        "description": "Token not found"})
    elif len(parts) > 2:
        raise Exception({"code": "invalid_header",
                        "description": "Authorization header must be Bearer token"})

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
                raise Exception('Unable to find appropriate key')

            # Verificar el token
            payload = jwt.decode(
                token,
                rsa_key,
                algorithms=['RS256'],
                audience=Config.AUTH0_AUDIENCE,
                issuer=f'https://{Config.AUTH0_DOMAIN}/'
            )

            # Debug: Imprimir el payload completo
            print("Token payload:", json.dumps(payload, indent=2))
            
            # Buscar el email en el payload
            email = payload.get('email')
            
            if not email:
                return jsonify({
                    "error": "No email claim in token",
                    "payload": payload  # Esto ayuda a debuggear
                }), 401

            user = User.query.filter_by(email=email).first()
            if not user:
                return jsonify({"error": f"User not found for email: {email}"}), 404
              
            if not user.has_role(Config.ADMIN_ROLE):
                return jsonify({"error": f"User {email} does not have admin role"}), 403

            return f(*args, **kwargs)

        except ExpiredSignatureError:
            return jsonify({"error": "Token has expired"}), 401
        except JWTError as e:
            return jsonify({"error": f"Invalid token: {str(e)}"}), 401
        except Exception as e:
            return jsonify({"error": str(e)}), 401

    return decorated