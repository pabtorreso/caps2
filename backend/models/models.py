# backend/models/models.py
from sqlalchemy import Column, Integer, String, Numeric, Date, Boolean, ForeignKey, DateTime, BigInteger, CheckConstraint, Text
from sqlalchemy.orm import relationship
from extensions import db

class Usuario(db.Model):
    __tablename__ = 'usuario'
    id_usuario = Column(Integer, primary_key=True)
    id_api = Column(Integer, unique=True)
    email = Column(String(255), unique=True, nullable=False)
    rol = Column(String(50), default='user')
    activo = Column(Boolean, default=True)
    creado_en = Column(DateTime, server_default=db.func.now())

class Modelo(db.Model):
    __tablename__ = 'modelo'
    modelo_id = Column(Integer, primary_key=True)
    modelo_desc = Column(String(100), nullable=False)
    marcas = relationship('Marca', back_populates='modelo')

class Marca(db.Model):
    __tablename__ = 'marca'
    marca_id = Column(Integer, primary_key=True)
    marca_desc = Column(String(100), nullable=False)
    modelo_id = Column(Integer, ForeignKey('modelo.modelo_id'), nullable=False)
    modelo = relationship('Modelo', back_populates='marcas')
    tipos_equipo = relationship('TipoEquipo', back_populates='marca')

class TipoEquipo(db.Model):
    __tablename__ = 'tipo_equipo'
    tipo_equipo_id = Column(Integer, primary_key=True)
    tipo_equipo_desc = Column(String(100), nullable=False)
    marca_id = Column(Integer, ForeignKey('marca.marca_id'))
    marca = relationship('Marca', back_populates='tipos_equipo')
    equipos = relationship('Equipo', back_populates='tipo_equipo')

class Equipo(db.Model):
    __tablename__ = 'equipo'
    equipo_id = Column(Integer, primary_key=True)
    equipo_desc = Column(String(100), nullable=False, unique=True)
    tipo_equipo_id = Column(Integer, ForeignKey('tipo_equipo.tipo_equipo_id'), nullable=False)
    tipo_equipo = relationship('TipoEquipo', back_populates='equipos')
    programas = relationship('Programa', back_populates='equipo')
    proximo_mantenimiento = relationship('ProximoMantenimiento', back_populates='equipo', uselist=False)
    tiempo_baja = relationship('TiempoBaja', back_populates='equipo')

class Faena(db.Model):
    __tablename__ = 'faena'
    faena_id = Column(Integer, primary_key=True)
    faena_desc = Column(String(100), nullable=False)
    programas = relationship('Programa', back_populates='faena')

class Proveedor(db.Model):
    __tablename__ = 'proveedor'
    proveedor_id = Column(Integer, primary_key=True)
    proveedor_desc = Column(String(100), nullable=False)

class Cuenta(db.Model):
    __tablename__ = 'cuenta'
    cuenta_id = Column(Integer, primary_key=True)
    cuenta_desc = Column(String(100), nullable=False)
    centros_costo = relationship('CentroCosto', back_populates='cuenta')

class CentroCosto(db.Model):
    __tablename__ = 'centro_costo'
    centro_costo_id = Column(Integer, primary_key=True)
    centro_costo_desc = Column(String(100), nullable=False)
    cuenta_id = Column(Integer, ForeignKey('cuenta.cuenta_id'))
    cuenta = relationship('Cuenta', back_populates='centros_costo')

class MotivoCompra(db.Model):
    __tablename__ = 'motivo_compra'
    motvo_compra_id = Column(Integer, primary_key=True)
    motvo_compra_desc = Column(String(100), nullable=False)

class Item(db.Model):
    __tablename__ = 'item'
    item_id = Column(Integer, primary_key=True)
    item_desc = Column(String(100), nullable=False)

class Sistema(db.Model):
    __tablename__ = 'sistema'
    sistema_id = Column(Integer, primary_key=True)
    sistema_reparacion_desc = Column(String(100), nullable=False)

class Sintoma(db.Model):
    __tablename__ = 'sintoma'
    sintoma_id = Column(Integer, primary_key=True)
    sintoma_reparacion_desc = Column(String(100), nullable=False)

class MotivoReparacion(db.Model):
    __tablename__ = 'motivo_reparacion'
    mo_reparacion_id = Column(Integer, primary_key=True)
    mo_reparacion_desc = Column(String(100), nullable=False)

class Programa(db.Model):
    __tablename__ = 'programa'
    programa_id = Column(Integer, primary_key=True)
    faena_id = Column(Integer, ForeignKey('faena.faena_id'))
    equipo_id = Column(Integer, ForeignKey('equipo.equipo_id'))
    horometro_referencia = Column(Numeric(10, 0))
    disponibilidad_insumos = Column(String(100))
    usuario_programacion = Column(String(100))
    estado_otm = Column(String(100))
    faena = relationship('Faena', back_populates='programas')
    equipo = relationship('Equipo', back_populates='programas')
    ordenes_man = relationship('OrdenMan', back_populates='programa')

class Notificacion(db.Model):
    __tablename__ = 'notificacion'
    notificacion_id = Column(Integer, primary_key=True)
    notificacion_desc = Column(String(100))
    notificacion_fec = Column(Date)
    equipo_id = Column(Integer, ForeignKey('equipo.equipo_id'))
    mo_reparacion_id = Column(Integer, ForeignKey('motivo_reparacion.mo_reparacion_id'))
    faena_id = Column(Integer, ForeignKey('faena.faena_id'))
    sistema_id = Column(Integer, ForeignKey('sistema.sistema_id'))
    sintoma_id = Column(Integer, ForeignKey('sintoma.sintoma_id'))
    ordenes_rep = relationship('OrdenRep', back_populates='notificacion')

class OrdenCompra(db.Model):
    __tablename__ = 'orden_compra'
    oc_id = Column(Integer, primary_key=True)
    oc_desc = Column(String(100))
    motvo_compra_id = Column(Integer, ForeignKey('motivo_compra.motvo_compra_id'))
    item_id = Column(Integer, ForeignKey('item.item_id'))
    proveedor_id = Column(Integer, ForeignKey('proveedor.proveedor_id'))
    centro_costo_id = Column(Integer, ForeignKey('centro_costo.centro_costo_id'))
    oc_item_cantidad = Column(Integer)
    oc_item_unidad = Column(String(30))
    oc_item_monto_total = Column(Numeric(12, 2))
    oc_monto_neto = Column(Numeric(12, 2))
    oc_valor_total = Column(Numeric(12, 2))
    oc_monto_total_factura = Column(Numeric(12, 2))
    oc_fecha_emision_factura = Column(Date)
    otm_id = Column(Integer, ForeignKey('orden_man.otm_id'))

# Alias para compatibilidad
Solicitud = OrdenCompra

class OrdenMan(db.Model):
    __tablename__ = 'orden_man'
    otm_id = Column(Integer, primary_key=True)
    otm_desc = Column(String(100))
    programa_id = Column(Integer, ForeignKey('programa.programa_id'))
    programa = relationship('Programa', back_populates='ordenes_man')
    reprogramaciones = relationship('ReprogramacionOtm', back_populates='orden_man')

class OrdenRep(db.Model):
    __tablename__ = 'orden_rep'
    otr_id = Column(Integer, primary_key=True)
    otr_desc = Column(String(100))
    notificacion_id = Column(Integer, ForeignKey('notificacion.notificacion_id'))
    notificacion = relationship('Notificacion', back_populates='ordenes_rep')

class MotivoReprogramacion(db.Model):
    __tablename__ = 'motivo_reprogramacion'
    motivo_reprogramacion_id = Column(Integer, primary_key=True)
    motivo_reprogramacion_desc = Column(String(200), nullable=False, unique=True)
    reprogramaciones = relationship('ReprogramacionOtm', back_populates='motivo')

class ReprogramacionOtm(db.Model):
    __tablename__ = 'reprogramacion_otm'
    n_reprogramacion = Column(Integer, primary_key=True)
    otm_id = Column(Integer, ForeignKey('orden_man.otm_id'), primary_key=True)
    fecha_inicio = Column(DateTime)
    motivo_reprogramacion_id = Column(Integer, ForeignKey('motivo_reprogramacion.motivo_reprogramacion_id'))
    orden_man = relationship('OrdenMan', back_populates='reprogramaciones')
    motivo = relationship('MotivoReprogramacion', back_populates='reprogramaciones')

class TiempoBaja(db.Model):
    __tablename__ = 'tiempo_baja'
    equipo_id = Column(Integer, ForeignKey('equipo.equipo_id'), primary_key=True)
    fecha_inicio = Column(Date, primary_key=True)
    turno = Column(Boolean)
    equipo = relationship('Equipo', back_populates='tiempo_baja')

class ProximoMantenimiento(db.Model):
    __tablename__ = 'proximo_mantenimiento'
    equipo_id = Column(Integer, ForeignKey('equipo.equipo_id'), primary_key=True)
    ultimo_horometro_otm = Column(Numeric(15, 2))
    fec_ultima_otm = Column(Date)
    prom_horas_entre_otm = Column(Numeric(15, 2))
    prom_horas_trabajadas_diarias = Column(Numeric(15, 2))
    dias_restantes = Column(Numeric(15, 2))
    fecha_prox_otm = Column(Date)
    horometro_prox_otm = Column(Numeric(15, 2))
    equipo = relationship('Equipo', back_populates='proximo_mantenimiento')