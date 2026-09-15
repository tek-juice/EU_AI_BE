from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token
from werkzeug.security import generate_password_hash

from config.extensions import db
from models.user import User


auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

@auth_bp.post("/client_register")
def client_register():
    """
    Register a new client.

    ---
    tags:
      - Client Authentication

    consumes:
      - application/json

    produces:
      - application/json

    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - first_name
            - email
            - password
          properties:
            first_name:
              type: string
              example: John
            last_name:
              type: string
              example: Doe
            email:
              type: string
              format: email
              example: john@example.com
            phone:
              type: string
              example: "+256700000000"
            password:
              type: string
              format: password
              example: "StrongPassword123!"

    responses:
      201:
        description: Client registered successfully
        schema:
          type: object
          properties:
            message:
              type: string
              example: Client registered successfully
            access_token:
              type: string
              example: eyJhbGciOiJIUzI1NiIs...
            user:
              type: object
              properties:
                id:
                  type: string
                  example: "550e8400-e29b-41d4-a716-446655440000"
                first_name:
                  type: string
                  example: John
                last_name:
                  type: string
                  example: Doe
                email:
                  type: string
                  example: john@example.com
                phone:
                  type: string
                  example: "+256700000000"
                role:
                  type: string
                  example: client

      400:
        description: Invalid request

      409:
        description: Email already exists
    """
    data = request.get_json()

    if not data:
        return jsonify({
            "message": "Request body is required"
        }), 400

    first_name = data.get("first_name")
    last_name = data.get("last_name")
    email = data.get("email")
    phone = data.get("phone")
    password = data.get("password")

    if not first_name or not email or not password:
        return jsonify({
            "message": "first_name, email and password are required"
        }), 400

    email = email.strip().lower()

    existing_user = User.query.filter_by(email=email).first()

    if existing_user:
        return jsonify({
            "message": "A user with this email already exists"
        }), 409

    password_hash = generate_password_hash(password)

    user = User(
        first_name=first_name.strip(),
        last_name=last_name.strip() if last_name else None,
        email=email,
        phone=phone.strip() if phone else None,
        password_hash=password_hash,
        role="client"
    )

    db.session.add(user)
    db.session.commit()

    access_token = create_access_token(
        identity=str(user.id),
        additional_claims={
            "role": user.role
        }
    )

    return jsonify({
        "message": "Client registered successfully",
        "access_token": access_token,
        "user": {
            "id": str(user.id),
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "phone": user.phone,
            "role": user.role
        }
    }), 201