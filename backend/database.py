import os
import logging
from dotenv import load_dotenv
from sqlalchemy import create_engine
from psycopg2.extras import RealDictCursor

# Loading the environment variables
load_dotenv()
DTABASE_URL = os.getenv("DATABASE_URL")

# Creating the SQLAlchemy engine
engine = create_engine(DTABASE_URL)

def get_db_connection():
    """
    Dependency that creates and yields a new raw database conection and cursor per request.
    This ensures the connection is always commited and closed properly
    """
    
    db_conn = None
    db_cursor = None
    try:
        db_conn = engine.raw_connection()
        db_cursor = db_conn.cursor(cursor_factory = RealDictCursor)
        logging.info("Databse connection opened.")
        yield db_cursor
    finally:
        if db_cursor:
            db_cursor.close()
        if db_conn:
            db_conn.commit()
            db_conn.close()
        logging.info("Database connection is closed.")
            