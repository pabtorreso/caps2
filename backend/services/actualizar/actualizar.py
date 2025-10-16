from __future__ import annotations
import os
from pathlib import Path
from typing import Callable, Optional
import re 

import psycopg2
import pandas as pd
from psycopg2.extras import execute_values
from dotenv import load_dotenv

# ============================================================
# .env
# ============================================================
ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=ENV_PATH)

ERP_DB_HOST = os.getenv("ERP_DB_HOST")
ERP_DB_PORT = os.getenv("ERP_DB_PORT", "5432")
ERP_DB_NAME = os.getenv("ERP_DB_NAME")
ERP_DB_USER = os.getenv("ERP_DB_USER")
ERP_DB_PASSWORD = os.getenv("ERP_DB_PASSWORD")
ERP_DB_SSLMODE = os.getenv("ERP_DB_SSLMODE", "disable")

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_SSLMODE = os.getenv("DB_SSLMODE", "disable")

DB_ORIGEN = (
    f"dbname={ERP_DB_NAME} user={ERP_DB_USER} password={ERP_DB_PASSWORD} "
    f"host={ERP_DB_HOST} port={ERP_DB_PORT} sslmode={ERP_DB_SSLMODE}"
)
DB_DESTINO = (
    f"dbname={DB_NAME} user={DB_USER} password={DB_PASSWORD} "
    f"host={DB_HOST} port={DB_PORT} sslmode={DB_SSLMODE}"
)

# ============================================================
# Query de extracción (igual a Esteban, sin ORDER BY final)
# ============================================================
QUERY_ORIGEN = """
WITH ordenes AS (
    SELECT
        nombre_faena,
        codigo_interno AS equipo_desc,
        actividad,
        estado_actividad,
        fecha_original,
        numero_otm AS otm_desc,
        fecha_inicio,
        motivo_no_cumplimiento AS motivo_reprogramacion_desc,
        -- Genera un número de secuencia para cada OT, ordenado por fecha de inicio.
        ROW_NUMBER() OVER (PARTITION BY numero_otm ORDER BY fecha_inicio ASC) AS rn
    FROM
        consultas_cgo_ext.v_reg_historico_ot_orden
    WHERE
        numero_otm LIKE 'M%'
)
SELECT
    nombre_faena,
    equipo_desc,
    actividad,
    estado_actividad,
    fecha_original,
    otm_desc,
    fecha_inicio,
    motivo_reprogramacion_desc
FROM
    ordenes
WHERE
    rn > 1; -- Filtra solo las reprogramaciones (segunda ocurrencia en adelante)
"""



# ============================================================
# Helpers (lógica Esteban modificada con limpieza extrema)
# ============================================================
def limpiar_motivos(df: pd.DataFrame) -> pd.DataFrame:
    """
    Limpia textos y normaliza valores nulos.
    Se añade limpieza extrema para eliminar caracteres invisibles.
    """
    columna = 'motivo_reprogramacion_desc'
    
    # 1. Rellenar nulos temporalmente con vacío para aplicar operaciones de cadena
    df[columna] = df[columna].fillna('')

    # 2. Eliminar todos los caracteres que no sean letras, números o espacios (limpieza extrema)
    df[columna] = df[columna].apply(lambda x: re.sub(r'[^\w\s]', '', str(x)))
    
    # 3. Reemplazar múltiples espacios con un solo espacio y limpiar espacios
    df[columna] = df[columna].str.replace(r'\s+', ' ', regex=True).str.strip()
    
    # 4. Convertir vacíos explícitamente a None
    df[columna] = df[columna].replace('', None)
    
    return df

def imputar_motivos_estadisticos(df: pd.DataFrame) -> pd.DataFrame:
    """Imputa los motivos faltantes basándose en patrones históricos (moda por actividad/estado)."""
    base = df.dropna(subset=["motivo_reprogramacion_desc"]).copy()

    moda_actividad = (
        base.groupby("actividad")["motivo_reprogramacion_desc"]
        .agg(lambda x: x.mode().iloc[0] if not x.mode().empty else None)
        .to_dict()
    )
    moda_estado = (
        base.groupby("estado_actividad")["motivo_reprogramacion_desc"]
        .agg(lambda x: x.mode().iloc[0] if not x.mode().empty else None)
        .to_dict()
    )

    def imputar(row):
        if pd.isna(row["motivo_reprogramacion_desc"]):
            act = row.get("actividad")
            est = row.get("estado_actividad")
            if act in moda_actividad and moda_actividad[act] is not None:
                return moda_actividad[act]
            elif est in moda_estado and moda_estado[est] is not None:
                return moda_estado[est]
            else:
                return None
        return row["motivo_reprogramacion_desc"]

    df["motivo_reprogramacion_desc"] = df.apply(imputar, axis=1)
    return df

# ============================================================
# Proceso completo (misma firma, con callback opcional)
# ============================================================
def ejecutar_proceso(callback: Optional[Callable[..., None]] = None) -> dict:
    """
    Full refresh con lógica de Esteban, con filtro explícito de OTROS/CAMBIO DE PROGRAMA.
    """
    def _ping(paso: str, p: int | None = None):
        if callback:
            try:
                callback(paso=paso, progreso=p)
            except Exception:
                pass

    _ping("Conectando a orígenes", 1)
    with psycopg2.connect(DB_ORIGEN) as conn_src, psycopg2.connect(DB_DESTINO) as conn_dst:
        conn_src.set_session(readonly=True, autocommit=False)
        conn_dst.set_session(autocommit=False)

        # 1) Extraer
        _ping("Extrayendo desde ERP", 5)
        with conn_src.cursor() as c:
            c.execute("SET LOCAL statement_timeout = '10min';")
        df = pd.read_sql_query(QUERY_ORIGEN, conn_src)
        total = int(len(df))

        # 2) Limpiar + imputar (Lógica Esteban con limpieza extrema)
        _ping("Limpiando motivos", 15)
        df = limpiar_motivos(df)

        _ping("Imputando motivos (moda)", 30)
        df = imputar_motivos_estadisticos(df)

        # 3) Filtrar y Excluir (El paso crucial para tu requerimiento)
        _ping("Filtrando registros (excluyendo y descartando nulos)", 40)

        # 3.1) Excluir explícitamente OTROS y CAMBIO DE PROGRAMA (Regla de negocio)
        # Convertimos la columna a mayúsculas para la comparación y filtramos.
        motivos_upper = df["motivo_reprogramacion_desc"].astype(str).str.strip().str.upper()
        motivos_a_excluir = ["OTROS", "CAMBIO DE PROGRAMA"]
        
        # Máscara para mantener solo los que NO estén en la lista de exclusión
        mascara_exclusion = ~motivos_upper.isin(motivos_a_excluir)
        df_filtrado = df[mascara_exclusion].copy()

        # 3.2) Filtrar filas sin motivo final (lógica dropna de Esteban)
        # Esto elimina los registros que no se pudieron imputar.
        df_final = df_filtrado.dropna(subset=["motivo_reprogramacion_desc"]).copy()
        
        no_imputados = int(total - len(df_final))

        # 4) TRUNCATE destino
        _ping("Truncando tablas destino", 55)
        with conn_dst.cursor() as cur:
            # Reconfirmamos el TRUNCATE CASCADE para asegurar que no queden datos antiguos.
            cur.execute("TRUNCATE TABLE public.reprogramacion_otm RESTART IDENTITY CASCADE;")
            cur.execute("TRUNCATE TABLE public.motivo_reprogramacion RESTART IDENTITY CASCADE;")
        conn_dst.commit()

        # 5) Insert catálogo de motivos
        _ping("Insertando catálogo de motivos", 70)
        motivos_unicos = df_final["motivo_reprogramacion_desc"].dropna().unique()
        motivos_insertados = 0
        if len(motivos_unicos) > 0:
            with conn_dst.cursor() as cur:
                execute_values(
                    cur,
                    "INSERT INTO public.motivo_reprogramacion (motivo_reprogramacion_desc) VALUES %s;",
                    [(str(m),) for m in motivos_unicos],
                )
            conn_dst.commit()
            motivos_insertados = int(len(motivos_unicos))

        # 6) Insert reprogramaciones
        _ping("Insertando reprogramaciones", 85)
        motivos = pd.read_sql_query(
            "SELECT motivo_reprogramacion_id, motivo_reprogramacion_desc FROM public.motivo_reprogramacion;",
            conn_dst,
        )
        otm = pd.read_sql_query(
            "SELECT otm_id, otm_desc FROM public.orden_man;",
            conn_dst,
        )

        df_final = df_final.merge(motivos, on="motivo_reprogramacion_desc", how="left")
        df_final = df_final.merge(otm, on="otm_desc", how="left")
        df_final = df_final.dropna(subset=["otm_id", "motivo_reprogramacion_id"]).copy()

        registros_insertados = 0
        if not df_final.empty:
            df_final = df_final.sort_values(["otm_id", "fecha_inicio"])
            df_final["n_reprogramacion"] = df_final.groupby("otm_id").cumcount() + 1

            registros = [
                (int(r.otm_id), int(r.n_reprogramacion), r.fecha_inicio, int(r.motivo_reprogramacion_id))
                for _, r in df_final.iterrows()
            ]

            with conn_dst.cursor() as cur:
                execute_values(
                    cur,
                    """
                    INSERT INTO public.reprogramacion_otm
                        (otm_id, n_reprogramacion, fecha_inicio, motivo_reprogramacion_id)
                    VALUES %s;
                    """,
                    registros,
                )
            conn_dst.commit()
            registros_insertados = int(len(registros))

    _ping("Finalizado", 100)
    return {
        "status": "success",
        "mensaje": "Proceso completado correctamente",
        "registros_extraidos": total,
        "motivos_insertados": motivos_insertados,
        "reprogramaciones_insertadas": registros_insertados,
        "registros_no_imputados": no_imputados,
        "modo": "full_refresh_truncate_esteban"
    }