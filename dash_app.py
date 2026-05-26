"""
dash_app.py
───────────
FIX PRODUCCION:
  · Imports de páginas corregidos: 'from page_xxx' (sin prefijo 'pages.')
    Los archivos page_*.py están en la raíz del proyecto, no en /pages/
  · Cada import envuelto en try/except para diagnosticar errores en producción
  · topbar con color dinámico corregido para todos los colores
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output

from theme import BG, S1, MONO, BORDE, VERDE, ROJO, ORO, LAVANDA, PAPER, GRIS
from theme import sidebar, topbar


def create_dash_app(server):
    app = dash.Dash(
        __name__,
        server=server,
        url_base_pathname="/dashboard/",
        external_stylesheets=[
            dbc.themes.BOOTSTRAP,
            "https://fonts.googleapis.com/css2?family=Courier+Prime:wght@400;700&display=swap",
        ],
        suppress_callback_exceptions=True,
    )
    app.title = "AgroClima Colombia · Dashboard"

    app.layout = html.Div([
        dcc.Location(id="url"),
        sidebar(),
        html.Div([
            html.Div(id="topbar-content"),
            html.Div(id="page-content", style={"padding": "16px 20px"}),
        ], style={"marginLeft": "210px", "minHeight": "100vh", "background": BG}),
    ], style={"background": BG, "minHeight": "100vh", "fontFamily": MONO})

    # ── Página de error reutilizable ──────────────────────────
    def error_page(msg):
        return html.Div([
            html.P("⚠ Error cargando página", style={"fontFamily": MONO,
                   "fontSize": "0.8rem", "color": ROJO, "marginBottom": "8px"}),
            html.Pre(str(msg), style={"fontFamily": MONO, "fontSize": "0.65rem",
                     "color": GRIS, "background": S1, "padding": "12px",
                     "border": f"1px solid {BORDE}", "borderRadius": "4px",
                     "whiteSpace": "pre-wrap", "wordBreak": "break-all"}),
        ])

    @app.callback(
        Output("page-content",   "children"),
        Output("topbar-content", "children"),
        Input("url", "pathname"),
    )
    def render_page(path):
        path = path or "/dashboard/"

        # ── FIX: imports sin prefijo 'pages.' ─────────────────
        if path.endswith("fao"):
            try:
                from pages.page_fao import layout
                return layout(), topbar(
                    "Cambio Climático & Agricultura — Colombia",
                    "FAO FAOSTAT · Producción Agrícola Colombia · 1990-2023 · FAO.ORG",
                    "● FAO · FAOSTAT", VERDE)
            except Exception as ex:
                return error_page(ex), topbar("Error", "page_fao", "● FAO", ROJO)

        if path.endswith("sensores"):
            try:
                from pages.page_sensores import layout
                return layout(), topbar(
                    "Cambio Climático & Agricultura — Colombia",
                    "Smart Farming Sensor Data 2024 · Kaggle · 2,000 Lecturas · Sensores IoT Agrícolas",
                    "▶ Kaggle · SF24", ORO)
            except Exception as ex:
                return error_page(ex), topbar("Error", "page_sensores", "▶ Sensores", ROJO)

        if path.endswith("cropyield"):
            try:
                from pages.page_cropyield import layout
                return layout(), topbar(
                    "Cambio Climático & Agricultura — Colombia",
                    "CropYield Prediction · Kaggle / ONU · 8 Países · 1990-2023",
                    "● Kaggle · ONU", LAVANDA)
            except Exception as ex:
                return error_page(ex), topbar("Error", "page_cropyield", "● CropYield", ROJO)

        if path.endswith("cafe"):
            try:
                from pages.page_cafe import layout
                return layout(), topbar(
                    "Cambio Climático & Agricultura — Colombia",
                    "AgroNET · Estadísticas Cafeteras Mensuales · agronet.gov.co · 2000-2024",
                    "● AgroNET · Café", ROJO)
            except Exception as ex:
                return error_page(ex), topbar("Error", "page_cafe", "● Café", ROJO)

        if path.endswith("mineria"):
            try:
                from pages.page_mineria import layout
                return layout(), topbar(
                    "Cambio Climático & Agricultura — Colombia",
                    "Minería de Datos · K-Means · Apriori · Random Forest · 5 Datasets",
                    "◆ Minería · ML", LAVANDA)
            except Exception as ex:
                return error_page(ex), topbar("Error", "page_mineria", "◆ Minería", ROJO)

        # Default → EVA
        try:
            from pages.page_eva import layout
            return layout(), topbar(
                "Cambio Climático & Agricultura — Colombia",
                "EVA · Evaluaciones Agropecuarias Municipales · datos.gov.co · MADR · 2007-2022",
                "● datos.gov.co", VERDE)
        except Exception as ex:
            return error_page(ex), topbar("Error", "page_eva", "● EVA", ROJO)

    return app