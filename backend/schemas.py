from pydantic import BaseModel
from typing import Optional, Dict, Any

# --- /chat Endpoint --- 

# ChatRequest modeli artık kullanılmıyor, veri Form ve File ile alınacak.
# class ChatRequest(BaseModel):
#     """Request model for the /chat endpoint."""
#     message: str

class ChatResponse(BaseModel):
    """Response model for the /chat endpoint."""
    response: str

# --- /generate-project modelleri kaldırıldı --- 

# class ProjectGenerationParams(BaseModel):
#     ...

# class ProjectGenerationResponse(BaseModel):
#     ... 