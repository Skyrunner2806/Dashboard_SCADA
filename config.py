# config.py
from pathlib import Path
import os

class Config:
    DEFAULT_DATA_PATH = Path(os.getenv(
        "DEFAULT_DATA_PATH",
        r"D:\Kuliah\Semester 7\Joki Joel\energy-dashboard\Data_Lengkap.csv"
    ))

    HARVESTED_DATA_PATH = Path(os.getenv(
        "HARVESTED_DATA_PATH",
        r"D:\Kuliah\Semester 7\Joki Joel\energy-dashboard\API_Harvest_2023_2025.csv"
    ))

    DATABASE_LIBUR_PATH = Path(os.getenv(
        "DATABASE_LIBUR_PATH",
        r"D:\Kuliah\Semester 7\Joki Joel\energy-dashboard\DATABASE_LIBUR.csv"
    ))

    TARIF_LISTRIK_PER_KWH = int(os.getenv("TARIF_LISTRIK_PER_KWH", "1500"))
    ISO_CONTAMINATION = float(os.getenv("ISO_CONTAMINATION", "0.02"))
    RANDOM_STATE = int(os.getenv("RANDOM_STATE", "42"))
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
