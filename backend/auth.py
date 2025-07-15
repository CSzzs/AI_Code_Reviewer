import os
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from psycopg2.extensions import connection
from dotenv import load_dotenv

import schemas
from database import get_db_connection

# Load envirnment varibles
load_dotenv()

#Loading environment variables
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = os.getenv("JWT_ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))

# Reusing the password context from main.py
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

#OAuth2 scheme to extract the toke from the "Authorizatin : Bearer <token> header"
oauth2_sheme = OAuth2PasswordBearer(tokenUrl="login")

def verify_password(plain_password: str, hashed_password:str) -> bool:
    """Verifies a plain password against a hashed_one"""
    return pwd_context.verify(plain_password, hashed_password)

def hash_password(password: str) -> str:
    """Hash a plain text password using bcrypt."""
    return pwd_context.hash(password)

def create_access_token(data: dict) -> str:
    """Creating a new JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(
    token: str = Depends(oauth2_sheme), db:connection = Depends("get_db_connection")) ->schemas.UserResponse:
    """
    Dependency function to secure endpoints
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail= "Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decode the Code to get payload
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("user_id")
        if user_id is None:
            raise credentials_exception
        
        token_data = schemas.TokenData(user_id=user_id)
        
    except JWTError:
        raise credentials_exception
    
    # Fetch user from database
    db.execute("SELECT * FROM users WHERE id = %s", (token_data.user_id,))
    user = db.fetchone()
    
    if user is None:
        raise credentials_exception
    return user
