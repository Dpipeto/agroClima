"""
page_mineria.py — Minería de Datos · AgroClima Colombia
────────────────────────────────────────────────────────
Técnicas implementadas:
  1. Clustering K-Means (Sensores IoT)        → 4 grupos de condiciones agroclimáticas
  2. Reglas de Asociación Apriori (EVA)       → patrones cultivo × región × rendimiento × ENSO
  3. Clasificación Random Forest (Sensores)   → predicción alerta_calor (Accuracy 99.8%)
"""
import warnings
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from dash import dcc, html

warnings.filterwarnings("ignore")

from theme import (ptpl, card, kpi, G2, G3, G4, G31,
                   BG, S1, S2, VERDE, ROJO, AZUL, ORO, LAVANDA,
                   PAPER, GRIS, BORDE, MONO, ENSO_C, XAXIS, YAXIS, LEGEND)

# ──────────────────────────────────────────────────────────────
#  Computar todos los resultados de minería al importar
# ──────────────────────────────────────────────────────────────
import os, sys
BASE = os.path.join(os.path.dirname(__file__), "..", "data")

def _compute():
    from sklearn.preprocessing import StandardScaler
    from sklearn.cluster import KMeans
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import train_test_split, cross_val_score
    from sklearn.metrics import accuracy_score, confusion_matrix
    from mlxtend.frequent_patterns import apriori, association_rules
    from mlxtend.preprocessing import TransactionEncoder

    results = {}

    # ── 1. CLUSTERING ─────────────────────────────────────────
    df_s = pd.read_csv(os.path.join(BASE, "Sensores_IoT.csv")).dropna()
    df_s = df_s[df_s["temperatura_c"].between(5, 40) & df_s["humedad_suelo_pct"].between(0, 100)]

    feats = ["temperatura_c", "humedad_suelo_pct", "ph_suelo", "rendimiento_t_ha"]
    X = df_s[feats].values
    scaler = StandardScaler()
    Xn = scaler.fit_transform(X)

    # Elbow method k=2..8
    inercias = []
    for k in range(2, 9):
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        km.fit(Xn)
        inercias.append(round(km.inertia_, 1))
    results["elbow"] = {"ks": list(range(2, 9)), "inercias": inercias}

    km4 = KMeans(n_clusters=4, random_state=42, n_init=10)
    df_s = df_s.copy()
    df_s["cluster"] = km4.fit_predict(Xn)

    centroids_df = df_s.groupby("cluster")[feats].mean().round(3).reset_index()
    labels_map = {
        0: "Tropical Húmedo",
        1: "Templado Moderado",
        2: "Seco Ácido",
        3: "Alto Andino"
    }
    centroids_df["nombre"] = centroids_df["cluster"].map(labels_map)
    results["centroids"] = centroids_df.to_dict("records")

    cult_cluster = df_s.groupby(["cluster", "cultivo"]).size().reset_index(name="n")
    cult_cluster["nombre"] = cult_cluster["cluster"].map(labels_map)
    results["cult_cluster"] = cult_cluster.to_dict("records")

    results["scatter_cluster"] = df_s[["temperatura_c", "humedad_suelo_pct",
                                       "rendimiento_t_ha", "cultivo", "cluster"]].copy()
    results["scatter_cluster"]["cluster_label"] = results["scatter_cluster"]["cluster"].map(labels_map)

    # ── 2. REGLAS DE ASOCIACIÓN ───────────────────────────────
    df_e = pd.read_csv(os.path.join(BASE, "EVA_produccion.csv")).dropna()
    df_e = df_e[df_e["Produccion_t"] > 0]

    df_e = df_e.copy()
    df_e["Rend_Cat"] = pd.qcut(df_e["Rendimiento_t_ha"], 3, labels=["Rend_Bajo", "Rend_Medio", "Rend_Alto"])
    df_e["Area_Cat"] = pd.qcut(df_e["Area_Sembrada_ha"], 3, labels=["Area_Peq", "Area_Med", "Area_Gran"])

    transactions = []
    for _, row in df_e.iterrows():
        t = [
            f"ENSO_{row['Fenomeno_ENSO'].replace(' ', '_')}",
            f"Reg_{row['Región'].replace(' ', '').replace('Ó', 'o')[:8]}",
            f"Cult_{row['Cultivo'][:8]}",
            str(row["Rend_Cat"]),
            str(row["Area_Cat"]),
        ]
        transactions.append(t)

    te = TransactionEncoder()
    te_arr = te.fit_transform(transactions)
    df_bin = pd.DataFrame(te_arr, columns=te.columns_)
    freq = apriori(df_bin, min_support=0.05, use_colnames=True)
    rules = association_rules(freq, metric="lift", min_threshold=1.2,
                              num_itemsets=len(freq))
    rules = rules.sort_values("lift", ascending=False).head(20)

    rules_list = []
    for _, r in rules.iterrows():
        rules_list.append({
            "antecedente": ", ".join(sorted(r["antecedents"])),
            "consecuente": ", ".join(sorted(r["consequents"])),
            "soporte":     round(float(r["support"]), 3),
            "confianza":   round(float(r["confidence"]), 3),
            "lift":        round(float(r["lift"]), 2),
        })
    results["rules"] = rules_list

    # Scatter soporte × confianza para top reglas
    results["rules_scatter"] = pd.DataFrame(rules_list)

    # ── 3. CLASIFICACIÓN Random Forest ───────────────────────
    df_cl = pd.read_csv(os.path.join(BASE, "Sensores_IoT.csv")).dropna()
    df_cl = df_cl[df_cl["temperatura_c"].between(5, 40) & df_cl["humedad_suelo_pct"].between(0, 100)]

    X2 = df_cl[["temperatura_c", "humedad_suelo_pct", "ph_suelo", "rendimiento_t_ha"]].values
    y2 = df_cl["alerta_calor"].values

    X_tr, X_te, y_tr, y_te = train_test_split(X2, y2, test_size=0.25, random_state=42, stratify=y2)
    sc2 = StandardScaler()
    X_tr_s = sc2.fit_transform(X_tr)
    X_te_s = sc2.transform(X_te)

    rf = RandomForestClassifier(n_estimators=200, max_depth=10, random_state=42)
    rf.fit(X_tr_s, y_tr)
    y_pred = rf.predict(X_te_s)

    results["rf_acc"]   = round(accuracy_score(y_te, y_pred) * 100, 2)
    results["rf_cv"]    = round(cross_val_score(rf, X_tr_s, y_tr, cv=5).mean() * 100, 2)
    results["rf_cm"]    = confusion_matrix(y_te, y_pred).tolist()
    results["rf_fi"]    = dict(zip(
        ["Temperatura", "Humedad Suelo", "pH Suelo", "Rendimiento"],
        rf.feature_importances_.round(4).tolist()
    ))

    # Decision boundary sample: temperatura vs rendimiento
    grid_t = np.linspace(5, 40, 60)
    grid_r = np.linspace(df_cl["rendimiento_t_ha"].min(), df_cl["rendimiento_t_ha"].max(), 60)
    T, R = np.meshgrid(grid_t, grid_r)
    Xgrid = sc2.transform(np.column_stack([
        T.ravel(),
        np.full(T.size, df_cl["humedad_suelo_pct"].median()),
        np.full(T.size, df_cl["ph_suelo"].median()),
        R.ravel(),
    ]))
    Z = rf.predict(Xgrid).reshape(T.shape)
    results["boundary"] = {"T": grid_t.tolist(), "R": grid_r.tolist(), "Z": Z.tolist()}

    return results

# ── Calcular una sola vez ─────────────────────────────────────
_R = _compute()

# ──────────────────────────────────────────────────────────────
#  Colores de clusters
# ──────────────────────────────────────────────────────────────
CLUSTER_C = {
    "Tropical Húmedo":  VERDE,
    "Templado Moderado": AZUL,
    "Seco Ácido":       ROJO,
    "Alto Andino":      ORO,
}

def layout():
    # ── KPIs ─────────────────────────────────────────────────
    n_rules   = len(_R["rules"])
    best_lift = max(r["lift"] for r in _R["rules"])
    top_rule  = max(_R["rules"], key=lambda r: r["lift"])

    # ── FIG 1 · Elbow ────────────────────────────────────────
    fig_elbow = go.Figure(go.Scatter(
        x=_R["elbow"]["ks"],
        y=_R["elbow"]["inercias"],
        mode="lines+markers",
        line=dict(color=VERDE, width=2),
        marker=dict(size=8, color=[ROJO if k == 4 else VERDE
                                    for k in _R["elbow"]["ks"]]),
    ))
    fig_elbow.add_vline(x=4, line_dash="dash", line_color=ROJO, line_width=1.5)
    fig_elbow.update_layout(
        **ptpl(),
        title=dict(text="Método del Codo · K óptimo = 4",
                   font=dict(color=VERDE, size=12)),
        xaxis=dict(**XAXIS, title="Número de clusters (K)"),
        yaxis=dict(**YAXIS, title="Inercia (WCSS)"),
    )

    # ── FIG 2 · Scatter clusters ─────────────────────────────
    sdf = _R["scatter_cluster"]
    fig_scatter = go.Figure()
    for lbl, col in CLUSTER_C.items():
        sub = sdf[sdf["cluster_label"] == lbl]
        fig_scatter.add_trace(go.Scatter(
            x=sub["temperatura_c"],
            y=sub["humedad_suelo_pct"],
            mode="markers",
            name=lbl,
            marker=dict(color=col, size=5, opacity=0.7),
            text=sub["cultivo"],
            hovertemplate="%{text}<br>T=%{x}°C · H=%{y}%<extra></extra>",
        ))
    fig_scatter.update_layout(
        **ptpl(),
        title=dict(text="Clusters K-Means · Temperatura vs Humedad",
                   font=dict(color=VERDE, size=12)),
        xaxis=dict(**XAXIS, title="Temperatura (°C)"),
        yaxis=dict(**YAXIS, title="Humedad suelo (%)"),
        legend=LEGEND,
    )

    # ── FIG 3 · Centroides ───────────────────────────────────
    cats = _R["centroids"]
    cat_names = [c["nombre"] for c in cats]
    feats_disp = ["temperatura_c", "humedad_suelo_pct", "ph_suelo", "rendimiento_t_ha"]
    feat_labels = ["Temp °C", "Humedad %", "pH Suelo", "Rend t/ha"]

    fig_centroid = go.Figure()
    for feat, flbl in zip(feats_disp, feat_labels):
        vals = []
        for c in cats:
            vals.append(c[feat])
        fig_centroid.add_trace(go.Bar(
            name=flbl,
            x=cat_names,
            y=vals,
            marker_line_width=0,
        ))
    colors_bar = [VERDE, AZUL, ROJO, ORO]
    for i, trace in enumerate(fig_centroid.data):
        trace.marker.color = colors_bar[i % len(colors_bar)]
    fig_centroid.update_layout(
        **ptpl(),
        barmode="group",
        title=dict(text="Centroides de clusters · Variables promedio",
                   font=dict(color=VERDE, size=12)),
        xaxis=XAXIS, yaxis=YAXIS, legend=LEGEND,
    )

    # ── FIG 4 · Cultivos × Cluster ───────────────────────────
    cc = pd.DataFrame(_R["cult_cluster"])
    fig_cult = go.Figure()
    cultivos = cc["cultivo"].unique()
    cult_colors = {"Arroz": ORO, "Café": "#C85C2A", "Maíz": VERDE,
                   "Papa": AZUL, "Plátano": LAVANDA}
    for cult in cultivos:
        sub = cc[cc["cultivo"] == cult]
        fig_cult.add_trace(go.Bar(
            name=cult,
            x=sub["nombre"],
            y=sub["n"],
            marker_color=cult_colors.get(cult, GRIS),
            marker_line_width=0,
        ))
    fig_cult.update_layout(
        **ptpl(),
        barmode="stack",
        title=dict(text="Distribución de cultivos por cluster",
                   font=dict(color=VERDE, size=12)),
        xaxis=XAXIS, yaxis=dict(**YAXIS, title="Observaciones"),
        legend=LEGEND,
    )

    # ── FIG 5 · Reglas scatter soporte×confianza ─────────────
    rdf = _R["rules_scatter"]
    fig_rules = go.Figure(go.Scatter(
        x=rdf["soporte"],
        y=rdf["confianza"],
        mode="markers",
        marker=dict(
            size=rdf["lift"] * 5,
            color=rdf["lift"],
            colorscale=[[0, S2], [0.5, AZUL], [1, ROJO]],
            showscale=True,
            colorbar=dict(title="Lift", thickness=10, tickfont=dict(size=9)),
            line=dict(width=0.5, color=BORDE),
        ),
        text=rdf["antecedente"] + " ⇒ " + rdf["consecuente"],
        hovertemplate="%{text}<br>Soporte=%{x:.3f} · Confianza=%{y:.3f}<extra></extra>",
    ))
    fig_rules.update_layout(
        **ptpl(),
        title=dict(text="Reglas de Asociación · Soporte × Confianza (tamaño=Lift)",
                   font=dict(color=VERDE, size=12)),
        xaxis=dict(**XAXIS, title="Soporte"),
        yaxis=dict(**YAXIS, title="Confianza"),
    )

    # ── FIG 6 · Importancia de variables ─────────────────────
    fi_items = sorted(_R["rf_fi"].items(), key=lambda x: x[1])
    fig_fi = go.Figure(go.Bar(
        y=[x[0] for x in fi_items],
        x=[x[1] for x in fi_items],
        orientation="h",
        marker=dict(
            color=[x[1] for x in fi_items],
            colorscale=[[0, S2], [0.5, AZUL], [1, ROJO]],
            showscale=False,
        ),
        marker_line_width=0,
        text=[f"{x[1]*100:.1f}%" for x in fi_items],
        textposition="outside",
        textfont=dict(color=PAPER, size=10),
    ))
    fig_fi.update_layout(
        paper_bgcolor=S1,
        plot_bgcolor=S2,
        font=dict(family=MONO, color=PAPER, size=11),
        title=dict(text="Random Forest · Importancia de variables",
                font=dict(color=VERDE, size=12)),
        xaxis=dict(**XAXIS, title="Importancia relativa"),
        yaxis=dict(gridcolor="rgba(74,222,128,0.07)", linecolor=BORDE,
                tickfont=dict(size=10)),
        margin=dict(t=50, b=40, l=140, r=80),
    )

    # ── FIG 7 · Matriz de confusión ──────────────────────────
    cm = _R["rf_cm"]
    labels = ["Sin Alerta", "Alerta Calor"]
    fig_cm = go.Figure(go.Heatmap(
        z=cm,
        x=labels,
        y=labels,
        colorscale=[[0, S2], [0.4, AZUL], [1, ROJO]],
        text=[[str(v) for v in row] for row in cm],
        texttemplate="%{text}",
        textfont=dict(size=16, color=PAPER),
        showscale=False,
    ))
    fig_cm.update_layout(
        **ptpl(),
        title=dict(text="Matriz de Confusión · Random Forest",
                   font=dict(color=VERDE, size=12)),
        xaxis=dict(title="Predicción", **XAXIS),
        yaxis=dict(title="Real", gridcolor="rgba(74,222,128,0.07)",
                   linecolor=BORDE, tickfont=dict(size=10)),
        margin=dict(t=50, b=60, l=80, r=20),
    )

    # ── FIG 8 · Decision boundary heatmap ───────────────────
    Z_vals = _R["boundary"]["Z"]
    T_vals = _R["boundary"]["T"]
    R_vals = _R["boundary"]["R"]
    fig_boundary = go.Figure(go.Heatmap(
        x=T_vals,
        y=R_vals,
        z=Z_vals,
        colorscale=[[0, AZUL], [1, ROJO]],
        showscale=True,
        colorbar=dict(title="Clase", tickvals=[0, 1],
                      ticktext=["Sin Alerta", "Alerta Calor"],
                      thickness=10, tickfont=dict(size=9)),
        opacity=0.75,
    ))
    fig_boundary.update_layout(
        **ptpl(),
        title=dict(text="Frontera de Decisión · Temperatura vs Rendimiento",
                   font=dict(color=VERDE, size=12)),
        xaxis=dict(**XAXIS, title="Temperatura (°C)"),
        yaxis=dict(**YAXIS, title="Rendimiento (t/ha)"),
    )

    # ── Tabla de reglas ──────────────────────────────────────
    top_rules = _R["rules"][:8]

    def rule_row(r, i):
        lift_color = ROJO if r["lift"] > 5 else (ORO if r["lift"] > 2 else VERDE)
        return html.Tr([
            html.Td(str(i+1), style={"color": GRIS, "fontFamily": MONO,
                                      "fontSize": "0.5rem", "padding": "6px 10px"}),
            html.Td(r["antecedente"], style={"fontFamily": MONO, "fontSize": "0.5rem",
                                              "color": PAPER, "padding": "6px 10px"}),
            html.Td(r["consecuente"], style={"fontFamily": MONO, "fontSize": "0.5rem",
                                              "color": AZUL, "padding": "6px 10px"}),
            html.Td(f"{r['soporte']:.3f}", style={"fontFamily": MONO, "fontSize": "0.5rem",
                                                    "color": VERDE, "textAlign": "right",
                                                    "padding": "6px 10px"}),
            html.Td(f"{r['confianza']:.3f}", style={"fontFamily": MONO, "fontSize": "0.5rem",
                                                      "color": ORO, "textAlign": "right",
                                                      "padding": "6px 10px"}),
            html.Td(f"{r['lift']:.2f}", style={"fontFamily": MONO, "fontSize": "0.55rem",
                                                "fontWeight": "700", "color": lift_color,
                                                "textAlign": "right", "padding": "6px 10px"}),
        ], style={"borderBottom": f"1px solid {BORDE}",
                  "background": "rgba(74,222,128,0.02)" if i % 2 == 0 else "transparent"})

    # ── Badge helper ─────────────────────────────────────────
    def badge(text, color):
        return html.Span(text, style={
            "fontFamily": MONO, "fontSize": "0.45rem",
            "padding": "3px 10px", "borderRadius": "3px",
            "background": f"rgba({','.join(str(int(color.lstrip('#')[i:i+2], 16)) for i in (0,2,4))},0.12)",
            "border": f"1px solid {color}", "color": color,
            "marginRight": "6px",
        })

    # ──────────────────────────────────────────────────────────
    return html.Div([

        # ── SECCIÓN 1: Header ─────────────────────────────────
        html.Div([
            html.P("MINERÍA DE DATOS · PATRONES OCULTOS",
                   style={"fontFamily": MONO, "fontSize": "0.45rem",
                           "letterSpacing": "0.25em", "color": GRIS, "margin": "0 0 6px"}),
            html.H2("AgroClima · Descubrimiento de Conocimiento",
                    style={"fontSize": "1.4rem", "fontWeight": "900", "color": PAPER,
                            "margin": "0 0 8px"}),
            html.P("K-Means Clustering · Reglas de Asociación Apriori · Random Forest Classifier",
                   style={"fontFamily": MONO, "fontSize": "0.55rem", "color": GRIS, "margin": 0}),
        ], style={"padding": "18px 0 14px", "borderBottom": f"1px solid {BORDE}",
                  "marginBottom": "16px"}),

        # ── KPIs ─────────────────────────────────────────────
        html.Div([
            kpi("Clusters", "4", VERDE, "Condiciones agroclimáticas"),
            kpi("Reglas", str(n_rules), ORO, f"Lift máx: {best_lift:.1f}x"),
            kpi("RF Accuracy", f"{_R['rf_acc']}%", ROJO, "Predicción alerta calor"),
            kpi("CV Score", f"{_R['rf_cv']}%", AZUL, "Validación cruzada 5-fold"),
        ], style={"display": "grid", "gridTemplateColumns": "1fr 1fr 1fr 1fr",
                  "gap": "14px", "marginBottom": "16px"}),

        # ── CLUSTERING ───────────────────────────────────────
        html.Div([
            html.P("● TÉCNICA 1 · CLUSTERING K-MEANS",
                   style={"fontFamily": MONO, "fontSize": "0.45rem",
                           "letterSpacing": "0.2em", "color": VERDE, "margin": "0 0 4px"}),
            html.P(
                "Segmentación no supervisada de 2.000 lecturas de sensores IoT agrícolas. "
                "K=4 elegido por método del codo. Variables: temperatura, humedad suelo, pH y rendimiento.",
                style={"fontFamily": MONO, "fontSize": "0.5rem", "color": GRIS,
                       "lineHeight": "1.7", "margin": 0}),
        ], style={"background": "rgba(74,222,128,0.04)", "border": f"1px solid {BORDE}",
                  "borderLeft": f"3px solid {VERDE}", "borderRadius": "4px",
                  "padding": "12px 16px", "marginBottom": "14px"}),

        html.Div([
            card("Método del Codo", "Selección de K óptimo",
                 [dcc.Graph(figure=fig_elbow, config={"displayModeBar": False},
                            style={"height": "260px"})]),
            card("Clusters K-Means", "Temperatura vs Humedad · 2000 sensores",
                 [dcc.Graph(figure=fig_scatter, config={"displayModeBar": False},
                            style={"height": "260px"})]),
        ], style={"display": "grid", "gridTemplateColumns": "1fr 1fr",
                  "gap": "14px", "marginBottom": "14px"}),

        html.Div([
            card("Centroides de Clusters", "Valores promedio por grupo agroclimático",
                 [dcc.Graph(figure=fig_centroid, config={"displayModeBar": False},
                            style={"height": "260px"})]),
            card("Cultivos por Cluster", "Composición interna de cada grupo",
                 [dcc.Graph(figure=fig_cult, config={"displayModeBar": False},
                            style={"height": "260px"})]),
        ], style={"display": "grid", "gridTemplateColumns": "1fr 1fr",
                  "gap": "14px", "marginBottom": "16px"}),

        # Leyenda de clusters
        html.Div([
            html.P("INTERPRETACIÓN DE CLUSTERS",
                   style={"fontFamily": MONO, "fontSize": "0.42rem",
                           "letterSpacing": "0.2em", "color": GRIS, "margin": "0 0 8px"}),
            html.Div([
                html.Div([
                    html.Span("▮ ", style={"color": VERDE}),
                    html.Span("Cluster 0 · Tropical Húmedo",
                              style={"fontFamily": MONO, "fontSize": "0.55rem",
                                     "fontWeight": "700", "color": VERDE}),
                    html.Br(),
                    html.Span("T≈23°C · H≈69% · pH 5.5 · Rend 2.9 t/ha — Café + Maíz + Arroz",
                              style={"fontFamily": MONO, "fontSize": "0.48rem", "color": GRIS}),
                ], style={"padding": "8px 12px", "borderLeft": f"3px solid {VERDE}",
                          "marginBottom": "6px"}),
                html.Div([
                    html.Span("▮ ", style={"color": AZUL}),
                    html.Span("Cluster 1 · Templado Moderado",
                              style={"fontFamily": MONO, "fontSize": "0.55rem",
                                     "fontWeight": "700", "color": AZUL}),
                    html.Br(),
                    html.Span("T≈21°C · H≈57% · pH 7.0 · Rend 2.5 t/ha — Café + Maíz + Arroz",
                              style={"fontFamily": MONO, "fontSize": "0.48rem", "color": GRIS}),
                ], style={"padding": "8px 12px", "borderLeft": f"3px solid {AZUL}",
                          "marginBottom": "6px"}),
                html.Div([
                    html.Span("▮ ", style={"color": ROJO}),
                    html.Span("Cluster 2 · Seco Ácido",
                              style={"fontFamily": MONO, "fontSize": "0.55rem",
                                     "fontWeight": "700", "color": ROJO}),
                    html.Br(),
                    html.Span("T≈21°C · H≈36% · pH 5.8 · Rend 1.8 t/ha — Menor rendimiento",
                              style={"fontFamily": MONO, "fontSize": "0.48rem", "color": GRIS}),
                ], style={"padding": "8px 12px", "borderLeft": f"3px solid {ROJO}",
                          "marginBottom": "6px"}),
                html.Div([
                    html.Span("▮ ", style={"color": ORO}),
                    html.Span("Cluster 3 · Alto Andino",
                              style={"fontFamily": MONO, "fontSize": "0.55rem",
                                     "fontWeight": "700", "color": ORO}),
                    html.Br(),
                    html.Span("T≈22°C · H≈59% · pH 6.3 · Rend 18 t/ha — Papa dominante · MÁXIMO rendimiento",
                              style={"fontFamily": MONO, "fontSize": "0.48rem", "color": GRIS}),
                ], style={"padding": "8px 12px", "borderLeft": f"3px solid {ORO}"}),
            ]),
        ], style={"background": S1, "border": f"1px solid {BORDE}", "borderRadius": "4px",
                  "padding": "14px", "marginBottom": "20px"}),

        # ── REGLAS DE ASOCIACIÓN ────────────────────────────
        html.Div([
            html.P("● TÉCNICA 2 · REGLAS DE ASOCIACIÓN · APRIORI",
                   style={"fontFamily": MONO, "fontSize": "0.45rem",
                           "letterSpacing": "0.2em", "color": ORO, "margin": "0 0 4px"}),
            html.P(
                "Minería de patrones frecuentes sobre EVA (928 registros). Variables binarizadas: "
                "cultivo, región, fenómeno ENSO, categoría de rendimiento y categoría de área. "
                "Soporte mínimo: 5% · Lift mínimo: 1.2.",
                style={"fontFamily": MONO, "fontSize": "0.5rem", "color": GRIS,
                       "lineHeight": "1.7", "margin": 0}),
        ], style={"background": "rgba(212,168,32,0.04)", "border": f"1px solid {BORDE}",
                  "borderLeft": f"3px solid {ORO}", "borderRadius": "4px",
                  "padding": "12px 16px", "marginBottom": "14px"}),

        html.Div([
            card("Soporte × Confianza", "Tamaño del punto proporcional al Lift",
                 [dcc.Graph(figure=fig_rules, config={"displayModeBar": False},
                            style={"height": "300px"})]),
            html.Div([
                card("Top 8 Reglas de Asociación", f"{n_rules} reglas · Lift máx {best_lift:.1f}x",
                     [html.Table([
                         html.Thead(html.Tr([
                             html.Th("#", style={"fontFamily": MONO, "fontSize": "0.42rem",
                                                  "color": GRIS, "padding": "6px 10px",
                                                  "borderBottom": f"1px solid {BORDE}"}),
                             html.Th("Antecedente", style={"fontFamily": MONO,
                                                            "fontSize": "0.42rem", "color": GRIS,
                                                            "padding": "6px 10px",
                                                            "borderBottom": f"1px solid {BORDE}"}),
                             html.Th("Consecuente", style={"fontFamily": MONO,
                                                            "fontSize": "0.42rem", "color": GRIS,
                                                            "padding": "6px 10px",
                                                            "borderBottom": f"1px solid {BORDE}"}),
                             html.Th("Sop.", style={"fontFamily": MONO, "fontSize": "0.42rem",
                                                     "color": GRIS, "padding": "6px 10px",
                                                     "textAlign": "right",
                                                     "borderBottom": f"1px solid {BORDE}"}),
                             html.Th("Conf.", style={"fontFamily": MONO, "fontSize": "0.42rem",
                                                      "color": GRIS, "padding": "6px 10px",
                                                      "textAlign": "right",
                                                      "borderBottom": f"1px solid {BORDE}"}),
                             html.Th("Lift", style={"fontFamily": MONO, "fontSize": "0.42rem",
                                                     "color": GRIS, "padding": "6px 10px",
                                                     "textAlign": "right",
                                                     "borderBottom": f"1px solid {BORDE}"}),
                         ])),
                         html.Tbody([rule_row(r, i) for i, r in enumerate(top_rules)]),
                     ], style={"width": "100%", "borderCollapse": "collapse",
                               "fontFamily": MONO})]),
            ]),
        ], style={"display": "grid", "gridTemplateColumns": "1fr 1fr",
                  "gap": "14px", "marginBottom": "20px"}),

        # ── CLASIFICACIÓN ────────────────────────────────────
        html.Div([
            html.P("● TÉCNICA 3 · CLASIFICACIÓN · RANDOM FOREST",
                   style={"fontFamily": MONO, "fontSize": "0.45rem",
                           "letterSpacing": "0.2em", "color": ROJO, "margin": "0 0 4px"}),
            html.P(
                "Clasificación binaria de alerta de calor sobre sensores IoT. "
                "200 árboles, profundidad máxima 10. Entrenamiento 75% / Prueba 25%. "
                f"Accuracy: {_R['rf_acc']}% · CV 5-fold: {_R['rf_cv']}%.",
                style={"fontFamily": MONO, "fontSize": "0.5rem", "color": GRIS,
                       "lineHeight": "1.7", "margin": 0}),
        ], style={"background": "rgba(249,115,22,0.04)", "border": f"1px solid {BORDE}",
                  "borderLeft": f"3px solid {ROJO}", "borderRadius": "4px",
                  "padding": "12px 16px", "marginBottom": "14px"}),

        html.Div([
            card("Importancia de Variables", "Random Forest · Feature Importance",
                 [dcc.Graph(figure=fig_fi, config={"displayModeBar": False},
                            style={"height": "280px"})]),
            card("Matriz de Confusión", "Predicción vs Realidad · 500 muestras test",
                 [dcc.Graph(figure=fig_cm, config={"displayModeBar": False},
                            style={"height": "280px"})]),
        ], style={"display": "grid", "gridTemplateColumns": "1fr 1fr",
                  "gap": "14px", "marginBottom": "14px"}),

        html.Div([
            card("Frontera de Decisión", "Temperatura × Rendimiento · Zona de alerta calor",
                 [dcc.Graph(figure=fig_boundary, config={"displayModeBar": False},
                            style={"height": "280px"})]),
            html.Div([
                card("Métricas del Modelo", "Resumen de rendimiento",
                     [
                         html.Div([
                             html.Div([
                                 html.P("ACCURACY TEST SET", style={"fontFamily": MONO,
                                        "fontSize": "0.4rem", "color": GRIS,
                                        "letterSpacing": "0.15em", "margin": "0 0 2px"}),
                                 html.Div(f"{_R['rf_acc']}%",
                                          style={"fontSize": "2.8rem", "fontWeight": "900",
                                                 "color": ROJO, "lineHeight": "1"}),
                             ], style={"borderBottom": f"1px solid {BORDE}",
                                       "paddingBottom": "12px", "marginBottom": "12px"}),
                             html.Div([
                                 html.P("VALIDACIÓN CRUZADA · 5-FOLD", style={"fontFamily": MONO,
                                        "fontSize": "0.4rem", "color": GRIS,
                                        "letterSpacing": "0.15em", "margin": "0 0 2px"}),
                                 html.Div(f"{_R['rf_cv']}%",
                                          style={"fontSize": "2.8rem", "fontWeight": "900",
                                                 "color": ORO, "lineHeight": "1"}),
                             ], style={"borderBottom": f"1px solid {BORDE}",
                                       "paddingBottom": "12px", "marginBottom": "12px"}),
                             html.Div([
                                 html.P("VARIABLE MÁS IMPORTANTE", style={"fontFamily": MONO,
                                        "fontSize": "0.4rem", "color": GRIS,
                                        "letterSpacing": "0.15em", "margin": "0 0 2px"}),
                                 html.Div("Temperatura",
                                          style={"fontSize": "1.5rem", "fontWeight": "900",
                                                 "color": VERDE, "lineHeight": "1"}),
                                 html.P("96.4% de importancia relativa",
                                        style={"fontFamily": MONO, "fontSize": "0.45rem",
                                               "color": GRIS, "margin": "4px 0 0"}),
                             ]),
                         ], style={"padding": "4px 0"}),
                     ]),
            ]),
        ], style={"display": "grid", "gridTemplateColumns": "1fr 1fr",
                  "gap": "14px", "marginBottom": "20px"}),

        # ── CONCLUSIONES ─────────────────────────────────────
        html.Div([
            html.P("● CONCLUSIONES · PATRONES OCULTOS DESCUBIERTOS",
                   style={"fontFamily": MONO, "fontSize": "0.45rem",
                           "letterSpacing": "0.2em", "color": LAVANDA, "margin": "0 0 12px"}),
            html.Div([
                html.Div([
                    html.Span("C1", style={"fontFamily": MONO, "fontSize": "0.45rem",
                                           "color": VERDE, "fontWeight": "700",
                                           "marginRight": "10px"}),
                    html.Span(
                        "La Papa exhibe un nicho agroclimático exclusivo (Cluster 3 · Alto Andino) "
                        "con rendimientos 6× superiores al promedio (18 t/ha vs 2.5 t/ha), "
                        "evidenciando especialización ecológica que no era visible en EDA tradicional.",
                        style={"fontFamily": MONO, "fontSize": "0.5rem",
                               "color": PAPER, "lineHeight": "1.7"}),
                ], style={"display": "flex", "marginBottom": "10px",
                          "padding": "10px", "borderLeft": f"2px solid {VERDE}",
                          "background": "rgba(74,222,128,0.03)"}),
                html.Div([
                    html.Span("C2", style={"fontFamily": MONO, "fontSize": "0.45rem",
                                           "color": ORO, "fontWeight": "700",
                                           "marginRight": "10px"}),
                    html.Span(
                        "La regla Frijol ⇒ {Área Pequeña, Rendimiento Bajo, Región Andina} "
                        "tiene confianza 100% y lift 14.5x, revelando que este cultivo está "
                        "confinado estructuralmente a minifundios andinos de baja productividad.",
                        style={"fontFamily": MONO, "fontSize": "0.5rem",
                               "color": PAPER, "lineHeight": "1.7"}),
                ], style={"display": "flex", "marginBottom": "10px",
                          "padding": "10px", "borderLeft": f"2px solid {ORO}",
                          "background": "rgba(212,168,32,0.03)"}),
                html.Div([
                    html.Span("C3", style={"fontFamily": MONO, "fontSize": "0.45rem",
                                           "color": ROJO, "fontWeight": "700",
                                           "marginRight": "10px"}),
                    html.Span(
                        "La temperatura es el predictor dominante de alertas de calor (96.4% de "
                        "importancia relativa). El Random Forest alcanza 99.8% de accuracy, "
                        "confirmando que las alertas siguen una frontera de decisión casi perfectamente "
                        "lineal en el eje térmico — umbral crítico ≈ 35°C.",
                        style={"fontFamily": MONO, "fontSize": "0.5rem",
                               "color": PAPER, "lineHeight": "1.7"}),
                ], style={"display": "flex", "marginBottom": "10px",
                          "padding": "10px", "borderLeft": f"2px solid {ROJO}",
                          "background": "rgba(249,115,22,0.03)"}),
                html.Div([
                    html.Span("C4", style={"fontFamily": MONO, "fontSize": "0.45rem",
                                           "color": AZUL, "fontWeight": "700",
                                           "marginRight": "10px"}),
                    html.Span(
                        "Las condiciones de baja humedad (Cluster 2 · Seco Ácido) producen un "
                        "rendimiento sistemáticamente menor (1.85 t/ha), siendo el estrés hídrico "
                        "el factor limitante más crítico para Café, Arroz y Maíz en Colombia.",
                        style={"fontFamily": MONO, "fontSize": "0.5rem",
                               "color": PAPER, "lineHeight": "1.7"}),
                ], style={"display": "flex",
                          "padding": "10px", "borderLeft": f"2px solid {AZUL}",
                          "background": "rgba(56,189,248,0.03)"}),
            ]),
        ], style={"background": S1, "border": f"1px solid {BORDE}", "borderRadius": "4px",
                  "padding": "16px", "marginBottom": "20px"}),

    ], style={"color": PAPER})