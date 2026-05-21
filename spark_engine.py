"""
spark_engine.py — Análisis distribuido con PySpark + MLlib
──────────────────────────────────────────────────────────
Módulo INDEPENDIENTE del engine.py principal (que usa Pandas).
Propósito: demostrar procesamiento distribuido real con Spark,
consultas analíticas avanzadas, MLlib y comparación de tiempos.

Jerarquía de ejecución simulada:
  local[1]  → master solo        (1 thread)
  local[2]  → master + 1 worker  (2 threads)
  local[4]  → master + 2 workers (4 threads)
"""

import os, sys, time, warnings
import pandas as pd
import numpy as np

warnings.filterwarnings("ignore")

# ── Rutas de datos ─────────────────────────────────────────────
DATA = os.path.join(os.path.dirname(__file__), "data")
def _p(f): return os.path.join(DATA, f)

# ── Cache de resultados (evita re-ejecutar Spark en cada request) ──
_results_cache = None


# ══════════════════════════════════════════════════════════════════
#  SPARK SESSION FACTORY
# ══════════════════════════════════════════════════════════════════
def _make_spark(master: str, app_name: str = "AgroClima-Spark"):
    """Crea una SparkSession con el master indicado."""
    import pyspark
    os.environ.setdefault("PYSPARK_PYTHON",        sys.executable)
    os.environ.setdefault("PYSPARK_DRIVER_PYTHON", sys.executable)
    os.environ.setdefault("SPARK_HOME", os.path.dirname(pyspark.__file__))

    from pyspark.sql import SparkSession
    spark = (SparkSession.builder
        .master(master)
        .appName(app_name)
        .config("spark.ui.enabled",            "false")
        .config("spark.sql.shuffle.partitions", "4")
        .config("spark.driver.memory",          "1g")
        .config("spark.driver.host",            "127.0.0.1")
        .config("spark.driver.bindAddress",     "127.0.0.1")
        .getOrCreate())
    spark.sparkContext.setLogLevel("ERROR")
    return spark


# ══════════════════════════════════════════════════════════════════
#  1. CARGA Y LIMPIEZA CON SPARK
# ══════════════════════════════════════════════════════════════════
def _load_and_clean(spark):
    """
    Carga los 5 CSVs como Spark DataFrames y aplica limpieza.
    Retorna dict con los DataFrames limpios + tiempo de carga.
    """
    from pyspark.sql.functions import col

    t0 = time.time()

    dfs = {}

    # EVA Producción
    df_eva = spark.read.csv(_p("EVA_produccion.csv"), header=True, inferSchema=True)
    df_eva = (df_eva
              .dropna(subset=["Cultivo", "Produccion_t"])
              .filter(col("Produccion_t") > 0)
              .filter(col("Area_Sembrada_ha") > 0))
    dfs["eva"] = df_eva

    # FAO FAOSTAT
    df_fao = spark.read.csv(_p("FAO_faostat.csv"), header=True, inferSchema=True)
    df_fao = df_fao.dropna().filter(col("Value_t") > 0)
    dfs["fao"] = df_fao

    # Sensores IoT
    df_sen = spark.read.csv(_p("Sensores_IoT.csv"), header=True, inferSchema=True)
    df_sen = (df_sen.dropna()
              .filter(col("temperatura_c").between(5, 40))
              .filter(col("humedad_suelo_pct").between(0, 100)))
    dfs["sensores"] = df_sen

    # AgroNET Café
    df_cafe = spark.read.csv(_p("AgroNET_cafe.csv"), header=True, inferSchema=True)
    df_cafe = df_cafe.dropna().filter(col("Produccion_sacos_60kg") > 0)
    dfs["cafe"] = df_cafe

    # CropYield Países
    df_cy = spark.read.csv(_p("CropYield_paises.csv"), header=True, inferSchema=True)
    df_cy = df_cy.dropna().filter(col("Rendimiento_t_ha") > 0)
    dfs["cropyield"] = df_cy

    load_time = round(time.time() - t0, 3)
    return dfs, load_time


# ══════════════════════════════════════════════════════════════════
#  2. CONSULTAS ANALÍTICAS CON SPARK SQL / DataFrame API
# ══════════════════════════════════════════════════════════════════
def _run_analytics(dfs):
    """
    Ejecuta 5 consultas analíticas sobre los DataFrames Spark.
    Cada consulta usa groupBy, agg, orderBy — API nativa de Spark.
    """
    from pyspark.sql.functions import (col, avg, sum as spark_sum,
                                       count, round as spark_round,
                                       stddev, max as spark_max, min as spark_min)

    results = {}
    times   = {}

    # ── Q1: Producción total por cultivo y fenómeno ENSO (EVA) ──
    t = time.time()
    q1 = (dfs["eva"]
          .groupBy("Cultivo", "Fenomeno_ENSO")
          .agg(
              spark_round(spark_sum("Produccion_t") / 1e6, 3).alias("prod_Mt"),
              spark_round(avg("Rendimiento_t_ha"), 4).alias("rend_medio"),
              count("*").alias("registros")
          )
          .orderBy("Cultivo", "Fenomeno_ENSO"))
    results["q1_enso_cultivo"] = [r.asDict() for r in q1.collect()]
    times["Q1_enso_cultivo_ms"] = round((time.time() - t) * 1000, 1)

    # ── Q2: Rendimiento promedio por región y año (EVA) ──
    t = time.time()
    q2 = (dfs["eva"]
          .groupBy("Región", "Año")
          .agg(
              spark_round(avg("Rendimiento_t_ha"), 4).alias("rend_medio"),
              spark_round(avg("Area_Sembrada_ha"), 1).alias("area_media")
          )
          .orderBy("Región", "Año"))
    results["q2_region_anio"] = [r.asDict() for r in q2.collect()]
    times["Q2_region_anio_ms"] = round((time.time() - t) * 1000, 1)

    # ── Q3: Impacto ENSO en café colombiano (AgroNET) ──
    t = time.time()
    q3 = (dfs["cafe"]
          .groupBy("Fenomeno_ENSO")
          .agg(
              spark_round(avg("Produccion_sacos_60kg"), 0).alias("prod_media"),
              spark_round(avg("Exportaciones_sacos_60kg"), 0).alias("exp_media"),
              spark_round(avg("Precio_NY_USD_lb"), 4).alias("precio_ny_medio"),
              spark_round(stddev("Produccion_sacos_60kg"), 0).alias("prod_std"),
              count("*").alias("meses")
          )
          .orderBy("Fenomeno_ENSO"))
    results["q3_cafe_enso"] = [r.asDict() for r in q3.collect()]
    times["Q3_cafe_enso_ms"] = round((time.time() - t) * 1000, 1)

    # ── Q4: Ranking países por rendimiento café (CropYield) ──
    t = time.time()
    q4 = (dfs["cropyield"]
          .filter(col("Item") == "Coffee, green")
          .groupBy("Pais", "Fenomeno_ENSO")
          .agg(
              spark_round(avg("Rendimiento_t_ha"), 4).alias("rend_medio"),
              spark_round(avg("Lluvia_mm"), 1).alias("lluvia_media"),
              spark_round(avg("Temp_C"), 2).alias("temp_media")
          )
          .orderBy(col("rend_medio").desc()))
    results["q4_ranking_paises"] = [r.asDict() for r in q4.collect()]
    times["Q4_ranking_paises_ms"] = round((time.time() - t) * 1000, 1)

    # ── Q5: Correlación alertas IoT por cultivo y región ──
    t = time.time()
    q5 = (dfs["sensores"]
          .groupBy("cultivo", "region")
          .agg(
              spark_round(avg("temperatura_c"), 2).alias("temp_media"),
              spark_round(avg("humedad_suelo_pct"), 2).alias("hum_media"),
              spark_round(avg("rendimiento_t_ha"), 4).alias("rend_medio"),
              spark_round(spark_sum("alerta_calor").cast("double") /
                          count("*") * 100, 1).alias("pct_alerta_calor"),
              spark_round(spark_sum("alerta_hidrico").cast("double") /
                          count("*") * 100, 1).alias("pct_alerta_hidrico"),
              count("*").alias("lecturas")
          )
          .orderBy("cultivo", "region"))
    results["q5_alertas_cultivo"] = [r.asDict() for r in q5.collect()]
    times["Q5_alertas_cultivo_ms"] = round((time.time() - t) * 1000, 1)

    return results, times


# ══════════════════════════════════════════════════════════════════
#  3. MACHINE LEARNING CON MLlib
#     RandomForestRegressor: predice rendimiento desde variables IoT
# ══════════════════════════════════════════════════════════════════
def _run_mllib(dfs):
    """
    Modelo: RandomForestRegressor (MLlib)
    Dataset: Sensores_IoT (2000 lecturas)
    Features: temperatura_c, humedad_suelo_pct, ph_suelo,
              alerta_calor, alerta_hidrico
    Target: rendimiento_t_ha
    """
    from pyspark.ml import Pipeline
    from pyspark.ml.feature import VectorAssembler, StandardScaler
    from pyspark.ml.regression import RandomForestRegressor
    from pyspark.ml.evaluation import RegressionEvaluator
    from pyspark.ml.tuning import CrossValidator, ParamGridBuilder
    from pyspark.sql.functions import col

    t0 = time.time()

    df = dfs["sensores"]

    feature_cols = ["temperatura_c", "humedad_suelo_pct",
                    "ph_suelo", "alerta_calor", "alerta_hidrico"]

    # Pipeline: ensamble de features → scaler → modelo
    assembler = VectorAssembler(inputCols=feature_cols, outputCol="features_raw")
    scaler    = StandardScaler(inputCol="features_raw", outputCol="features",
                               withStd=True, withMean=True)
    rf        = RandomForestRegressor(
                    featuresCol="features",
                    labelCol="rendimiento_t_ha",
                    numTrees=50,
                    maxDepth=6,
                    seed=42)

    pipeline = Pipeline(stages=[assembler, scaler, rf])

    # Split 80/20
    train, test = df.randomSplit([0.8, 0.2], seed=42)

    # Entrenamiento
    t_train = time.time()
    model   = pipeline.fit(train)
    train_time = round(time.time() - t_train, 3)

    # Evaluación
    predictions = model.transform(test)
    evaluator_r2   = RegressionEvaluator(labelCol="rendimiento_t_ha",
                                         predictionCol="prediction",
                                         metricName="r2")
    evaluator_rmse = RegressionEvaluator(labelCol="rendimiento_t_ha",
                                         predictionCol="prediction",
                                         metricName="rmse")
    evaluator_mae  = RegressionEvaluator(labelCol="rendimiento_t_ha",
                                         predictionCol="prediction",
                                         metricName="mae")

    r2   = round(float(evaluator_r2.evaluate(predictions)),   4)
    rmse = round(float(evaluator_rmse.evaluate(predictions)), 4)
    mae  = round(float(evaluator_mae.evaluate(predictions)),  4)

    # Importancia de features
    rf_model       = model.stages[-1]
    feature_imp    = rf_model.featureImportances.toArray().tolist()
    importances    = [{"feature": f, "importance": round(float(v), 4)}
                      for f, v in zip(feature_cols, feature_imp)]
    importances.sort(key=lambda x: x["importance"], reverse=True)

    # Muestra de predicciones vs real (primeras 20)
    sample_preds = (predictions
                    .select("cultivo", "region", "temperatura_c",
                            "humedad_suelo_pct", "rendimiento_t_ha", "prediction")
                    .limit(20)
                    .collect())
    sample = [{"cultivo":  r["cultivo"],
               "region":   r["region"],
               "temp":     round(float(r["temperatura_c"]), 2),
               "hum":      round(float(r["humedad_suelo_pct"]), 2),
               "real":     round(float(r["rendimiento_t_ha"]), 4),
               "pred":     round(float(r["prediction"]), 4)}
              for r in sample_preds]

    total_time = round(time.time() - t0, 3)

    return {
        "modelo":         "RandomForestRegressor (MLlib)",
        "dataset":        "Sensores_IoT.csv",
        "n_features":     len(feature_cols),
        "features":       feature_cols,
        "n_trees":        50,
        "train_size":     int(train.count()),
        "test_size":      int(test.count()),
        "r2":             r2,
        "rmse":           rmse,
        "mae":            mae,
        "train_time_s":   train_time,
        "total_time_s":   total_time,
        "importancias":   importances,
        "predicciones":   sample,
    }


# ══════════════════════════════════════════════════════════════════
#  4. COMPARACIÓN DE TIEMPOS: local[1] vs local[2] vs local[4]
# ══════════════════════════════════════════════════════════════════
def _benchmark_masters():
    """
    Ejecuta la misma operación (groupBy + agg sobre EVA) con
    3 configuraciones de master distintas y mide el tiempo.
    Retorna lista con resultados comparativos.
    """
    configs = [
        ("local[1]", "Solo master (1 thread)"),
        ("local[2]", "Master + 1 worker (2 threads)"),
        ("local[4]", "Master + 2 workers (4 threads)"),
    ]
    benchmark = []

    for master, label in configs:
        spark = None
        try:
            spark = _make_spark(master, app_name=f"AgroClima-Bench-{master}")

            from pyspark.sql.functions import avg, sum as spark_sum, count, col

            # Operación de referencia: groupBy múltiple sobre los 5 datasets
            t0 = time.time()

            # Carga de los 5 CSVs
            df_eva  = spark.read.csv(_p("EVA_produccion.csv"),  header=True, inferSchema=True)
            df_fao  = spark.read.csv(_p("FAO_faostat.csv"),     header=True, inferSchema=True)
            df_sen  = spark.read.csv(_p("Sensores_IoT.csv"),    header=True, inferSchema=True)
            df_cafe = spark.read.csv(_p("AgroNET_cafe.csv"),    header=True, inferSchema=True)
            df_cy   = spark.read.csv(_p("CropYield_paises.csv"),header=True, inferSchema=True)
            t_load  = round(time.time() - t0, 3)

            # Consulta 1: EVA groupBy
            t1 = time.time()
            r1 = (df_eva.groupBy("Cultivo","Fenomeno_ENSO")
                        .agg(avg("Rendimiento_t_ha").alias("rend"))
                        .count())
            t_q1 = round(time.time() - t1, 3)

            # Consulta 2: Café groupBy + agg múltiple
            t2 = time.time()
            r2 = (df_cafe.groupBy("Fenomeno_ENSO","Año")
                         .agg(avg("Produccion_sacos_60kg"),
                              avg("Precio_NY_USD_lb"))
                         .count())
            t_q2 = round(time.time() - t2, 3)

            # Consulta 3: Sensores groupBy + filtro
            t3 = time.time()
            r3 = (df_sen.filter(col("alerta_calor") == 1)
                        .groupBy("cultivo","region")
                        .agg(avg("rendimiento_t_ha"), count("*"))
                        .count())
            t_q3 = round(time.time() - t3, 3)

            # Consulta 4: CropYield join simulado (groupBy múltiple)
            t4 = time.time()
            r4 = (df_cy.groupBy("Pais","Item","Fenomeno_ENSO")
                       .agg(avg("Rendimiento_t_ha"), avg("Lluvia_mm"))
                       .count())
            t_q4 = round(time.time() - t4, 3)

            t_total = round(t_load + t_q1 + t_q2 + t_q3 + t_q4, 3)

            benchmark.append({
                "master":      master,
                "label":       label,
                "t_carga_s":   t_load,
                "t_q1_s":      t_q1,
                "t_q2_s":      t_q2,
                "t_q3_s":      t_q3,
                "t_q4_s":      t_q4,
                "t_total_s":   t_total,
                "filas_procesadas": 5404,
                "ok": True,
            })

        except Exception as ex:
            benchmark.append({
                "master":    master,
                "label":     label,
                "t_total_s": -1,
                "ok":        False,
                "error":     str(ex)[:120],
            })
        finally:
            if spark:
                try:
                    spark.stop()
                except Exception:
                    pass

    return benchmark


# ══════════════════════════════════════════════════════════════════
#  5. FUNCIÓN PRINCIPAL — llamada desde app.py
# ══════════════════════════════════════════════════════════════════
def run_spark_analysis(force: bool = False) -> dict:
    """
    Punto de entrada único. Ejecuta TODO el pipeline Spark:
      1. Benchmark de tiempos (local[1/2/4])
      2. Carga + limpieza con Spark
      3. 5 consultas analíticas
      4. Modelo RandomForest MLlib
    Cachea el resultado para requests posteriores.

    Args:
        force: si True, ignora el caché y re-ejecuta.
    Returns:
        dict con todas las secciones listas para el template.
    """
    global _results_cache
    if _results_cache is not None and not force:
        return _results_cache

    out = {
        "ok":        False,
        "error":     None,
        "benchmark": [],
        "analytics": {},
        "query_times": {},
        "mllib":     {},
        "load_time_s": 0,
        "datasets_info": [
            {"nombre": "EVA_produccion.csv",   "filas": 928,  "fuente": "MADR · datos.gov.co"},
            {"nombre": "FAO_faostat.csv",       "filas": 272,  "fuente": "FAO · ONU"},
            {"nombre": "Sensores_IoT.csv",      "filas": 2000, "fuente": "Kaggle · SF24"},
            {"nombre": "AgroNET_cafe.csv",      "filas": 300,  "fuente": "AgroNET · Colombia"},
            {"nombre": "CropYield_paises.csv",  "filas": 1904, "fuente": "Kaggle · ONU"},
        ],
    }

    spark = None
    try:
        # ── Paso 1: Benchmark tiempos ──────────────────────────
        out["benchmark"] = _benchmark_masters()

        # ── Paso 2 & 3: Análisis principal con local[2] ────────
        spark = _make_spark("local[2]", "AgroClima-Analysis")
        dfs, load_time = _load_and_clean(spark)
        out["load_time_s"] = load_time

        analytics, qtimes = _run_analytics(dfs)
        out["analytics"]   = analytics
        out["query_times"] = qtimes

        # ── Paso 4: MLlib ──────────────────────────────────────
        out["mllib"] = _run_mllib(dfs)

        out["ok"] = True

    except Exception as ex:
        out["error"] = str(ex)
    finally:
        if spark:
            try:
                spark.stop()
            except Exception:
                pass

    _results_cache = out
    return out