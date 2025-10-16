# models.py
from datetime import datetime
from sqlalchemy import CheckConstraint, Column, DateTime, Integer, String, ForeignKey, Date, Boolean, Numeric, DECIMAL, UniqueConstraint, func, Index

from sqlalchemy.orm import relationship
from extensions import db


# ===========================
# USUARIO
# ===========================
class Usuario(db.Model):
    __tablename__ = "usuario"
    __table_args__ = {"schema": "public"}

    id_usuario = Column(Integer, primary_key=True)
    id_api = Column(Integer, unique=True, nullable=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    rol = Column(String(50), nullable=False, default="user")
    activo = Column(Boolean, nullable=False, default=True)
    creado_en = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Usuario {self.id_usuario} {self.email}>"


# ===========================================================
# CATÁLOGOS / MAESTROS
# ===========================================================
class Modelo(db.Model):
    __tablename__ = "modelo"
    __table_args__ = {"schema": "public"}

    modelo_id = Column(Integer, primary_key=True)
    modelo_desc = Column(String(50), unique=True, nullable=False)

    # 1:N Modelo -> Marca
    marcas = relationship("Marca", back_populates="modelo")


class Marca(db.Model):
    __tablename__ = "marca"
    __table_args__ = {"schema": "public"}

    marca_id = Column(Integer, primary_key=True)
    marca_desc = Column(String(50), unique=True, nullable=False)
    modelo_id = Column(Integer, ForeignKey("public.modelo.modelo_id"), nullable=False)

    # N:1 Marca -> Modelo
    modelo = relationship("Modelo", back_populates="marcas")

    # OJO: NO definimos Marca.equipos porque no hay FK directo desde EQUIPO a MARCA


class TipoEquipo(db.Model):
    __tablename__ = "tipo_equipo"
    __table_args__ = {"schema": "public"}

    tipo_equipo_id = Column(Integer, primary_key=True)
    tipo_equipo_desc = Column(String(50), unique=True, nullable=False)
    # En tu BD, tipo_equipo tiene marca_id
    marca_id = Column(Integer, ForeignKey("public.marca.marca_id"), nullable=False)

    # N:1 TipoEquipo -> Marca
    marca = relationship("Marca")

    # 1:N TipoEquipo -> Equipo
    equipos = relationship("Equipo", back_populates="tipo_equipo")


class Equipo(db.Model):
    __tablename__ = "equipo"
    __table_args__ = {"schema": "public"}

    equipo_id = Column(Integer, primary_key=True)
    equipo_desc = Column(String(50), unique=True, nullable=False)

    # En tu BD, equipo SOLO tiene tipo_equipo_id
    tipo_equipo_id = Column(Integer, ForeignKey("public.tipo_equipo.tipo_equipo_id"), nullable=False)

    # N:1 Equipo -> TipoEquipo
    tipo_equipo = relationship("TipoEquipo", back_populates="equipos")

    # Relaciones operativas
    programas = relationship("Programa", back_populates="equipo")
    notificaciones = relationship("Notificacion", back_populates="equipo")
    tiempos_baja = relationship("TiempoBaja", back_populates="equipo")
    proximos_mantenimientos = relationship("ProximoMantenimiento", back_populates="equipo")


class Faena(db.Model):
    __tablename__ = "faena"
    __table_args__ = {"schema": "public"}

    faena_id = Column(Integer, primary_key=True)
    faena_desc = Column(String(50), unique=True, nullable=False)

    notificaciones = relationship("Notificacion", back_populates="faena")
    programas = relationship("Programa", back_populates="faena")


class Proveedor(db.Model):
    __tablename__ = "proveedor"
    __table_args__ = {"schema": "public"}

    proveedor_id = Column(Integer, primary_key=True)
    proveedor_desc = Column(String(50), unique=True, nullable=False)

    ordenes_compra = relationship("OrdenCompra", back_populates="proveedor")


class Cuenta(db.Model):
    __tablename__ = "cuenta"
    __table_args__ = {"schema": "public"}

    cuenta_id = Column(Integer, primary_key=True)
    cuenta_desc = Column(String(50), unique=True, nullable=False)

    centros_costo = relationship("CentroCosto", back_populates="cuenta")


class CentroCosto(db.Model):
    __tablename__ = "centro_costo"
    __table_args__ = {"schema": "public"}

    centro_costo_id = Column(Integer, primary_key=True)
    centro_costo_desc = Column(String(50), unique=True, nullable=False)
    cuenta_id = Column(Integer, ForeignKey("public.cuenta.cuenta_id"))

    cuenta = relationship("Cuenta", back_populates="centros_costo")
    ordenes_compra = relationship("OrdenCompra", back_populates="centro_costo")


class MotivoCompra(db.Model):
    __tablename__ = "motivo_compra"
    __table_args__ = {"schema": "public"}

    motvo_compra_id = Column(Integer, primary_key=True)
    motvo_compra_desc = Column(String(50), unique=True, nullable=False)

    ordenes_compra = relationship("OrdenCompra", back_populates="motivo_compra")


class Item(db.Model):
    __tablename__ = "item"
    __table_args__ = {"schema": "public"}

    item_id = Column(Integer, primary_key=True)
    item_desc = Column(String(50), unique=True, nullable=False)

    ordenes_compra = relationship("OrdenCompra", back_populates="item")


class Sistema(db.Model):
    __tablename__ = "sistema"
    __table_args__ = {"schema": "public"}

    sistema_id = Column(Integer, primary_key=True)
    sistema_reparacion_desc = Column(String(50), unique=True, nullable=False)

    notificaciones = relationship("Notificacion", back_populates="sistema")


class Sintoma(db.Model):
    __tablename__ = "sintoma"
    __table_args__ = {"schema": "public"}

    sintoma_id = Column(Integer, primary_key=True)
    sintoma_reparacion_desc = Column(String(50), unique=True, nullable=False)

    notificaciones = relationship("Notificacion", back_populates="sintoma")


class MotivoReparacion(db.Model):
    __tablename__ = "motivo_reparacion"
    __table_args__ = {"schema": "public"}

    mo_reparacion_id = Column(Integer, primary_key=True)
    mo_reparacion_desc = Column(String(50), unique=True, nullable=False)

    notificaciones = relationship("Notificacion", back_populates="motivo_reparacion")


# ===========================================================
# COMPRAS / PROGRAMA / MANTENIMIENTO
# ===========================================================
class OrdenCompra(db.Model):
    __tablename__ = "orden_compra"
    __table_args__ = {"schema": "public"}

    oc_id = Column(Integer, primary_key=True)
    oc_desc = Column(String(50))
    motvo_compra_id = Column(Integer, ForeignKey("public.motivo_compra.motvo_compra_id"))
    item_id = Column(Integer, ForeignKey("public.item.item_id"))
    proveedor_id = Column(Integer, ForeignKey("public.proveedor.proveedor_id"))
    centro_costo_id = Column(Integer, ForeignKey("public.centro_costo.centro_costo_id"))
    oc_item_cantidad = Column(Integer)
    oc_item_unidad = Column(String(30))
    oc_item_monto_total = Column(DECIMAL(12, 2))
    oc_monto_neto = Column(DECIMAL(12, 2))
    oc_valor_total = Column(DECIMAL(12, 2))
    oc_monto_total_factura = Column(DECIMAL(12, 2))
    oc_fecha_emision_factura = Column(Date)
    otm_id = Column(Integer, ForeignKey("public.orden_man.otm_id"))

    motivo_compra = relationship("MotivoCompra", back_populates="ordenes_compra")
    item = relationship("Item", back_populates="ordenes_compra")
    proveedor = relationship("Proveedor", back_populates="ordenes_compra")
    centro_costo = relationship("CentroCosto", back_populates="ordenes_compra")
    orden_man = relationship("OrdenMan", back_populates="orden_compra")


class Programa(db.Model):
    __tablename__ = "programa"
    __table_args__ = {"schema": "public"}

    programa_id = Column(Integer, primary_key=True)
    faena_id = Column(Integer, ForeignKey("public.faena.faena_id"))
    equipo_id = Column(Integer, ForeignKey("public.equipo.equipo_id"))
    horometro_referencia = Column(Numeric(10, 0))
    disponibilidad_insumos = Column(String(50))
    usuario_programacion = Column(String(50))
    estado_otm = Column(String(50))

    equipo = relationship("Equipo", back_populates="programas")
    faena = relationship("Faena", back_populates="programas")
    ordenes_man = relationship("OrdenMan", back_populates="programa")


class Notificacion(db.Model):
    __tablename__ = "notificacion"
    __table_args__ = {"schema": "public"}

    notificacion_id = Column(Integer, primary_key=True)
    notificacion_desc = Column(String(50))
    notificacion_fec = Column(Date)
    equipo_id = Column(Integer, ForeignKey("public.equipo.equipo_id"))
    mo_reparacion_id = Column(Integer, ForeignKey("public.motivo_reparacion.mo_reparacion_id"))
    faena_id = Column(Integer, ForeignKey("public.faena.faena_id"))
    sistema_id = Column(Integer, ForeignKey("public.sistema.sistema_id"))
    sintoma_id = Column(Integer, ForeignKey("public.sintoma.sintoma_id"))

    equipo = relationship("Equipo", back_populates="notificaciones")
    motivo_reparacion = relationship("MotivoReparacion", back_populates="notificaciones")
    faena = relationship("Faena", back_populates="notificaciones")
    sistema = relationship("Sistema", back_populates="notificaciones")
    sintoma = relationship("Sintoma", back_populates="notificaciones")
    solicitudes = relationship("Solicitud", back_populates="notificacion")
    ordenes_rep = relationship("OrdenRep", back_populates="notificacion")


class Solicitud(db.Model):
    __tablename__ = "solicitud"
    __table_args__ = {"schema": "public"}

    solicitud_id = Column(Integer, primary_key=True)
    notificacion_id = Column(Integer, ForeignKey("public.notificacion.notificacion_id"))

    notificacion = relationship("Notificacion", back_populates="solicitudes")
    ordenes_man = relationship("OrdenMan", back_populates="solicitud")


class OrdenMan(db.Model):
    __tablename__ = "orden_man"
    __table_args__ = {"schema": "public"}

    otm_id = Column(Integer, primary_key=True)
    otm_desc = Column(String(50))
    programa_id = Column(Integer, ForeignKey("public.programa.programa_id"))
    solicitud_id = Column(Integer, ForeignKey("public.solicitud.solicitud_id"), nullable=True)

    programa = relationship("Programa", back_populates="ordenes_man")
    solicitud = relationship("Solicitud", back_populates="ordenes_man")
    orden_compra = relationship("OrdenCompra", back_populates="orden_man")
    reprogramaciones = relationship("ReprogramacionOtm", back_populates="orden_man")


class OrdenRep(db.Model):
    __tablename__ = "orden_rep"
    __table_args__ = {"schema": "public"}

    otr_id = Column(Integer, primary_key=True)
    otr_desc = Column(String(50))
    notificacion_id = Column(Integer, ForeignKey("public.notificacion.notificacion_id"))

    notificacion = relationship("Notificacion", back_populates="ordenes_rep")


# ===========================================================
# REPROGRAMACIONES
# ===========================================================
class MotivoReprogramacion(db.Model):
    __tablename__ = "motivo_reprogramacion"
    __table_args__ = {"schema": "public"}

    motivo_reprogramacion_id = Column(Integer, primary_key=True)
    motivo_reprogramacion_desc = Column(String(100), unique=True)

    reprogramaciones_otm = relationship("ReprogramacionOtm", back_populates="motivo_reprogramacion")



class ReprogramacionOtm(db.Model):
    __tablename__ = "reprogramacion_otm"
    __table_args__ = (
        UniqueConstraint(
            "otm_id", "fecha_inicio", "motivo_reprogramacion_id",
            name="uq_reprog_otm_fecha_motivo"
        ),
        Index("ix_reprog_otm_otm_fecha", "otm_id", "fecha_inicio"),
        {"schema": "public"},
    )

    n_reprogramacion = Column(Integer, primary_key=True)
    otm_id = Column(Integer, ForeignKey("public.orden_man.otm_id"), primary_key=True)

    fecha_inicio = Column(DateTime(timezone=True), nullable=False)

    motivo_reprogramacion_id = Column(
        Integer,
        ForeignKey("public.motivo_reprogramacion.motivo_reprogramacion_id"),
        nullable=False
    )

    orden_man = relationship("OrdenMan", back_populates="reprogramaciones")
    motivo_reprogramacion = relationship("MotivoReprogramacion", back_populates="reprogramaciones_otm")

# ===========================================================
# TIEMPOS DE BAJA
# ===========================================================
class TiempoBaja(db.Model):
    __tablename__ = "tiempo_baja"
    __table_args__ = {"schema": "public"}

    equipo_id = Column(Integer, ForeignKey("public.equipo.equipo_id"), primary_key=True)
    fecha_inicio = Column(Date, primary_key=True)
    turno = Column(Boolean)

    equipo = relationship("Equipo", back_populates="tiempos_baja")


# ===========================================================
# PRÓXIMO MANTENIMIENTO
# ===========================================================
class ProximoMantenimiento(db.Model):
    __tablename__ = "proximo_mantenimiento"
    __table_args__ = {"schema": "public"}

    equipo_id = Column(Integer, ForeignKey("public.equipo.equipo_id"), primary_key=True)
    ultimo_horometro_otm = Column(Numeric(8, 0))
    fec_ultima_otm = Column(Date)
    prom_horas_entre_otm = Column(Numeric(5, 0))
    prom_horas_trabajadas_diarias = Column(Numeric(5, 0))
    dias_restantes = Column(Numeric(3, 1))
    fecha_prox_otm = Column(Date)
    horometro_prox_otm = Column(Numeric(7, 0))

    equipo = relationship("Equipo", back_populates="proximos_mantenimientos")


class ActualizacionData(db.Model):
    __tablename__ = "actualizacion_data"
    __table_args__ = (
        CheckConstraint(
            "estado IN ('ejecutando','completado','error')",
            name="chk_actualizacion_estado"
        ),
        Index("idx_actualizacion_data_nombre_inicio", "nombre_proceso", db.text("inicio DESC")),
        {"schema": "public"},
    )

    id_actualizacion = Column(Integer, primary_key=True, autoincrement=True)  
    nombre_proceso   = Column(String, nullable=False)     
    estado           = Column(String, nullable=False)       
    inicio           = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    fin              = Column(DateTime(timezone=True))
    usuario_ejecuto  = Column(String)
    filas_extraidas  = Column(Integer)
    filas_insertadas = Column(Integer)
    mensaje          = Column(String)

    def __repr__(self):
        return f"<ActualizacionData {self.id_actualizacion} {self.nombre_proceso} {self.estado}>"