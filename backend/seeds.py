# seeds.py
from datetime import datetime
from werkzeug.security import generate_password_hash
from extensions import db
from models import Rol, Permiso, RolPermiso, Usuario

def seed_roles_permisos(session):
    admin = session.query(Rol).filter_by(codigo="admin").one_or_none()
    if not admin:
        admin = Rol(codigo="admin", nombre="Administrador")
        session.add(admin)

    ver = session.query(Permiso).filter_by(codigo="ver_dashboard").one_or_none()
    if not ver:
        ver = Permiso(codigo="ver_dashboard", nombre="Ver dashboard", modulo="core")
        session.add(ver)

    existe = session.query(RolPermiso).filter_by(id_rol=admin.id_rol if admin.id_rol else None,
                                                 id_permiso=ver.id_permiso if ver.id_permiso else None).one_or_none()
    session.flush() 
    if not session.query(RolPermiso).filter_by(id_rol=admin.id_rol, id_permiso=ver.id_permiso).one_or_none():
        session.add(RolPermiso(id_rol=admin.id_rol, id_permiso=ver.id_permiso))

    session.commit()

def seed_superusuario(session, email, password):
    if not session.query(Usuario).filter_by(email=email).one_or_none():
        u = Usuario(
            email=email,
            hash_clave=generate_password_hash(password),
            activo=True,
            creado_en=datetime.utcnow(),
        )
        session.add(u)
        session.commit()
