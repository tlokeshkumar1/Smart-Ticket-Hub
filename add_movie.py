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
    "movie_name": "Guntur Kaaram",
    "thumbnail": "https://assets-in.bmscdn.com/iedb/movies/images/mobile/thumbnail/xlarge/guntur-kaaram-et00310760-1686726453.jpg",
    "trailer": "https://www.youtube.com/watch?v=DYLG65xz55U",
    "language": "Telugu",
    "cast": ["Mahesh Babu","Sreeleela","Meenakshi Chaudhary","Ramya Krishnan","Jayaram","Prakash Raj","Jagapathi Babu","Murli Sharma","Vennela Kishore"]
}

# Insert the movie data
result = collection.insert_one(movie_data)
print(f"Inserted movie with ID: {result.inserted_id}")
