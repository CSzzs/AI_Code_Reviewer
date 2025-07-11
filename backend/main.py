import logging
import os

import psycopg2
import schemas
from dotenv import load_dotenv
from fastapi import FastAPI, Response, status, Depends, HTTPException
from psycopg2.extras import RealDictCursor
from passlib.context import CryptContext
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import Pool
from sqlalchemy.engine.base import Connection


#---Configuration and setup---

# Configure Logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s -%(messages)s')

# Load environment variables
load_dotenv()

# ---Database Connection---

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    logging.critical("DATABASE_URL environment variable not set. Application cannot start.")

# Create FastAPI application instance
app = FastAPI(
    title="AI Code Reviewer API",
    description="The backend service for the AI Code Review and refactoring assitant.",
    version="0.1.0",
)
# ---Setup the password hashing---
pwd_context = CryptContext(schemas=["bcrypt"], deprecated = "auto")

engine = create_engine(DATABASE_URL) 

SessionLocal = sessionmaker(autocommit= False, autoflush=False, bind=engine)

# Dependency to get a DB session for a single request
def get_db():
    db_conn = None
    db_cursor = None
    try:
        db_conn = engine.raw_connection()
        db_cursor = db_conn.cursor(cursor_factory=RealDictCursor)
        logging.info("Databse session opened.")
        yield db_cursor
    finally:
        if db_cursor:
            db_cursor.close()
        if db_conn:
            db_conn.commit()
            db_conn.close()
        logging.info("Databse session closed.")
        
# --- Helper Functions ---

def hash_password(password: str):
    """Hashes a plain-text password using bcrypt."""
    return pwd_context.hash(password)      
        
# ---API Endpoints---
@app.get("/", tags=["Health Check"])
def health_check(response: Response, db: Connection = Depends(get_db)):
    """
    Checks the health of the API. The Depends(get_db) part also implicitly
    checks if the database connection can be established.
    """
    return {"status": "success", "message": "API is running and database connection is healthy."}
    
@app.post("/register", status_code=status.HTTP_201_CREATED,response_model= schemas.UserResponse, tags=["Authentication"])
def register_user(user: schemas.UserCreate, db: Connection = Depends(get_db)):
    """
    Registers a new user in the database.
    - Hashes the password for security.
    - Check for duplicate emails.
    """
    # 1. Check if a user with this email already exists
    logging.info(f"Checking for existing user with email:{user.email}")
    db.execute("SELECT id FROM users WHERE email = %s", (user.email,))
    existing_user = db.fetchone()
    
    if existing_user:
        logging.warning(f"Registration attempt failed for existing email:{user.email}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists."
        )
        
    # 2. Hash the user's password
    hashed_pass = hash_password(user.password)
    logging.info(f"Password hashed for user:{user.email}")
    
    # 3. Insert new user into the database
    try:
        logging.info(f"Creating new user: {user.email}")
        db.execute(
            "INSERT INTO users (email, hashed_password) VLAUES (%s, %s) RETURNING id, email, created_at ",
            (user.email, hashed_pass)
        )
        
        new_user_record = db.fetchone()
        logging.info(f"Successfully created user with ID: {new_user_record['id']}")
        return new_user_record
    
    except psycopg2.Error as e:
        logging.error(f"Databse error during user creation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create user due to database error."
        )