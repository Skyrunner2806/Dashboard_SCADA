# services/anomaly_service.py
from __future__ import annotations
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

def detect_anomaly_isoforest(ts_df: pd.DataFrame, contamination: float = 0.02, random_state: int = 42) -> pd.DataFrame:
    """
    Input: ts_df columns: ['ts','kwh']
    Output: adds ['score','is_anomaly','anom_category']
      - score: decision_function (lebih kecil = lebih anomali)
      - anom_category: HIGH_USAGE / LOW_USAGE (dibanding median)
    """
    x = ts_df.copy().dropna(subset=["kwh"])
    if len(x) == 0:
        x["score"] = []
        x["is_anomaly"] = []
        x["anom_category"] = []
        return x

    scaler = StandardScaler()
    X = scaler.fit_transform(x[["kwh"]].values)

    model = IsolationForest(
        n_estimators=300,
        contamination=contamination,
        random_state=random_state
    )

    pred = model.fit_predict(X)          # -1 anomaly, 1 normal
    score = model.decision_function(X)   # smaller => more anomalous

    x["score"] = score
    x["is_anomaly"] = (pred == -1)

    med = x["kwh"].median()
    x["anom_category"] = "NORMAL"
    x.loc[x["is_anomaly"] & (x["kwh"] >= med), "anom_category"] = "HIGH_USAGE"
    x.loc[x["is_anomaly"] & (x["kwh"] < med), "anom_category"] = "LOW_USAGE"

    return x
