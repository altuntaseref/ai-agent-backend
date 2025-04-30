import os
from dotenv import load_dotenv

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

# You can add other configurations like database connection strings, etc.

# Basic validation (optional but recommended)
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY environment variable not set.")

print("Configuration loaded.")
print(f"Using LLM Provider: {LLM_PROVIDER}") 