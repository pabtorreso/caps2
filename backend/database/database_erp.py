# backend/database/database_erp.py
import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Carga .env explícitamente desde /backend
ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=ENV_PATH)

ERP_DB_HOST = os.getenv("ERP_DB_HOST")
ERP_DB_PORT = os.getenv("ERP_DB_PORT", "5432")
ERP_DB_NAME = os.getenv("ERP_DB_NAME")
ERP_DB_USER = os.getenv("ERP_DB_USER")
ERP_DB_PASSWORD = os.getenv("ERP_DB_PASSWORD")
ERP_DB_SSLMODE = os.getenv("ERP_DB_SSLMODE", "disable")

missing = [k for k,v in {
    "ERP_DB_HOST": ERP_DB_HOST,
    "ERP_DB_NAME": ERP_DB_NAME,
    "ERP_DB_USER": ERP_DB_USER,
    "ERP_DB_PASSWORD": ERP_DB_PASSWORD,
}.items() if not v]
if missing:
    raise RuntimeError(f"Faltan variables ERP en .env: {', '.join(missing)}")

ERP_DATABASE_URL = (
    f"postgresql+psycopg2://{ERP_DB_USER}:{ERP_DB_PASSWORD}"
    f"@{ERP_DB_HOST}:{ERP_DB_PORT}/{ERP_DB_NAME}?sslmode={ERP_DB_SSLMODE}"
)

engine_erp = create_engine(ERP_DATABASE_URL, pool_pre_ping=True, future=True)
SessionERP = sessionmaker(autocommit=False, autoflush=False, bind=engine_erp)

def get_erp_db():
    db = SessionERP()
    try:
        yield db
    finally:
        db.close()
