# app.py
from __future__ import annotations
from flask import Flask, render_template, request, send_file
from plotly.io import to_html
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import datetime
import io

from config import Config
from services.data_service import load_energy_data, load_holiday_database, aggregate, anomaly_heatmap_weekday_hour
from services.anomaly_service import detect_anomaly_isoforest

app = Flask(__name__)
app.config.from_object(Config)

# Load database hari libur satu kali saat aplikasi dijalankan
HOLIDAYS = load_holiday_database(app.config["DATABASE_LIBUR_PATH"])

def pick_source_path(source: str):
    """Menentukan file CSV mana yang akan dibaca berdasarkan pilihan user."""
    return app.config["HARVESTED_DATA_PATH"] if source == "harvested" else app.config["DEFAULT_DATA_PATH"]

def is_hari_libur(ts: pd.Timestamp) -> bool:
    """Mengecek apakah suatu tanggal adalah hari libur atau akhir pekan."""
    key = ts.strftime("%Y-%m-%d")
    if key in HOLIDAYS:
        return True
    return ts.weekday() >= 5  # Sabtu=5, Minggu=6

def make_blue_shadow_line(ts_anom: pd.DataFrame, title: str):
    """Membuat grafik garis dengan efek bayangan biru dan titik anomali merah kontras."""
    x = ts_anom.copy().dropna(subset=["kwh"])
    if len(x) == 0:
        fig = go.Figure()
        fig.update_layout(template="plotly_dark", title=title, height=420)
        return fig

    y = x["kwh"].astype(float).values
    fig = go.Figure()

    # Efek pseudo-gradient (shadow) di bawah garis agar lebih estetik
    fig.add_trace(go.Scatter(x=x["ts"], y=0.85 * y, mode="lines", line=dict(width=0), 
                             fill="tozeroy", fillcolor="rgba(59,130,246,0.06)", showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=x["ts"], y=0.95 * y, mode="lines", line=dict(width=0), 
                             fill="tonexty", fillcolor="rgba(59,130,246,0.12)", showlegend=False, hoverinfo="skip"))
    
    # Garis Utama (Biru Terang)
    fig.add_trace(go.Scatter(x=x["ts"], y=y, mode="lines", name="Konsumsi kWh", 
                             line=dict(color="#3B82F6", width=3)))

    # Titik Anomali (Merah Terang agar sangat kontras dengan Biru)
    anom = x[x["is_anomaly"] == True]
    fig.add_trace(go.Scatter(x=anom["ts"], y=anom["kwh"], mode="markers", name="Anomali", 
                             marker=dict(color="#FF4B4B", size=9, line=dict(width=1.5, color="white"))))

    fig.update_layout(
        title=f"<b>{title}</b>",
        template="plotly_dark",
        height=420,
        margin=dict(l=20, r=20, t=60, b=20),
        xaxis_title="Waktu",
        yaxis_title="kWh",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color="#E2E8F0"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    return fig

def make_anomaly_heatmap(pivot_df):
    """Membuat heatmap estetik dengan skema warna profesional (Merah-Kuning-Hijau)."""
    fig = px.imshow(
        pivot_df.values,
        x=[str(h) for h in pivot_df.columns],
        y=[str(d) for d in pivot_df.index],
        aspect="auto",
        color_continuous_scale="RdYlGn_r", # Merah untuk intensitas kejadian tinggi
        labels=dict(x="Jam", y="Hari", color="Total Anomali")
    )
    
    fig.update_layout(
        template="plotly_dark",
        title="<b>Intensitas Waktu Kejadian Anomali</b>",
        height=400,
        margin=dict(l=20, r=20, t=70, b=20),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color="#E2E8F0")
    )
    return fig

def common_data(args, contamination):
    """Fungsi pembantu untuk memproses data berdasarkan filter input user."""
    source = args.get("source", "harvested")
    start = args.get("start")
    end = args.get("end")

    start_dt = pd.to_datetime(start) if start else None
    end_dt = pd.to_datetime(end) if end else None

    loaded = load_energy_data(pick_source_path(source), source_name=source)
    ts = aggregate(loaded["df"], loaded["datetime_col"], freq="H")
    
    if start_dt:
        ts = ts[ts["ts"] >= start_dt]
    if end_dt:
        ts = ts[ts["ts"] <= end_dt]

    # Deteksi Anomali menggunakan Isolation Forest
    ts_anom = detect_anomaly_isoforest(ts, contamination=contamination, random_state=app.config["RANDOM_STATE"])
    
    return source, loaded, ts_anom, start, end

@app.route("/", methods=["GET", "POST"])
@app.route("/home", methods=["GET", "POST"])
def home():
    # Mengambil nilai contamination dari form POST atau parameter GET
    contam_val = request.form.get("contamination") or request.args.get("contamination")
    try:
        contamination = float(contam_val)
    except (TypeError, ValueError):
        contamination = app.config.get("ISO_CONTAMINATION", 0.02)

    args = request.form if request.method == "POST" else request.args
    source, loaded, ts_anom, start, end = common_data(args, contamination)

    # 1) Perhitungan Statistik KPI untuk Dashboard
    anom_only = ts_anom[ts_anom["is_anomaly"] == True]
    total_kwh = ts_anom["kwh"].sum()
    high_usage_count = len(anom_only[anom_only["anom_category"] == "HIGH_USAGE"])
    low_usage_count = len(anom_only[anom_only["anom_category"] == "LOW_USAGE"])

    # 2) Render Grafik & Heatmap
    chart_line = to_html(make_blue_shadow_line(ts_anom, "Tren Konsumsi & Deteksi Anomali"), include_plotlyjs="cdn", full_html=False)
    
    pivot_hm = anomaly_heatmap_weekday_hour(ts_anom)
    chart_hm = to_html(make_anomaly_heatmap(pivot_hm), include_plotlyjs=False, full_html=False)

    # 3) Menyiapkan Tabel Anomali (30 Data Terbaru)
    anom_table = anom_only.sort_values("ts", ascending=False).head(30).copy()
    if not anom_table.empty:
        anom_table["status_hari"] = anom_table["ts"].apply(lambda t: "Hari Libur" if is_hari_libur(pd.Timestamp(t)) else "Hari Kerja")
    
    return render_template(
        "home.html",
        active="home",
        source=source,
        start=start or "",
        end=end or "",
        chart_line=chart_line,
        chart_hm=chart_hm,
        rows=anom_table.to_dict("records"),
        contamination=contamination,
        total_kwh=total_kwh,
        high_usage_count=high_usage_count,
        low_usage_count=low_usage_count
    )

@app.route("/heatmap")
def heatmap():
    contamination = float(request.args.get("contamination", app.config["ISO_CONTAMINATION"]))
    source, _, ts_anom, start, end = common_data(request.args, contamination)
    chart = to_html(make_anomaly_heatmap(anomaly_heatmap_weekday_hour(ts_anom)), include_plotlyjs="cdn", full_html=False)
    return render_template("heatmap.html", active="heatmap", source=source, start=start or "", end=end or "", chart=chart, contamination=contamination)

@app.route("/anomalies")
def anomalies():
    contamination = float(request.args.get("contamination", app.config["ISO_CONTAMINATION"]))
    source, _, ts_anom, start, end = common_data(request.args, contamination)
    anom = ts_anom[ts_anom["is_anomaly"] == True].copy().sort_values("ts", ascending=False)
    if len(anom):
        anom["status_hari"] = anom["ts"].apply(lambda t: "Hari Libur" if is_hari_libur(pd.Timestamp(t)) else "Hari Kerja")
    return render_template("anomalies.html", active="anomalies", source=source, start=start or "", end=end or "", rows=anom.head(500).to_dict("records"), contamination=contamination)

@app.route("/download_anomalies")
def download_anomalies():
    contamination = float(request.args.get("contamination", app.config["ISO_CONTAMINATION"]))
    source, _, ts_anom, _, _ = common_data(request.args, contamination)
    anom = ts_anom[ts_anom["is_anomaly"] == True].copy()
    output = io.StringIO()
    anom.to_csv(output, index=False)
    mem = io.BytesIO()
    mem.write(output.getvalue().encode('utf-8'))
    mem.seek(0)
    return send_file(mem, as_attachment=True, download_name=f"anomali_{source}_{datetime.now().strftime('%Y%m%d')}.csv", mimetype="text/csv")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
