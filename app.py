"""
app.py
──────
SOLO rutas Flask y montaje del Dash app.
Layout, páginas y lógica visual → dash_app.py
Análisis de datos               → engine.py
Análisis distribuido PySpark    → spark_engine.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
 
import warnings
warnings.filterwarnings("ignore")
 
from flask import Flask, render_template
from dash_app import create_dash_app
from spark_engine import run_spark_analysis       # ← NUEVO
 
# ── Flask server ───────────────────────────────────────────────
server = Flask(__name__, template_folder="templates")
 
# ── Rutas HTML (páginas estáticas) ─────────────────────────────
@server.route("/")
def index():
    return render_template("index.html")
 
@server.route("/problema")
def problema():
    return render_template("problema.html")
 
@server.route("/datasets")
def datasets():
    return render_template("datasets.html")
 
@server.route("/dashboard")
def dashboard_info():
    return render_template("dashboard.html")
 
@server.route("/modelo")
def modelo():
    return render_template("modelo.html")
 
# ── Ruta PySpark ────────────────────────────────────────────── ← NUEVO
@server.route("/spark")
def spark_page():
    data = run_spark_analysis()          # cachea tras la primera llamada
    return render_template("spark.html", **data)
 
@server.route("/spark/refresh")
def spark_refresh():
    """Fuerza re-ejecución del análisis Spark (útil para capturas del informe)."""
    data = run_spark_analysis(force=True)
    return render_template("spark.html", **data)
 
# ── Dash app montado sobre el server Flask ─────────────────────
app = create_dash_app(server)
 
# ── Entry point ────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n🌿  AgroClima Colombia")
    print("   Inicio:       http://localhost:8050/")
    print("   Problema:     http://localhost:8050/problema")
    print("   Datasets:     http://localhost:8050/datasets")
    print("   Dashboard:    http://localhost:8050/dashboard/eva")
    print("   PySpark:      http://localhost:8050/spark\n")    # ← NUEVO
    app.run(debug=False, host="0.0.0.0", port=8050)