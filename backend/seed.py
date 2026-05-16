"""
Seed script — run once to create admin user and sample data.
Usage: python seed.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from pymongo import MongoClient
import certifi
from config import MONGO_URI
from utils.auth_middleware import hash_password
from datetime import datetime, timezone, timedelta

client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
# Get the database from the URI path
if "mongodb+srv" in MONGO_URI or ("@" in MONGO_URI and "/" in MONGO_URI.split("@")[-1]):
    db = client.get_default_database()
    if db.name in ("admin", None):
        db = client["moviebooking"]
else:
    db = client["moviebooking"]

print(f"Connected to database: {db.name}")

# ── Admin user ────────────────────────────────────────────────────────────────
if not db.users.find_one({"email": "admin@cinema.com"}):
    db.users.insert_one({
        "name": "Admin",
        "email": "admin@cinema.com",
        "password": hash_password("Admin@123"),
        "role": "admin",
    })
    print("Admin user created: admin@cinema.com / Admin@123")
else:
    print("Admin user already exists")

# ── Sample movies ─────────────────────────────────────────────────────────────
sample_movies = [
    {
        "title": "Kalki 2898 AD",
        "genre": "Sci-Fi",
        "language": "Telugu",
        "duration": "3h 1m",
        "description": "A futuristic mythological epic set in the year 2898 AD, following the prophesied avatar of Vishnu on an action-packed journey.",
        "rating": 8.2,
        "cast": ["Prabhas", "Deepika Padukone", "Amitabh Bachchan"],
        "poster_url": "https://upload.wikimedia.org/wikipedia/en/5/57/Kalki_2898_AD_film_poster.jpg",
        "is_active": True,
    },
    {
        "title": "Pushpa 2: The Rule",
        "genre": "Action",
        "language": "Telugu",
        "duration": "3h 23m",
        "description": "Pushpa Raj continues his reign over the red sandalwood smuggling world while battling a relentless police officer.",
        "rating": 7.9,
        "cast": ["Allu Arjun", "Rashmika Mandanna", "Fahadh Faasil"],
        "poster_url": "https://upload.wikimedia.org/wikipedia/en/thumb/4/4c/Pushpa_2_The_Rule_poster.jpg/220px-Pushpa_2_The_Rule_poster.jpg",
        "is_active": True,
    },
    {
        "title": "Stree 2",
        "genre": "Horror Comedy",
        "language": "Hindi",
        "duration": "2h 20m",
        "description": "The residents of Chanderi face a new supernatural threat as the legend of Stree evolves into a bigger mystery.",
        "rating": 8.5,
        "cast": ["Rajkummar Rao", "Shraddha Kapoor", "Tamannaah Bhatia"],
        "poster_url": "https://upload.wikimedia.org/wikipedia/en/7/7c/Stree_2_poster.jpg",
        "is_active": True,
    },
    {
        "title": "Fighter",
        "genre": "Action",
        "language": "Hindi",
        "duration": "2h 46m",
        "description": "An elite air force unit takes on a daring mission to neutralize a terrorist threat against India.",
        "rating": 6.8,
        "cast": ["Hrithik Roshan", "Deepika Padukone", "Anil Kapoor"],
        "poster_url": "https://upload.wikimedia.org/wikipedia/en/8/89/Fighter_2024_film_poster.jpg",
        "is_active": True,
    },
    {
        "title": "Animal",
        "genre": "Drama",
        "language": "Hindi",
        "duration": "3h 21m",
        "description": "A son's obsessive love for his father takes a dark and violent turn in this intense drama.",
        "rating": 7.4,
        "cast": ["Ranbir Kapoor", "Rashmika Mandanna", "Anil Kapoor"],
        "poster_url": "https://upload.wikimedia.org/wikipedia/en/6/6a/Animal_2023_film_poster.jpg",
        "is_active": True,
    },
]

# Only insert if no movies exist
if db.movies.count_documents({}) == 0:
    result = db.movies.insert_many(sample_movies)
    movie_ids = result.inserted_ids
    print(f"Inserted {len(movie_ids)} sample movies")
else:
    movie_ids = [m["_id"] for m in db.movies.find({}, {"_id": 1}).limit(5)]
    print("Movies already exist")

# ── Sample theaters ───────────────────────────────────────────────────────────
sample_theaters = [
    {
        "name": "INOX Megaplex",
        "location": "GVK One Mall, Banjara Hills",
        "city": "Hyderabad",
        "screens": [
            {"screen_no": 1, "rows": 8, "cols": 12},
            {"screen_no": 2, "rows": 6, "cols": 10},
            {"screen_no": 3, "rows": 10, "cols": 14},
        ],
    },
    {
        "name": "PVR Cinemas",
        "location": "Phoenix Palladium, Lower Parel",
        "city": "Mumbai",
        "screens": [
            {"screen_no": 1, "rows": 8, "cols": 10},
            {"screen_no": 2, "rows": 8, "cols": 10},
        ],
    },
    {
        "name": "Cinepolis",
        "location": "Forum Mall, Koramangala",
        "city": "Bangalore",
        "screens": [
            {"screen_no": 1, "rows": 9, "cols": 11},
            {"screen_no": 2, "rows": 7, "cols": 9},
        ],
    },
]

if db.theaters.count_documents({}) == 0:
    t_result = db.theaters.insert_many(sample_theaters)
    theater_ids = t_result.inserted_ids
    print(f"Inserted {len(theater_ids)} sample theaters")
else:
    theater_ids = [t["_id"] for t in db.theaters.find({}, {"_id": 1}).limit(3)]
    print("Theaters already exist")

# ── Sample shows ──────────────────────────────────────────────────────────────
if db.shows.count_documents({}) == 0 and len(movie_ids) >= 2 and len(theater_ids) >= 2:
    now = datetime.now(timezone.utc)
    base_date = now.replace(hour=10, minute=0, second=0, microsecond=0)

    sample_shows = [
        {
            "movie_id": movie_ids[0],
            "theater_id": theater_ids[0],
            "movie_title": sample_movies[0]["title"],
            "movie_poster": sample_movies[0]["poster_url"],
            "theater_name": sample_theaters[0]["name"],
            "theater_city": sample_theaters[0]["city"],
            "screen_no": 1,
            "datetime": (base_date + timedelta(days=1)).strftime("%Y-%m-%dT10:00"),
            "price": 200,
            "rows": 8,
            "cols": 12,
        },
        {
            "movie_id": movie_ids[0],
            "theater_id": theater_ids[0],
            "movie_title": sample_movies[0]["title"],
            "movie_poster": sample_movies[0]["poster_url"],
            "theater_name": sample_theaters[0]["name"],
            "theater_city": sample_theaters[0]["city"],
            "screen_no": 2,
            "datetime": (base_date + timedelta(days=1)).strftime("%Y-%m-%dT14:30"),
            "price": 200,
            "rows": 6,
            "cols": 10,
        },
        {
            "movie_id": movie_ids[1],
            "theater_id": theater_ids[1],
            "movie_title": sample_movies[1]["title"],
            "movie_poster": sample_movies[1]["poster_url"],
            "theater_name": sample_theaters[1]["name"],
            "theater_city": sample_theaters[1]["city"],
            "screen_no": 1,
            "datetime": (base_date + timedelta(days=2)).strftime("%Y-%m-%dT18:00"),
            "price": 250,
            "rows": 8,
            "cols": 10,
        },
        {
            "movie_id": movie_ids[2],
            "theater_id": theater_ids[2],
            "movie_title": sample_movies[2]["title"],
            "movie_poster": sample_movies[2]["poster_url"],
            "theater_name": sample_theaters[2]["name"],
            "theater_city": sample_theaters[2]["city"],
            "screen_no": 1,
            "datetime": (base_date + timedelta(days=1)).strftime("%Y-%m-%dT21:00"),
            "price": 180,
            "rows": 9,
            "cols": 11,
        },
    ]
    db.shows.insert_many(sample_shows)
    print(f"Inserted {len(sample_shows)} sample shows")
else:
    print("Shows already exist or insufficient data")

# ── TTL index for seat locks ──────────────────────────────────────────────────
try:
    db.seat_locks.create_index("expires_at", expireAfterSeconds=0)
    print("TTL index created on seat_locks")
except Exception as e:
    print(f"TTL index: {e}")

print("\nDatabase seeded successfully!")
print("   Admin login: admin@cinema.com / Admin@123")
print("   Admin panel: http://localhost:5000/admin-x9k2/login.html")
