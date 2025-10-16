from __future__ import annotations
import os
from pathlib import Path
from typing import Callable, Optional
import re
import warnings

import psycopg2
import pandas as pd
from psycopg2.extras import execute_values
from dotenv import load_dotenv

warnings.filterwarnings("ignore", category=UserWarning, module="pandas.io.sql")

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
# QUERIES
# ============================================================
QUERY_REPROGRAMACION = """
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
    rn > 1;
"""

QUERY_COMPRAS = """
WITH ot_mantenimiento AS (
    SELECT
        motivo_compra,
        item_material_o_servicio
    FROM consultas_cgo_ext.v_sol_items_otm_otr
    WHERE motivo_compra IS NOT NULL 
       OR item_material_o_servicio IS NOT NULL
)
SELECT DISTINCT
    motivo_compra,
    item_material_o_servicio
FROM ot_mantenimiento;
"""

# ============================================================
# CONSTANTES COMPRAS
# ============================================================
ABREVIACIONES = {
    'hrs': 'horas', 'mtto': 'mantenimiento', 'mant': 'mantenimiento',
    'rep': 'reparacion', 'serv': 'servicio', 'equip': 'equipo',
    'flex': 'flexible', 'fabr': 'fabricacion', 'trasl': 'traslado',
    'comb': 'combustible', 'lubr': 'lubricante', 'filt': 'filtro',
    'camb': 'cambio', 'inst': 'instalacion', 'sist': 'sistema',
}

TERMINOS_MOTIVOS = {
    'mantenimiento', 'reparacion', 'cambio', 'instalacion', 'fabricacion',
    'servicio', 'traslado', 'inspeccion', 'revision', 'limpieza',
    'lavado', 'pintura', 'soldadura', 'calibracion', 'ajuste',
    'cotizacion', 'compra', 'reemplazo', 'desmontaje', 'montaje',
    'certificacion', 'prueba', 'diagnostico', 'evaluacion'
}

TERMINOS_ITEMS = {
    'filtro', 'aceite', 'combustible', 'flexible', 'neumatico',
    'kit', 'repuesto', 'componente', 'sistema', 'motor', 'freno',
    'cabina', 'vidrio', 'lubricante', 'sello', 'bomba', 'valvula',
    'sensor', 'manguera', 'correa', 'bateria', 'alternador',
    'acumulador', 'adaptador', 'abrazadera', 'conexion', 'empaque',
    'junta', 'perno', 'tuerca', 'tornillo', 'placa', 'lamina',
    'rodamiento', 'retenes', 'cojinete', 'eje', 'engrane',
    'cilindro', 'piston', 'biela', 'carburador', 'inyector',
    'turbo', 'radiador', 'ventilador', 'compresor', 'condensador',
    'evaporador', 'amortiguador', 'suspension', 'resorte', 'barra',
    'varilla', 'vastago', 'bulon', 'pasador', 'chaveta',
    'polea', 'tensor', 'damper', 'volante', 'embrague',
    'clutch', 'transmision', 'diferencial', 'corona', 'pinon',
    'cadena', 'oruga', 'zapata', 'rodillo', 'buje', 'casquillo',
    'espaciador', 'arandela', 'retenedor', 'guardapolvo', 'fuelle',
    'tapa', 'cubierta', 'protector', 'relay', 'fusible',
    'contactor', 'interruptor', 'switch', 'caudalimetro',
    'manometro', 'termometro', 'tacometro', 'indicador',
    'medidor', 'transmisor', 'receptor', 'llave', 'broca',
    'disco', 'esmeril', 'soldador', 'electrodo', 'alambre'
}

# ============================================================
# LIMPIEZA REPROGRAMACION
# ============================================================
def limpiar_motivos_reprogramacion(df: pd.DataFrame) -> pd.DataFrame:
    columna = 'motivo_reprogramacion_desc'
    df[columna] = df[columna].fillna('')
    df[columna] = df[columna].apply(lambda x: re.sub(r'[^\w\s]', '', str(x)))
    df[columna] = df[columna].str.replace(r'\s+', ' ', regex=True).str.strip()
    df[columna] = df[columna].replace('', None)
    return df

def imputar_motivos_estadisticos(df: pd.DataFrame) -> pd.DataFrame:
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
# LIMPIEZA COMPRAS
# ============================================================
def normalizar_texto(texto):
    if pd.isna(texto) or texto == '':
        return None
    
    texto = str(texto).lower().strip()
    
    if re.match(r'^\d{6,}[a-z]?$', texto):
        return None
    
    texto = texto.replace('\r\n', ' ').replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
    texto = re.sub(r'\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b', '', texto)
    texto = re.sub(r'\b[a-z]{2}-\d{1,3}\b', '', texto)
    texto = re.sub(r'\b[mr]\d{7}\b', '', texto)
    texto = re.sub(r'^\s*-?\d+\s+', '', texto)
    texto = re.sub(r'^-\s*', '', texto)
    
    if re.match(r'^-?\d+k?m?$', texto.strip()):
        return None
    
    for a, s in {'á':'a','é':'e','í':'i','ó':'o','ú':'u','ñ':'n'}.items():
        texto = texto.replace(a, s)
    
    texto = re.sub(r'[^\w\s-]', ' ', texto)
    texto = re.sub(r'\s+', ' ', texto).strip()
    
    if len(texto) < 3 or re.match(r'^[a-z]\s+[a-z]$', texto):
        return None
    
    return texto if texto else None

def expandir_abreviaciones(texto):
    if not texto:
        return None
    palabras = [ABREVIACIONES.get(p, p) for p in texto.split()]
    return ' '.join(palabras)

def extraer_concepto_principal(texto, diccionario_terminos):
    if not texto:
        return None
    
    for palabra in texto.split():
        if palabra in diccionario_terminos:
            return palabra
    
    return None

def estandarizar_motivo(texto):
    if pd.isna(texto) or texto == '':
        return None
    
    texto = normalizar_texto(texto)
    if not texto:
        return None
    
    texto = expandir_abreviaciones(texto)
    if not texto:
        return None
    
    concepto = extraer_concepto_principal(texto, TERMINOS_MOTIVOS)
    if not concepto:
        return None
    
    return concepto.strip() if len(concepto.strip()) >= 3 else None

def estandarizar_item(texto):
    if pd.isna(texto) or texto == '':
        return None
    
    texto = normalizar_texto(texto)
    if not texto:
        return None
    
    texto = expandir_abreviaciones(texto)
    if not texto:
        return None
    
    concepto = extraer_concepto_principal(texto, TERMINOS_ITEMS)
    if not concepto:
        return None
    
    return concepto.strip() if len(concepto.strip()) >= 3 else None

def limpiar_motivos_items(df):
    df['motivo_compra_limpio'] = df['motivo_compra'].apply(estandarizar_motivo)
    df['item_limpio'] = df['item_material_o_servicio'].apply(estandarizar_item)
    return df

# ============================================================
# PROCESO REPROGRAMACION
# ============================================================
def ejecutar_proceso_reprogramacion(conn_src, conn_dst, callback=None):
    def _ping(paso: str, p: int | None = None):
        if callback:
            try:
                callback(paso=paso, progreso=p)
            except Exception:
                pass

    _ping("Extrayendo reprogramaciones", 5)
    df = pd.read_sql_query(QUERY_REPROGRAMACION, conn_src)
    total = int(len(df))

    _ping("Limpiando motivos reprogramación", 15)
    df = limpiar_motivos_reprogramacion(df)

    _ping("Imputando motivos", 25)
    df = imputar_motivos_estadisticos(df)

    _ping("Filtrando registros", 35)
    motivos_upper = df["motivo_reprogramacion_desc"].astype(str).str.strip().str.upper()
    motivos_a_excluir = ["OTROS", "CAMBIO DE PROGRAMA"]
    mascara_exclusion = ~motivos_upper.isin(motivos_a_excluir)
    df_filtrado = df[mascara_exclusion].copy()
    df_final = df_filtrado.dropna(subset=["motivo_reprogramacion_desc"]).copy()
    no_imputados = int(total - len(df_final))

    _ping("Truncando tablas reprogramación", 45)
    with conn_dst.cursor() as cur:
        cur.execute("TRUNCATE TABLE public.reprogramacion_otm RESTART IDENTITY CASCADE;")
        cur.execute("TRUNCATE TABLE public.motivo_reprogramacion RESTART IDENTITY CASCADE;")
    conn_dst.commit()

    _ping("Insertando motivos", 55)
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

    _ping("Insertando reprogramaciones", 65)
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

    return {
        "registros_extraidos": total,
        "motivos_insertados": motivos_insertados,
        "reprogramaciones_insertadas": registros_insertados,
        "registros_no_imputados": no_imputados
    }

# ============================================================
# PROCESO COMPRAS
# ============================================================
def ejecutar_proceso_compras(conn_src, conn_dst, callback=None):
    def _ping(paso: str, p: int | None = None):
        if callback:
            try:
                callback(paso=paso, progreso=p)
            except Exception:
                pass

    _ping("Extrayendo compras", 70)
    df = pd.read_sql_query(QUERY_COMPRAS, conn_src)
    total = int(len(df))

    _ping("Limpiando motivos e items", 75)
    df = limpiar_motivos_items(df)

    _ping("Deduplicando catálogos", 80)
    motivos_unicos = sorted(set(df['motivo_compra_limpio'].dropna().unique().tolist()))
    items_unicos = sorted(set(df['item_limpio'].dropna().unique().tolist()))

    _ping("Truncando tablas compras", 85)
    with conn_dst.cursor() as cur:
        cur.execute("TRUNCATE TABLE public.motivo_compra RESTART IDENTITY CASCADE;")
        cur.execute("TRUNCATE TABLE public.item RESTART IDENTITY CASCADE;")
    conn_dst.commit()

    _ping("Insertando catálogos", 90)
    motivos_insertados = 0
    items_insertados = 0
    
    if motivos_unicos:
        with conn_dst.cursor() as cur:
            execute_values(cur, "INSERT INTO public.motivo_compra (motvo_compra_desc) VALUES %s;", [(m,) for m in motivos_unicos])
        conn_dst.commit()
        motivos_insertados = len(motivos_unicos)
    
    if items_unicos:
        with conn_dst.cursor() as cur:
            execute_values(cur, "INSERT INTO public.item (item_desc) VALUES %s;", [(i,) for i in items_unicos])
        conn_dst.commit()
        items_insertados = len(items_unicos)

    return {
        "registros_extraidos": total,
        "motivos_insertados": motivos_insertados,
        "items_insertados": items_insertados
    }

# ============================================================
# PROCESO COMPLETO
# ============================================================
def ejecutar_proceso(callback: Optional[Callable[..., None]] = None) -> dict:
    def _ping(paso: str, p: int | None = None):
        if callback:
            try:
                callback(paso=paso, progreso=p)
            except Exception:
                pass

    _ping("Conectando a bases de datos", 1)
    with psycopg2.connect(DB_ORIGEN) as conn_src, psycopg2.connect(DB_DESTINO) as conn_dst:
        conn_src.set_session(readonly=True, autocommit=False)
        conn_dst.set_session(autocommit=False)

        with conn_src.cursor() as c:
            c.execute("SET LOCAL statement_timeout = '10min';")

        # Pipeline 1: Reprogramaciones
        resultado_reprog = ejecutar_proceso_reprogramacion(conn_src, conn_dst, callback)

        # Pipeline 2: Compras
        resultado_compras = ejecutar_proceso_compras(conn_src, conn_dst, callback)

    _ping("Finalizado", 100)
    return {
        "status": "success",
        "mensaje": "Ambos pipelines completados",
        "reprogramaciones": resultado_reprog,
        "compras": resultado_compras
    }