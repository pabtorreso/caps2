from flask import Blueprint, jsonify, request
from sqlalchemy import text
from database.database_erp import get_erp_db
from decimal import Decimal
from datetime import datetime, date, timedelta
from collections import defaultdict

home_bp = Blueprint("home_bp", __name__)

# -------- utilidades de serialización --------
def to_float(x):
    if x is None: 
        return 0.0
    if isinstance(x, Decimal):
        return float(x)
    try:
        return float(x)
    except Exception:
        return 0.0

def to_iso(dt):
    if isinstance(dt, (datetime, date)):
        return dt.isoformat()
    return None

def hours_between(a, b):
    if not a or not b:
        return 0.0
    if isinstance(a, date) and not isinstance(a, datetime):
        a = datetime.combine(a, datetime.min.time())
    if isinstance(b, date) and not isinstance(b, datetime):
        b = datetime.combine(b, datetime.min.time())
    delta = b - a
    return max(delta.total_seconds() / 3600.0, 0.0)

def month_key(dt):
    if not isinstance(dt, (datetime, date)):
        return None
    return f"{dt.year}-{dt.month:02d}"


def to_datetime(v):
    """Convierte date -> datetime (00:00), deja datetime tal cual, None -> None."""
    if isinstance(v, datetime):
        return v
    if isinstance(v, date):
        return datetime.combine(v, datetime.min.time())
    return None

def best_date(r):
    """Mejor fecha disponible en el registro (sin coerción)."""
    return r.get("fecha_solicitud") or r.get("fecha_inicio") or r.get("fecha_ejecucion_otm") or r.get("fecha_log")

def best_date_dt(r):
    """Mejor fecha, siempre como datetime (o datetime.min si no hay nada)."""
    return to_datetime(best_date(r)) or datetime.min

# --------- endpoint principal ---------
@home_bp.get("/dashboard")
def dashboard():
    # Parámetros del front
    p_from = request.args.get("from")  # 'YYYY-MM-DD'
    p_to = request.args.get("to")
    site = request.args.get("site")     # nombre de faena (o "TODOS")
    machine = request.args.get("machine")  # código (o "TODAS")

    # Defaults seguros si no vienen
    try:
        date_from = datetime.fromisoformat(p_from) if p_from else datetime.now() - timedelta(days=90)
        date_to = datetime.fromisoformat(p_to) if p_to else datetime.now()
    except Exception:
        date_from = datetime.now() - timedelta(days=90)
        date_to = datetime.now()

    # Construye filtros dinámicos
    conds = ["COALESCE(rotm.fecha_inicio, pro.fecha_log, otm.fecha_solicitud) BETWEEN :dfrom AND :dto"]
    params = {"dfrom": date_from, "dto": date_to}

    if site and site.upper() != "TODOS":
        conds.append("rotm.nombre_faena = :site")
        params["site"] = site

    if machine and machine.upper() != "TODAS":
        conds.append("eq.equipo_codigo = :machine")
        params["machine"] = machine

    where_clause = " AND ".join(conds)

    # Query base (tu misma CTE, sin WHERE por id fijo)
    sql = f"""
WITH programa AS (
    SELECT
        id_programa_otm,
        equipo,
        codigo_tarea,
        horometro_referencia,
        descripcion,
        disponibilidad_insumos,
        instrucciones_especiales,
        fecha_limite,
        cantidad_reprogramaciones,
        usuario_programacion,
        estado_programa,
        otm,
        nombre_prioridad_otm,
        fecha_ejecucion_otm,
        horometro_planificacion,
        ultimo_horometro,
        fecha_ultimo_horometro,
        usuario_ultimo_horometro,
        fecha_log,
        fecha_hora_inicio,
        fecha_hora_fin
    FROM CONSULTAS_CGO_EXT.V_PROGRAMA_OTM
),
reg_otm AS (
    SELECT
        id_otm,
        fecha_inicio,
        anio,
        nombre_faena,
        codigo_interno,
        actividad,
        tipo_actividad,
        estado_actividad,
        motivo_no_cumplimiento,
        numero_otm,
        fecha_original,
        cantidad_reprogramaciones
    FROM CONSULTAS_CGO_EXT.V_REG_HISTORICO_OT_ORDEN
    WHERE numero_otm ~ '^M[0-9]+$'
),
ot_mantenimiento AS (
    SELECT
        numero_solicitud,
        fecha_solicitud,
        ot,
        tipo_solicitud,                -- típicamente OTM/OTR
        equipo,
        solicitante,
        estado_solicitud,
        faena,
        cuenta_contable,
        centro_costos,
        proveedor_seleccionado,
        fecha_cotizacion,
        condicion_pago,
        monto_neto,
        valor_total,
        plazo_entrega,
        motivo_compra,
        orden_compra,
        fecha_orden_compra,
        fecha_emision_factura,
        monto_total_factura,
        item_material_o_servicio,
        item_cantidad,
        item_unidad,
        item_monto_total,
        estado_recepcion,
        fecha_aceptado,
        fecha_aceptado_gerencia,
        validador,
        validador_gerencia
    FROM CONSULTAS_CGO_EXT.V_SOL_ITEMS_OTM_OTR
),
equipo AS (
    SELECT DISTINCT
        equipo_codigo,
        TRIM(REGEXP_REPLACE(SPLIT_PART(equipo, ' - ', 1), '^[A-Z0-9-]+ ', '')) AS tipo_equipo,
        SPLIT_PART(equipo, ' - ', 2) AS marca,
        SPLIT_PART(equipo, ' - ', 3) AS modelo
    FROM CONSULTAS_CGO_EXT.V_REGISTRO_DIARIO_ANGLO_EXPORT
    UNION ALL
    SELECT DISTINCT equipo_codigo,
        TRIM(REGEXP_REPLACE(SPLIT_PART(equipo, ' - ', 1), '^[A-Z0-9-]+ ', '')),
        SPLIT_PART(equipo, ' - ', 2),
        SPLIT_PART(equipo, ' - ', 3)
    FROM CONSULTAS_CGO_EXT.V_REGISTRO_DIARIO_CGO_ANDINA_EXPORT
    UNION ALL
    SELECT DISTINCT equipo_codigo,
        TRIM(REGEXP_REPLACE(SPLIT_PART(equipo, ' - ', 1), '^[A-Z0-9-]+ ', '')),
        SPLIT_PART(equipo, ' - ', 2),
        SPLIT_PART(equipo, ' - ', 3)
    FROM CONSULTAS_CGO_EXT.V_REGISTRO_DIARIO_CGO_CUMET_VENTANAS_EXPORT
    UNION ALL
    SELECT DISTINCT equipo_codigo,
        TRIM(REGEXP_REPLACE(SPLIT_PART(equipo, ' - ', 1), '^[A-Z0-9-]+ ', '')),
        SPLIT_PART(equipo, ' - ', 2),
        SPLIT_PART(equipo, ' - ', 3)
    FROM CONSULTAS_CGO_EXT.V_REGISTRO_DIARIO_CUCONS_EXPORT
    UNION ALL
    SELECT DISTINCT equipo_codigo,
        TRIM(REGEXP_REPLACE(SPLIT_PART(equipo, ' - ', 1), '^[A-Z0-9-]+ ', '')),
        SPLIT_PART(equipo, ' - ', 2),
        SPLIT_PART(equipo, ' - ', 3)
    FROM CONSULTAS_CGO_EXT.V_REGISTRO_DIARIO_ETEO_EXPORT
    UNION ALL
    SELECT DISTINCT equipo_codigo,
        TRIM(REGEXP_REPLACE(SPLIT_PART(equipo, ' - ', 1), '^[A-Z0-9-]+ ', '')),
        SPLIT_PART(equipo, ' - ', 2),
        SPLIT_PART(equipo, ' - ', 3)
    FROM CONSULTAS_CGO_EXT.V_REGISTRO_DIARIO_KDM_EXPORT
    UNION ALL
    SELECT DISTINCT equipo_codigo,
        TRIM(REGEXP_REPLACE(SPLIT_PART(equipo, ' - ', 1), '^[A-Z0-9-]+ ', '')),
        SPLIT_PART(equipo, ' - ', 2),
        SPLIT_PART(equipo, ' - ', 3)
    FROM CONSULTAS_CGO_EXT.V_REGISTRO_DIARIO_TC_EXPORT
    UNION ALL
    SELECT DISTINCT equipo_codigo,
        TRIM(REGEXP_REPLACE(SPLIT_PART(equipo, ' - ', 1), '^[A-Z0-9-]+ ', '')),
        SPLIT_PART(equipo, ' - ', 2),
        SPLIT_PART(equipo, ' - ', 3)
    FROM CONSULTAS_CGO_EXT.V_REGISTRO_DIARIO_CATODO_EXPORT
    UNION ALL
    SELECT DISTINCT equipo_codigo,
        TRIM(REGEXP_REPLACE(SPLIT_PART(equipo, ' - ', 1), '^[A-Z0-9-]+ ', '')),
        SPLIT_PART(equipo, ' - ', 2),
        SPLIT_PART(equipo, ' - ', 3)
    FROM CONSULTAS_CGO_EXT.V_REGISTRO_DIARIO_SPOT_EXPORT
)
SELECT
    pro.id_programa_otm,
    pro.equipo,
    pro.codigo_tarea,
    pro.descripcion,
    pro.fecha_limite,
    pro.fecha_ejecucion_otm,
    pro.fecha_hora_inicio,
    pro.fecha_hora_fin,
    pro.fecha_log,

    eq.equipo_codigo,
    eq.tipo_equipo,
    eq.marca,
    eq.modelo,

    rotm.nombre_faena,
    rotm.actividad,
    rotm.tipo_actividad,
    rotm.estado_actividad,
    rotm.fecha_inicio,
    rotm.numero_otm,

    otm.tipo_solicitud,
    otm.valor_total,
    otm.monto_total_factura,
    otm.monto_neto,
    otm.fecha_solicitud
FROM programa pro
LEFT JOIN equipo eq ON eq.equipo_codigo = pro.equipo
LEFT JOIN reg_otm rotm ON pro.otm = rotm.numero_otm
LEFT JOIN ot_mantenimiento otm ON rotm.numero_otm = otm.ot
WHERE {where_clause}
LIMIT 20000
"""

    db = next(get_erp_db())
    try:
        res = db.execute(text(sql), params).mappings().all()
    except Exception as e:
        db.close()
        return jsonify({"error": str(e)}), 500

    # ====== Agregaciones para payload ======
    # Costos: preferimos monto_total_factura > valor_total > monto_neto
    def row_cost(r):
        return to_float(r.get("monto_total_factura")) or to_float(r.get("valor_total")) or to_float(r.get("monto_neto"))

    # Downtime: usamos programa.fecha_hora_inicio/fin cuando existen
    def row_downtime_hours(r):
        return hours_between(r.get("fecha_hora_inicio"), r.get("fecha_hora_fin"))

    # ¿Es OTR (reparación)? heurística por tipo_solicitud o tipo_actividad
    def is_otr(r):
        ts = (r.get("tipo_solicitud") or "").upper()
        ta = (r.get("tipo_actividad") or "").upper()
        return ("OTR" in ts) or ("REPAR" in ta)  # REPAR… (Reparación)

    # ===== KPIs =====
    cost_total = sum(row_cost(r) for r in res)
    downtime_total = sum(row_downtime_hours(r) for r in res)
    # MTTR: promedio de duraciones en OTR
    mttr_numer = 0.0
    mttr_den = 0
    for r in res:
        if is_otr(r):
            h = row_downtime_hours(r)
            if h > 0:
                mttr_numer += h
                mttr_den += 1
    mttr = (mttr_numer / mttr_den) if mttr_den else 0.0

    # MTBF aprox: (horas del periodo) / (# OTR por máquina) → luego promediamos
    period_hours = max((date_to - date_from).total_seconds() / 3600.0, 1.0)
    otr_count_by_machine = defaultdict(int)
    for r in res:
        if is_otr(r):
            m = r.get("equipo_codigo") or r.get("equipo")
            if m:
                otr_count_by_machine[m] += 1
    mtbf_vals = []
    for m, c in otr_count_by_machine.items():
        mtbf_vals.append(period_hours / c if c else period_hours)
    mtbf = (sum(mtbf_vals) / len(mtbf_vals)) if mtbf_vals else 0.0

    # ===== Charts =====
    # 1) Costos por mes
    cost_by_month = defaultdict(float)
    for r in res:
        # Mes por fecha de solicitud (compra) o por fecha_inicio (OTM) o fecha_log
        base_date = r.get("fecha_solicitud") or r.get("fecha_inicio") or r.get("fecha_log") or r.get("fecha_ejecucion_otm")
        key = month_key(base_date)
        if key:
            cost_by_month[key] += row_cost(r)
    cost_monthly = [{"month": k, "cost": v} for k, v in sorted(cost_by_month.items())]

    # 2) Pareto de causas por costo (usamos rotm.actividad como “causa”)
    cost_by_cause = defaultdict(float)
    for r in res:
        cause = r.get("actividad") or "Sin causa"
        cost_by_cause[cause] += row_cost(r)
    pareto_items = sorted(cost_by_cause.items(), key=lambda kv: kv[1], reverse=True)
    cum = 0.0
    total = sum(v for _, v in pareto_items) or 1.0
    cause_pareto = []
    for cause, val in pareto_items:
        cum += val
        cause_pareto.append({"cause": cause, "cost": val, "cumPct": min(cum / total * 100.0, 100.0)})

    # 3) Downtime por máquina
    dt_by_machine = defaultdict(float)
    for r in res:
        mach = r.get("equipo_codigo") or r.get("equipo") or "N/D"
        dt_by_machine[mach] += row_downtime_hours(r)
    downtime_by_machine = [{"machine": k, "hours": v} for k, v in sorted(dt_by_machine.items(), key=lambda kv: kv[1], reverse=True)]

    # 4) MTTR / MTBF por máquina
    mttr_by_machine_n = defaultdict(float)
    mttr_by_machine_d = defaultdict(int)
    for r in res:
        if is_otr(r):
            m = r.get("equipo_codigo") or r.get("equipo") or "N/D"
            h = row_downtime_hours(r)
            if h > 0:
                mttr_by_machine_n[m] += h
                mttr_by_machine_d[m] += 1
    mttr_mtbf_by_machine = []
    # para MTBF por máquina: mismo estimador simple del periodo / OTRs
    for m in set(list(dt_by_machine.keys()) + list(otr_count_by_machine.keys())):
        m_mttr = (mttr_by_machine_n[m] / mttr_by_machine_d[m]) if mttr_by_machine_d[m] else 0.0
        m_mtbf = (period_hours / otr_count_by_machine[m]) if otr_count_by_machine[m] else 0.0
        mttr_mtbf_by_machine.append({"machine": m, "mttr": m_mttr, "mtbf": m_mtbf})

    # ===== Tabla de recientes =====
    # Ordena por fecha (desc) usando “mejor disponible”
    def best_date(r):
        return r.get("fecha_solicitud") or r.get("fecha_inicio") or r.get("fecha_ejecucion_otm") or r.get("fecha_log")
    sorted_res = sorted(res, key=best_date_dt, reverse=True)
    recent = []
    for r in sorted_res[:50]:
        recent.append({
            "ot": r.get("numero_otm") or r.get("tipo_solicitud") or "N/D",
            "fecha": to_iso(best_date(r)) or "",
            "maquina": r.get("equipo_codigo") or r.get("equipo") or "N/D",
            "causa": r.get("actividad") or (r.get("tipo_actividad") or "N/D"),
            "costo": row_cost(r),
            "estado": r.get("estado_actividad") or r.get("tipo_solicitud") or "N/D",
        })

    # ===== Filtros de UI (valores reales presentes en data) =====
    sites = sorted({r.get("nombre_faena") for r in res if r.get("nombre_faena")}) or []
    machines = sorted({(r.get("equipo_codigo") or r.get("equipo")) for r in res if (r.get("equipo_codigo") or r.get("equipo"))}) or []

    payload = {
        "filters": {
            "sites": sites + (["TODOS"] if "TODOS" not in sites else []),
            "machines": machines + (["TODAS"] if "TODAS" not in machines else []),
        },
        "kpis": {
            "cost_total": cost_total,
            "downtime_total": downtime_total,
            "mttr": mttr,
            "mtbf": mtbf,
            "wo_closed": len([r for r in res if (r.get("estado_actividad") or "").upper() in ("CERRADA", "CERRADO")]),
            # tendencias simples (vs mes anterior) si existen ≥2 meses
            "cost_trend": _trend(cost_monthly, key="cost"),
            "downtime_trend": _trend_series(downtime_by_machine, key="hours"),
        },
        "charts": {
            "cost_monthly": cost_monthly,
            "cause_pareto": cause_pareto,
            "downtime_by_machine": downtime_by_machine,
            "mttr_mtbf_by_machine": mttr_mtbf_by_machine,
        },
        "recent": recent,
    }

    db.close()
    return jsonify(_json_ready(payload)), 200


# ---- helpers de tendencia y json safe ----
def _trend(series, key):
    """Comparación último vs penúltimo valor (%). Para cost_monthly."""
    if not series or len(series) < 2:
        return 0.0
    a = to_float(series[-2].get(key))
    b = to_float(series[-1].get(key))
    if a == 0:
        return 0.0
    return ((b - a) / a) * 100.0

def _trend_series(series, key):
    """Versión simplificada para una lista cualquiera: promedio mitad 1 vs mitad 2."""
    n = len(series)
    if n < 2:
        return 0.0
    mid = n // 2
    a = sum(to_float(x.get(key)) for x in series[:mid]) / max(mid, 1)
    b = sum(to_float(x.get(key)) for x in series[mid:]) / max(n - mid, 1)
    if a == 0:
        return 0.0
    return ((b - a) / a) * 100.0

def _json_ready(obj):
    """Convierte Decimals/fechas anidadas para jsonify."""
    if isinstance(obj, dict):
        return {k: _json_ready(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_json_ready(x) for x in obj]
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    return obj
