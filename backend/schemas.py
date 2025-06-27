from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any
from datetime import datetime

# --- /chat Endpoint --- 

# ChatRequest modeli artık kullanılmıyor, veri Form ve File ile alınacak.
# class ChatRequest(BaseModel):
#     """Request model for the /chat endpoint."""
#     message: str

class ChatResponse(BaseModel):
    """Response model for the /chat endpoint."""
    response: str
    session_title: Optional[str] = None

# --- /generate-project modelleri kaldırıldı --- 

# class ProjectGenerationParams(BaseModel):
#     ...

# class ProjectGenerationResponse(BaseModel):
#     ... 

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    is_admin: Optional[bool] = False

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    email: EmailStr
    is_admin: bool
    class Config:
        orm_mode = True 

class ChatHistoryResponse(BaseModel):
    id: int
    message: str
    response: str
    timestamp: datetime
    class Config:
        from_attributes = True

class ChatHistoryListResponse(BaseModel):
    history: list[ChatHistoryResponse] 

class ChatSessionCreate(BaseModel):
    title: Optional[str] = None

class ChatSessionResponse(BaseModel):
    id: int
    title: str
    created_at: datetime
    class Config:
        from_attributes = True

class ChatSessionListResponse(BaseModel):
    sessions: list[ChatSessionResponse] 