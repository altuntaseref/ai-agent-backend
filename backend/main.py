import os
import json
import requests
import tempfile # Geçici dosya işlemleri için
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
import uvicorn
from typing import Optional, Dict, Any
from models import User, ChatHistory, ChatSession
from passlib.context import CryptContext
from jose import jwt, JWTError
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from datetime import datetime, timedelta
from config import get_db

from agent import SoftwareDevAgent
from tools.project_generator import ProjectGeneratorTool
from tools.jenkins.jenkins_tools import CreatePipelineTool, TriggerPipelineTool, PipelineStatusTool, AppHealthCheckTool
from schemas import ChatResponse, UserResponse, UserCreate, ChatHistoryListResponse, ChatHistoryResponse, ChatSessionCreate, ChatSessionResponse, ChatSessionListResponse
import config
import prompts

# --- FastAPI Uygulamasını Oluşturma --- 
app = FastAPI(
    title="Software Development AI Agent API (Single Endpoint)",
    description="API for interacting with the AI agent, accepting text and optional file uploads via a single endpoint.",
    version="0.2.0"
)

# --- CORS Ayarları --- 
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Agent Başlatma --- 
agent_instance: Optional[SoftwareDevAgent] = None

@app.on_event("startup")
def startup_event():
    global agent_instance
    print("Initializing Agent...")
    try:
        # Tüm araçları yükleyelim
        tools_to_load = [
            ProjectGeneratorTool(),  # Proje oluşturma aracı
            CreatePipelineTool(),    # Jenkins pipeline oluşturma aracı
            TriggerPipelineTool(),   # Jenkins pipeline tetikleme aracı  
            PipelineStatusTool(),    # Jenkins pipeline durum sorgulama aracı
            AppHealthCheckTool()     # Uygulama sağlık kontrolü aracı
        ]
        agent_instance = SoftwareDevAgent(tools=tools_to_load)
        print(f"Agent initialized successfully with {len(tools_to_load)} tools.")
        print(f"Available tools: {', '.join([tool.name for tool in tools_to_load])}")
    except Exception as e:
        print(f"CRITICAL: Agent initialization failed: {e}")
        agent_instance = None
# JWT ayarları
def get_jwt_settings():
    secret = os.getenv("JWT_SECRET", "supersecretjwtkey")
    print("JWT_SECRET:", secret)
    algo = os.getenv("JWT_ALGORITHM", "HS256")
    print("JWT_ALGORITHM:", algo)
    expire = int(os.getenv("JWT_EXPIRE_MINUTES", 60))
    return secret, algo, expire
# --- Bağımlılık (Dependency) --- 
def get_agent():
    if agent_instance is None:
        raise HTTPException(status_code=503, detail="Agent is not available.")
    return agent_instance

# --- Postman JSON Doğrulama Yardımcısı ---
def is_valid_postman_collection(file_content: bytes) -> bool:
    """Yüklenen dosyanın geçerli bir Postman koleksiyonu olup olmadığını kontrol eder."""
    try:
        json_data = json.loads(file_content)
        
        # Temel Postman koleksiyon yapısı kontrolü
        if not isinstance(json_data, dict):
            return False
            
        # Postman koleksiyonları genelde bu anahtarlardan en az birini içerir
        required_keys = ["info", "item", "request", "variable"]
        if not any(key in json_data for key in required_keys):
            return False
            
        # info anahtarı varsa, _postman_id veya schema kontrolü
        if "info" in json_data and isinstance(json_data["info"], dict):
            info = json_data["info"]
            if "_postman_id" in info or "schema" in info:
                return True
                
        # item anahtarı varsa ve liste ise
        if "item" in json_data and isinstance(json_data["item"], list):
            return True
            
        return False
    except (json.JSONDecodeError, TypeError, KeyError):
        return False
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

# Kullanıcıyı token'dan bulma
def get_current_user(token: str = Depends(oauth2_scheme), db=Depends(get_db)):
    secret, algo, _ = get_jwt_settings()
    try:
        print("Token:", token)
        payload = jwt.decode(token, secret, algorithms=[algo])
        
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Geçersiz kimlik doğrulama. User Id yok")
        user = db.query(User).filter(User.id == int(user_id)).first()
        if user is None:
            raise HTTPException(status_code=401, detail="Geçersiz kimlik doğrulama. User yok")
        return user
    except JWTError as e:
        print("JWTError:", str(e))
        raise HTTPException(status_code=401, detail="Geçersiz kimlik doğrulama. Exception")

# --- Ana Chat Endpoint'i --- 
@app.post("/chat", response_model=ChatResponse)
async def handle_chat_with_file(
    agent: SoftwareDevAgent = Depends(get_agent),
    message: str = Form(...),
    session_id: int = Form(...),
    postman_collection: Optional[UploadFile] = File(None),
    project_details: Optional[Dict[str, Any]] = Body(None),
    current_user: User = Depends(get_current_user),
    db=Depends(get_db)
):
    # Session kontrolü
    session = db.query(ChatSession).filter(ChatSession.id == session_id, ChatSession.user_id == current_user.id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found.")
    input_for_agent = message
    temp_file_path = None # Geçici dosya yolu

    # 1. Postman koleksiyonunu işle
    if postman_collection:
        try:
            # Dosyayı oku
            content = await postman_collection.read()
            
            # Dosyanın boş olup olmadığını kontrol et
            if not content:
                raise ValueError("Uploaded Postman collection file is empty.")
                
            # Postman koleksiyonu formatını doğrula
            if not is_valid_postman_collection(content):
                raise ValueError("The uploaded file is not a valid Postman collection.")
                
            # Geçici dosya oluştur (.json uzantılı)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as temp_file:
                temp_file.write(content)
                temp_file_path = temp_file.name
                print(f"Postman collection saved temporarily to: {temp_file_path}")
                
                # Agent'a dosya bilgisini ekle
                input_for_agent += f"\n\n[System Note: User uploaded a Postman collection named '{postman_collection.filename}'. It is available at the temporary path: {temp_file_path}]"
                
                # Proje detayları varsa onları da ekle
                if project_details:
                    input_for_agent += f"\n[System Note: User also provided the following project details: {json.dumps(project_details)}]"
                    
        except Exception as e:
            print(f"Error processing Postman collection: {e}")
            await postman_collection.close()
            
            # Hata durumunda kullanıcıya anlamlı bir mesaj ver
            return ChatResponse(response=f"Postman koleksiyonu işlenirken bir hata oluştu: {e}")
        finally:
            await postman_collection.close()
    
    # 2. Agent'ı çalıştır
    try:
        # Agent'a mesajı ve gerekli bilgileri ilet
        agent_response = agent.run(input_for_agent)
        
        # Chat geçmişine kaydet
        chat_entry = ChatHistory(
            user_id=current_user.id,
            session_id=session_id,
            message=message,
            response=agent_response
        )
        db.add(chat_entry)
        db.commit()
        
        # Başarılı işlem sonrası geçici dosyayı temizle
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                # Dosya silinmeden önce aracın dosyayı işlemesi için biraz bekleyebilirsiniz
                # Bu durumda Project Generator aracı dosyayı kopyalama işlemini tamamlamış olmalı
                # os.remove(temp_file_path) # Dikkat: Eğer araç dosyayı hala okuyorsa sorun olabilir!
                print(f"Note: Temporary file {temp_file_path} can be manually removed later.")
            except OSError as e:
                print(f"Error cleaning up temp file {temp_file_path}: {e}")
                
        return ChatResponse(response=agent_response)
    except Exception as e:
        print(f"Chat endpoint error: {e}")
        # Agent çalışırken hata olursa geçici dosyayı temizle
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except:
                pass
        raise HTTPException(status_code=500, detail=f"Bir iç hata oluştu: {e}")

# Şifre hashleme için context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")




# Şifre hashleme ve doğrulama
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

# JWT token oluşturma
def create_access_token(data: dict, expires_delta: timedelta = None):
    secret, algo, expire_minutes = get_jwt_settings()
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=expire_minutes))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, secret, algorithm=algo)

def create_refresh_token(data: dict, expires_delta: timedelta = None):
    secret, algo, _ = get_jwt_settings()
    expire = datetime.utcnow() + (expires_delta or timedelta(days=7))
    to_encode = data.copy()
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, secret, algorithm=algo)

# Admin mi kontrolü
def get_current_admin(current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Sadece admin erişebilir.")
    return current_user

# Register endpointi (sadece admin)
@app.post("/register", response_model=UserResponse)
def register(user: UserCreate, db=Depends(get_db), admin: User = Depends(get_current_admin)):
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Bu email zaten kayıtlı.")
    hashed = hash_password(user.password)
    db_user = User(email=user.email, password_hash=hashed, is_admin=user.is_admin or False)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# Login endpointi
@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db=Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Geçersiz email veya şifre.")
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

@app.post("/chat/session", response_model=ChatSessionResponse)
def create_chat_session(session: ChatSessionCreate, current_user: User = Depends(get_current_user), db=Depends(get_db)):
    new_session = ChatSession(user_id=current_user.id, title=session.title)
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    return new_session

@app.get("/chat/sessions", response_model=ChatSessionListResponse)
def list_chat_sessions(current_user: User = Depends(get_current_user), db=Depends(get_db)):
    sessions = db.query(ChatSession).filter(ChatSession.user_id == current_user.id).order_by(ChatSession.created_at.desc()).all()
    session_list = [ChatSessionResponse.from_orm(s) for s in sessions]
    return ChatSessionListResponse(sessions=session_list)

@app.get("/chat/history", response_model=ChatHistoryListResponse)
def get_chat_history(session_id: int, current_user: User = Depends(get_current_user), db=Depends(get_db)):
    session = db.query(ChatSession).filter(ChatSession.id == session_id, ChatSession.user_id == current_user.id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found.")
    history = db.query(ChatHistory).filter(ChatHistory.session_id == session_id).order_by(ChatHistory.timestamp.asc()).all()
    return ChatHistoryListResponse(history=history)

# Basit bir refresh token blacklist (bellekte, örnek amaçlı)
refresh_token_blacklist = set()

@app.post("/logout")
def logout(refresh_token: str = Body(...)):
    refresh_token_blacklist.add(refresh_token)
    return {"message": "Başarıyla çıkış yapıldı."}

# /refresh endpointini güncelle: Blacklist kontrolü ekle
@app.post("/refresh")
def refresh_token(refresh_token: str = Body(...), db=Depends(get_db)):
    if refresh_token in refresh_token_blacklist:
        raise HTTPException(status_code=401, detail="Bu refresh token ile tekrar giriş yapılamaz.")
    secret, algo, _ = get_jwt_settings()
    try:
        payload = jwt.decode(refresh_token, secret, algorithms=[algo])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Geçersiz refresh token.")
        user = db.query(User).filter(User.id == int(user_id)).first()
        if user is None:
            raise HTTPException(status_code=401, detail="Kullanıcı bulunamadı.")
        new_access_token = create_access_token(data={"sub": str(user.id)})
        return {"access_token": new_access_token, "token_type": "bearer"}
    except JWTError:
        raise HTTPException(status_code=401, detail="Geçersiz refresh token.")

@app.delete("/chat/session/{session_id}")
def delete_chat_session(session_id: int, current_user: User = Depends(get_current_user), db=Depends(get_db)):
    session = db.query(ChatSession).filter(ChatSession.id == session_id, ChatSession.user_id == current_user.id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found.")
    # Önce ilgili tüm mesajları sil
    db.query(ChatHistory).filter(ChatHistory.session_id == session_id).delete()
    db.delete(session)
    db.commit()
    return {"message": "Chat oturumu ve mesajları silindi."}

@app.put("/chat/session/{session_id}", response_model=ChatSessionResponse)
def update_chat_session(session_id: int, session_update: ChatSessionCreate, current_user: User = Depends(get_current_user), db=Depends(get_db)):
    session = db.query(ChatSession).filter(ChatSession.id == session_id, ChatSession.user_id == current_user.id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found.")
    session.title = session_update.title
    db.commit()
    db.refresh(session)
    return ChatSessionResponse.from_orm(session)

@app.get("/chat/sessions/search", response_model=ChatSessionListResponse)
def search_chat_sessions(query: str, current_user: User = Depends(get_current_user), db=Depends(get_db)):
    sessions = db.query(ChatSession).filter(ChatSession.user_id == current_user.id, ChatSession.title.ilike(f"%{query}%")).order_by(ChatSession.created_at.desc()).all()
    session_list = [ChatSessionResponse.from_orm(s) for s in sessions]
    return ChatSessionListResponse(sessions=session_list)

# --- Uygulamayı Çalıştırma --- 
if __name__ == "__main__":
    print("Starting API server (single endpoint mode)...")
    uvicorn.run("main:app", host="127.0.0.1", port=8080, reload=True)