import os
import json
import requests
import tempfile # Geçici dosya işlemleri için
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
import uvicorn
from typing import Optional, Dict, Any

from agent import SoftwareDevAgent
from tools.project_generator import ProjectGeneratorTool # Araç hala tanımlı olmalı
from schemas import ChatResponse # Sadece ChatResponse kaldı
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
        # Agent'ı proje oluşturma aracıyla birlikte başlatmalıyız ki onu kullanabilsin
        tools_to_load = [ProjectGeneratorTool()]
        agent_instance = SoftwareDevAgent(tools=tools_to_load)
        print("Agent initialized successfully with tools.")
    except Exception as e:
        print(f"CRITICAL: Agent initialization failed: {e}")
        agent_instance = None

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

# --- Ana Chat Endpoint'i --- 
@app.post("/chat", response_model=ChatResponse)
async def handle_chat_with_file(
    agent: SoftwareDevAgent = Depends(get_agent),
    message: str = Form(...), # Kullanıcı mesajı form alanı olarak
    postman_collection: Optional[UploadFile] = File(None), # Postman koleksiyonu için özel alan
    project_details: Optional[Dict[str, Any]] = Body(None) # Proje detayları (opsiyonel, JSON body)
):
    """
    Kullanıcıdan gelen mesajı, Postman koleksiyonunu ve proje detaylarını işler.
    
    - message: Kullanıcı mesajı (zorunlu)
    - postman_collection: Yüklenen Postman koleksiyonu dosyası (opsiyonel)
    - project_details: Proje detayları (opsiyonel, JSON gövdesi)
    """
    
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

# --- Uygulamayı Çalıştırma --- 
if __name__ == "__main__":
    print("Starting API server (single endpoint mode)...")
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)