# app.py
from flask import Flask
from flask_smorest import Api
from extensions import db
import os
from dotenv import load_dotenv
from routes.note_routes import note_bp

load_dotenv()

def create_app():
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.secret_key = os.getenv("FLASK_KEY")
    app.config["PROPAGATE_EXCEPTIONS"] = True
    app.config["API_TITLE"] = "Weather REST API"
    app.config["API_VERSION"] = "v1"
    app.config["OPENAPI_VERSION"] = "3.0.3"
    app.config["OPENAPI_URL_PREFIX"] = "/"
    app.config["OPENAPI_SWAGGER_UI_PATH"] = "/swagger-ui"
    app.config["OPENAPI_SWAGGER_UI_URL"] = "https://cdn.jsdelivr.net/npm/swagger-ui-dist/"
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    api = Api(app)

    db.init_app(app)
    with app.app_context():
        db.create_all()
    api.register_blueprint(note_bp)
    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)