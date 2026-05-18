"""
pages/page_eva.py — EVA · Evaluaciones Agropecuarias Municipales
Fuente: datos.gov.co · MADR · 2007-2022
"""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import dcc, html

import engine as e
from theme import (ptpl, card, kpi, G2, G4, G31,
                   VERDE, ROJO, AZUL, ORO, CULT_C, ENSO_C,
                   XAXIS, YAXIS, LEGEND)


def layout():
    k     = e.eva_kpis()
    prod  = e.eva_produccion_anual()
    deps  = e.eva_area_departamento()
    bdata = e.eva_rendimiento_region_enso()
    hdata = e.eva_heatmap_cultivo_enso()

    # Líneas producción por cultivo
    fig_prod = go.Figure()
    for c, data in prod.items():
        fig_prod.add_trace(go.Scatter(
            x=[d["año"] for d in data],
            y=[d["prod"] / 1e6 for d in data],
            name=c, mode="lines",
            line=dict(color=CULT_C.get(c, VERDE), width=2),
        ))
    fig_prod.update_layout(
        **ptpl(),
        title=dict(text="Producción total por cultivo · 2007-2022",
                   font=dict(color=VERDE, size=12)),
        xaxis_title="Año", yaxis_title="Producción (millones t)",
        xaxis=XAXIS, yaxis=YAXIS, legend=LEGEND,
    )

    # Barras horizontales top departamentos
    fig_dep = go.Figure(go.Bar(
        x=[d["area"] / 1e3 for d in deps],
        y=[d["dep"]        for d in deps],
        orientation="h", marker_color=VERDE, marker_line_width=0,
    ))
    fig_dep.update_layout(
        **ptpl(),
        title=dict(text="Top 12 departamentos por área sembrada promedio",
                   font=dict(color=VERDE, size=12)),
        xaxis_title="Ha promedio (miles)",
        xaxis=XAXIS,
        yaxis=dict(autorange="reversed",
                   gridcolor="rgba(74,222,128,0.07)",
                   linecolor="rgba(74,222,128,0.14)",
                   tickfont=dict(size=8)),
    )

    # Box plot rendimiento por región × ENSO
    fig_box = go.Figure()
    for en, col in ENSO_C.items():
        sub = [b for b in bdata if b["enso"] == en]
        for b in sub:
            fig_box.add_trace(go.Box(
                y=b["vals"], name=b["region"],
                marker_color=col, line_color=col,
                legendgroup=en,
                legendgrouptitle_text=en if b == sub[0] else "",
                showlegend=(b == sub[0]),
                boxpoints="outliers", pointpos=0,
            ))
    fig_box.update_layout(
        **ptpl(),
        title=dict(text="Rendimiento (t/ha) por región y fenómeno ENSO",
                   font=dict(color=VERDE, size=12)),
        xaxis_title="Región", yaxis_title="t/ha",
        xaxis=XAXIS, yaxis=YAXIS,
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=10),
                    groupclick="toggleitem"),
    )

    # Heatmap cultivo × ENSO
    hdf = pd.DataFrame(hdata).pivot(
        index="cultivo", columns="enso", values="rend"
    ).fillna(0)
    fig_heat = px.imshow(
        hdf,
        color_continuous_scale=[[0, ROJO], [0.5, ORO], [1, VERDE]],
        title="Rendimiento promedio (t/ha) · Cultivo × Fenómeno ENSO",
        aspect="auto", labels={"color": "t/ha"},
    )
    fig_heat.update_layout(
        **ptpl(),
        title=dict(font=dict(color=VERDE, size=12)),
    )

    return html.Div([
        html.Div([
            kpi("Registros EVA",       f"{k['registros']:,}",    VERDE, "2007-2022 · 18 departamentos"),
            kpi("Área total sembrada", f"{k['area_total_M']}M ha", AZUL, "acumulado histórico"),
            kpi("Caída Rend. El Niño", f"{k['caida_rend_pct']}%", ROJO, "▼ vs año normal"),
            kpi("Cultivos monitoreados", str(k['n_cultivos']),    ORO,  "Aguacate · Arroz · Café..."),
        ], style=G4),
        html.Div([
            card("Producción anual por cultivo", "Fuente: EVA · datos.gov.co",
                 [dcc.Graph(figure=fig_prod, config={"displayModeBar": False},
                            style={"height": "360px"})]),
            card("Área por departamento", "Fuente: EVA · MADR",
                 [dcc.Graph(figure=fig_dep,  config={"displayModeBar": False},
                            style={"height": "360px"})]),
        ], style=G31),
        html.Div([
            card("Rendimiento por región y ENSO", "Distribución estadística",
                 [dcc.Graph(figure=fig_box,  config={"displayModeBar": False},
                            style={"height": "360px"})]),
            card("Heatmap cultivo × ENSO", "t/ha promedio",
                 [dcc.Graph(figure=fig_heat, config={"displayModeBar": False},
                            style={"height": "360px"})]),
        ], style=G2),
    ])