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
@app.get