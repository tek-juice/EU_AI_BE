from flask import Flask
from flask_cors import CORS
from flasgger import Swagger
from config.extensions import Config
from config.extensions import db, migrate, jwt
from routes.client_auth import auth_bp


app = Flask(__name__)

app.config.from_object(Config)

CORS(app)

db.init_app(app)
migrate.init_app(app, db)
jwt.init_app(app)

Swagger(app)

app.register_blueprint(auth_bp)


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )