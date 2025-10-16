# app.py
import os
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
from extensions import db
from database.database import DATABASE_URL  
from database.database_erp import ERP_DATABASE_URL
import models.models as models


load_dotenv()

def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = (
        os.getenv("SECRET_KEY")        
        or os.getenv("JWT_SECRET_KEY")       
        or "dev-secret"
    )
    app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
    app.config["ERP_DATABASE_URL"] = ERP_DATABASE_URL
    app.config["COSTOS_SCHEMA"] = "consultas_cgo_ext" 
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False


    CORS(
        app,
        resources={r"/*": {"origins": [
            "http://localhost:5173",
            "http://127.0.0.1:5173"
            
        ]}},
        supports_credentials=False,
    )

    db.init_app(app)

    with app.app_context():
        from routes.login.login import auth_web
        from endpoints.erp_query import erp_query_api
        from routes.home.home import home_bp
        from routes.home.diagnostics import home_diag_bp
        from endpoints.query.reprogramaciones.reprogrmaciones import reprogramaciones_api 
        from endpoints.query.costos.costos import costos_bp
        from endpoints.query.proxmtto.proxmtto import proxmtto_bp 
        from endpoints.query.tiempofuera.tiempofuera import tfuera_bp
        from endpoints.query.actualizar.actualizar import actualizar_api

        app.register_blueprint(erp_query_api, url_prefix="/erp")
        app.register_blueprint(auth_web, url_prefix="") 
        app.register_blueprint(home_bp, url_prefix="/endpoints/home")
        app.register_blueprint(home_diag_bp, url_prefix="/endpoints/home")
        app.register_blueprint(reprogramaciones_api) 
        app.register_blueprint(costos_bp)
        app.register_blueprint(proxmtto_bp)
        app.register_blueprint(tfuera_bp)
        app.register_blueprint(actualizar_api)

        
    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, use_reloader=False, threaded=True)

