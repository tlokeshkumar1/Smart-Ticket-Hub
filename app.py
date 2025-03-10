from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_pymongo import PyMongo
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token
from flask_session import Session
from dotenv import load_dotenv
import os
from ocr import extract_text
from datetime import datetime
import pytz
from pymongo import errors
from chatbot import generate_response

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
    """Landing page with active tickets"""
    if 'full_name' in session:
        username = session['username']
        
        active_tickets = list(mongo.db.buyed_movie_ticket.find({
            'buyed_username': username
        }, {'_id': 0, 'ticket_details': 1, 'buyed_date_time': 1}))
        
        movies = list(mongo.db.movie_details.find({}, {'_id': 0, 'movie_name': 1, 'thumbnail': 1}))
        
        return render_template('home.html', 
                            full_name=session['full_name'],
                            movies=movies,
                            tickets=active_tickets)
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
    session['access_token'] = access_token

    return redirect(url_for('home'))

@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('full_name', None)
    return redirect(url_for('home'))  

@app.route('/view_ticket/<booking_id>')
def view_ticket(booking_id):
    """Display detailed view of a purchased ticket with thumbnail"""
    if 'username' not in session:
        return redirect(url_for('login'))

    ticket = mongo.db.buyed_movie_ticket.find_one({
        'ticket_details.booking_id': booking_id,
        'buyed_username': session['username']
    })
    
    if not ticket:
        return render_template('error.html', 
                             message="Ticket not found or unauthorized access"), 404

    movie_data = mongo.db.movie_details.find_one(
        {'movie_name': ticket['ticket_details']['movie_name']},
        {'thumbnail': 1, '_id': 0}
    )
    
    return render_template('buyed_movie_ticket.html', 
                         ticket=ticket,
                         thumbnail=movie_data.get('thumbnail') if movie_data else None)

@app.route('/movie_tickets')
def movie_tickets():
    """Show available movie tickets if logged in, else redirect to login."""
    if 'full_name' in session:
        movies = list(mongo.db.movie_details.find({}, {'_id': 0, 'movie_name': 1, 'thumbnail': 1}))
        
        for movie in movies:
            movie['available_tickets'] = mongo.db.movie_tickets.count_documents({
                'movie_name': movie['movie_name']
            })
            
        return render_template('movie_tickets.html', 
                             full_name=session['full_name'], 
                             movies=movies)
    return redirect(url_for('home'))

@app.route('/balance', methods=['GET', 'POST'])
def balance():
    """Handles balance display and add money functionality."""
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']
    user_balance = mongo.db.balance.find_one({'username': username})

    if not user_balance:
        user_balance = {'username': username, 'balance': 0, 'transactions': []}
        mongo.db.balance.insert_one(user_balance)

    if request.method == 'POST':
        amount = request.form.get('amount')
        if amount and amount.isdigit():
            amount = int(amount)
            new_balance = user_balance['balance'] + amount

            utc_now = datetime.utcnow()
            ist = pytz.timezone('Asia/Kolkata')
            ist_now = utc_now.replace(tzinfo=pytz.utc).astimezone(ist)

            mongo.db.balance.update_one(
                {'username': username},
                {
                    '$set': {'balance': new_balance},
                    '$push': {
                        'transactions': {
                            'type': 'credit',
                            'amount': amount,
                            'timestamp': ist_now.strftime('%d-%m-%Y %I:%M:%S %p')  # Correct IST format
                        }
                    }
                }
            )
            return redirect(url_for('balance'))

    user_balance = mongo.db.balance.find_one({'username': username})
    
    return render_template('balance.html', balance=user_balance['balance'])

@app.route('/balance_history')
def balance_history():
    """Handles transaction history display with movie details if applicable."""
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']
    user_balance = mongo.db.balance.find_one({'username': username})

    transactions = user_balance.get('transactions', []) if user_balance else []

    transactions.sort(key=lambda x: x['timestamp'], reverse=True)

    return render_template('balance_history.html', transactions=transactions)

@app.route('/upload_page')
def upload_page():
    if 'full_name' in session:
        """Render the upload page with the movie name if provided."""
        movie_name = request.args.get('movie', 'a movie')  
        session['expected_movie_name'] = movie_name
        return render_template('upload.html', movie_name=movie_name)
    return redirect(url_for('home'))

@app.route('/upload', methods=['POST'])
def upload_image():
    """API to extract text and QR code from an uploaded image."""
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']
    result = extract_text(file)  
    
    return jsonify(result)

@app.route('/sell_ticket', methods=['POST'])
def sell_ticket():
    """Store complete ticket data including QR code in database."""
    if 'username' not in session:
        return jsonify({"error": "Please login to sell tickets"}), 401

    ticket_data = request.get_json()
    if not ticket_data:
        return jsonify({"error": "No data provided"}), 400

    required_fields = ["movie_name", "booking_id", "qr_code_image"]
    missing_fields = [field for field in required_fields if field not in ticket_data]
    
    if missing_fields:
        return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400

    expected_movie = session.get('expected_movie_name')
    if expected_movie and ticket_data["movie_name"].lower().strip() != expected_movie.lower().strip():
        return jsonify({
            "error": f"Movie mismatch. Expected: {expected_movie}, Got: {ticket_data['movie_name']}"
        }), 400

    booking_id = ticket_data["booking_id"]
    try:
        if mongo.db.movie_tickets.find_one({"booking_id": booking_id}):
            return jsonify({
                "error": "Duplicate booking ID",
                "suggestion": "Please verify ticket authenticity"
            }), 409

        ticket_data.update({
            "upload_date": datetime.utcnow(),
            "seller_username": session['username'],
            "status": "available"
        })
        ticket_data.pop("_id", None) 

        result = mongo.db.movie_tickets.insert_one(ticket_data)
        if result.inserted_id:
            return jsonify({
                "message": "Ticket successfully listed for sale",
                "ticket_id": str(result.inserted_id),
                "redirect": url_for('movie_tickets') 
            }), 201
        
        return jsonify({"error": "Failed to save ticket"}), 500

    except errors.PyMongoError as e:
        return jsonify({
            "error": "Database error",
            "details": str(e)
        }), 500

@app.route('/buy_ticket', methods=['POST'])
def buy_ticket():
    if 'username' not in session:
        return jsonify({'error': 'Login required'}), 401

    buyer_username = session['username']
    data = request.get_json()
    booking_id = data.get("booking_id")

    ticket = mongo.db.movie_tickets.find_one({"booking_id": booking_id})
    if not ticket:
        return jsonify({'error': 'Ticket not found'}), 404

    if ticket['username'] == buyer_username:
        return jsonify({'error': 'You cannot buy your own ticket'}), 403

    buyer_balance = mongo.db.balance.find_one({'username': buyer_username})
    ticket_amount = float(ticket['total_amount'])
    if not buyer_balance or buyer_balance.get('balance', 0) < ticket_amount:
        return jsonify({'error': 'Insufficient balance'}), 400

    ist_now = datetime.utcnow().replace(tzinfo=pytz.utc).astimezone(pytz.timezone('Asia/Kolkata'))
    mongo.db.balance.update_one(
        {'username': buyer_username},
        {
            '$set': {'balance': buyer_balance['balance'] - ticket_amount},
            '$push': {
                'transactions': {
                    'type': 'debit',
                    'amount': ticket_amount,
                    'timestamp': ist_now.strftime('%d-%m-%Y %I:%M:%S %p'),
                    'description': f"Bought ticket for {ticket['movie_name']}"
                }
            }
        }
    )

    seller_username = ticket['username']
    mongo.db.balance.update_one(
        {'username': seller_username},
        {
            '$inc': {'balance': ticket_amount},
            '$push': {
                'transactions': {
                    'type': 'credit',
                    'amount': ticket_amount,
                    'timestamp': ist_now.strftime('%d-%m-%Y %I:%M:%S %p'),
                    'description': f"Sold ticket of {ticket['movie_name']}"
                }
            }
        },
        upsert=True 
    )

    buyed_ticket = {
        "seller_username": seller_username,
        "buyed_username": buyer_username,
        "buyed_date_time": ist_now.strftime('%d-%m-%Y %I:%M:%S %p'),
        "ticket_details": {**ticket, "username": buyer_username}
    }
    mongo.db.buyed_movie_ticket.insert_one(buyed_ticket)
    mongo.db.movie_tickets.delete_one({"booking_id": booking_id})

    return jsonify({'message': 'Ticket purchased successfully'}), 200

@app.route('/movie_thumbnail')
def movie_thumbnail():
    movie_name = request.args.get('movie')
    
    if not movie_name:
        return redirect(url_for('movie_tickets'))

    movie = mongo.db.movie_details.find_one({'movie_name': movie_name}, {'_id': 0})
    
    if not movie:
        return "Movie not found", 404

    movie['available_tickets'] = mongo.db.movie_tickets.count_documents({
        'movie_name': movie_name
    })

    return render_template('movie_thumbnail.html', movie=movie)

@app.route('/buy_page')
def buy_page():
    """Display available tickets for the selected movie."""
    if 'full_name' not in session:
        return redirect(url_for('home'))
    
    movie_name = request.args.get('movie')
    if not movie_name:
        return redirect(url_for('movie_tickets'))
    
    tickets = list(mongo.db.movie_tickets.find({'movie_name': movie_name}, {'_id': 0}))
    return render_template('buy.html', movie_name=movie_name, tickets=tickets)

@app.route('/chat', methods=['POST'])
def chat():
    if 'username' not in session:
        return jsonify({'response': 'Please log in to use the chat feature.'}), 401
        
    data = request.get_json()
    user_message = data.get('message', '').lower()
    
    if not user_message:
        return jsonify({'response': 'Please provide a message.'}), 400
    
    try:
        movies = list(mongo.db.movie_details.find({}, {'_id': 0}))
        tickets = list(mongo.db.movie_tickets.find({}, {'_id': 0}))
        response = generate_response(user_message, movies, tickets)
        return jsonify({'response': response})
        
    except Exception as e:
        print(f"Error in chat endpoint: {str(e)}")
        return jsonify({'response': 'I encountered an error. Please try again.'}), 500

try:
    mongo.db.users.find_one()
    print("MongoDB Connected Successfully!")
except Exception as e:
    print(f"MongoDB connection failed: {e}")

if __name__ == '__main__':
    app.run(host='0.0.0.0',debug=True)