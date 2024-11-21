from . import db
import json

class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(200), nullable=False)
    roleType = db.Column(db.String(50), nullable=False)
    scope = db.Column(db.String(50), nullable=False)
    permissions = db.Column(db.String(500))

    def to_dict(self):
        try:
            # Manejo seguro de permisos
            permissions = self.permissions
            if isinstance(permissions, str):
                try:
                    permissions = json.loads(permissions)
                except json.JSONDecodeError:
                    permissions = [permissions]
            
            return {
                'id': self.id,
                'name': self.name,
                'description': self.description,
                'roleType': self.roleType,
                'scope': self.scope,
                'permissions': permissions
            }
        except Exception as e:
            print(f"Error en to_dict para rol {self.id}: {str(e)}")
            return {
                'id': self.id,
                'name': self.name,
                'description': self.description,
                'roleType': self.roleType,
                'scope': self.scope,
                'permissions': []
            }