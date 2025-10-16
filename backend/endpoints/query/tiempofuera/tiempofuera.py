from flask import Blueprint, request, jsonify, current_app
import psycopg2, psycopg2.extras

tfuera_bp = Blueprint("tfuera_api", __name__, url_prefix="/query/tiempo-fuera")

def _schema() -> str:
    return current_app.config.get("COSTOS_SCHEMA", "consultas_cgo_ext")

def _get_conn():
    dsn = (
        current_app.config.get("ERP_DATABASE_URL")
        or current_app.config.get("PG_DSN")
        or current_app.config.get("SQLALCHEMY_DATABASE_URI")
    )
    if not dsn:
        raise RuntimeError("No hay DSN (ERP_DATABASE_URL/PG_DSN/SQLALCHEMY_DATABASE_URI) en config")
    if dsn.startswith("postgresql+psycopg2://"):
        dsn = dsn.replace("postgresql+psycopg2://", "postgresql://", 1)
    return psycopg2.connect(dsn, cursor_factory=psycopg2.extras.RealDictCursor)

def _ok(data): return jsonify({"ok": True, "data": data})
def _err(msg, code=400):
    r = jsonify({"ok": False, "error": msg}); r.status_code = code; return r


# --------- Filtros ----------
@tfuera_bp.get("/filters/faenas")
def filtros_faenas():
    s = _schema()
    sql = f"""
    WITH union_rd AS (
        SELECT distrito FROM {s}.v_registro_diario_anglo_export
        UNION ALL SELECT distrito FROM {s}.v_registro_diario_catodo_export
        UNION ALL SELECT distrito FROM {s}.v_registro_diario_cgo_andina_export
        UNION ALL SELECT distrito FROM {s}.v_registro_diario_cgo_cumet_ventanas_export
        UNION ALL SELECT distrito FROM {s}.v_registro_diario_cucons_export
        UNION ALL SELECT distrito FROM {s}.v_registro_diario_eteo_export
        UNION ALL SELECT distrito FROM {s}.v_registro_diario_kdm_export
        UNION ALL SELECT distrito FROM {s}.v_registro_diario_spot_export
    )
    SELECT DISTINCT TRIM(distrito) AS faena
    FROM union_rd
    WHERE distrito IS NOT NULL AND TRIM(distrito) <> ''
    ORDER BY 1;
    """
    conn = _get_conn()
    try:
        with conn, conn.cursor() as cur:
            cur.execute(sql)
            return _ok([r["faena"] for r in cur.fetchall()])
    finally:
        conn.close()


@tfuera_bp.get("/filters/tipos")
def filtros_tipos():
    faena = request.args.get("faena", "").strip()
    if not faena: return _err("Falta parámetro 'faena'.")

    s = _schema()
    sql = f"""
    WITH equipos AS (
        SELECT equipo FROM {s}.v_registro_diario_anglo_export            WHERE distrito = %(faena)s
        UNION ALL SELECT equipo FROM {s}.v_registro_diario_catodo_export WHERE distrito = %(faena)s
        UNION ALL SELECT equipo FROM {s}.v_registro_diario_cgo_andina_export WHERE distrito = %(faena)s
        UNION ALL SELECT equipo FROM {s}.v_registro_diario_cgo_cumet_ventanas_export WHERE distrito = %(faena)s
        UNION ALL SELECT equipo FROM {s}.v_registro_diario_cucons_export WHERE distrito = %(faena)s
        UNION ALL SELECT equipo FROM {s}.v_registro_diario_eteo_export WHERE distrito = %(faena)s
        UNION ALL SELECT equipo FROM {s}.v_registro_diario_kdm_export WHERE distrito = %(faena)s
        UNION ALL SELECT equipo FROM {s}.v_registro_diario_spot_export WHERE distrito = %(faena)s
    )
    SELECT DISTINCT TRIM(REGEXP_REPLACE(SPLIT_PART(equipo,' - ',1),'^[A-Z0-9-]+ ',''))
    AS tipo_equipo
    FROM equipos
    WHERE equipo IS NOT NULL
    ORDER BY 1;
    """
    conn = _get_conn()
    try:
        with conn, conn.cursor() as cur:
            cur.execute(sql, {"faena": faena})
            return _ok([r["tipo_equipo"] for r in cur.fetchall() if r["tipo_equipo"]])
    finally:
        conn.close()


@tfuera_bp.get("/filters/equipos")
def filtros_equipos():
    faena = request.args.get("faena", "").strip()
    tipo  = request.args.get("tipo", "").strip()
    if not faena or not tipo: return _err("Faltan parámetros 'faena' y/o 'tipo'.")

    s = _schema()
    sql = f"""
    WITH u AS (
        SELECT equipo_codigo, equipo, distrito FROM {s}.v_registro_diario_anglo_export
        UNION ALL SELECT equipo_codigo, equipo, distrito FROM {s}.v_registro_diario_catodo_export
        UNION ALL SELECT equipo_codigo, equipo, distrito FROM {s}.v_registro_diario_cgo_andina_export
        UNION ALL SELECT equipo_codigo, equipo, distrito FROM {s}.v_registro_diario_cgo_cumet_ventanas_export
        UNION ALL SELECT equipo_codigo, equipo, distrito FROM {s}.v_registro_diario_cucons_export
        UNION ALL SELECT equipo_codigo, equipo, distrito FROM {s}.v_registro_diario_eteo_export
        UNION ALL SELECT equipo_codigo, equipo, distrito FROM {s}.v_registro_diario_kdm_export
        UNION ALL SELECT equipo_codigo, equipo, distrito FROM {s}.v_registro_diario_spot_export
    )
    SELECT DISTINCT TRIM(equipo_codigo) AS equipo_codigo
    FROM u
    WHERE distrito = %(faena)s
      AND TRIM(REGEXP_REPLACE(SPLIT_PART(equipo,' - ',1),'^[A-Z0-9-]+ ',''))
          = %(tipo)s
      AND equipo_codigo IS NOT NULL
    ORDER BY 1;
    """
    conn = _get_conn()
    try:
        with conn, conn.cursor() as cur:
            cur.execute(sql, {"faena": faena, "tipo": tipo})
            return _ok([r["equipo_codigo"] for r in cur.fetchall()])
    finally:
        conn.close()


# --------- Data principal ----------
@tfuera_bp.get("")
def get_tiempo_fuera():
    """
    Tiempo fuera de servicio por equipo:
      - cuenta de períodos fuera
      - promedio de días fuera
    Filtros: faena (oblig/opt), tipo (opt), equipo (opt).
    Optimizado con ventana (MIN() FILTER) para evitar subconsultas costosas.
    """
    faena  = request.args.get("faena", "").strip()
    tipo   = request.args.get("tipo", "").strip()
    equipo = request.args.get("equipo", "").strip()
    limit  = int(request.args.get("limit", 500))
    offset = int(request.args.get("offset", 0))

    s = _schema()

    sql = f"""
    -- 1) Turnos (filtrados por faena desde el origen para recortar el set)
    WITH turnos AS (
        SELECT equipo_codigo, fecha_inicio::timestamp AS fecha, distrito
        FROM {s}.v_registro_diario_anglo_export
        WHERE (%(faena)s = '' OR distrito = %(faena)s)
        UNION ALL
        SELECT equipo_codigo, fecha_inicio::timestamp, distrito
        FROM {s}.v_registro_diario_catodo_export
        WHERE (%(faena)s = '' OR distrito = %(faena)s)
        UNION ALL
        SELECT equipo_codigo, fecha_inicio::timestamp, distrito
        FROM {s}.v_registro_diario_cgo_andina_export
        WHERE (%(faena)s = '' OR distrito = %(faena)s)
        UNION ALL
        SELECT equipo_codigo, fecha_inicio::timestamp, distrito
        FROM {s}.v_registro_diario_cgo_cumet_ventanas_export
        WHERE (%(faena)s = '' OR distrito = %(faena)s)
        UNION ALL
        SELECT equipo_codigo, fecha_inicio::timestamp, distrito
        FROM {s}.v_registro_diario_cucons_export
        WHERE (%(faena)s = '' OR distrito = %(faena)s)
        UNION ALL
        SELECT equipo_codigo, fecha_inicio::timestamp, distrito
        FROM {s}.v_registro_diario_eteo_export
        WHERE (%(faena)s = '' OR distrito = %(faena)s)
        UNION ALL
        SELECT equipo_codigo, fecha_inicio::timestamp, distrito
        FROM {s}.v_registro_diario_kdm_export
        WHERE (%(faena)s = '' OR distrito = %(faena)s)
        UNION ALL
        SELECT equipo_codigo, fecha_inicio::timestamp, distrito
        FROM {s}.v_registro_diario_spot_export
        WHERE (%(faena)s = '' OR distrito = %(faena)s)
    ),
    -- 2) Notificaciones de falla (solo de equipos que existen en la faena filtrada)
    notif AS (
        SELECT
          n.codigo_interno::text AS equipo_codigo,
          n.fecha::timestamp     AS fecha
        FROM {s}.v_notificacion_reporte n
        WHERE n.motivo = 'FALLA - DAÑO'
          AND (
                %(faena)s = ''
            OR  EXISTS (
                  SELECT 1 FROM turnos t
                  WHERE t.equipo_codigo = n.codigo_interno::text
                )
          )
    ),
    -- 3) Unimos eventos y calculamos el próximo turno con ventana
    eventos AS (
        SELECT equipo_codigo, fecha, 'turno' AS tipo FROM turnos
        UNION ALL
        SELECT equipo_codigo, fecha, 'notif' AS tipo FROM notif
    ),
    eventos_orden AS (
        SELECT
          equipo_codigo,
          fecha,
          tipo,
          -- próximo turno hacia adelante dentro del mismo equipo
          MIN(fecha) FILTER (WHERE tipo = 'turno')
            OVER (PARTITION BY equipo_codigo
                  ORDER BY fecha
                  ROWS BETWEEN CURRENT ROW AND UNBOUNDED FOLLOWING) AS prox_turno
        FROM eventos
    ),
    difs AS (
        SELECT
          e.equipo_codigo,
          e.fecha        AS fecha_falla,
          e.prox_turno   AS fecha_reanudacion,
          EXTRACT(EPOCH FROM (e.prox_turno - e.fecha)) / 86400.0 AS dias_fuera
        FROM eventos_orden e
        WHERE e.tipo = 'notif' AND e.prox_turno IS NOT NULL
    ),
    -- 4) (Opcional) filtrar por tipo/equipo aquí. Para 'tipo' necesitamos mapa de equipo->tipo.
    equipos_tipo AS (
        SELECT DISTINCT
          TRIM(r.equipo_codigo) AS equipo_codigo,
          TRIM(REGEXP_REPLACE(SPLIT_PART(r.equipo, ' - ', 1), '^[A-Z0-9-]+ ', '')) AS tipo_equipo
        FROM (
            SELECT equipo_codigo, equipo FROM {s}.v_registro_diario_anglo_export
            UNION ALL SELECT equipo_codigo, equipo FROM {s}.v_registro_diario_catodo_export
            UNION ALL SELECT equipo_codigo, equipo FROM {s}.v_registro_diario_cgo_andina_export
            UNION ALL SELECT equipo_codigo, equipo FROM {s}.v_registro_diario_cgo_cumet_ventanas_export
            UNION ALL SELECT equipo_codigo, equipo FROM {s}.v_registro_diario_cucons_export
            UNION ALL SELECT equipo_codigo, equipo FROM {s}.v_registro_diario_eteo_export
            UNION ALL SELECT equipo_codigo, equipo FROM {s}.v_registro_diario_kdm_export
            UNION ALL SELECT equipo_codigo, equipo FROM {s}.v_registro_diario_spot_export
        ) r
        WHERE r.equipo_codigo IS NOT NULL AND r.equipo IS NOT NULL
    )
    SELECT
      d.equipo_codigo,
      COUNT(*)                                   AS total_periodos_fuera_servicio,
      ROUND(AVG(d.dias_fuera)::numeric, 2)       AS promedio_dias_fuera_servicio
    FROM difs d
    LEFT JOIN equipos_tipo et ON et.equipo_codigo = d.equipo_codigo
    WHERE (%(equipo)s = '' OR d.equipo_codigo = %(equipo)s)
      AND (%(tipo)s   = '' OR et.tipo_equipo = %(tipo)s)
    GROUP BY d.equipo_codigo
    ORDER BY promedio_dias_fuera_servicio DESC NULLS LAST, d.equipo_codigo
    LIMIT %(limit)s OFFSET %(offset)s;
    """

    params = {"faena": faena, "tipo": tipo, "equipo": equipo, "limit": limit, "offset": offset}

    conn = _get_conn()
    try:
        with conn, conn.cursor() as cur:
            # si quieres, sube un poco el timeout local (p.ej. 90s)
            cur.execute("SET LOCAL statement_timeout = '90s';")
            cur.execute(sql, params)
            rows = cur.fetchall()
        return _ok(rows)
    finally:
        conn.close()