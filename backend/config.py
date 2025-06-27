import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Load environment variables from a .env file if it exists
load_dotenv()

# --- LLM Configuration ---
# We will use Google Gemini
LLM_PROVIDER = "gemini" # Sabit olarak gemini ayarladık
# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") # OpenAI kullanmayacağımız için kaldırıldı/yorumlandı
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# --- Tool API Configurations ---
PROJECT_GENERATOR_API_URL = os.getenv("PROJECT_GENERATOR_API_URL")
# Add environment variables for your other tool APIs here as needed
# Example:
# CODE_GENERATOR_API_URL = os.getenv("CODE_GENERATOR_API_URL")
# CODE_GENERATOR_API_KEY = os.getenv("CODE_GENERATOR_API_KEY")
# CI_CD_API_URL = os.getenv("CI_CD_API_URL")
# LOG_ANALYZER_API_URL = os.getenv("LOG_ANALYZER_API_URL")

# --- Jenkins API Configuration ---
JENKINS_API_BASE_URL = os.getenv("JENKINS_API_BASE_URL", "http://localhost:8080")
# Eğer değer belirtilmezse, varsayılan olarak localhost:8080 kullan

# You can add other configurations like database connection strings, etc.

# Basic validation (optional but recommended)
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY environment variable not set.")

print("Configuration loaded.")
print(f"Using LLM Provider: {LLM_PROVIDER}")
print(f"Jenkins API URL: {JENKINS_API_BASE_URL}")

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "aiagentdb")
DB_USER = os.getenv("DB_USER", "aiagentuser")
DB_PASSWORD = os.getenv("DB_PASSWORD", "supersecretpassword")

DATABASE_URL = os.getenv("DATABASE_URL")
DATABASE_URL_SYNC = os.getenv("DATABASE_URL_SYNC")

# Alembic ve sync işlemler için kullanılacak bağlantı adresi
SQLALCHEMY_DATABASE_URL = DATABASE_URL_SYNC or f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 