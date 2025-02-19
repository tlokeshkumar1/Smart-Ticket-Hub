import os
import pymongo
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Connect to MongoDB
MONGO_URI = os.getenv("MONGO_URI")
client = pymongo.MongoClient(MONGO_URI)
db = client.get_database()  # Use the default database from the URI
collection = db["movie_details"]

# Sample movie data
movie_data = {
    "movie_name": "HIT: The Second Case (2022)",
    "thumbnail": "https://assets-in.bmscdn.com/discovery-catalog/events/tr:w-250,h-390/et00327635-effhmzfywb-portrait.jpg",
    "trailer": "https://www.youtube.com/watch?v=X3Nt-fh56gI",
    "language": "Telugu",
    "cast": ["Adivi Sesh", "Meenakshi Chaudhary"]
}

# Insert the movie data
result = collection.insert_one(movie_data)
print(f"Inserted movie with ID: {result.inserted_id}")
