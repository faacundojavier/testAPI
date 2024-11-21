from . import db
import json

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True)
    userType = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(50), nullable=False)
    roles = db.Column(db.String(200), nullable=True)

    # Añadir serialización consistente
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'userType': self.userType,
            'status': self.status,
            "roles": json.loads(self.roles) if isinstance(self.roles, str) else self.roles
        }

    def has_role(self, role_name):
        user_roles = json.loads(self.roles) if self.roles else []
        return role_name in user_roles