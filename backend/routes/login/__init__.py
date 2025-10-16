from flask import Blueprint

login_bp = Blueprint("login", __name__)

# Importa las rutas que usan este blueprint (después de declararlo)
from . import login  # noqa: F401
