from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_pymongo import PyMongo
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token
from flask_session import Session
from dotenv import load_dotenv
import os
from ocr import extract_text

load_dotenv()

app = Flask(__name__)

app.config['MONGO_URI'] = os.getenv('MONGO_URI')
mongo = PyMongo(app)

bcrypt = Bcrypt(app)
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')
jwt = JWTManager(app)

app.config['SESSION_TYPE'] = 'filesystem'
app.config['SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')
Session(app)

@app.route('/')
def home():
    """Landing page: Show full name if logged in, else show login page with movies."""
    if 'full_name' in session:
        movies = list(mongo.db.movie_details.find({}, {'_id': 0, 'movie_name': 1, 'thumbnail': 1}))
        return render_template('home.html', full_name=session['full_name'], movies=movies)
    return render_template('index.html')

@app.route('/movie_tickets')
def movie_tickets():
    """Show available movie tickets if logged in, else redirect to login."""
    if 'full_name' in session:
        movies = list(mongo.db.movie_details.find({}, {'_id': 0, 'movie_name': 1, 'thumbnail': 1, 'tickets_available': 1}))
        return render_template('movie_tickets.html', full_name=session['full_name'], movies=movies)
    return redirect(url_for('home'))

@app.route('/upload_page')
def upload_page():
    """Render the upload page."""
    return render_template('upload.html')

@app.route('/upload', methods=['POST'])
def upload_image():
    """API to extract text and QR code from an uploaded image."""
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']
    result = extract_text(file)  # Now returns both text & QR code image

    return jsonify(result)  # Return extracted text & QR code image

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

    if mongo.db.users.find_one({'$or': [{'username': username}, {'email': email}]}):
        return jsonify({'error': 'Username or email already exists'}), 400

    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

    user = {
        'full_name': full_name,
        'username': username,
        'email': email,
        'password': hashed_password,
        'dob': dob
    }
    mongo.db.users.insert_one(user)

    return render_template('index.html'),201

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

    session['username'] = username
    session['full_name'] = user['full_name']

    return redirect(url_for('home'))

@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('full_name', None)
    return redirect(url_for('home'))  

try:
    mongo.db.users.find_one()
    print("✅ MongoDB Connected Successfully!")
except Exception as e:
    print(f"❌ MongoDB connection failed: {e}")

if __name__ == '__main__':
    app.run(debug=True)
