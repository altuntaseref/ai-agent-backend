import os
from getpass import getpass
from sqlalchemy.orm import Session
from config import SessionLocal
from models import User
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def main():
    db: Session = SessionLocal()
    email = input("Admin email: ").strip()
    password = getpass("Admin şifre: ")
    if db.query(User).filter(User.email == email).first():
        print("Bu email zaten kayıtlı.")
        return
    hashed = hash_password(password)
    admin = User(email=email, password_hash=hashed, is_admin=True)
    db.add(admin)
    db.commit()
    print(f"Admin kullanıcı oluşturuldu: {email}")

if __name__ == "__main__":
    main() 