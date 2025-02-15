from flask import Flask, render_template, request, jsonify
from flask_pymongo import PyMongo
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

app = Flask(__name__)

# MongoDB configuration
app.config['MONGO_URI'] = os.getenv('MONGO_URI')
mongo = PyMongo(app)

# Initialize Bcrypt and JWT
bcrypt = Bcrypt(app)
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')
jwt = JWTManager(app)

@app.route('/')
def login_page():
    return render_template('index.html')

@app.route('/signup')
def signup_page():
    return render_template('signup.html')

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json(silent=True) or request.form.to_dict()

    full_name = data.get('full_name')
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    confirm_password = data.get('confirm_password')
    dob = data.get('dob')

    if not (full_name and username and email and password and confirm_password and dob):
        return jsonify({'error': 'Missing fields'}), 400

    if password != confirm_password:
        return jsonify({'error': 'Passwords do not match'}), 400

    # Check if username or email already exists
    if mongo.db.users.find_one({'$or': [{'username': username}, {'email': email}]}):
        return jsonify({'error': 'Username or email already exists'}), 400

    # Hash password
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

    # Insert user into MongoDB
    user = {
        'full_name': full_name,
        'username': username,
        'email': email,
        'password': hashed_password,
        'dob': dob
    }
    mongo.db.users.insert_one(user)

    return jsonify({'message': 'User registered successfully'}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or request.form.to_dict()

    if not data:
        return jsonify({'error': 'Invalid request format'}), 400

    username = data.get('username')
    password = data.get('password')

    user = mongo.db.users.find_one({'username': username})
    
    if not user or not bcrypt.check_password_hash(user['password'], password):
        return jsonify({'error': 'Invalid username or password'}), 401

    access_token = create_access_token(identity=username)
    
    return jsonify({'message': 'Login successful', 'token': access_token}), 200

# Check if MongoDB connection works
try:
    mongo.db.users.find_one()
    print("✅ MongoDB Connected Successfully!")
except Exception as e:
    print(f"❌ MongoDB connection failed: {e}")

if __name__ == '__main__':
    app.run(debug=True)
