from flask import Flask

app = Flask(__name__)

# DB config
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///roles.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Role modeling
class Rol(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(200), nullable=False)
    roleType = db.Column(db.String(50), nullable=False)
    scope = db.Column(db.String(50), nullable=False)

# Create table
with app.app_context():
    db.create_all()

db = SQLAlchemy(app)

# Routing to root
@app.route('/')
def home():
    return "Probando out para API REST."

# Create role
@app.route('/createRol', methods=['POST'])
def create_rol():
    data = request.get_json()
    
    # Check required fields
    if not all(key in data for key in ("name", "description", "roleType", "scope")):
        return jsonify({"error": "Faltan campos requeridos"}), 400
    
    new_rol = Rol(
        name=data["name"],
        description=data["description"],
        roleType=data["roleType"],
        scope=data["scope"]
    )
    
    db.session.add(new_rol)  # Add new role to session
    db.session.commit()         # Save role to DB
    
    return jsonify({"id": new_rol.id, "name": new_rol.name}), 201

# Modify role
@app.route('/roles/<int:id>', methods=['PUT'])
def modify_rol(id):
    rol = Rol.query.get(id)
    
    if rol is None:
        return jsonify({"error": "Rol not found"}), 404
    
    data = request.get_json()
    
    # Actualizar los campos del rol
    if 'name' in data:
        rol.name = data['name']
    if 'description' in data:
        rol.description = data['description']
    if 'roleType' in data:
        rol.roleType = data['roleType']
    if 'scope' in data:
        rol.scope = data['scope']
    
    db.session.commit()  # Save role to DB
    
    return jsonify({"id": rol.id, "name": rol.name}), 200

# Return all roles
@app.route('/roles', methods=['GET'])
def get_roles():
    roles = Rol.query.all()  # Get all roles from DB
    result = []
    
    for rol in roles:
        result.append({
            "id": rol.id,
            "name": rol.name,
            "description": rol.description,
            "roleType": rol.roleType,
            "scope": rol.scope
        })
    
    return jsonify(result), 200  # Return list in JSON format

if __name__ == '__main__':
    app.run(debug=True)