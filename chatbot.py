import os
import requests
import re
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Retrieve the API key from the environment
api_key = os.getenv('GEMINI_API_KEY')

# Define the API endpoint
url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

def generate_response(user_message, movies, tickets):
    """Generate contextual responses based on available movie and ticket information"""
    
    # Check for ticket price queries
    if any(word in user_message for word in ['price', 'cost', 'how much']):
        if tickets:
            prices = set(str(ticket['price']) for ticket in tickets)
            if len(prices) == 1:
                return f"Tickets are priced at ₹{prices.pop()}"
            else:
                return f"Ticket prices range from ₹{min(map(float, prices))} to ₹{max(map(float, prices))}"
    
    # Check for movie availability
    if any(word in user_message for word in ['available', 'showing', 'playing']):
        if movies:
            movie_names = [movie['movie_name'] for movie in movies]
            return f"Currently showing movies: {', '.join(movie_names)}"
        return "Sorry, no movies are currently available."
    
    # Check for specific movie information
    for movie in movies:
        if movie['movie_name'].lower() in user_message:
            info = [f"Movie: {movie['movie_name']}"]
            if 'language' in movie:
                info.append(f"Language: {movie['language']}")
            if 'cast' in movie:
                cast = movie['cast'] if isinstance(movie['cast'], str) else ', '.join(movie['cast'])
                info.append(f"Cast: {cast}")
            return '\n'.join(info)
    
    # Fallback to Google Gemini API for other queries
    return interact_with_gemini(user_message)

def interact_with_gemini(user_message):
    headers = {'Content-Type': 'application/json'}

    instruction = (
        "You are Smart Ticket Assistant, a helpful assistant on a movie ticket marketplace website. "
        "You ONLY answer questions related to this platform, such as:\n"
        "- Available movies\n"
        "- Ticket prices\n"
        "- Ticket upload or buy instructions\n"
        "- Cast and language of movies\n"
        "Do NOT respond about banks, balance inquiries, external websites, or general web search topics.\n"
        "If a user asks something out of scope, politely tell them to check the platform features or pages."
    )

    data = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": instruction}]
            },
            {
                "role": "user",
                "parts": [{"text": user_message}]
            }
        ]
    }

    response = requests.post(
        f"{url}?key={api_key}",
        headers=headers,
        json=data
    )

    if response.status_code == 200:
        try:
            return response.json()['candidates'][0]['content']['parts'][0]['text']
        except Exception:
            return "Sorry, I couldn't process your question. Try rephrasing."
    else:
        return f"Gemini API error {response.status_code}: {response.text}"