from functools import wraps
from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt, get_jwt_identity


def admin_required(fn):
    """Require a valid JWT with role 'admin' or 'super_admin'."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        claims = get_jwt()
        role = claims.get("role")

        if role not in ["admin", "super_admin"]:
            return jsonify({
                "success": False,
                "message": "Admin access required"
            }), 403

        return fn(*args, **kwargs)
    return wrapper


def client_required(fn):
    """Require a valid JWT with role 'client'."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        claims = get_jwt()
        role = claims.get("role")

        if role != "client":
            return jsonify({
                "success": False,
                "message": "Client access required"
            }), 403

        return fn(*args, **kwargs)
    return wrapper


def any_authenticated_required(fn):
    """Require a valid JWT, regardless of role (admin or client).
    Useful for routes both roles should be able to hit, e.g. viewing
    public itinerary data while still tracking who's asking."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        return fn(*args, **kwargs)
    return wrapper


def get_current_user_id():
    """Convenience helper: the authenticated user's id as a string,
    for use inside a route body (e.g. to scope a query to the caller)."""
    return get_jwt_identity()