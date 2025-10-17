# backend/endpoints/query/reprogramaciones/reprogrmaciones.py
from __future__ import annotations

from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
from datetime import datetime, timedelta
from sqlalchemy import func, or_, literal
from sqlalchemy.orm import aliased


from database.database import get_db
from models.models import (
    Faena, Equipo, TipoEquipo, Marca, Modelo,
    Programa, OrdenMan,
    ReprogramacionOtm, MotivoReprogramacion,
)

reprogramaciones_api = Blueprint(
    "reprogramaciones_api",
    __name__,
    url_prefix="/query/reprogramaciones",
)

# ----------------------- Utils -----------------------
def _parse_date(s: str | None):
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f"):
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            pass
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return None

# ----------------------- Filtros -----------------------
@reprogramaciones_api.get("/filters/faenas", strict_slashes=False)
@cross_origin()
def filtros_faenas():
    db = next(get_db())
    try:
        rows = (
            db.query(Faena.faena_id.label("id"), Faena.faena_desc.label("desc"))
              .join(Programa, Programa.faena_id == Faena.faena_id)
              .join(Equipo, Equipo.equipo_id == Programa.equipo_id)
              .distinct()
              .order_by(Faena.faena_desc.asc())
              .all()
        )
        return jsonify({"ok": True, "data": [{"id": r.id, "desc": r.desc} for r in rows]})
    finally:
        db.close()


@reprogramaciones_api.get("/filters/tipos", strict_slashes=False)
@cross_origin()
def filtros_tipos():
    faena_id = request.args.get("faena_id", type=int)
    if not faena_id:
        return jsonify({"ok": False, "error": "faena_id es requerido"}), 400

    db = next(get_db())
    try:
        rows = (
            db.query(
                TipoEquipo.tipo_equipo_desc.label("desc"),
                func.array_agg(func.distinct(TipoEquipo.tipo_equipo_id)).label("ids"),
                func.count(func.distinct(Equipo.equipo_id)).label("equipos_count"),
            )
            .join(Equipo, Equipo.tipo_equipo_id == TipoEquipo.tipo_equipo_id)
            .join(Programa, Programa.equipo_id == Equipo.equipo_id)
            .filter(Programa.faena_id == faena_id)
            .group_by(TipoEquipo.tipo_equipo_desc)
            .order_by(TipoEquipo.tipo_equipo_desc.asc())
            .all()
        )

        data = [{"desc": r.desc, "ids": [int(i) for i in r.ids], "equipos_count": int(r.equipos_count)} for r in rows]
        return jsonify({"ok": True, "data": data})
    except Exception as e:
        db.rollback()
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        db.close()


@reprogramaciones_api.get("/filters/equipos", strict_slashes=False)
@cross_origin()
def filtros_equipos():
    faena_id = request.args.get("faena_id", type=int)
    tipo_ids_csv = request.args.get("tipo_ids", default="", type=str)
    tipo_ids_list = request.args.getlist("tipo_ids", type=int)
    if not tipo_ids_list and tipo_ids_csv:
        tipo_ids_list = [int(x) for x in tipo_ids_csv.split(",") if x.strip().isdigit()]

    if not faena_id:
        return jsonify({"ok": False, "error": "faena_id es requerido"}), 400

    db = next(get_db())
    try:
        q = (
            db.query(Equipo.equipo_id.label("id"), Equipo.equipo_desc.label("desc"))
              .join(Programa, Programa.equipo_id == Equipo.equipo_id)
              .filter(Programa.faena_id == faena_id)
        )
        if tipo_ids_list:
            q = q.filter(Equipo.tipo_equipo_id.in_(tipo_ids_list))

        rows = q.distinct().order_by(Equipo.equipo_desc.asc()).all()
        return jsonify({"ok": True, "data": [{"id": r.id, "desc": r.desc} for r in rows]})
    except Exception as e:
        db.rollback()
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        db.close()


# ----------------------- Listado principal -----------------------
@reprogramaciones_api.get("/", strict_slashes=False)
@cross_origin()
def listar_reprogramaciones():
    faena_id  = request.args.get("faena_id",  type=int)
    tipo_id   = request.args.get("tipo_id",   type=int)
    equipo_id = request.args.get("equipo_id", type=int)

    desde_ts = _parse_date(request.args.get("desde"))
    hasta_ts = _parse_date(request.args.get("hasta"))
    if hasta_ts:
        hasta_ts = hasta_ts + timedelta(days=1)

    limit  = request.args.get("limit",  default=100, type=int)
    offset = request.args.get("offset", default=0,   type=int)

    db = next(get_db())
    try:
        Eq = aliased(Equipo)
        Te = aliased(TipoEquipo)
        Ma = aliased(Marca)
        Mo = aliased(Modelo)

        r_sub = (
            db.query(
                ReprogramacionOtm.otm_id.label("otm_id"),
                func.count(ReprogramacionOtm.n_reprogramacion).label("reprogramaciones_cantidad"),
                func.min(ReprogramacionOtm.fecha_inicio).label("reg_fecha_programada_original"),
                func.max(ReprogramacionOtm.fecha_inicio).label("reg_fecha_inicio_real"),
                func.max(MotivoReprogramacion.motivo_reprogramacion_desc).label("reprogramaciones_motivo"),
            )
            .outerjoin(
                MotivoReprogramacion,
                ReprogramacionOtm.motivo_reprogramacion_id == MotivoReprogramacion.motivo_reprogramacion_id
            )
            .group_by(ReprogramacionOtm.otm_id)
            .subquery()
        )

        q = (
            db.query(
                OrdenMan.otm_id.label("id_programa_otm"),
                OrdenMan.otm_id.label("otm_numero"),
                OrdenMan.otm_desc.label("actividad_nombre"),
                Programa.estado_otm.label("actividad_estado"),
                literal("MANTENIMIENTO").label("actividad_tipo"),
                Programa.usuario_programacion.label("otm_usuario_programador"),
                Programa.disponibilidad_insumos.label("otm_disponibilidad_insumos"),

                r_sub.c.reg_fecha_inicio_real,
                r_sub.c.reg_fecha_programada_original,
                r_sub.c.reprogramaciones_cantidad,
                r_sub.c.reprogramaciones_motivo,

                Eq.equipo_desc.label("equipo_codigo"),
                Te.tipo_equipo_desc.label("equipo_tipo"),
                Ma.marca_desc.label("equipo_marca"),
                Mo.modelo_desc.label("equipo_modelo"),

                Faena.faena_desc.label("faena_nombre"),
                Eq.equipo_desc.label("faena_codigo_interno"),
            )
            .select_from(OrdenMan)
            .join(Programa, OrdenMan.programa_id == Programa.programa_id)
            .join(Eq, Eq.equipo_id == Programa.equipo_id)
            .join(Te, Te.tipo_equipo_id == Eq.tipo_equipo_id)
            .join(Ma, Ma.marca_id == Te.marca_id)
            .join(Mo, Mo.modelo_id == Ma.modelo_id)
            .join(Faena, Faena.faena_id == Programa.faena_id)
            .outerjoin(r_sub, r_sub.c.otm_id == OrdenMan.otm_id)
        )

        if faena_id:
            q = q.filter(Programa.faena_id == faena_id)
        if tipo_id:
            q = q.filter(Eq.tipo_equipo_id == tipo_id)
        if equipo_id:
            q = q.filter(Eq.equipo_id == equipo_id)

        if desde_ts or hasta_ts:
            if desde_ts and hasta_ts:
                q = q.filter(
                    or_(
                        r_sub.c.reg_fecha_inicio_real.between(desde_ts, hasta_ts),
                        r_sub.c.reg_fecha_inicio_real.is_(None)
                    )
                )
            elif desde_ts:
                q = q.filter(
                    or_(
                        r_sub.c.reg_fecha_inicio_real >= desde_ts,
                        r_sub.c.reg_fecha_inicio_real.is_(None)
                    )
                )
            elif hasta_ts:
                q = q.filter(
                    or_(
                        r_sub.c.reg_fecha_inicio_real <= hasta_ts,
                        r_sub.c.reg_fecha_inicio_real.is_(None)
                    )
                )

        q = q.order_by(r_sub.c.reprogramaciones_cantidad.desc().nullslast())
        q = q.limit(limit).offset(offset)

        rows = q.all()

        data = []
        for r in rows:
            data.append({
                "id_programa_otm": r.id_programa_otm,
                "otm_numero": r.otm_numero,
                "actividad_nombre": r.actividad_nombre,
                "actividad_estado": r.actividad_estado,
                "actividad_tipo": r.actividad_tipo,
                "otm_usuario_programador": r.otm_usuario_programador,
                "otm_disponibilidad_insumos": r.otm_disponibilidad_insumos,
                "reg_fecha_inicio_real": r.reg_fecha_inicio_real.isoformat() if r.reg_fecha_inicio_real else None,
                "reg_fecha_programada_original": r.reg_fecha_programada_original.isoformat() if r.reg_fecha_programada_original else None,
                "reprogramaciones_cantidad": int(r.reprogramaciones_cantidad) if r.reprogramaciones_cantidad else 0,
                "reprogramaciones_motivo": r.reprogramaciones_motivo,
                "equipo_codigo": r.equipo_codigo,
                "equipo_tipo": r.equipo_tipo,
                "equipo_marca": r.equipo_marca,
                "equipo_modelo": r.equipo_modelo,
                "faena_nombre": r.faena_nombre,
                "faena_codigo_interno": r.faena_codigo_interno,
            })

        return jsonify({"ok": True, "data": data})

    except Exception as e:
        db.rollback()
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        db.close()