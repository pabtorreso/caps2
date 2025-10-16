from flask import Blueprint, request, jsonify, current_app
import psycopg2
import psycopg2.extras

costos_bp = Blueprint("costos_api", __name__, url_prefix="/query/costos")


def _get_conn():
    dsn = (
        current_app.config.get("ERP_DATABASE_URL")
        or current_app.config.get("PG_DSN")
        or current_app.config.get("SQLALCHEMY_DATABASE_URI")
    )
    if not dsn:
        raise RuntimeError("No hay DSN (ERP_DATABASE_URL / PG_DSN / SQLALCHEMY_DATABASE_URI) en config")

    if dsn.startswith("postgresql+psycopg2://"):
        dsn = dsn.replace("postgresql+psycopg2://", "postgresql://", 1)

    return psycopg2.connect(dsn, cursor_factory=psycopg2.extras.RealDictCursor)


def _ok(data):
    return jsonify({"ok": True, "data": data})


def _err(msg, code=400):
    resp = jsonify({"ok": False, "error": msg})
    resp.status_code = code
    return resp



@costos_bp.get("/filters/faenas")
def filtros_faenas():

    sql = """
        SELECT DISTINCT faena
        FROM consultas_cgo_ext.v_sol_items_otm_otr
        WHERE faena IS NOT NULL AND TRIM(faena) <> ''
        ORDER BY 1;
    """
    conn = _get_conn()
    try:
        with conn, conn.cursor() as cur:
            cur.execute(sql)
            rows = [r["faena"] for r in cur.fetchall()]
        return _ok(rows)
    finally:
        conn.close()


@costos_bp.get("/filters/tipos")
def filtros_tipos():

    faena = request.args.get("faena", "").strip()
    if not faena:
        return _err("Falta parámetro 'faena'.")

    sql = """
    WITH ot_mantenimiento AS (
        SELECT DISTINCT
            equipo,
            faena
        FROM consultas_cgo_ext.v_sol_items_otm_otr
        WHERE faena = %(faena)s
    ),
    equipo AS (
        SELECT DISTINCT
            equipo_codigo,
            TRIM(REGEXP_REPLACE(SPLIT_PART(equipo, ' - ', 1), '^[A-Z0-9-]+ ', '')) AS tipo_equipo
        FROM consultas_cgo_ext.v_registro_diario_anglo_export
        UNION ALL
        SELECT DISTINCT equipo_codigo,
            TRIM(REGEXP_REPLACE(SPLIT_PART(equipo, ' - ', 1), '^[A-Z0-9-]+ ', ''))
        FROM consultas_cgo_ext.v_registro_diario_cgo_andina_export
        UNION ALL
        SELECT DISTINCT equipo_codigo,
            TRIM(REGEXP_REPLACE(SPLIT_PART(equipo, ' - ', 1), '^[A-Z0-9-]+ ', ''))
        FROM consultas_cgo_ext.v_registro_diario_cgo_cumet_ventanas_export
        UNION ALL
        SELECT DISTINCT equipo_codigo,
            TRIM(REGEXP_REPLACE(SPLIT_PART(equipo, ' - ', 1), '^[A-Z0-9-]+ ', ''))
        FROM consultas_cgo_ext.v_registro_diario_cucons_export
        UNION ALL
        SELECT DISTINCT equipo_codigo,
            TRIM(REGEXP_REPLACE(SPLIT_PART(equipo, ' - ', 1), '^[A-Z0-9-]+ ', ''))
        FROM consultas_cgo_ext.v_registro_diario_eteo_export
        UNION ALL
        SELECT DISTINCT equipo_codigo,
            TRIM(REGEXP_REPLACE(SPLIT_PART(equipo, ' - ', 1), '^[A-Z0-9-]+ ', ''))
        FROM consultas_cgo_ext.v_registro_diario_kdm_export
        UNION ALL
        SELECT DISTINCT equipo_codigo,
            TRIM(REGEXP_REPLACE(SPLIT_PART(equipo, ' - ', 1), '^[A-Z0-9-]+ ', ''))
        FROM consultas_cgo_ext.v_registro_diario_tc_export
        UNION ALL
        SELECT DISTINCT equipo_codigo,
            TRIM(REGEXP_REPLACE(SPLIT_PART(equipo, ' - ', 1), '^[A-Z0-9-]+ ', ''))
        FROM consultas_cgo_ext.v_registro_diario_catodo_export
        UNION ALL
        SELECT DISTINCT equipo_codigo,
            TRIM(REGEXP_REPLACE(SPLIT_PART(equipo, ' - ', 1), '^[A-Z0-9-]+ ', ''))
        FROM consultas_cgo_ext.v_registro_diario_spot_export
    )
    SELECT DISTINCT e.tipo_equipo
    FROM ot_mantenimiento otm
    JOIN equipo e ON TRIM(otm.equipo) = TRIM(e.equipo_codigo)
    WHERE e.tipo_equipo IS NOT NULL AND e.tipo_equipo <> ''
    ORDER BY 1;
    """
    conn = _get_conn()
    try:
        with conn, conn.cursor() as cur:
            cur.execute(sql, {"faena": faena})
            rows = [r["tipo_equipo"] for r in cur.fetchall()]
        return _ok(rows)
    finally:
        conn.close()


@costos_bp.get("/filters/equipos")
def filtros_equipos():

    faena = request.args.get("faena", "").strip()
    tipo = request.args.get("tipo", "").strip()
    if not faena or not tipo:
        return _err("Faltan parámetros 'faena' y/o 'tipo'.")

    sql = """
    WITH ot_mantenimiento AS (
        SELECT DISTINCT equipo, faena
        FROM consultas_cgo_ext.v_sol_items_otm_otr
        WHERE faena = %(faena)s
    ),
    equipo AS (
        SELECT DISTINCT
            equipo_codigo,
            TRIM(REGEXP_REPLACE(SPLIT_PART(equipo, ' - ', 1), '^[A-Z0-9-]+ ', '')) AS tipo_equipo
        FROM consultas_cgo_ext.v_registro_diario_anglo_export
        UNION ALL
        SELECT DISTINCT equipo_codigo,
            TRIM(REGEXP_REPLACE(SPLIT_PART(equipo, ' - ', 1), '^[A-Z0-9-]+ ', ''))
        FROM consultas_cgo_ext.v_registro_diario_cgo_andina_export
        UNION ALL
        SELECT DISTINCT equipo_codigo,
            TRIM(REGEXP_REPLACE(SPLIT_PART(equipo, ' - ', 1), '^[A-Z0-9-]+ ', ''))
        FROM consultas_cgo_ext.v_registro_diario_cgo_cumet_ventanas_export
        UNION ALL
        SELECT DISTINCT equipo_codigo,
            TRIM(REGEXP_REPLACE(SPLIT_PART(equipo, ' - ', 1), '^[A-Z0-9-]+ ', ''))
        FROM consultas_cgo_ext.v_registro_diario_cucons_export
        UNION ALL
        SELECT DISTINCT equipo_codigo,
            TRIM(REGEXP_REPLACE(SPLIT_PART(equipo, ' - ', 1), '^[A-Z0-9-]+ ', ''))
        FROM consultas_cgo_ext.v_registro_diario_eteo_export
        UNION ALL
        SELECT DISTINCT equipo_codigo,
            TRIM(REGEXP_REPLACE(SPLIT_PART(equipo, ' - ', 1), '^[A-Z0-9-]+ ', ''))
        FROM consultas_cgo_ext.v_registro_diario_kdm_export
        UNION ALL
        SELECT DISTINCT equipo_codigo,
            TRIM(REGEXP_REPLACE(SPLIT_PART(equipo, ' - ', 1), '^[A-Z0-9-]+ ', ''))
        FROM consultas_cgo_ext.v_registro_diario_tc_export
        UNION ALL
        SELECT DISTINCT equipo_codigo,
            TRIM(REGEXP_REPLACE(SPLIT_PART(equipo, ' - ', 1), '^[A-Z0-9-]+ ', ''))
        FROM consultas_cgo_ext.v_registro_diario_catodo_export
        UNION ALL
        SELECT DISTINCT equipo_codigo,
            TRIM(REGEXP_REPLACE(SPLIT_PART(equipo, ' - ', 1), '^[A-Z0-9-]+ ', ''))
        FROM consultas_cgo_ext.v_registro_diario_spot_export
    )
    SELECT DISTINCT TRIM(otm.equipo) AS equipo_codigo
    FROM ot_mantenimiento otm
    JOIN equipo e ON TRIM(otm.equipo) = TRIM(e.equipo_codigo)
    WHERE e.tipo_equipo = %(tipo)s
    ORDER BY 1;
    """
    conn = _get_conn()
    try:
        with conn, conn.cursor() as cur:
            cur.execute(sql, {"faena": faena, "tipo": tipo})
            rows = [r["equipo_codigo"] for r in cur.fetchall()]
        return _ok(rows)
    finally:
        conn.close()


# === Data main ===

@costos_bp.get("")
def get_costos():

    faena = request.args.get("faena", "").strip()
    equipo = request.args.get("equipo", "").strip()
    limit = int(request.args.get("limit", 1000))
    offset = int(request.args.get("offset", 0))

    if not faena or not equipo:
        return _err("Faltan parámetros 'faena' y/o 'equipo'.")

    sql = """
    WITH programa AS (
        SELECT
            id_programa_otm,
            otm AS numero_otm,
            equipo,
            codigo_tarea,
            horometro_referencia,
            disponibilidad_insumos,
            instrucciones_especiales,
            fecha_limite,
            cantidad_reprogramaciones,
            usuario_programacion,
            nombre_prioridad_otm,
            fecha_ejecucion_otm,
            horometro_planificacion,
            ultimo_horometro,
            fecha_ultimo_horometro,
            usuario_ultimo_horometro,
            fecha_log,
            fecha_hora_inicio,
            fecha_hora_fin,
            estado_programa
        FROM consultas_cgo_ext.v_programa_otm
    ),
    ot_mantenimiento AS (
        SELECT
            numero_solicitud,
            fecha_solicitud,
            ot,
            tipo_solicitud,
            equipo,
            solicitante,
            estado_solicitud,
            faena,
            SPLIT_PART(cuenta_contable, ':', 1) AS id_cuenta,
            TRIM(SPLIT_PART(cuenta_contable, ':', 2)) AS descripcion_cuenta,
            centro_costos,
            SPLIT_PART(proveedor_seleccionado, ' - ', 1) AS proveedor_rut,
            SPLIT_PART(proveedor_seleccionado, ' - ', 2) AS proveedor_nombre,
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
            SPLIT_PART(item_unidad, ' - ', 2) AS item_unidad,
            item_monto_total,
            estado_recepcion,
            fecha_aceptado,
            fecha_aceptado_gerencia,
            validador,
            validador_gerencia
        FROM consultas_cgo_ext.v_sol_items_otm_otr
        WHERE faena = %(faena)s
    ),
    equipo AS (
        SELECT DISTINCT
            equipo_codigo,
            TRIM(REGEXP_REPLACE(SPLIT_PART(equipo, ' - ', 1), '^[A-Z0-9-]+ ', '')) AS tipo_equipo,
            SPLIT_PART(equipo, ' - ', 2) AS marca_equipo,
            SPLIT_PART(equipo, ' - ', 3) AS modelo_equipo
        FROM consultas_cgo_ext.v_registro_diario_anglo_export
        UNION ALL SELECT DISTINCT equipo_codigo,
            TRIM(REGEXP_REPLACE(SPLIT_PART(equipo, ' - ', 1), '^[A-Z0-9-]+ ', '')),
            SPLIT_PART(equipo, ' - ', 2),
            SPLIT_PART(equipo, ' - ', 3)
        FROM consultas_cgo_ext.v_registro_diario_cgo_andina_export
        UNION ALL SELECT DISTINCT equipo_codigo,
            TRIM(REGEXP_REPLACE(SPLIT_PART(equipo, ' - ', 1), '^[A-Z0-9-]+ ', '')),
            SPLIT_PART(equipo, ' - ', 2),
            SPLIT_PART(equipo, ' - ', 3)
        FROM consultas_cgo_ext.v_registro_diario_cgo_cumet_ventanas_export
        UNION ALL SELECT DISTINCT equipo_codigo,
            TRIM(REGEXP_REPLACE(SPLIT_PART(equipo, ' - ', 1), '^[A-Z0-9-]+ ', '')),
            SPLIT_PART(equipo, ' - ', 2),
            SPLIT_PART(equipo, ' - ', 3)
        FROM consultas_cgo_ext.v_registro_diario_cucons_export
        UNION ALL SELECT DISTINCT equipo_codigo,
            TRIM(REGEXP_REPLACE(SPLIT_PART(equipo, ' - ', 1), '^[A-Z0-9-]+ ', '')),
            SPLIT_PART(equipo, ' - ', 2),
            SPLIT_PART(equipo, ' - ', 3)
        FROM consultas_cgo_ext.v_registro_diario_eteo_export
        UNION ALL SELECT DISTINCT equipo_codigo,
            TRIM(REGEXP_REPLACE(SPLIT_PART(equipo, ' - ', 1), '^[A-Z0-9-]+ ', '')),
            SPLIT_PART(equipo, ' - ', 2),
            SPLIT_PART(equipo, ' - ', 3)
        FROM consultas_cgo_ext.v_registro_diario_kdm_export
        UNION ALL SELECT DISTINCT equipo_codigo,
            TRIM(REGEXP_REPLACE(SPLIT_PART(equipo, ' - ', 1), '^[A-Z0-9-]+ ', '')),
            SPLIT_PART(equipo, ' - ', 2),
            SPLIT_PART(equipo, ' - ', 3)
        FROM consultas_cgo_ext.v_registro_diario_tc_export
        UNION ALL SELECT DISTINCT equipo_codigo,
            TRIM(REGEXP_REPLACE(SPLIT_PART(equipo, ' - ', 1), '^[A-Z0-9-]+ ', '')),
            SPLIT_PART(equipo, ' - ', 2),
            SPLIT_PART(equipo, ' - ', 3)
        FROM consultas_cgo_ext.v_registro_diario_catodo_export
        UNION ALL SELECT DISTINCT equipo_codigo,
            TRIM(REGEXP_REPLACE(SPLIT_PART(equipo, ' - ', 1), '^[A-Z0-9-]+ ', '')),
            SPLIT_PART(equipo, ' - ', 2),
            SPLIT_PART(equipo, ' - ', 3)
        FROM consultas_cgo_ext.v_registro_diario_spot_export
    )
    SELECT DISTINCT
        -- Identificación
        p.id_programa_otm                         AS id_programa_otm,
        p.numero_otm                              AS otm_numero,

        -- Equipo
        p.equipo                                  AS equipo_codigo,
        e.tipo_equipo                             AS equipo_tipo,
        e.marca_equipo                            AS equipo_marca,
        e.modelo_equipo                           AS equipo_modelo,
        p.horometro_planificacion                 AS equipo_horometro_planificacion,

        -- Compras / Insumos
        otm.numero_solicitud                      AS compra_numero_solicitud,
        otm.fecha_solicitud                       AS compra_fecha_solicitud,
        otm.proveedor_rut                         AS rut_proveedor,
        otm.proveedor_nombre                      AS nombre_proveedor,
        otm.motivo_compra                         AS motivo_compra,
        otm.item_material_o_servicio              AS compra_item,
        otm.item_cantidad                         AS compra_cantidad,
        otm.item_unidad                           AS compra_unidad,
        otm.item_monto_total                      AS compra_monto_item,
        otm.monto_neto                            AS compra_monto_neto,
        otm.valor_total                           AS compra_valor_total,
        otm.monto_total_factura                   AS compra_monto_total_factura,
        otm.fecha_emision_factura                 AS compra_fecha_factura,
        otm.orden_compra                          AS compra_orden,
        otm.estado_solicitud                      AS compra_estado,
        otm.condicion_pago                        AS compra_condicion_pago,
        otm.id_cuenta                             AS id_cuenta,
        otm.descripcion_cuenta                    AS descripcion_cuenta,
        otm.centro_costos                         AS compra_centro_costos,

        p.estado_programa                         AS estado_programa
    FROM programa p
    LEFT JOIN ot_mantenimiento otm ON p.numero_otm = otm.ot
    LEFT JOIN equipo e ON TRIM(p.equipo) = TRIM(e.equipo_codigo)
    WHERE otm.faena = %(faena)s
      AND TRIM(p.equipo) = %(equipo)s
    ORDER BY p.id_programa_otm, p.numero_otm, otm.fecha_solicitud
    LIMIT %(limit)s OFFSET %(offset)s;
    """

    conn = _get_conn()
    try:
        with conn, conn.cursor() as cur:
            cur.execute(sql, {
                "faena": faena,
                "equipo": equipo,
                "limit": limit,
                "offset": offset
            })
            rows = cur.fetchall()
        return _ok(rows)
    finally:
        conn.close()
