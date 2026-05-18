"""
pages/page_sensores.py
──────────────────────
Página 3 — Smart Farming Sensor Data 2024
Fuente: Kaggle · datasetengineer · 2.000 lecturas IoT
"""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import dcc, html

import engine as e
from theme import (ptpl, card, kpi, G2, G4,
                   VERDE, ROJO, AZUL, ORO, LAVANDA, ENSO_C)


def layout():
    k      = e.sensor_kpis()
    sdata  = e.sensor_scatter()
    alerts = e.sensor_alertas_cultivo()
    vdata  = e.sensor_violin()
    cm     = e.sensor_correlacion_matrix()

    # ── Scatter temperatura vs rendimiento ─────────────────────
    df_s = pd.DataFrame(sdata)
    fig_scat = px.scatter(
        df_s, x="temp", y="rend", color="cultivo", size="hum",
        color_discrete_map={
            "Café": "#C85C2A", "Maíz": VERDE,
            "Arroz": ORO, "Papa": AZUL, "Plátano": LAVANDA,
        },
        title="Temperatura vs Rendimiento estimado · Sensores IoT",
        labels={
            "temp": "Temperatura (°C)", "rend": "Rendimiento (t/ha)",
            "cultivo": "cultivo", "hum": "Humedad suelo",
        },
        opacity=0.65,
    )
    fig_scat.add_vline(
        x=30, line_dash="dash", line_color=ROJO,
        annotation_text="30°C umbral",
        annotation_font_color=ROJO, annotation_font_size=9,
    )
    fig_scat.update_layout(
        **ptpl(),
        title=dict(font=dict(color=VERDE, size=12)),
    )

    # ── Barras agrupadas alertas por cultivo ───────────────────
    df_al = pd.DataFrame(alerts)
    df_melt = df_al.melt(
        id_vars="cultivo",
        value_vars=["calor", "hidrico"],
        var_name="Tipo", value_name="N",
    )
    df_melt["Tipo"] = df_melt["Tipo"].map({
        "calor":   "Calor >30°C",
        "hidrico": "Estrés hídrico",
    })
    fig_alerts = px.bar(
        df_melt, x="cultivo", y="N", color="Tipo", barmode="group",
        color_discrete_map={"Calor >30°C": ROJO, "Estrés hídrico": AZUL},
        title="Alertas detectadas por cultivo · Sensores IoT",
        labels={"cultivo": "Cultivo", "N": "Nº alertas", "Tipo": "Tipo"},
    )
    fig_alerts.update_layout(
        **ptpl(),
        title=dict(font=dict(color=VERDE, size=12)),
    )

    # ── Violin temperatura por región ──────────────────────────
    colors = [AZUL, ROJO, VERDE, LAVANDA, ORO]
    fig_vio = go.Figure()
    for idx, (reg, vals) in enumerate(vdata.items()):
        c = colors[idx % len(colors)]
        fig_vio.add_trace(go.Violin(
            y=vals, name=reg,
            box_visible=True, meanline_visible=True,
            fillcolor=c, opacity=0.7, line_color=c,
            points="outliers",
        ))
    fig_vio.update_layout(
        **ptpl(),
        title=dict(text="Distribución de temperatura por región",
                   font=dict(color=VERDE, size=12)),
        yaxis_title="Temperatura (°C)",
        showlegend=False, violinmode="group",
    )

    # ── Scatter matrix correlación ─────────────────────────────
    df_cm = pd.DataFrame(cm)
    fig_mat = px.scatter_matrix(
        df_cm,
        dimensions=["temperatura_c", "humedad_suelo_pct",
                     "ph_suelo",       "rendimiento_t_ha"],
        color=df_cm["alerta_calor"].map({0: VERDE, 1: ROJO}),
        labels={
            "temperatura_c":     "Temp °C",
            "humedad_suelo_pct": "Hum. suelo",
            "ph_suelo":          "pH",
            "rendimiento_t_ha":  "Rend. t/ha",
        },
        title="Matriz de correlación · variables del sensor",
        opacity=0.5,
    )
    fig_mat.update_layout(
        **ptpl(),
        title=dict(font=dict(color=VERDE, size=12)),
    )
    fig_mat.update_traces(diagonal_visible=False, marker_size=2)

    # ── Layout ─────────────────────────────────────────────────
    return html.Div([
        html.Div([
            kpi("Lecturas de sensores",    f"{k['lecturas']:,}",      ORO,   "2023-2024 · IoT"),
            kpi("Alertas calor >30°C",     str(k["alertas_calor"]),   ROJO,  f"de {k['lecturas']:,} lecturas"),
            kpi("Alertas estrés hídrico",  str(k["alertas_hidrico"]), AZUL,  "humedad suelo <30%"),
            kpi("Cultivos monitoreados",   str(k["n_cultivos"]),      VERDE, f"{k['n_sensores']} sensores únicos"),
        ], style=G4),

        html.Div([
            card("Temperatura vs Rendimiento estimado", "Kaggle · Smart Farming SF24",
                 [dcc.Graph(figure=fig_scat,   config={"displayModeBar": False},
                            style={"height": "360px"})]),
            card("Alertas por cultivo", "Calor extremo + Estrés hídrico",
                 [dcc.Graph(figure=fig_alerts, config={"displayModeBar": False},
                            style={"height": "360px"})]),
        ], style=G2),

        html.Div([
            card("Temperatura por región", "Violín + outliers",
                 [dcc.Graph(figure=fig_vio, config={"displayModeBar": False},
                            style={"height": "360px"})]),
            card("Matriz de correlación sensor", "Verde=normal · Rojo=alerta calor",
                 [dcc.Graph(figure=fig_mat, config={"displayModeBar": False},
                            style={"height": "360px"})]),
        ], style=G2),
    ])
