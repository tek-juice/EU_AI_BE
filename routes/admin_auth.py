from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token

from config.extensions import db
from models.user import User


admin_auth_bp = Blueprint("admin_auth", __name__, url_prefix="/api/admin/auth")


@admin_auth_bp.route("/admin_register", methods=["POST"])
def admin_register():
    """
    Register Admin
    ---
    tags:
      - Admin Authentication

    consumes:
      - application/json

    produces:
      - application/json

    parameters:
      - in: body
        name: admin_registration
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
              example: admin@example.com
            phone:
              type: string
              example: "0700000000"
            password:
              type: string
              format: password
              example: password123

    responses:
      201:
        description: Admin registered successfully
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            message:
              type: string
              example: Admin registered successfully
            user:
              type: object
              properties:
                id:
                  type: string
                  example: 550e8400-e29b-41d4-a716-446655440000
                first_name:
                  type: string
                  example: John
                last_name:
                  type: string
                  example: Doe
                email:
                  type: string
                  example: admin@example.com
                phone:
                  type: string
                  example: "0700000000"
                role:
                  type: string
                  example: admin
                is_active:
                  type: boolean
                  example: true

      400:
        description: Missing or invalid registration data

      409:
        description: Email already registered

      500:
        description: Internal server error
    """

    data = request.get_json()

    if not data:
        return jsonify({
            "success": False,
            "message": "Request body is required"
        }), 400

    first_name = data.get("first_name", "").strip()
    last_name = data.get("last_name")
    email = data.get("email", "").strip().lower()
    phone = data.get("phone")
    password = data.get("password", "")

    if last_name:
        last_name = last_name.strip()

    if phone:
        phone = phone.strip()

    if not first_name or not email or not password:
        return jsonify({
            "success": False,
            "message": "First name, email and password are required"
        }), 400

    if len(password) < 8:
        return jsonify({
            "success": False,
            "message": "Password must be at least 8 characters long"
        }), 400

    existing_user = User.query.filter_by(email=email).first()

    if existing_user:
        return jsonify({
            "success": False,
            "message": "A user with this email already exists"
        }), 409

    try:
        password_hash = generate_password_hash(password)

        admin = User(
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            password_hash=password_hash,
            role="admin",
            is_active=True
        )

        db.session.add(admin)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Admin registered successfully",
            "user": {
                "id": str(admin.id),
                "first_name": admin.first_name,
                "last_name": admin.last_name,
                "email": admin.email,
                "phone": admin.phone,
                "role": admin.role,
                "is_active": admin.is_active
            }
        }), 201

    except Exception:
        db.session.rollback()

        return jsonify({
            "success": False,
            "message": "An error occurred while registering the admin"
        }), 500


@admin_auth_bp.route("/admin_login", methods=["POST"])
def admin_login():
    """
    Admin Login
    ---
    tags:
      - Admin Authentication
    consumes:
      - application/json
    produces:
      - application/json

    parameters:
      - in: body
        name: credentials
        required: true
        schema:
          type: object
          required:
            - email
            - password
          properties:
            email:
              type: string
              format: email
              example: admin@example.com
            password:
              type: string
              format: password
              example: password123

    responses:
      200:
        description: Admin login successful
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            message:
              type: string
              example: Admin login successful
            access_token:
              type: string
              example: eyJhbGciOiJIUzI1NiIs...
            user:
              type: object
              properties:
                id:
                  type: string
                  example: 550e8400-e29b-41d4-a716-446655440000
                first_name:
                  type: string
                  example: John
                last_name:
                  type: string
                  example: Doe
                email:
                  type: string
                  example: admin@example.com
                phone:
                  type: string
                  example: "0700000000"
                role:
                  type: string
                  example: admin
                is_active:
                  type: boolean
                  example: true

      400:
        description: Missing request body or credentials

      401:
        description: Invalid email or password

      403:
        description: User is not an administrator or account is inactive
    """

    data = request.get_json()

    if not data:
        return jsonify({
            "success": False,
            "message": "Request body is required"
        }), 400

    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({
            "success": False,
            "message": "Email and password are required"
        }), 400

    user = User.query.filter_by(email=email).first()

    if not user:
        return jsonify({
            "success": False,
            "message": "Invalid email or password"
        }), 401

    if user.role not in ["admin", "super_admin"]:
        return jsonify({
            "success": False,
            "message": "Administrator access required"
        }), 403

    if not user.is_active:
        return jsonify({
            "success": False,
            "message": "Your account is inactive"
        }), 403

    if not check_password_hash(user.password_hash, password):
        return jsonify({
            "success": False,
            "message": "Invalid email or password"
        }), 401

    access_token = create_access_token(
        identity=str(user.id),
        additional_claims={
            "role": user.role,
            "email": user.email
        }
    )

    return jsonify({
        "success": True,
        "message": "Admin login successful",
        "access_token": access_token,
        "user": {
            "id": str(user.id),
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "phone": user.phone,
            "role": user.role,
            "is_active": user.is_active
        }
    }), 200