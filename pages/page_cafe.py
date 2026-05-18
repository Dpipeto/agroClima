"""
pages/page_cafe.py — AgroNET · Estadísticas Cafeteras Mensuales
Fuente: agronet.gov.co · 2000-2024 · 289 meses
"""
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from dash import dcc, html

import engine as e
from theme import (ptpl, card, kpi, G2, G4,
                   VERDE, ROJO, AZUL, ORO, ENSO_C,
                   XAXIS, YAXIS, LEGEND)


def layout():
    k     = e.cafe_kpis()
    mens  = e.cafe_mensual()
    pdat  = e.cafe_precio_doble_eje()
    est   = e.cafe_estacionalidad()
    pvse  = e.cafe_prod_vs_exp_anual()

    df_m   = pd.DataFrame(mens)
    df_p   = pd.DataFrame(pdat)
    df_est = pd.DataFrame(est)
    df_pe  = pd.DataFrame(pvse)

    # Barras producción mensual coloreadas por ENSO
    fig_mens = go.Figure()
    for en, col in ENSO_C.items():
        sub = df_m[df_m["enso"] == en]
        fig_mens.add_trace(go.Bar(
            x=sub["fecha"], y=sub["prod"],
            name=en, marker_color=col,
            marker_line_width=0, opacity=0.85,
        ))
    fig_mens.update_layout(
        **ptpl(),
        barmode="stack",
        title=dict(text="Producción mensual café (sacos 60kg) · 2000-2024",
                   font=dict(color=VERDE, size=12)),
        xaxis_title="Fecha", yaxis_title="sacos 60kg",
        xaxis=dict(gridcolor="rgba(74,222,128,0.07)",
                   linecolor="rgba(74,222,128,0.14)",
                   tickfont=dict(size=7)),
        yaxis=YAXIS,
        legend=LEGEND,
    )

    # Doble eje precio COP / USD
    fig_precio = make_subplots(specs=[[{"secondary_y": True}]])
    fig_precio.add_trace(
        go.Scatter(x=df_p["fecha"], y=df_p["precio_cop"],
                   name="Precio interno (COP/carga)",
                   line=dict(color=ORO, width=1.5)),
        secondary_y=False,
    )
    fig_precio.add_trace(
        go.Scatter(x=df_p["fecha"], y=df_p["precio_ny"],
                   name="Precio NY (USD/lb)",
                   line=dict(color=AZUL, width=1.5)),
        secondary_y=True,
    )
    fig_precio.update_layout(
        **ptpl(),
        title=dict(text="Precio café interno (COP) vs Bolsa NY (USD)",
                   font=dict(color=VERDE, size=12)),
        legend=LEGEND,
    )
    fig_precio.update_xaxes(**XAXIS)
    fig_precio.update_yaxes(title_text="COP/carga", secondary_y=False,
                             gridcolor="rgba(74,222,128,0.07)",
                             linecolor="rgba(74,222,128,0.14)",
                             tickfont=dict(size=8))
    fig_precio.update_yaxes(title_text="USD/libra", secondary_y=True,
                             gridcolor="rgba(74,222,128,0.07)",
                             linecolor="rgba(74,222,128,0.14)",
                             tickfont=dict(size=8))

    # Estacionalidad mensual
    fig_est = go.Figure([
        go.Bar(x=df_est["nombre"], y=df_est["mean"],
               error_y=dict(type="data", array=df_est["std"], visible=True),
               marker_color=VERDE, marker_line_width=0,
               name="Promedio ± std")
    ])
    fig_est.update_layout(
        **ptpl(),
        title=dict(text="Estacionalidad producción café por mes",
                   font=dict(color=VERDE, size=12)),
        xaxis_title="Mes", yaxis_title="Sacos 60kg promedio",
        xaxis=XAXIS, yaxis=YAXIS,
        showlegend=False,
    )

    # Producción vs exportaciones anuales
    fig_pvse = go.Figure()
    fig_pvse.add_trace(go.Bar(
        x=df_pe["año"], y=df_pe["prod"],
        name="Producción", marker_color=VERDE,
        marker_line_width=0, opacity=0.85,
    ))
    fig_pvse.add_trace(go.Bar(
        x=df_pe["año"], y=df_pe["exp"],
        name="Exportaciones", marker_color=AZUL,
        marker_line_width=0, opacity=0.85,
    ))
    for _, row in df_pe[df_pe["enso"] == "El Niño"].iterrows():
        fig_pvse.add_vline(x=row["año"], line_color=ROJO,
                           line_dash="dot", opacity=0.5, line_width=1)
    fig_pvse.update_layout(
        **ptpl(),
        barmode="group",
        title=dict(text="Producción vs Exportaciones cafeteras anuales",
                   font=dict(color=VERDE, size=12)),
        xaxis_title="Año", yaxis_title="sacos 60kg",
        xaxis=XAXIS, yaxis=YAXIS, legend=LEGEND,
    )

    return html.Div([
        html.Div([
            kpi("Meses registrados",   str(k["meses"]),                     ROJO,  "2000-2024 · AgroNET"),
            kpi("Producción pico",     f"{k['prod_pico']/1000:.0f}k sacos", VERDE, "máximo mensual histórico"),
            kpi("Caída El Niño",       f"{k['caida_nino']}%",               ROJO,  "vs año normal"),
            kpi("Precio interno máx.", f"${k['precio_max_M']}M COP/carga",  ORO),
        ], style=G4),
        html.Div([
            card("Producción mensual 2000-2024 por fenómeno ENSO",
                 "Rojo=El Niño · Azul=La Niña · Verde=Normal",
                 [dcc.Graph(figure=fig_mens, config={"displayModeBar": False},
                            style={"height": "360px"})]),
        ], style={"marginBottom": "14px"}),
        html.Div([
            card("Precio interno COP vs Bolsa Nueva York USD",
                 "Doble eje · AgroNET · 2000-2024",
                 [dcc.Graph(figure=fig_precio, config={"displayModeBar": False},
                            style={"height": "320px"})]),
            card("Estacionalidad mensual", "Promedio ± desviación estándar",
                 [dcc.Graph(figure=fig_est, config={"displayModeBar": False},
                            style={"height": "320px"})]),
        ], style=G2),
        html.Div([
            card("Producción vs Exportaciones anuales · líneas rojas = El Niño",
                 "AgroNET · Federación Nacional de Cafeteros",
                 [dcc.Graph(figure=fig_pvse, config={"displayModeBar": False},
                            style={"height": "320px"})]),
        ], style={"marginBottom": "14px"}),
    ])