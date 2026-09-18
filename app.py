from flask import Flask
from flask_cors import CORS
from flasgger import Swagger

from config.extensions import Config
from config.extensions import db, migrate, jwt

from routes.client_auth import client_auth_bp
from routes.admin_auth import admin_auth_bp
from routes.itinerary_data import itinerary_data_bp


app = Flask(__name__)

app.config.from_object(Config)

CORS(app)

db.init_app(app)
migrate.init_app(app, db)
jwt.init_app(app)


swagger_config = {
    "headers": [],
    "specs": [
        {
            "endpoint": "apispec",
            "route": "/apispec.json",
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/docs/"
}


swagger_template = {
    "swagger": "2.0",
    "info": {
        "title": "Everything Uganda AI API",
        "description": "API documentation for the Everything Uganda itinerary builder.",
        "version": "1.0.0"
    },

    "securityDefinitions": {
        "Bearer": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
            "description": "Enter your JWT token as: Bearer <your_token>"
        }
    },

    "security": []
}


Swagger(
    app,
    config=swagger_config,
    template=swagger_template
)


app.register_blueprint(client_auth_bp)
app.register_blueprint(admin_auth_bp)
app.register_blueprint(itinerary_data_bp)


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )