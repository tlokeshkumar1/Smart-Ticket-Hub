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
    
    # Check for booking help
    if any(word in user_message for word in ['book', 'buy', 'purchase']):
        return "To book tickets, browse our available movies and click the 'Buy Tickets' button on the movie you'd like to watch. Make sure you're logged in to complete the purchase."
    
    # Check for account/balance queries
    if any(word in user_message for word in ['account', 'balance', 'wallet']):
        return "You can check your account balance and add funds in the Balance section. Your balance is used for purchasing tickets."
    
    # Default response
    return "I can help you with:\n- Movie information and showtimes\n- Ticket prices and availability\n- Booking process\n- Account balance\nWhat would you like to know?"
