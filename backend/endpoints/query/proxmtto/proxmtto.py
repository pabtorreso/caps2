from flask import Blueprint, request, jsonify, current_app
import psycopg2
import psycopg2.extras

proxmtto_bp = Blueprint("proxmtto_api", __name__, url_prefix="/query/proxmtto")

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

def _ok(data):
    return jsonify({"ok": True, "data": data})

def _err(msg, code=400):
    resp = jsonify({"ok": False, "error": msg})
    resp.status_code = code
    return resp


# ========= Filtros =========
@proxmtto_bp.get("/filters/faenas")
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
            rows = [r["faena"] for r in cur.fetchall()]
        return _ok(rows)
    finally:
        conn.close()


@proxmtto_bp.get("/filters/tipos")
def filtros_tipos():
    faena = request.args.get("faena", "").strip()
    if not faena:
        return _err("Falta parámetro 'faena'.")

    s = _schema()
    sql = f"""
    WITH equipos AS (
        SELECT equipo FROM {s}.v_registro_diario_anglo_export WHERE distrito = %(faena)s
        UNION ALL SELECT equipo FROM {s}.v_registro_diario_catodo_export WHERE distrito = %(faena)s
        UNION ALL SELECT equipo FROM {s}.v_registro_diario_cgo_andina_export WHERE distrito = %(faena)s
        UNION ALL SELECT equipo FROM {s}.v_registro_diario_cgo_cumet_ventanas_export WHERE distrito = %(faena)s
        UNION ALL SELECT equipo FROM {s}.v_registro_diario_cucons_export WHERE distrito = %(faena)s
        UNION ALL SELECT equipo FROM {s}.v_registro_diario_eteo_export WHERE distrito = %(faena)s
        UNION ALL SELECT equipo FROM {s}.v_registro_diario_kdm_export WHERE distrito = %(faena)s
        UNION ALL SELECT equipo FROM {s}.v_registro_diario_spot_export WHERE distrito = %(faena)s
    )
    SELECT DISTINCT
        TRIM(REGEXP_REPLACE(SPLIT_PART(equipo, ' - ', 1), '^[A-Z0-9-]+ ', '')) AS tipo_equipo
    FROM equipos
    WHERE equipo IS NOT NULL
    ORDER BY 1;
    """
    conn = _get_conn()
    try:
        with conn, conn.cursor() as cur:
            cur.execute(sql, {"faena": faena})
            rows = [r["tipo_equipo"] for r in cur.fetchall() if r["tipo_equipo"]]
        return _ok(rows)
    finally:
        conn.close()


@proxmtto_bp.get("/filters/equipos")
def filtros_equipos():
    faena = request.args.get("faena", "").strip()
    tipo = request.args.get("tipo", "").strip()
    if not faena or not tipo:
        return _err("Faltan parámetros 'faena' y/o 'tipo'.")

    s = _schema()
    sql = f"""
    WITH equipos AS (
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
    FROM equipos
    WHERE distrito = %(faena)s
      AND TRIM(REGEXP_REPLACE(SPLIT_PART(equipo, ' - ', 1), '^[A-Z0-9-]+ ', '')) = %(tipo)s
      AND equipo_codigo IS NOT NULL
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


# ========= Data principal =========
@proxmtto_bp.get("")
def analisis_proximo_mantenimiento():
    """
    Próximo mantenimiento estimado por equipo.
    Filtros: faena (obligatorio o vacío para todas), tipo (opcional), equipo (opcional).
    """
    faena  = request.args.get("faena", "").strip()
    tipo   = request.args.get("tipo", "").strip()
    equipo = request.args.get("equipo", "").strip()  # sigue siendo opcional
    limit  = int(request.args.get("limit", 500))
    offset = int(request.args.get("offset", 0))

    s = _schema()
    sql = f"""
    WITH 
    promedio_mantencion AS (
        WITH difs AS (
            SELECT DISTINCT
                equipo,
                horometro_planificacion,
                LAG(horometro_planificacion, 1, 0) OVER (
                    PARTITION BY equipo 
                    ORDER BY horometro_planificacion
                ) AS horometro_anterior
            FROM {s}.v_programa_otm
            WHERE horometro_planificacion IS NOT NULL
        )
        SELECT
            equipo,
            ROUND(AVG(horometro_planificacion - horometro_anterior), 0) AS promedio_diferencia_horometro
        FROM difs
        WHERE horometro_anterior IS NOT NULL
        GROUP BY equipo
    ),
    promedio_semanal AS (
        WITH horometros_turnos AS (
            SELECT
                r.FECHA_INICIO::date AS fecha_inicio,
                r.EQUIPO_CODIGO,
                r.distrito,
                MAX(r.HOROMETRO_FIN) AS horometro_fin
            FROM (
                SELECT * FROM {s}.v_registro_diario_anglo_export
                UNION ALL SELECT * FROM {s}.v_registro_diario_catodo_export
                UNION ALL SELECT * FROM {s}.v_registro_diario_cgo_andina_export
                UNION ALL SELECT * FROM {s}.v_registro_diario_cgo_cumet_ventanas_export
                UNION ALL SELECT * FROM {s}.v_registro_diario_cucons_export
                UNION ALL SELECT * FROM {s}.v_registro_diario_eteo_export
                UNION ALL SELECT * FROM {s}.v_registro_diario_kdm_export
                UNION ALL SELECT * FROM {s}.v_registro_diario_spot_export
            ) r
            WHERE r.HOROMETRO_FIN IS NOT NULL
            GROUP BY r.EQUIPO_CODIGO, r.distrito, r.FECHA_INICIO::date
        ),
        diferencias AS (
            SELECT
                EQUIPO_CODIGO,
                fecha_inicio,
                distrito,
                horometro_fin,
                LAG(horometro_fin) OVER (
                    PARTITION BY EQUIPO_CODIGO 
                    ORDER BY fecha_inicio
                ) AS horometro_anterior
            FROM horometros_turnos
        )
        SELECT
            EQUIPO_CODIGO,
            distrito,
            ROUND(AVG(horometro_fin - horometro_anterior), 2) AS promedio_diferencia_horometro
        FROM diferencias
        WHERE horometro_anterior IS NOT NULL
        GROUP BY EQUIPO_CODIGO, distrito
    ),
    equipo_tipo AS (
        SELECT DISTINCT
            equipo_codigo,
            TRIM(REGEXP_REPLACE(SPLIT_PART(equipo, ' - ', 1), '^[A-Z0-9-]+ ', '')) AS tipo_equipo
        FROM {s}.v_registro_diario_anglo_export
        UNION ALL SELECT DISTINCT equipo_codigo,
            TRIM(REGEXP_REPLACE(SPLIT_PART(equipo, ' - ', 1), '^[A-Z0-9-]+ ', ''))
        FROM {s}.v_registro_diario_catodo_export
        UNION ALL SELECT DISTINCT equipo_codigo,
            TRIM(REGEXP_REPLACE(SPLIT_PART(equipo, ' - ', 1), '^[A-Z0-9-]+ ', ''))
        FROM {s}.v_registro_diario_cgo_andina_export
        UNION ALL SELECT DISTINCT equipo_codigo,
            TRIM(REGEXP_REPLACE(SPLIT_PART(equipo, ' - ', 1), '^[A-Z0-9-]+ ', ''))
        FROM {s}.v_registro_diario_cgo_cumet_ventanas_export
        UNION ALL SELECT DISTINCT equipo_codigo,
            TRIM(REGEXP_REPLACE(SPLIT_PART(equipo, ' - ', 1), '^[A-Z0-9-]+ ', ''))
        FROM {s}.v_registro_diario_cucons_export
        UNION ALL SELECT DISTINCT equipo_codigo,
            TRIM(REGEXP_REPLACE(SPLIT_PART(equipo, ' - ', 1), '^[A-Z0-9-]+ ', ''))
        FROM {s}.v_registro_diario_eteo_export
        UNION ALL SELECT DISTINCT equipo_codigo,
            TRIM(REGEXP_REPLACE(SPLIT_PART(equipo, ' - ', 1), '^[A-Z0-9-]+ ', ''))
        FROM {s}.v_registro_diario_kdm_export
        UNION ALL SELECT DISTINCT equipo_codigo,
            TRIM(REGEXP_REPLACE(SPLIT_PART(equipo, ' - ', 1), '^[A-Z0-9-]+ ', ''))
        FROM {s}.v_registro_diario_spot_export
    ),
    ultimo_mant AS (
        SELECT DISTINCT
            equipo,
            MAX(fecha_ejecucion_otm) AS fecha_mentenimiento,
            MAX(horometro_planificacion) AS horometro_ultimo_mant
        FROM {s}.v_programa_otm
        GROUP BY equipo
    )
    SELECT
        u.equipo AS equipo_codigo,
        s1.distrito AS faena,
        u.horometro_ultimo_mantenimiento,
        u.fecha_mentenimiento      AS fecha_ultimo_mantenimiento,
        p.promedio_diferencia_horometro AS promedio_horas_entre_mantenimientos,
        s1.promedio_diferencia_horometro AS promedio_horas_trabajadas_diarias,
        CASE 
            WHEN COALESCE(s1.promedio_diferencia_horometro, 0) = 0 THEN NULL
            ELSE ROUND(p.promedio_diferencia_horometro / s1.promedio_diferencia_horometro, 1)
        END AS dias_restantes_aprox,
        CASE 
            WHEN COALESCE(s1.promedio_diferencia_horometro, 0) = 0 THEN NULL
            ELSE CURRENT_DATE + (p.promedio_diferencia_horometro / s1.promedio_diferencia_horometro) * interval '1 day'
        END::date AS fecha_proximo_mantenimiento,
        (u.horometro_ultimo_mantenimiento + p.promedio_diferencia_horometro) AS horometro_estimado_proximo_mantenimiento
    FROM (
        SELECT equipo, fecha_mentenimiento, horometro_ultimo_mant AS horometro_ultimo_mantenimiento
        FROM ultimo_mant
    ) u
    JOIN promedio_mantencion p ON p.equipo = u.equipo
    JOIN promedio_semanal s1   ON s1.EQUIPO_CODIGO = u.equipo
    LEFT JOIN equipo_tipo et   ON et.equipo_codigo = u.equipo
    WHERE COALESCE(s1.promedio_diferencia_horometro, 0) > 0
      AND (%(faena)s  = '' OR s1.distrito = %(faena)s)
      AND (%(tipo)s   = '' OR et.tipo_equipo = %(tipo)s)
      AND (%(equipo)s = '' OR u.equipo = %(equipo)s)
    ORDER BY fecha_proximo_mantenimiento ASC
    LIMIT %(limit)s OFFSET %(offset)s;
    """

    params = {"faena": faena, "tipo": tipo, "equipo": equipo, "limit": limit, "offset": offset}

    conn = _get_conn()
    try:
        with conn, conn.cursor() as cur:
            cur.execute("SET LOCAL statement_timeout = '45s';")
            cur.execute(sql, params)
            rows = cur.fetchall()
        return _ok(rows)
    finally:
        conn.close()