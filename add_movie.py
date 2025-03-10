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
    "movie_name": "Dragon",
    "thumbnail": "https://assets-in.bmscdn.com/iedb/movies/images/mobile/thumbnail/xlarge/return-of-the-dragon-et00433943-1739944684.jpg",
    "trailer": "https://www.youtube.com/watch?v=m1i-sYxTX8I",
    "language": "Telugu",
    "cast": ["Pradeep Ranganathan","Anupama Parameswaran","Kayadu Lohar","Ivana","Gautham vasudev"]
}

# Insert the movie data
result = collection.insert_one(movie_data)
print(f"Inserted movie with ID: {result.inserted_id}")
