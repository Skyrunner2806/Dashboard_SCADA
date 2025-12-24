# services/data_service.py
from __future__ import annotations
from pathlib import Path
import pandas as pd
import numpy as np

POSSIBLE_TIME_NAMES = [
    "Waktu","waktu","WAKTU",
    "Tanggal","tanggal","TANGGAL",
    "Date","date","DATE",
    "DateTime","datetime","DATETIME",
    "Timestamp","timestamp","TIMESTAMP",
    "Time","time","TIME"
]

def detect_datetime_column(df: pd.DataFrame) -> str | None:
    # 1) exact match
    for col in df.columns:
        if col in POSSIBLE_TIME_NAMES:
            return col

    # 2) contains keyword
    for col in df.columns:
        s = str(col).lower()
        if any(k in s for k in ["time","date","tanggal","waktu"]):
            return col

    # 3) try parse
    for col in df.columns:
        try:
            test = pd.to_datetime(df[col].head(20), errors="coerce")
            if test.notna().sum() >= 10:
                return col
        except Exception:
            pass

    return None

def detect_energy_columns(df: pd.DataFrame, dt_col: str) -> list[str]:
    # cari kolom yang kira-kira energi
    candidates = []
    for col in df.columns:
        if col == dt_col:
            continue
        s = str(col).lower()
        if any(k in s for k in ["kwh","energy","konsumsi","usage","power"]):
            candidates.append(col)

    # fallback: semua numerik kecuali dt
    if not candidates:
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        candidates = [c for c in numeric_cols if c != dt_col]

    return candidates if candidates else []

def load_holiday_database(csv_path: Path) -> dict[str, str]:
    """
    Return dict: 'YYYY-MM-DD' -> keterangan (kalau ada)
    """
    if not Path(csv_path).exists():
        return {}

    df = pd.read_csv(csv_path)

    # fleksibel: tanggal/Tanggal
    tcol = "tanggal" if "tanggal" in df.columns else ("Tanggal" if "Tanggal" in df.columns else None)
    if not tcol:
        return {}

    df[tcol] = pd.to_datetime(df[tcol], errors="coerce")

    # optional kolom keterangan
    ket_col = None
    for c in ["libur apa","Libur apa","keterangan","Keterangan","nama","Nama"]:
        if c in df.columns:
            ket_col = c
            break

    out = {}
    for _, r in df.iterrows():
        if pd.notna(r[tcol]):
            key = r[tcol].strftime("%Y-%m-%d")
            out[key] = str(r[ket_col]) if ket_col else "Libur"
    return out

def load_energy_data(csv_path: Path, source_name: str = "data") -> dict:
    """
    Load CSV -> return dict berisi:
      df, datetime_col, energy_cols, source_name
    """
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"File tidak ditemukan: {csv_path}")

    df = pd.read_csv(csv_path)

    dt_col = detect_datetime_column(df)
    if not dt_col:
        raise ValueError("Kolom waktu/tanggal tidak terdeteksi di CSV.")

    df[dt_col] = pd.to_datetime(df[dt_col], errors="coerce")
    df = df.dropna(subset=[dt_col]).sort_values(dt_col)

    energy_cols = detect_energy_columns(df, dt_col)
    if not energy_cols:
        raise ValueError("Kolom energi tidak terdeteksi (kWh/energy/power).")

    for c in energy_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    df["energy_total_kwh"] = df[energy_cols].sum(axis=1, skipna=True)

    return {
        "df": df,
        "datetime_col": dt_col,
        "energy_cols": energy_cols,
        "source_name": source_name
    }

def aggregate(df: pd.DataFrame, dt_col: str, freq: str = "H") -> pd.DataFrame:
    """
    freq: 'H' hourly, 'D' daily, 'MS' month start, dll
    """
    x = df[[dt_col, "energy_total_kwh"]].copy()
    x = x.dropna(subset=["energy_total_kwh"])
    x = x.set_index(dt_col)

    agg = x["energy_total_kwh"].resample(freq).sum().to_frame("kwh")
    agg = agg.reset_index().rename(columns={dt_col: "ts"})
    return agg

def anomaly_heatmap_weekday_hour(ts_anom: pd.DataFrame) -> pd.DataFrame:
    """
    ts_anom: hasil anomaly (kolom minimal: ts, is_anomaly)
    output: pivot weekday x hour berisi COUNT anomali
    """
    x = ts_anom.copy()
    x = x[x["is_anomaly"] == True]

    order = ["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"]

    if len(x) == 0:
        return pd.DataFrame(0, index=order, columns=list(range(24)))

    x["weekday"] = x["ts"].dt.day_name()
    x["hour"] = x["ts"].dt.hour
    x["weekday"] = pd.Categorical(x["weekday"], categories=order, ordered=True)

    pivot = x.pivot_table(index="weekday", columns="hour", values="kwh", aggfunc="count").fillna(0).astype(int)

    for h in range(24):
        if h not in pivot.columns:
            pivot[h] = 0
    pivot = pivot[[h for h in range(24)]]
    return pivot
