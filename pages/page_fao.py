"""
pages/page_fao.py
─────────────────
Página 2 — FAO FAOSTAT · Producción histórica Colombia
Fuente: fao.org · Naciones Unidas · 1990-2023
"""
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from dash import dcc, html

import engine as e
from theme import (ptpl, card, kpi, G2, G4,
                   VERDE, ROJO, AZUL, ORO, LAVANDA, ENSO_C)


def layout():
    k     = e.fao_kpis()
    prod  = e.fao_produccion_historica()
    aread = e.fao_area_historica()
    ensod = e.fao_enso_comparacion()
    rmult = e.fao_rendimiento_pequeno_multiplo()

    # ── Área apilada producción histórica ──────────────────────
    fig_area = go.Figure()
    for item, data in prod.items():
        fig_area.add_trace(go.Scatter(
            x=[d["year"] for d in data],
            y=[d["prod"] / 1e6 for d in data],
            name=item, fill="tonexty", mode="lines",
            line=dict(width=0.5),
        ))
    fig_area.update_layout(
        **ptpl(),
        title=dict(text="Producción agrícola Colombia 1990-2023 (FAO)",
                   font=dict(color=VERDE, size=12)),
        xaxis_title="Año", yaxis_title="Producción (millones t)",
    )

    # ── Líneas área cultivada ──────────────────────────────────
    fig_area2 = go.Figure()
    for item, data in aread.items():
        fig_area2.add_trace(go.Scatter(
            x=[d["year"] for d in data],
            y=[d["area"] / 1e6 for d in data],
            name=item, mode="lines", line=dict(width=1.5),
        ))
    fig_area2.update_layout(
        **ptpl(),
        title=dict(text="Área cultivada Colombia 1990-2023 (ha)",
                   font=dict(color=VERDE, size=12)),
        xaxis_title="Año", yaxis_title="Área (millones ha)",
    )

    # ── Barras agrupadas impacto ENSO ──────────────────────────
    df_enso = pd.DataFrame(ensod)
    fig_enso = px.bar(
        df_enso, x="item", y="prod", color="enso", barmode="group",
        color_discrete_map=ENSO_C,
        title="Producción promedio por cultivo y fenómeno ENSO · FAO",
        labels={"item": "Cultivo", "prod": "Producción (t)", "enso": "ENSO"},
    )
    fig_enso.update_layout(
        **ptpl(),
        title=dict(font=dict(color=VERDE, size=12)),
    )

    # ── Pequeño múltiplo rendimiento ───────────────────────────
    items  = list(rmult.keys())
    cols_n = 4
    rows_n = int(np.ceil(len(items) / cols_n))
    fig_mult = make_subplots(
        rows=rows_n, cols=cols_n,
        subplot_titles=items,
        shared_yaxes=False,
    )
    for idx, item in enumerate(items):
        r_idx = idx // cols_n + 1
        c_idx = idx  % cols_n + 1
        data  = rmult[item]
        fig_mult.add_trace(
            go.Scatter(
                x=[d["year"] for d in data],
                y=[d["rend"] for d in data],
                name=item, mode="lines",
                line=dict(width=1.5), showlegend=False,
            ),
            row=r_idx, col=c_idx,
        )
    fig_mult.update_layout(
        **ptpl(),
        title=dict(text="Rendimiento (t/ha) por cultivo · FAO 1990-2023",
                   font=dict(color=VERDE, size=12)),
        height=400,
    )
    fig_mult.update_annotations(font_size=8, font_color=VERDE)

    # ── Layout ─────────────────────────────────────────────────
    return html.Div([
        html.Div([
            kpi("Registros FAO",       str(k["registros"]),          AZUL,    "1990-2023 · 8 cultivos"),
            kpi("Producción total 2023", f"{k['prod_total_MT']}M t", VERDE),
            kpi("Área total 2023",      f"{k['area_total_Mha']}M ha", ORO),
            kpi("Cultivos FAO",         str(k["n_cultivos"]),         LAVANDA, "inc. caña de azúcar"),
        ], style=G4),

        html.Div([
            card("Producción histórica 1990-2023", "Fuente: FAO FAOSTAT · Colombia",
                 [dcc.Graph(figure=fig_area,  config={"displayModeBar": False},
                            style={"height": "360px"})]),
            card("Área cultivada", "Hectáreas por cultivo",
                 [dcc.Graph(figure=fig_area2, config={"displayModeBar": False},
                            style={"height": "360px"})]),
        ], style=G2),

        html.Div([
            card("Impacto ENSO en producción promedio", "El Niño vs La Niña vs Normal",
                 [dcc.Graph(figure=fig_enso, config={"displayModeBar": False},
                            style={"height": "320px"})]),
            card("Rendimiento por cultivo (pequeño múltiplo)", "t/ha · FAO FAOSTAT",
                 [dcc.Graph(figure=fig_mult, config={"displayModeBar": False},
                            style={"height": "320px"})]),
        ], style=G2),
    ])
