# backend/routes/home/diagnostics.py
from flask import Blueprint, jsonify, request
from sqlalchemy import text
from database.database_erp import get_erp_db
from datetime import datetime, timedelta

home_diag_bp = Blueprint("home_diag_bp", __name__)

@home_diag_bp.get("/ping")
def ping_basic():
    """Sanity check: conexión al ERP"""
    db = next(get_erp_db())
    try:
        db.execute(text("SELECT 1"))
        return jsonify(ok=True), 200
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500
    finally:
        db.close()

@home_diag_bp.get("/ping/vista")
def ping_views():
    """Verifica permisos de lectura mínimos en las vistas usadas por el dashboard."""
    checks = {
        "V_PROGRAMA_OTM": "SELECT 1 FROM CONSULTAS_CGO_EXT.V_PROGRAMA_OTM LIMIT 1",
        "V_REG_HISTORICO_OT_ORDEN": "SELECT 1 FROM CONSULTAS_CGO_EXT.V_REG_HISTORICO_OT_ORDEN LIMIT 1",
        "V_SOL_ITEMS_OTM_OTR": "SELECT 1 FROM CONSULTAS_CGO_EXT.V_SOL_ITEMS_OTM_OTR LIMIT 1",
        # alguna de las tablas de 'equipo' (usa cualquiera que tengas permiso)
        "V_REGISTRO_DIARIO_SPOT_EXPORT": "SELECT 1 FROM CONSULTAS_CGO_EXT.V_REGISTRO_DIARIO_SPOT_EXPORT LIMIT 1",
    }
    db = next(get_erp_db())
    out = {}
    code = 200
    try:
        for name, q in checks.items():
            try:
                db.execute(text(q))
                out[name] = "ok"
            except Exception as e:
                out[name] = f"error: {e}"
                code = 500
        return jsonify(out), code
    finally:
        db.close()

@home_diag_bp.get("/sample")
def sample_query():
    """
    Ejecuta una versión mínima de la query del dashboard con filtros
    y devuelve 5 filas para inspección (sin agregaciones).
    Útil para ver si el WHERE/filtros están bien y si hay datos.
    """
    # Filtros
    p_from = request.args.get("from")
    p_to = request.args.get("to")
    site = request.args.get("site")
    machine = request.args.get("machine")

    try:
        date_from = datetime.fromisoformat(p_from) if p_from else datetime.now() - timedelta(days=90)
        date_to = datetime.fromisoformat(p_to) if p_to else datetime.now()
    except Exception:
        date_from = datetime.now() - timedelta(days=90)
        date_to = datetime.now()

    conds = ["COALESCE(rotm.fecha_inicio, pro.fecha_log, otm.fecha_solicitud::timestamp) BETWEEN :dfrom AND :dto"]
    params = {"dfrom": date_from, "dto": date_to}

    if site and site.upper() != "TODOS":
        conds.append("rotm.nombre_faena = :site")
        params["site"] = site

    if machine and machine.upper() != "TODAS":
        conds.append("eq.equipo_codigo = :machine")
        params["machine"] = machine

    where_clause = " AND ".join(conds)

    sql = f"""
WITH programa AS (
    SELECT id_programa_otm, equipo, codigo_tarea, descripcion, fecha_log, fecha_hora_inicio, fecha_hora_fin, fecha_ejecucion_otm
    FROM CONSULTAS_CGO_EXT.V_PROGRAMA_OTM
),
reg_otm AS (
    SELECT nombre_faena, actividad, tipo_actividad, estado_actividad, fecha_inicio, numero_otm
    FROM CONSULTAS_CGO_EXT.V_REG_HISTORICO_OT_ORDEN
    WHERE numero_otm ~ '^M[0-9]+$'
),
ot_mantenimiento AS (
    SELECT tipo_solicitud, valor_total, monto_total_factura, monto_neto, fecha_solicitud, ot
    FROM CONSULTAS_CGO_EXT.V_SOL_ITEMS_OTM_OTR
),
equipo AS (
    SELECT DISTINCT
        equipo_codigo,
        TRIM(REGEXP_REPLACE(SPLIT_PART(equipo, ' - ', 1), '^[A-Z0-9-]+ ', '')) AS tipo_equipo,
        SPLIT_PART(equipo, ' - ', 2) AS marca,
        SPLIT_PART(equipo, ' - ', 3) AS modelo
    FROM CONSULTAS_CGO_EXT.V_REGISTRO_DIARIO_SPOT_EXPORT
)
SELECT
    pro.id_programa_otm,
    pro.equipo,
    eq.equipo_codigo,
    eq.tipo_equipo,
    eq.marca,
    eq.modelo,
    rotm.numero_otm,
    rotm.nombre_faena,
    rotm.actividad,
    rotm.tipo_actividad,
    rotm.estado_actividad,
    rotm.fecha_inicio,
    pro.fecha_log,
    pro.fecha_hora_inicio,
    pro.fecha_hora_fin,
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
ORDER BY COALESCE(otm.fecha_solicitud, rotm.fecha_inicio, pro.fecha_log) DESC
LIMIT 5
"""
    db = next(get_erp_db())
    try:
        rows = db.execute(text(sql), params).mappings().all()
        # serializar seguro
        def conv(v):
            from decimal import Decimal
            if v is None: return None
            if hasattr(v, "isoformat"): return v.isoformat()
            if isinstance(v, Decimal): return float(v)
            return v
        data = [{k: conv(v) for k, v in r.items()} for r in rows]
        return jsonify({"count": len(data), "rows": data, "filters": {
            "from": date_from.isoformat(), "to": date_to.isoformat(),
            "site": site, "machine": machine
        }}), 200
    except Exception as e:
        # devolvemos el error para verlo desde el front
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500
    finally:
        db.close()
