# routes/auth_web.py
from flask import Blueprint, request, jsonify, current_app
from flask_cors import cross_origin
import os, unicodedata, datetime, base64, requests, logging
from itsdangerous import URLSafeTimedSerializer

auth_web = Blueprint("auth_web", __name__)
logging.basicConfig(level=logging.INFO)

API_USUARIO = os.getenv("API_USUARIO", "movil_externo")
API_PASSWORD = os.getenv("API_PASSWORD", "Qaes$s450o9")
LOGIN_URL   = os.getenv("LOGIN_URL", "https://apis.indemin.cl/api_indemin/movil_login_prod001.php")

def _sign_token(payload: dict) -> str:
    s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="auth-token")
    return s.dumps(payload)

LOGIN_DEBUG = os.getenv("LOGIN_DEBUG", "false").lower() in ("1", "true", "yes")

def _post_login(headers, email, pin):
    data = {"usuario": email, "pin": pin}
    return requests.post(LOGIN_URL, json=data, headers=headers, timeout=12)

def _verificar_usuario_en_api_externa(email: str, pin: str):
    headers_basic = {
        "Content-Type": "application/json",
        "Authorization": "Basic " + base64.b64encode(f"{API_USUARIO}:{API_PASSWORD}".encode()).decode(),
    }
    r1 = _post_login(headers_basic, email, pin)
    try:
        j1 = r1.json()
    except Exception:
        j1 = {}

    if LOGIN_DEBUG:
        logging.info(f"[ext-login] basic http={r1.status_code} body={j1}")

    ok1 = (r1.status_code == 200
           and j1.get("codigo_respuesta") == 200
           and (j1.get("msg_autorizacion") or "").lower() == "ok")
    if ok1:
        return j1.get("id_usuario")

    headers_legacy = {
        "Content-Type": "application/json",
        "Authorization": base64.b64encode(f"{API_USUARIO} {API_PASSWORD}".encode()).decode(),
    }
    r2 = _post_login(headers_legacy, email, pin)
    try:
        j2 = r2.json()
    except Exception:
        j2 = {}

    if LOGIN_DEBUG:
        logging.info(f"[ext-login] legacy http={r2.status_code} body={j2}")

    ok2 = (r2.status_code == 200
           and j2.get("codigo_respuesta") == 200
           and (j2.get("msg_autorizacion") or "").lower() == "ok")
    return j2.get("id_usuario") if ok2 else None

@auth_web.route("/login", methods=["POST", "OPTIONS"])
@cross_origin(
    origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_headers=["Content-Type", "Authorization"],
    methods=["POST", "OPTIONS"],
    max_age=600,
)
def login_web():
    # --- responder preflight ---
    if request.method == "OPTIONS":
        return ("", 204)

    body = request.get_json(silent=True) or {}
    email = unicodedata.normalize("NFKC", str(body.get("email") or "")).strip().lower()
    pin   = unicodedata.normalize("NFKC", str(body.get("password") or "")).strip()

    if not email or not pin:
        return jsonify(message="Email y PIN requeridos"), 400
    if not (len(pin) == 4 and pin.isdigit()):
        return jsonify(message="El PIN debe tener 4 dígitos"), 400

    try:
        id_usuario = _verificar_usuario_en_api_externa(email, pin)
        if not id_usuario:
            return jsonify(message="Credenciales inválidas"), 401

        payload = {"uid": str(id_usuario), "email": email,
                   "exp": (datetime.datetime.utcnow() + datetime.timedelta(hours=2)).timestamp()}
        token = _sign_token(payload)

        return jsonify(message="Login exitoso", token=token,
                       user={"id_usuario": str(id_usuario), "email": email}), 200
    except requests.HTTPError as e:
        return jsonify(message="Error autenticando", detail=str(e)), 502
    except Exception as e:
        return jsonify(message="Error en el servidor", detail=str(e)), 500
