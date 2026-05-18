"""
theme.py
────────
Paleta, constantes de ejes y componentes reutilizables.
ptpl() NO incluye legend/xaxis/yaxis — se usan las constantes
XAXIS, YAXIS, LEGEND directamente en cada update_layout().
"""
from dash import html, dcc

# ── Paleta ─────────────────────────────────────────────────────
BG      = "#0B0F08"
S1      = "#101510"
S2      = "#172015"
VERDE   = "#4ADE80"
ROJO    = "#F97316"
AZUL    = "#38BDF8"
ORO     = "#D4A820"
LAVANDA = "#A78BFA"
PAPER   = "#E8EDE5"
GRIS    = "#5A6355"
BORDE   = "rgba(74,222,128,0.14)"

ENSO_C  = {"El Niño": ROJO, "La Niña": AZUL, "Normal": VERDE}
CULT_C  = {
    "Café":           "#C85C2A",
    "Arroz":          ORO,
    "Maíz":           VERDE,
    "Papa":           AZUL,
    "Plátano":        LAVANDA,
    "Aguacate":       "#B46432",
    "Yuca":           "#78A05A",
    "Frijol":         "#D4909A",
    "Caña de Azúcar": "#8FBC8F",
}

MONO = "'Courier New', 'Lucida Console', monospace"

# ── Grid layouts ───────────────────────────────────────────────
G2  = {"display":"grid","gridTemplateColumns":"1fr 1fr",         "gap":"14px","marginBottom":"14px"}
G3  = {"display":"grid","gridTemplateColumns":"1fr 1fr 1fr",     "gap":"14px","marginBottom":"14px"}
G4  = {"display":"grid","gridTemplateColumns":"1fr 1fr 1fr 1fr", "gap":"14px","marginBottom":"14px"}
G31 = {"display":"grid","gridTemplateColumns":"2fr 1fr",          "gap":"14px","marginBottom":"14px"}
G13 = {"display":"grid","gridTemplateColumns":"1fr 2fr",          "gap":"14px","marginBottom":"14px"}

# ── Constantes de ejes — usar en update_layout() por separado ──
XAXIS  = dict(gridcolor="rgba(74,222,128,0.07)", linecolor=BORDE, tickfont=dict(size=9))
YAXIS  = dict(gridcolor="rgba(74,222,128,0.07)", linecolor=BORDE, tickfont=dict(size=9))
LEGEND = dict(bgcolor="rgba(0,0,0,0)", font=dict(size=10))

# ── Plotly template base ────────────────────────────────────────
def ptpl():
    """Layout base Plotly SIN legend/xaxis/yaxis.
    Agregar esas claves directamente en update_layout() de cada figura.
    """
    return dict(
        paper_bgcolor = S1,
        plot_bgcolor  = S2,
        font          = dict(family=MONO, color=PAPER, size=11),
        margin        = dict(t=50, b=40, l=50, r=20),
    )

# ── Componentes Dash ───────────────────────────────────────────
def kpi(label, val, color=VERDE, sub=None):
    return html.Div([
        html.Div(style={"position":"absolute","top":0,"left":0,"right":0,
                        "height":"2px","background":color}),
        html.P(label, style={"fontFamily":MONO,"fontSize":"0.48rem",
                              "letterSpacing":"0.18em","textTransform":"uppercase",
                              "color":GRIS,"margin":"0 0 6px"}),
        html.Div(val, style={"fontSize":"2.2rem","fontWeight":"900","lineHeight":"1",
                              "color":color,"fontFamily":MONO}),
        html.P(sub, style={"fontFamily":MONO,"fontSize":"0.45rem",
                            "color":GRIS,"marginTop":"4px"}) if sub else None,
    ], style={"background":S1,"border":f"1px solid {BORDE}","borderRadius":"4px",
              "padding":"14px","position":"relative","overflow":"hidden"})


def card(title, subtitle, children):
    return html.Div([
        html.Div([
            html.P(title, style={"fontFamily":MONO,"fontSize":"0.65rem",
                                  "letterSpacing":"0.2em","textTransform":"uppercase",
                                  "color":VERDE,"margin":"0 0 2px"}),
            html.P(subtitle, style={"fontFamily":MONO,"fontSize":"0.5rem",
                                     "color":GRIS,"margin":"0 0 10px"}),
        ]),
        *children,
    ], style={"background":S1,"border":f"1px solid {BORDE}","borderRadius":"4px",
              "padding":"14px","height":"100%"})


def navstyle(active=False):
    return {
        "display":"flex","alignItems":"center","gap":"8px","padding":"8px 14px",
        "fontFamily":MONO,"fontSize":"0.6rem",
        "color":VERDE if active else "rgba(232,237,229,0.45)",
        "borderLeft":f"2px solid {VERDE}" if active else "2px solid transparent",
        "background":"rgba(74,222,128,0.06)" if active else "transparent",
        "textDecoration":"none","transition":"all 0.15s","cursor":"pointer",
    }


def sidebar():
    return html.Div([
        html.Div([
            html.Div("AgroClima", style={"fontSize":"1.3rem","fontWeight":"900",
                                          "color":VERDE,"fontFamily":MONO}),
            html.Div("Colombia",  style={"fontSize":"1.3rem","fontWeight":"900",
                                          "color":PAPER,"fontFamily":MONO}),
            html.P("5 Datasets · Dash + Plotly",
                   style={"fontFamily":MONO,"fontSize":"0.42rem","color":GRIS,"marginTop":"4px"}),
        ], style={"padding":"18px 14px 12px","borderBottom":f"1px solid {BORDE}"}),
        html.Nav([
            html.A([html.Span("🌾 "), "EVA · Producción"],
                   href="/dashboard/eva",       id="nav-eva",      style=navstyle()),
            html.A([html.Span("🌍 "), "FAO · Histórico"],
                   href="/dashboard/fao",       id="nav-fao",      style=navstyle()),
            html.A([html.Span("📡 "), "Sensores 2024"],
                   href="/dashboard/sensores",  id="nav-sensores", style=navstyle()),
            html.A([html.Span("📊 "), "CropYield · Países"],
                   href="/dashboard/cropyield", id="nav-cyp",      style=navstyle()),
            html.A([html.Span("☕ "), "AgroNET · Café"],
                   href="/dashboard/cafe",      id="nav-cafe",     style=navstyle()),
        ], style={"padding":"10px 0","flex":"1"}),
        html.Div([
            html.Div([
                html.P("⚠ ALERTA 2026",
                       style={"fontFamily":MONO,"fontSize":"0.4rem",
                               "letterSpacing":"0.15em","color":ROJO,"margin":"0 0 3px"}),
                html.P("50% prob. El Niño · jul-sep 2026 · IDEAM",
                       style={"fontFamily":MONO,"fontSize":"0.5rem",
                               "color":"rgba(232,237,229,0.65)","lineHeight":"1.4","margin":0}),
            ], style={"background":"rgba(249,115,22,0.13)","border":"1px solid rgba(249,115,22,0.3)",
                      "borderRadius":"4px","padding":"8px 10px"}),
        ], style={"padding":"10px 14px","borderTop":f"1px solid {BORDE}"}),
    ], style={"position":"fixed","top":0,"left":0,"bottom":0,"width":"210px",
              "background":S1,"borderRight":f"1px solid {BORDE}","display":"flex",
              "flexDirection":"column","zIndex":50,"overflowY":"auto"})


def topbar(title, subtitle, badge_text, badge_color=VERDE):
    bg_badge = "rgba(74,222,128,0.12)" if badge_color == VERDE else "rgba(249,115,22,0.12)"
    return html.Div([
        html.Div([
            html.Div(title,  style={"fontSize":"0.95rem","fontWeight":"700","color":PAPER}),
            html.P(subtitle, style={"fontFamily":MONO,"fontSize":"0.44rem","color":GRIS,
                                    "letterSpacing":"0.12em","textTransform":"uppercase","margin":0}),
        ]),
        html.Span(badge_text, style={"fontFamily":MONO,"fontSize":"0.48rem","padding":"4px 12px",
            "borderRadius":"3px","background":bg_badge,
            "border":f"1px solid {badge_color}","color":badge_color}),
    ], style={"display":"flex","justifyContent":"space-between","alignItems":"center",
              "padding":"10px 20px","background":S1,"borderBottom":f"1px solid {BORDE}",
              "position":"sticky","top":0,"zIndex":40})