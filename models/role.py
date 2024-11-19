from . import db

class Role(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(200), nullable=False)
    roleType = db.Column(db.String(50), nullable=False)
    scope = db.Column(db.String(50), nullable=False)
    permissions = db.Column(db.String(500))