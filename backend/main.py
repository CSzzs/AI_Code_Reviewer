import logging
import os

import psycopg2
from dotenv import load_dotenv
from fastapi import FastAPI, Response, status
from psycopg2.extras import RealDictCursor

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s -%(messages)s')

load_dotenv()

app = FastAPI(
    title="AI Code Reviewer API",
    description="The backend service for the AI Code Review and refactoring assitant.",
    version="0.1.0",
)

# ---Database Connection---

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    logging.critical("DATABASE_URL environment variable not set. Application cannot start.")
    
# ---API Endpoints---
@app.get("/", tags=["Health Check"])
def health_check(response: Response):
    """
    Checks the Helath of the API and its database connection
    """
    conn = None
    try:
        if not DATABASE_URL:
            raise ValueError("Database URL is Not configured.")
        
        logging.info("Attempting to connect to the databse...")
        conn = psycopg2.connect(DATABASE_URL)
        
        logging.info("Database connection succesful.")
        
        return{"status": "success", "message": "API is running and database connection is helthy."}
    
    except psycopg2. OperationalError as e:
        logging.error(f"Database operational error: {e}")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "error", "message": "Could not connect to the database"}
    
    except Exception as e:
        logging.error(f"An unexepected error occured during health check: {e}")
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return{"status": "error", "message": "An internal server error occured."}
    
    finally:
        if conn is not None:
            conn.close()
            logging.info("Database connection closed")