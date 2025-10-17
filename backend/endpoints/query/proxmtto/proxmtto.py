# backend/endpoints/query/proxmtto/proxmtto.py
from flask import Blueprint, request, jsonify
from sqlalchemy import text
from database.database import get_db
from decimal import Decimal
from datetime import datetime, date

proxmtto_bp = Blueprint("proxmtto_api", __name__, url_prefix="/query/proxmtto")

def _to_json(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, (datetime, date)):
        return obj.isoformat()
    return obj

def _ok(data):
    return jsonify({"ok": True, "data": data})

def _err(msg, code=400):
    resp = jsonify({"ok": False, "error": msg})
    resp.status_code = code
    return resp


# ========= Filtros =========
@proxmtto_bp.get("/filters/faenas", strict_slashes=False)
def filtros_faenas():
    db = next(get_db())
    try:
        sql = text("""
            SELECT DISTINCT f.faena_desc
            FROM proximo_mantenimiento pm
            JOIN equipo e ON e.equipo_id = pm.equipo_id
            JOIN programa p ON p.equipo_id = e.equipo_id
            JOIN faena f ON f.faena_id = p.faena_id
            ORDER BY f.faena_desc
        """)
        
        rows = db.execute(sql).fetchall()
        return _ok([r[0] for r in rows])
    except Exception as e:
        db.rollback()
        return _err(str(e), 500)
    finally:
        db.close()


@proxmtto_bp.get("/filters/tipos", strict_slashes=False)
def filtros_tipos():
    faena = request.args.get("faena", "").strip()
    if not faena:
        return _err("Falta parámetro 'faena'.")
    
    db = next(get_db())
    try:
        sql = text("""
            SELECT DISTINCT te.tipo_equipo_desc
            FROM proximo_mantenimiento pm
            JOIN equipo e ON e.equipo_id = pm.equipo_id
            JOIN tipo_equipo te ON te.tipo_equipo_id = e.tipo_equipo_id
            JOIN programa p ON p.equipo_id = e.equipo_id
            JOIN faena f ON f.faena_id = p.faena_id
            WHERE f.faena_desc = :faena
            ORDER BY te.tipo_equipo_desc
        """)
        
        rows = db.execute(sql, {"faena": faena}).fetchall()
        return _ok([r[0] for r in rows])
    except Exception as e:
        db.rollback()
        return _err(str(e), 500)
    finally:
        db.close()


@proxmtto_bp.get("/filters/equipos", strict_slashes=False)
def filtros_equipos():
    faena = request.args.get("faena", "").strip()
    tipo = request.args.get("tipo", "").strip()
    
    if not faena:
        return _err("Falta parámetro 'faena'.")
    
    db = next(get_db())
    try:
        sql_str = """
            SELECT DISTINCT e.equipo_desc
            FROM proximo_mantenimiento pm
            JOIN equipo e ON e.equipo_id = pm.equipo_id
            JOIN tipo_equipo te ON te.tipo_equipo_id = e.tipo_equipo_id
            JOIN programa p ON p.equipo_id = e.equipo_id
            JOIN faena f ON f.faena_id = p.faena_id
            WHERE f.faena_desc = :faena
        """
        params = {"faena": faena}
        
        if tipo:
            sql_str += " AND te.tipo_equipo_desc = :tipo"
            params["tipo"] = tipo
        
        sql_str += " ORDER BY e.equipo_desc"
        
        rows = db.execute(text(sql_str), params).fetchall()
        return _ok([r[0] for r in rows])
    except Exception as e:
        db.rollback()
        return _err(str(e), 500)
    finally:
        db.close()


# ========= Data Principal =========
@proxmtto_bp.get("", strict_slashes=False)
def get_proximo_mantenimiento():
    faena = request.args.get("faena", "").strip()
    tipo = request.args.get("tipo", "").strip()
    equipo_param = request.args.get("equipo", "").strip()
    limit = int(request.args.get("limit", 500))
    offset = int(request.args.get("offset", 0))
    
    db = next(get_db())
    try:
        sql_str = """
            SELECT 
                e.equipo_desc,
                f.faena_desc,
                pm.ultimo_horometro_otm,
                pm.fec_ultima_otm,
                pm.prom_horas_entre_otm,
                pm.prom_horas_trabajadas_diarias,
                pm.dias_restantes,
                pm.fecha_prox_otm,
                pm.horometro_prox_otm
            FROM proximo_mantenimiento pm
            JOIN equipo e ON e.equipo_id = pm.equipo_id
            LEFT JOIN tipo_equipo te ON te.tipo_equipo_id = e.tipo_equipo_id
            LEFT JOIN (
                SELECT DISTINCT ON (equipo_id) 
                    equipo_id, faena_id
                FROM programa
                ORDER BY equipo_id, programa_id DESC
            ) p ON p.equipo_id = e.equipo_id
            LEFT JOIN faena f ON f.faena_id = p.faena_id
            WHERE 1=1
        """
        
        params = {}
        
        if faena:
            sql_str += " AND f.faena_desc = :faena"
            params["faena"] = faena
        
        if tipo:
            sql_str += " AND te.tipo_equipo_desc = :tipo"
            params["tipo"] = tipo
        
        if equipo_param:
            sql_str += " AND e.equipo_desc = :equipo"
            params["equipo"] = equipo_param
        
        sql_str += " ORDER BY pm.dias_restantes ASC NULLS LAST LIMIT :limit OFFSET :offset"
        params["limit"] = limit
        params["offset"] = offset
        
        rows = db.execute(text(sql_str), params).fetchall()
        
        # ✅ NOMBRES CORREGIDOS PARA COINCIDIR CON EL FRONTEND
        data = []
        for r in rows:
            data.append({
                "equipo_codigo": r[0],  # ✅ era "equipo"
                "faena": r[1],
                "horometro_ultimo_mantenimiento": _to_json(r[2]),  # ✅ era "horo_ultimo_mant"
                "fecha_ultimo_mantenimiento": _to_json(r[3]),  # ✅ era "f_ultimo_mant"
                "promedio_horas_entre_mantenimientos": _to_json(r[4]),  # ✅ era "prom_horas_entre_mant"
                "promedio_horas_trabajadas_diarias": _to_json(r[5]),  # ✅ era "prom_horas_diarias"
                "dias_restantes_aprox": _to_json(r[6]),  # ✅ era "dias_restantes"
                "fecha_proximo_mantenimiento": _to_json(r[7]),  # ✅ era "f_proximo_mant"
                "horometro_estimado_proximo_mantenimiento": _to_json(r[8]),  # ✅ era "horo_estimado_proximo"
            })
        
        return _ok(data)
    
    except Exception as e:
        db.rollback()
        return _err(str(e), 500)
    finally:
        db.close()