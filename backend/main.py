import logging

import psycopg2
from fastapi import FastAPI, Response, status, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from psycopg2.extensions import connection
import psycopg2.extras

import auth
import schemas
import ai_core
from database import get_db_connection

#---Configuration and setup---

# Configure Logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s -%(message)s')

# Create FastAPI application instance
app = FastAPI(
    title="AI Code Reviewer API",
    description="The backend service for the AI Code Review and refactoring assistant.",
    version="0.1.0",
)
          
# ---API Endpoints---
@app.get("/", tags=["Health Check"])
def health_check(response: Response, db: connection = Depends(get_db_connection)):
    """
    Checks the health of the API. The Depends(get_db_connection) part also implicitly
    checks if the database connection can be established.
    """
    return {"status": "success", "message": "API is running and database connection is healthy."}
    
@app.post("/register", status_code=status.HTTP_201_CREATED,response_model=schemas.UserResponse, tags=["Authentication"])
def register_user(user:schemas.UserCreate, db: connection = Depends(get_db_connection)):
    """
    Registers a new user in the database.
    - Hashes the password for security.
    - Check for duplicate emails.
    """
    # 1. Check if a user with this email already exists
    logging.info(f"Checking for existing user with email: {user.email}")
    db.execute("SELECT id FROM users WHERE email = %s", (user.email,))
    existing_user = db.fetchone()
    
    if existing_user:
        logging.warning(f"Registration attempt failed for existing email:{user.email}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists."
        )
        
    # 2. Hash the user's password
    hashed_pass = auth.hash_password(user.password)
    logging.info(f"Password hashed for user: {user.email}")
    
    # 3. Insert new user into the database
    try:
        logging.info(f"Creating new user: {user.email}")
        db.execute(
            "INSERT INTO users (email, hashed_password) VALUES (%s, %s) RETURNING id, email, created_at ",
            (user.email, hashed_pass)
        )
        
        new_user_record = db.fetchone()
        logging.info(f"Successfully created user with ID: {new_user_record['id']}")
        return new_user_record
    
    except psycopg2.Error as e:
        logging.error(f"Database error during user creation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create user due to database error."
        )

@app.post("/login", response_model=schemas.Token, tags=["Authentication"])
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), db: connection = Depends(get_db_connection)):
    """
    Logs a user in by verifying their credentials and returning JWT token.
    """
    # 1. Finding the user by their email
    logging.info(f"Login attempt for user: {form_data.username}")
    db.execute("SELECT * FROM users WHERE email = %s", (form_data.username,))
    user = db.fetchone()
    
    # 2. Check if user exists and if the Password is correct
    if not user or not auth.verify_password(form_data.password, user['hashed_password']):
        logging.warning(f"Failed logging attempt for user: {form_data.username}")
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect Email or Password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 3. Creating the JWT token if user is valid
    access_token = auth.create_access_token(
        data={"sub": user['email'], "user_id":user['id']}
    )
    logging.info(f"Successfully login and token created for user:{form_data.username}")
    
    # 4. Return the token
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me", response_model= schemas.UserResponse, tags=["Users"])
def read_users_me(current_user: schemas.UserResponse = Depends(auth.get_current_user)):
    """
    Fethches the details fro the currently logged in user.
    This is the protected endpoint.  A valid JWT Token must be provided
    """
    logging.info(f"Fetching details for user ID: {current_user['id']}")
    return current_user

@app.post("/code/analyze", response_model=schemas.Analysis, tags=["Analysis"])
def analyze_code(
    submission: schemas.CodeSubmission,
    db: connection = Depends(get_db_connection),
    current_user: schemas.UserResponse = Depends(auth.get_current_user)
):
    """
    Saves the submission and analysis results to the database.
    """
    user_id = current_user['id']
    logging.info(f"Received code submission from the user ID: {user_id}")
    
    try:
        # 1. saving the user submitted code to the 'submission' table
        db.execute(
            "INSERT INTO submission (user_id, original_code) VALUES (%s, %s) RETURNING id",
            (user_id, submission.code)
            
        )
        
        submission_record = db.fetchone()
        submission_id = submission_record['id']
        logging.info(f"Code saved with submission ID: {submission_id}")
        
        # 2. Call the AI core to get the analysis
        analysis_results = ai_core.analyze_code_with_ai(submission.code)
        model_used = "mock_ai_v1.0"
        
        # 3. Save the analysis result to the 'analyses' table
        db.execute(
            """
            INSERT INTO analyses (submission_id, analysis_results, model_used)
            VALUES (%s, %s, %s)
            RETURNING id, submission_id, analysis_results, model_used
            """,
            (submission_id, psycopg2.extras.Json(analysis_results), model_used)
        )
        new_analysis_record = db.fetchone()
        logging.info(f"Analysis saved with analysis id: {new_analysis_record['id']}")
        
        # 4. returning the newly created analysis record
        return new_analysis_record
    
    except psycopg2.Error as e:
        logging.error(f"Database error during the analysis for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A database error occurred while processing your request."
        )
        
    except Exception as e:
        logging.error(f"An unexpected error occured during the analysis for user {user_id}: {e}")
        raise HTTPException(
            status_code= status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred."
        )