from flask import Blueprint, jsonify, request
from sqlalchemy import text
from database.database_erp import get_erp_db
from decimal import Decimal
from datetime import datetime, date

erp_query_api = Blueprint('erp_query_api', __name__)

def _jsonify_row(row: dict) -> dict:
    out = {}
    for k, v in row.items():
        if isinstance(v, Decimal):
            out[k] = float(v)
        elif isinstance(v, (datetime, date)):
            out[k] = v.isoformat()
        else:
            out[k] = v
    return out

@erp_query_api.route('/extraer_programa_otm', methods=['GET'])
def extraer_programa_otm():
    id_programa = request.args.get('id', type=int) or 294

    db = next(get_erp_db())
    query = text("""
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
        tipo_solicitud,
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
    SELECT DISTINCT
        equipo_codigo,
        TRIM(REGEXP_REPLACE(SPLIT_PART(equipo, ' - ', 1), '^[A-Z0-9-]+ ', '')) AS tipo_equipo,
        SPLIT_PART(equipo, ' - ', 2) AS marca,
        SPLIT_PART(equipo, ' - ', 3) AS modelo
    FROM CONSULTAS_CGO_EXT.V_REGISTRO_DIARIO_CGO_ANDINA_EXPORT
    UNION ALL
    SELECT DISTINCT
        equipo_codigo,
        TRIM(REGEXP_REPLACE(SPLIT_PART(equipo, ' - ', 1), '^[A-Z0-9-]+ ', '')) AS tipo_equipo,
        SPLIT_PART(equipo, ' - ', 2) AS marca,
        SPLIT_PART(equipo, ' - ', 3) AS modelo
    FROM CONSULTAS_CGO_EXT.V_REGISTRO_DIARIO_CGO_CUMET_VENTANAS_EXPORT
    UNION ALL
    SELECT DISTINCT
        equipo_codigo,
        TRIM(REGEXP_REPLACE(SPLIT_PART(equipo, ' - ', 1), '^[A-Z0-9-]+ ', '')) AS tipo_equipo,
        SPLIT_PART(equipo, ' - ', 2) AS marca,
        SPLIT_PART(equipo, ' - ', 3) AS modelo
    FROM CONSULTAS_CGO_EXT.V_REGISTRO_DIARIO_CUCONS_EXPORT
    UNION ALL
    SELECT DISTINCT
        equipo_codigo,
        TRIM(REGEXP_REPLACE(SPLIT_PART(equipo, ' - ', 1), '^[A-Z0-9-]+ ', '')) AS tipo_equipo,
        SPLIT_PART(equipo, ' - ', 2) AS marca,
        SPLIT_PART(equipo, ' - ', 3) AS modelo
    FROM CONSULTAS_CGO_EXT.V_REGISTRO_DIARIO_ETEO_EXPORT
    UNION ALL
    SELECT DISTINCT
        equipo_codigo,
        TRIM(REGEXP_REPLACE(SPLIT_PART(equipo, ' - ', 1), '^[A-Z0-9-]+ ', '')) AS tipo_equipo,
        SPLIT_PART(equipo, ' - ', 2) AS marca,
        SPLIT_PART(equipo, ' - ', 3) AS modelo
    FROM CONSULTAS_CGO_EXT.V_REGISTRO_DIARIO_KDM_EXPORT
    UNION ALL
    SELECT DISTINCT
        equipo_codigo,
        TRIM(REGEXP_REPLACE(SPLIT_PART(equipo, ' - ', 1), '^[A-Z0-9-]+ ', '')) AS tipo_equipo,
        SPLIT_PART(equipo, ' - ', 2) AS marca,
        SPLIT_PART(equipo, ' - ', 3) AS modelo
    FROM CONSULTAS_CGO_EXT.V_REGISTRO_DIARIO_TC_EXPORT
    UNION ALL
    SELECT DISTINCT
        equipo_codigo,
        TRIM(REGEXP_REPLACE(SPLIT_PART(equipo, ' - ', 1), '^[A-Z0-9-]+ ', '')) AS tipo_equipo,
        SPLIT_PART(equipo, ' - ', 2) AS marca,
        SPLIT_PART(equipo, ' - ', 3) AS modelo
    FROM CONSULTAS_CGO_EXT.V_REGISTRO_DIARIO_CATODO_EXPORT
    UNION ALL
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
    pro.codigo_tarea,
    pro.horometro_referencia,
    pro.descripcion,
    pro.disponibilidad_insumos,
    pro.instrucciones_especiales,
    pro.fecha_limite,
    pro.cantidad_reprogramaciones AS cantidad_reprogramaciones_programa,
    pro.usuario_programacion,
    pro.estado_programa,
    pro.otm,
    pro.nombre_prioridad_otm,
    pro.fecha_ejecucion_otm,
    pro.horometro_planificacion,
    pro.ultimo_horometro,
    pro.fecha_ultimo_horometro,
    pro.usuario_ultimo_horometro,
    pro.fecha_log,
    pro.fecha_hora_inicio,
    pro.fecha_hora_fin,

    eq.equipo_codigo,
    eq.tipo_equipo,
    eq.marca,
    eq.modelo,

    rotm.id_otm,
    rotm.fecha_inicio,
    rotm.anio,
    rotm.nombre_faena,
    rotm.codigo_interno,
    rotm.actividad,
    rotm.tipo_actividad,
    rotm.estado_actividad,
    rotm.motivo_no_cumplimiento,
    rotm.numero_otm,
    rotm.fecha_original,
    rotm.cantidad_reprogramaciones AS cantidad_reprogramaciones_otm,

    otm.numero_solicitud,
    otm.fecha_solicitud,
    otm.ot,
    otm.tipo_solicitud,
    otm.equipo AS equipo_mantencion,
    otm.solicitante,
    otm.estado_solicitud,
    otm.faena,
    otm.cuenta_contable,
    otm.centro_costos,
    otm.proveedor_seleccionado,
    otm.fecha_cotizacion,
    otm.condicion_pago,
    otm.monto_neto,
    otm.valor_total,
    otm.plazo_entrega,
    otm.motivo_compra,
    otm.orden_compra,
    otm.fecha_orden_compra,
    otm.fecha_emision_factura,
    otm.monto_total_factura,
    otm.item_material_o_servicio,
    otm.item_cantidad,
    otm.item_unidad,
    otm.item_monto_total,
    otm.estado_recepcion,
    otm.fecha_aceptado,
    otm.fecha_aceptado_gerencia,
    otm.validador,
    otm.validador_gerencia
FROM programa pro
LEFT JOIN equipo eq
    ON eq.equipo_codigo = pro.equipo
LEFT JOIN reg_otm rotm
    ON pro.otm = rotm.numero_otm
LEFT JOIN ot_mantenimiento otm
    ON rotm.numero_otm = otm.ot
WHERE pro.id_programa_otm = :id_programa
""")

    try:
        result = db.execute(query, {"id_programa": id_programa})
        rows = result.mappings().all()
        data = [_jsonify_row(r) for r in rows]
        return jsonify(data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()
