from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id : int
    email : EmailStr
    created_at : str
    
    class Config:
        from_attributes = True