"""
engine.py — Motor de datos AgroClima Colombia
──────────────────────────────────────────────
FIX PRODUCCION:
  · DATA path corregido: busca CSVs junto al engine.py (no en /data/)
  · PySpark completamente removido (no hay Java en Render)
  · get_spark() retorna None con advertencia — no rompe el arranque
"""
import os, sys, warnings
import pandas as pd
import numpy as np

warnings.filterwarnings("ignore")

# ── FIX 1: Path robusto — funciona tanto local como en Render ──
# Busca los CSV en el mismo directorio del engine.py
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Detecta si los CSV están en /data/ o en raíz y ajusta automáticamente
_DATA_SUBDIR = os.path.join(_BASE_DIR, "data")
DATA = _DATA_SUBDIR if os.path.isdir(_DATA_SUBDIR) else _BASE_DIR

def _p(f): return os.path.join(DATA, f)

# ── FIX 2: PySpark removido — no disponible en Render (sin Java) ──
_spark = None
def get_spark():
    """PySpark no disponible en producción. Devuelve None sin romper el arranque."""
    return None

# ── Pandas cache ───────────────────────────────────────────────
_cache = {}
def _pd(name):
    if name not in _cache:
        path = _p(name)
        if not os.path.exists(path):
            raise FileNotFoundError(
                f"CSV no encontrado: '{path}'\n"
                f"  Directorio engine.py: {_BASE_DIR}\n"
                f"  DATA resuelto a:      {DATA}\n"
                f"  Archivos disponibles: {os.listdir(DATA) if os.path.isdir(DATA) else 'DIRECTORIO NO EXISTE'}"
            )
        df = pd.read_csv(path)
        if "produccion" in name:
            df = df.dropna(subset=["Cultivo","Produccion_t"])
            df = df[df["Produccion_t"]>0]
            df = df[df["Area_Sembrada_ha"]>0]
        elif "faostat" in name:
            df = df.dropna()
            df = df[df["Value_t"]>0]
        elif "Sensores" in name:
            df = df.dropna()
            df = df[df["temperatura_c"].between(5,40)]
            df = df[df["humedad_suelo_pct"].between(0,100)]
        elif "cafe" in name:
            df = df.dropna()
            df = df[df["Produccion_sacos_60kg"]>0]
        elif "CropYield" in name:
            df = df.dropna()
            df = df[df["Rendimiento_t_ha"]>0]
        _cache[name] = df
    return _cache[name]


# ══════════════════════════════════════════════════════════════
#  1. EVA — PRODUCCIÓN MUNICIPAL
# ══════════════════════════════════════════════════════════════
def eva_kpis():
    df = _pd("EVA_produccion.csv")
    total = len(df)
    area  = df["Area_Sembrada_ha"].sum()
    n_dep = df["Departamento"].nunique()
    n_cul = df["Cultivo"].nunique()
    rend_n = df[df["Fenomeno_ENSO"]=="Normal"]["Rendimiento_t_ha"].mean()
    rend_e = df[df["Fenomeno_ENSO"]=="El Niño"]["Rendimiento_t_ha"].mean()
    caida  = round((rend_e-rend_n)/rend_n*100,1) if rend_n else 0
    return {"registros":int(total),"area_total_M":round(area/1e6,1),
            "caida_rend_pct":float(caida),"n_departamentos":int(n_dep),"n_cultivos":int(n_cul)}

def eva_produccion_anual():
    df  = _pd("EVA_produccion.csv")
    grp = (df.groupby(["Año","Cultivo","Fenomeno_ENSO"])["Produccion_t"]
             .sum().reset_index()
             .sort_values(["Cultivo","Año"]))
    r = {}
    for _, row in grp.iterrows():
        c = row["Cultivo"]
        if c not in r: r[c] = []
        r[c].append({"año":int(row["Año"]),"prod":int(row["Produccion_t"]),"enso":row["Fenomeno_ENSO"]})
    return r

def eva_area_departamento():
    df=_pd("EVA_produccion.csv")
    top=df.groupby("Departamento")["Area_Sembrada_ha"].mean().nlargest(12).reset_index()
    return [{"dep":r["Departamento"],"area":round(float(r["Area_Sembrada_ha"]),0)} for _,r in top.iterrows()]

def eva_rendimiento_region_enso():
    df  = _pd("EVA_produccion.csv")
    result = []
    for (region, enso), grp in df.groupby(["Región","Fenomeno_ENSO"]):
        vals = grp["Rendimiento_t_ha"].dropna().tolist()
        if not vals: continue
        s = pd.Series(vals)
        result.append({"region":region,"enso":enso,
            "q1":round(float(s.quantile(0.25)),3),"med":round(float(s.quantile(0.50)),3),
            "q3":round(float(s.quantile(0.75)),3),"min":round(float(s.min()),3),
            "max":round(float(s.max()),3),"vals":[round(v,3) for v in vals[:50]]})
    return result

def eva_heatmap_cultivo_enso():
    df=_pd("EVA_produccion.csv")
    pivot=df.groupby(["Cultivo","Fenomeno_ENSO"])["Rendimiento_t_ha"].mean().reset_index()
    return [{"cultivo":r["Cultivo"],"enso":r["Fenomeno_ENSO"],"rend":round(float(r["Rendimiento_t_ha"]),4)}
            for _,r in pivot.iterrows()]

# ══════════════════════════════════════════════════════════════
#  2. FAO FAOSTAT
# ══════════════════════════════════════════════════════════════
def fao_kpis():
    df=_pd("FAO_faostat.csv")
    last=df[df["Year"]==df["Year"].max()]
    return {"registros":int(len(df)),"prod_total_MT":round(last["Value_t"].sum()/1e6,1),
            "area_total_Mha":round(last["Area_ha"].sum()/1e6,1),"n_cultivos":int(df["Item"].nunique())}

def fao_produccion_historica():
    df  = _pd("FAO_faostat.csv")
    grp = (df.groupby(["Year","Item"])["Value_t"].sum().reset_index().sort_values(["Item","Year"]))
    r = {}
    for _, row in grp.iterrows():
        it = row["Item"]
        if it not in r: r[it] = []
        r[it].append({"year":int(row["Year"]),"prod":int(row["Value_t"])})
    return r

def fao_area_historica():
    df  = _pd("FAO_faostat.csv")
    grp = (df.groupby(["Year","Item"])["Area_ha"].sum().reset_index().sort_values(["Item","Year"]))
    r = {}
    for _, row in grp.iterrows():
        it = row["Item"]
        if it not in r: r[it] = []
        r[it].append({"year":int(row["Year"]),"area":int(row["Area_ha"])})
    return r

def fao_enso_comparacion():
    df=_pd("FAO_faostat.csv")
    grp=df.groupby(["Item","Fenomeno_ENSO"])["Value_t"].mean().reset_index()
    return [{"item":r["Item"],"enso":r["Fenomeno_ENSO"],"prod":round(float(r["Value_t"]),0)}
            for _,r in grp.iterrows()]

def fao_rendimiento_pequeno_multiplo():
    df=_pd("FAO_faostat.csv")
    r={}
    for item in df["Item"].unique():
        sub=df[df["Item"]==item].groupby("Year")["Yield_t_ha"].mean().reset_index()
        r[item]=[{"year":int(row["Year"]),"rend":round(float(row["Yield_t_ha"]),4)} for _,row in sub.iterrows()]
    return r

# ══════════════════════════════════════════════════════════════
#  3. SENSORES IoT
# ══════════════════════════════════════════════════════════════
def sensor_kpis():
    df=_pd("Sensores_IoT.csv")
    return {"lecturas":int(len(df)),"alertas_calor":int(df["alerta_calor"].sum()),
            "alertas_hidrico":int(df["alerta_hidrico"].sum()),
            "n_sensores":int(df["region"].nunique()*10),"n_cultivos":int(df["cultivo"].nunique())}

def sensor_scatter():
    df=_pd("Sensores_IoT.csv")
    return [{"cultivo":r["cultivo"],"region":r["region"],"temp":float(r["temperatura_c"]),
             "hum":float(r["humedad_suelo_pct"]),"ph":float(r["ph_suelo"]),
             "rend":float(r["rendimiento_t_ha"]),"alerta_calor":int(r["alerta_calor"]),
             "alerta_hidrico":int(r["alerta_hidrico"])} for _,r in df.iterrows()]

def sensor_alertas_cultivo():
    df=_pd("Sensores_IoT.csv")
    grp=df.groupby("cultivo")[["alerta_calor","alerta_hidrico"]].sum().reset_index()
    return [{"cultivo":r["cultivo"],"calor":int(r["alerta_calor"]),"hidrico":int(r["alerta_hidrico"])}
            for _,r in grp.iterrows()]

def sensor_violin():
    df=_pd("Sensores_IoT.csv")
    r={}
    for reg in df["region"].unique():
        r[reg]=df[df["region"]==reg]["temperatura_c"].tolist()
    return r

def sensor_correlacion_matrix():
    df=_pd("Sensores_IoT.csv")[["temperatura_c","humedad_suelo_pct","ph_suelo","rendimiento_t_ha","alerta_calor"]].copy()
    return df.to_dict("records")

# ══════════════════════════════════════════════════════════════
#  4. AgroNET CAFÉ
# ══════════════════════════════════════════════════════════════
def cafe_kpis():
    df=_pd("AgroNET_cafe.csv")
    prod_n=df[df["Fenomeno_ENSO"]=="Normal"]["Produccion_sacos_60kg"].mean()
    prod_e=df[df["Fenomeno_ENSO"]=="El Niño"]["Produccion_sacos_60kg"].mean()
    caida=round((prod_e-prod_n)/prod_n*100,1) if prod_n else 0
    return {"meses":int(len(df)),"prod_pico":round(float(df["Produccion_sacos_60kg"].max()),0),
            "caida_nino":float(caida),"precio_max_M":round(float(df["Precio_Interno_COP"].max()/1e6),2)}

def cafe_mensual():
    df=_pd("AgroNET_cafe.csv")
    return [{"fecha":r["fecha"],"año":int(r["Año"]),"mes":int(r["Mes"]),
             "prod":float(r["Produccion_sacos_60kg"]),"exp":float(r["Exportaciones_sacos_60kg"]),
             "precio":float(r["Precio_Interno_COP"]),"precio_ny":float(r["Precio_NY_USD_lb"]),
             "enso":r["Fenomeno_ENSO"]} for _,r in df.iterrows()]

def cafe_precio_doble_eje():
    df=(_pd("AgroNET_cafe.csv").sort_values(["Año","Mes"]).reset_index(drop=True))
    return [{"fecha":r["fecha"],"precio_cop":float(r["Precio_Interno_COP"]),
             "precio_ny":float(r["Precio_NY_USD_lb"]),"enso":r["Fenomeno_ENSO"]}
            for _,r in df.iterrows()]

def cafe_estacionalidad():
    df=_pd("AgroNET_cafe.csv")
    meses_nom=["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
    grp=df.groupby("Mes")["Produccion_sacos_60kg"].agg(["mean","std"]).reset_index()
    return [{"mes":int(r["Mes"]),"nombre":meses_nom[int(r["Mes"])-1],
             "mean":round(float(r["mean"]),0),"std":round(float(r["std"]),0)}
            for _,r in grp.iterrows()]

def cafe_prod_vs_exp_anual():
    df=_pd("AgroNET_cafe.csv")
    grp=(df.groupby(["Año","Fenomeno_ENSO"])
          .agg(prod=("Produccion_sacos_60kg","sum"),exp=("Exportaciones_sacos_60kg","sum"))
          .reset_index().sort_values("Año"))
    return [{"año":int(r["Año"]),"prod":int(r["prod"]),"exp":int(r["exp"]),"enso":r["Fenomeno_ENSO"]}
            for _,r in grp.iterrows()]

# ══════════════════════════════════════════════════════════════
#  5. CROPYIELD PAÍSES
# ══════════════════════════════════════════════════════════════
def cyp_kpis():
    df=_pd("CropYield_paises.csv")
    col=df[df["Pais"]=="Colombia"]
    return {"registros":int(len(df)),"paises":int(df["Pais"].nunique()),
            "cultivos":int(df["Item"].nunique()),"años":int(df["Year"].nunique()),
            "rend_col":round(float(col["Rendimiento_t_ha"].mean()),3)}

def cyp_cafe_paises():
    df=_pd("CropYield_paises.csv")
    grp=(df[df["Item"]=="Coffee, green"]
          .groupby(["Pais","Year"])["Rendimiento_t_ha"].mean().reset_index()
          .sort_values(["Pais","Year"]))
    r={}
    for _,row in grp.iterrows():
        p=row["Pais"]
        if p not in r: r[p]=[]
        r[p].append({"year":int(row["Year"]),"rend":round(float(row["Rendimiento_t_ha"]),4)})
    return r

def cyp_heatmap_paises_cultivos():
    df=_pd("CropYield_paises.csv")
    grp=df.groupby(["Pais","Item"])["Rendimiento_t_ha"].mean().reset_index()
    return [{"pais":r["Pais"],"item":r["Item"],"rend":round(float(r["Rendimiento_t_ha"]),3)}
            for _,r in grp.iterrows()]

def cyp_lluvia_rendimiento():
    df=_pd("CropYield_paises.csv")
    col=df[df["Pais"]=="Colombia"]
    return [{"item":r["Item"],"year":int(r["Year"]),"lluvia":float(r["Lluvia_mm"]),
             "rend":float(r["Rendimiento_t_ha"]),"enso":r["Fenomeno_ENSO"]}
            for _,r in col.iterrows()]

def cyp_enso_comparacion():
    df=_pd("CropYield_paises.csv")
    grp=df[df["Item"]=="Coffee, green"].groupby(["Pais","Fenomeno_ENSO"])["Rendimiento_t_ha"].mean().reset_index()
    return [{"pais":r["Pais"],"enso":r["Fenomeno_ENSO"],"rend":round(float(r["Rendimiento_t_ha"]),4)}
            for _,r in grp.iterrows()]

def cyp_top_cultivos_colombia():
    df=_pd("CropYield_paises.csv")
    col=df[df["Pais"]=="Colombia"].groupby("Item")["Rendimiento_t_ha"].mean().sort_values().reset_index()
    return [{"item":r["Item"],"rend":round(float(r["Rendimiento_t_ha"]),3)} for _,r in col.iterrows()]