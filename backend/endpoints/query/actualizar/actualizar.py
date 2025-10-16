from __future__ import annotations
import threading
import time
import traceback
from datetime import datetime
from typing import Any, Dict
from flask import Blueprint, jsonify

from services.actualizar.actualizar import ejecutar_proceso

actualizar_api = Blueprint("actualizar_api", __name__, url_prefix="/query/actualizar")

_estado_lock = threading.Lock()
_en_ejecucion = threading.Event()
_estado: Dict[str, Any] = {
    "status": "inactivo",     
    "mensaje": None,
    "resultado": None,        
    "ultimo_inicio": None,
    "ultimo_fin": None,
    "duracion_seg": None,
    "progreso": 0,            
    "paso": None,             
    "heartbeat": None,        
    "traceback": None,
}

def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")

def _set(**kwargs):
    with _estado_lock:
        _estado.update(kwargs)

def _reset():
    _set(
        status="inactivo",
        mensaje=None,
        resultado=None,
        ultimo_inicio=None,
        ultimo_fin=None,
        duracion_seg=None,
        progreso=0,
        paso=None,
        heartbeat=None,
        traceback=None,
    )

def reportar(paso: str | None = None, progreso: int | None = None):
    """Callback para que ejecutar_proceso() pueda reportar avance."""
    data = {"heartbeat": _now()}
    if paso is not None:
        data["paso"] = paso
    if progreso is not None:
        data["progreso"] = max(0, min(100, int(progreso)))
    _set(**data)

def _worker():
    start = time.time()
    _set(status="ejecutando", mensaje="Proceso en curso", ultimo_inicio=_now(),
         progreso=0, paso="Inicializando", heartbeat=_now())
    try:
        resultado = ejecutar_proceso(callback=reportar)
        _set(status="completado", mensaje="OK", resultado=resultado, ultimo_fin=_now(),
             duracion_seg=round(time.time() - start, 3), progreso=100, paso="Finalizado")
    except Exception as e:
        _set(status="error", mensaje=str(e), traceback=traceback.format_exc(),
             ultimo_fin=_now(), duracion_seg=round(time.time() - start, 3))
    finally:
        _en_ejecucion.clear()

@actualizar_api.post("/iniciar")
def iniciar_actualizacion():
    if _en_ejecucion.is_set():
        with _estado_lock:
            return jsonify({"ok": True, "mensaje": "Proceso ya en curso", "estado": dict(_estado)}), 202
    _en_ejecucion.set()
    _reset()
    hilo = threading.Thread(target=_worker, daemon=True)
    hilo.start()
    with _estado_lock:
        return jsonify({"ok": True, "mensaje": "Proceso iniciado", "estado": dict(_estado)}), 202

@actualizar_api.get("/estado")
def estado_actualizacion():
    with _estado_lock:
        return jsonify(dict(_estado)), 200

@actualizar_api.post("/reiniciar")
def reiniciar():
    if _en_ejecucion.is_set():
        return jsonify({"ok": False, "mensaje": "No se puede reiniciar mientras hay un proceso en ejecución"}), 409
    _reset()
    with _estado_lock:
        return jsonify({"ok": True, "mensaje": "Estado reiniciado", "estado": dict(_estado)}), 200
