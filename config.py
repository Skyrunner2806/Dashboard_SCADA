# config.py
from pathlib import Path
import os

# Mendapatkan path folder utama proyek secara dinamis
BASE_DIR = Path(__file__).resolve().parent

class Config:
    # Path otomatis: akan mencari file CSV di dalam folder yang sama dengan config.py
    DEFAULT_DATA_PATH = Path(os.getenv(
        "DEFAULT_DATA_PATH",
        BASE_DIR / "Data_Lengkap.csv"
    ))

    HARVESTED_DATA_PATH = Path(os.getenv(
        "HARVESTED_DATA_PATH",
        BASE_DIR / "API_Harvest_2023_2025.csv"
    ))

    DATABASE_LIBUR_PATH = Path(os.getenv(
        "DATABASE_LIBUR_PATH",
        BASE_DIR / "DATABASE_LIBUR.csv"
    ))

    TARIF_LISTRIK_PER_KWH = int(os.getenv("TARIF_LISTRIK_PER_KWH", "1500"))
    ISO_CONTAMINATION = float(os.getenv("ISO_CONTAMINATION", "0.02"))
    RANDOM_STATE = int(os.getenv("RANDOM_STATE", "42"))
    
    # Gunakan environment variable untuk keamanan di server
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-123")
