from . import db

class User(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    userType = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(50), nullable=False)
    roles = db.Column(db.String(200), nullable=True)