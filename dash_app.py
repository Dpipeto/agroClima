"""
dash_app.py
───────────
Registro del Dash app, layout base y callback de routing.
NO contiene figuras ni lógica de visualización.
Esas viven en pages/page_*.py
"""
import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output

from theme import BG, S1, MONO, BORDE, VERDE, ROJO, ORO, LAVANDA
from theme import sidebar, topbar


def create_dash_app(server):
    """Crea y devuelve el Dash app montado sobre el Flask server."""

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

    # ── Layout base ────────────────────────────────────────────
    app.layout = html.Div([
        dcc.Location(id="url"),
        sidebar(),
        html.Div([
            html.Div(id="topbar-content"),
            html.Div(id="page-content",
                     style={"padding": "16px 20px"}),
        ], style={"marginLeft": "210px", "minHeight": "100vh",
                  "background": BG}),
    ], style={"background": BG, "minHeight": "100vh",
              "fontFamily": MONO})

    # ── Callback router ────────────────────────────────────────
    @app.callback(
        Output("page-content",    "children"),
        Output("topbar-content",  "children"),
        Input("url", "pathname"),
    )
    def render_page(path):
        path = path or "/dashboard/"

        # Importación diferida para no bloquear el arranque
        if path.endswith("fao"):
            from pages.page_fao       import layout
            return layout(), topbar(
                "Cambio Climático & Agricultura — Colombia",
                "FAO FAOSTAT · Producción Agrícola Colombia · 1990-2023 · FAO.ORG",
                "● FAO · FAOSTAT", VERDE,
            )

        if path.endswith("sensores"):
            from pages.page_sensores  import layout
            return layout(), topbar(
                "Cambio Climático & Agricultura — Colombia",
                "Smart Farming Sensor Data 2024 · Kaggle · 2,000 Lecturas · Sensores IoT Agrícolas",
                "▶ Kaggle · SF24", ORO,
            )

        if path.endswith("cropyield"):
            from pages.page_cropyield import layout
            return layout(), topbar(
                "Cambio Climático & Agricultura — Colombia",
                "CropYield Prediction · Kaggle / ONU · 8 Países · 1990-2023",
                "● Kaggle · ONU", LAVANDA,
            )

        if path.endswith("cafe"):
            from pages.page_cafe      import layout
            return layout(), topbar(
                "Cambio Climático & Agricultura — Colombia",
                "AgroNET · Estadísticas Cafeteras Mensuales · agronet.gov.co · 2000-2024 · 289 Meses",
                "● AgroNET · Café", ROJO,
            )

        # Default → EVA
        from pages.page_eva import layout
        return layout(), topbar(
            "Cambio Climático & Agricultura — Colombia",
            "EVA · Evaluaciones Agropecuarias Municipales · datos.gov.co · MADR · 2007-2022",
            "● datos.gov.co", VERDE,
        )

    return app
