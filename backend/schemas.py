from pydantic import BaseModel, EmailStr
from datetime import datetime

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id : int
    email : EmailStr
    created_at : datetime
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    
class TokenData(BaseModel):
    user_id:int

class CodeSubmission(BaseModel):
    code:str
    
class Analysis(BaseModel):
    id:int
    submission_id: int
    analysis_results: dict 
    model_used: str
    
    class Config:
        from_attributes = True