"""
pages/page_cropyield.py — CropYield Prediction · Comparativa países
Fuente: Kaggle / ONU · 8 países · 1990-2023
"""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import dcc, html

import engine as e
from theme import (ptpl, card, kpi, G2, G4,
                   VERDE, ROJO, AZUL, ORO, LAVANDA, GRIS, ENSO_C,
                   XAXIS, YAXIS, LEGEND)

PAIS_C = {
    "Colombia":  VERDE,   "Brasil":    ROJO,
    "México":    ORO,     "Perú":      AZUL,
    "Ecuador":   LAVANDA, "Argentina": "#E8A0A0",
    "Venezuela": "#A0C8E8", "Bolivia": "#C8E8A0",
}


def layout():
    k      = e.cyp_kpis()
    cafe_p = e.cyp_cafe_paises()
    top    = e.cyp_top_cultivos_colombia()
    hdata  = e.cyp_heatmap_paises_cultivos()
    lr     = e.cyp_lluvia_rendimiento()
    ecyp   = e.cyp_enso_comparacion()

    # Líneas café por país
    fig_cafe = go.Figure()
    for pais, data in cafe_p.items():
        fig_cafe.add_trace(go.Scatter(
            x=[d["year"] for d in data], y=[d["rend"] for d in data],
            name=pais, mode="lines",
            line=dict(color=PAIS_C.get(pais, GRIS),
                      width=3 if pais == "Colombia" else 1.5),
        ))
    fig_cafe.update_layout(
        **ptpl(),
        title=dict(text="Rendimiento café (t/ha) · Colombia vs países · 1990-2023",
                   font=dict(color=VERDE, size=12)),
        xaxis_title="Año", yaxis_title="Rendimiento (t/ha)",
        xaxis=XAXIS, yaxis=YAXIS, legend=LEGEND,
    )

    # Ranking cultivos Colombia (barras horizontales)
    fig_rank = go.Figure(go.Bar(
        x=[d["rend"] for d in top],
        y=[d["item"] for d in top],
        orientation="h",
        marker=dict(
            color=[d["rend"] for d in top],
            colorscale=[[0, ROJO], [1, VERDE]],
        ),
        text=[f"{d['rend']:.2f}" for d in top],
        textposition="outside",
    ))
    fig_rank.update_layout(
        **ptpl(),
        title=dict(text="Ranking por cultivo · Colombia",
                   font=dict(color=VERDE, size=12)),
        xaxis_title="Rendimiento (t/ha)",
        xaxis=XAXIS,
        yaxis=dict(autorange="reversed",
                   gridcolor="rgba(74,222,128,0.07)",
                   linecolor="rgba(74,222,128,0.14)",
                   tickfont=dict(size=9)),
    )

    # Heatmap países × cultivos
    hdf = pd.DataFrame(hdata).pivot(
        index="pais", columns="item", values="rend"
    ).fillna(0)
    fig_heat = px.imshow(
        hdf,
        color_continuous_scale=[[0, ROJO], [0.5, ORO], [1, VERDE]],
        title="Rendimiento promedio (t/ha) · Países × Cultivos",
        aspect="auto", labels={"color": "t/ha"},
    )
    fig_heat.update_layout(
        **ptpl(),
        title=dict(font=dict(color=VERDE, size=12)),
    )

    # Scatter lluvia vs rendimiento Colombia
    df_lr = pd.DataFrame(lr)
    fig_lr = px.scatter(
        df_lr, x="lluvia", y="rend", color="enso", symbol="item",
        color_discrete_map=ENSO_C,
        title="Lluvia anual vs Rendimiento · Colombia",
        labels={"lluvia": "Lluvia (mm/año)", "rend": "Rendimiento (t/ha)",
                "enso": "ENSO", "item": "Cultivo"},
        trendline="ols", trendline_scope="overall",
        trendline_color_override=ORO, opacity=0.7,
    )
    fig_lr.update_layout(
        **ptpl(),
        title=dict(font=dict(color=VERDE, size=12)),
        xaxis=XAXIS, yaxis=YAXIS, legend=LEGEND,
    )

    # Barras agrupadas ENSO por país
    df_ec = pd.DataFrame(ecyp)
    fig_ec = px.bar(
        df_ec, x="pais", y="rend", color="enso", barmode="group",
        color_discrete_map=ENSO_C,
        title="Rendimiento café por país y fenómeno ENSO",
        labels={"pais": "País", "rend": "Rendimiento (t/ha)", "enso": "ENSO"},
    )
    fig_ec.update_layout(
        **ptpl(),
        title=dict(font=dict(color=VERDE, size=12)),
        xaxis=XAXIS, yaxis=YAXIS, legend=LEGEND,
    )

    return html.Div([
        html.Div([
            kpi("Países analizados",   str(k["paises"]),            LAVANDA, "Colombia · Brasil · México..."),
            kpi("Cultivos globales",    str(k["cultivos"]),          VERDE),
            kpi("Años cubiertos",       "1990-2023",                 AZUL,    f"{k['años']} años"),
            kpi("Rend. Colombia prom.", f"{k['rend_col']:.2f} t/ha", ORO),
        ], style=G4),
        html.Div([
            card("Rendimiento café · Colombia vs países", "Kaggle CropYield · ONU",
                 [dcc.Graph(figure=fig_cafe, config={"displayModeBar": False},
                            style={"height": "340px"})]),
            card("Ranking por cultivo · Colombia", "Promedio 1990-2023",
                 [dcc.Graph(figure=fig_rank, config={"displayModeBar": False},
                            style={"height": "340px"})]),
        ], style=G2),
        html.Div([
            card("Lluvia vs Rendimiento · Colombia", "Correlación + regresión",
                 [dcc.Graph(figure=fig_lr,   config={"displayModeBar": False},
                            style={"height": "320px"})]),
            card("Rendimiento café por país y ENSO", "El Niño vs Normal vs La Niña",
                 [dcc.Graph(figure=fig_ec,   config={"displayModeBar": False},
                            style={"height": "320px"})]),
        ], style=G2),
        html.Div([
            card("Heatmap rendimiento · Países × Cultivos", "Promedio histórico t/ha",
                 [dcc.Graph(figure=fig_heat, config={"displayModeBar": False},
                            style={"height": "320px"})]),
        ], style={"marginBottom": "14px"}),
    ])