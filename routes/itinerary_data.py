from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt
from slugify import slugify
from datetime import date
from config.extensions import db
from datetime import datetime
from models.itinerary import Destination, DestinationImage, Accommodation, AccommodationImage, AccommodationRate, Activity, ActivityImage, ActivityRate
from decorators.deco import admin_required, client_required, any_authenticated_required

itinerary_data_bp = Blueprint("destination", __name__, url_prefix="/api/itinerary_data")

@itinerary_data_bp.route("/create_destination", methods=["POST"])
@admin_required
def create_destination():
    """
    Create a new destination
    ---
    tags:
      - itinerary_data
    security:
      - Bearer: []
    consumes:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - name
            - destination_type
          properties:
            name:
              type: string
              example: Murchison Falls National Park
            description:
              type: string
              example: Uganda's largest national park, famous for its wildlife and the powerful Murchison Falls.
            short_description:
              type: string
              example: Uganda's largest national park and a premier wildlife destination.
            destination_type:
              type: string
              example: National Park
            region:
              type: string
              example: Northern Uganda
            district:
              type: string
              example: Murchison
            is_active:
              type: boolean
              example: true
    responses:
      201:
        description: Destination created successfully
      400:
        description: Validation error
      401:
        description: Authentication required
      403:
        description: Admin access required
      409:
        description: Destination already exists
      500:
        description: Internal server error
    """
    try:
        claims = get_jwt()
        role = claims.get("role")

        if role not in ["admin", "super_admin"]:
            return jsonify({
                "success": False,
                "message": "Admin access required"
            }), 403
        data = request.get_json()

        if not data:
            return jsonify({
                "success": False,
                "message": "Request body is required"
            }), 400

        name = data.get("name")
        destination_type = data.get("destination_type")

        if not name:
            return jsonify({
                "success": False,
                "message": "Destination name is required"
            }), 400

        if not destination_type:
            return jsonify({
                "success": False,
                "message": "Destination type is required"
            }), 400

        name = name.strip()
        destination_type = destination_type.strip()

        if not name:
            return jsonify({
                "success": False,
                "message": "Destination name cannot be empty"
            }), 400

        slug = slugify(name)

        existing_name = Destination.query.filter(
            db.func.lower(Destination.name) == name.lower()
        ).first()

        if existing_name:
            return jsonify({
                "success": False,
                "message": "A destination with this name already exists"
            }), 409

        existing_slug = Destination.query.filter_by(slug=slug).first()

        if existing_slug:
            return jsonify({
                "success": False,
                "message": "A destination with this slug already exists"
            }), 409

        destination = Destination(
            name=name,
            slug=slug,
            description=data.get("description"),
            short_description=data.get("short_description"),
            destination_type=destination_type,
            region=data.get("region"),
            district=data.get("district"),
            is_active=data.get("is_active", True)
        )

        db.session.add(destination)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Destination created successfully",
            "destination": {
                "id": str(destination.id),
                "name": destination.name,
                "slug": destination.slug,
                "description": destination.description,
                "short_description": destination.short_description,
                "destination_type": destination.destination_type,
                "region": destination.region,
                "district": destination.district,
                "is_active": destination.is_active,
                "created_at": destination.created_at.isoformat()
                    if destination.created_at else None,
                "updated_at": destination.updated_at.isoformat()
                    if destination.updated_at else None
            }
        }), 201

    except Exception as e:
        db.session.rollback()

        return jsonify({
            "success": False,
            "message": "Failed to create destination",
            "error": str(e)
        }), 500

@itinerary_data_bp.route("/add_destination_image", methods=["POST"])
@admin_required
def create_destination_image():
    """
    Add an image to a destination
    ---
    tags:
      - itinerary_data
    security:
      - Bearer: []
    consumes:
      - application/json

    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - destination_id
            - image_url
          properties:
            destination_id:
              type: string
              format: uuid
              example: "550e8400-e29b-41d4-a716-446655440000"
            image_url:
              type: string
              example: "https://example.com/images/murchison-falls.jpg"
            caption:
              type: string
              example: "Murchison Falls viewed from the Nile"
            alt_text:
              type: string
              example: "Murchison Falls National Park waterfall"
            sort_order:
              type: integer
              example: 0
            is_active:
              type: boolean
              example: true

    responses:
      201:
        description: Destination image created successfully
      400:
        description: Validation error
      401:
        description: Authentication required
      403:
        description: Admin access required
      404:
        description: Destination not found
      500:
        description: Internal server error
    """

    try:
        # Check admin role
        claims = get_jwt()
        role = claims.get("role")

        if role not in ["admin", "super_admin"]:
            return jsonify({
                "success": False,
                "message": "Admin access required"
            }), 403

        # Get request data
        data = request.get_json()

        if not data:
            return jsonify({
                "success": False,
                "message": "Request body is required"
            }), 400

        # Required fields
        destination_id = data.get("destination_id")
        image_url = data.get("image_url")

        if not destination_id:
            return jsonify({
                "success": False,
                "message": "destination_id is required"
            }), 400

        if not image_url:
            return jsonify({
                "success": False,
                "message": "image_url is required"
            }), 400

        image_url = image_url.strip()

        if not image_url:
            return jsonify({
                "success": False,
                "message": "image_url cannot be empty"
            }), 400

        # Check destination exists
        destination = Destination.query.get(destination_id)

        if not destination:
            return jsonify({
                "success": False,
                "message": "Destination not found"
            }), 404

        # Optional fields
        caption = data.get("caption")
        alt_text = data.get("alt_text")
        sort_order = data.get("sort_order", 0)
        is_active = data.get("is_active", True)

        # Validate sort_order
        try:
            sort_order = int(sort_order)
        except (TypeError, ValueError):
            return jsonify({
                "success": False,
                "message": "sort_order must be an integer"
            }), 400

        # Create destination image
        destination_image = DestinationImage(
            destination_id=destination.id,
            image_url=image_url,
            caption=caption,
            alt_text=alt_text,
            sort_order=sort_order,
            is_active=is_active
        )

        db.session.add(destination_image)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Destination image created successfully",
            "image": {
                "id": str(destination_image.id),
                "destination_id": str(destination_image.destination_id),
                "image_url": destination_image.image_url,
                "caption": destination_image.caption,
                "alt_text": destination_image.alt_text,
                "sort_order": destination_image.sort_order,
                "is_active": destination_image.is_active,
                "created_at": (
                    destination_image.created_at.isoformat()
                    if destination_image.created_at
                    else None
                )
            }
        }), 201

    except Exception as e:
        db.session.rollback()

        return jsonify({
            "success": False,
            "message": "Failed to create destination image",
            "error": str(e)
        }), 500


@itinerary_data_bp.route("/create_accomadation", methods=["POST"])
@admin_required
def create_accommodation():
    """
    Create a new accommodation
    ---
    tags:
      - itinerary_data
    security:
      - Bearer: []
    consumes:
      - application/json

    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - destination_id
            - name
            - accommodation_type
          properties:
            destination_id:
              type: string
              format: uuid
              example: "550e8400-e29b-41d4-a716-446655440000"
            name:
              type: string
              example: Paraa Safari Lodge
            description:
              type: string
              example: A luxury safari lodge overlooking the Nile River.
            accommodation_type:
              type: string
              example: Safari Lodge
            address:
              type: string
              example: Murchison Falls National Park, Uganda
            rating:
              type: number
              format: float
              example: 4.5
            is_active:
              type: boolean
              example: true

    responses:
      201:
        description: Accommodation created successfully
      400:
        description: Validation error
      401:
        description: Authentication required
      403:
        description: Admin access required
      404:
        description: Destination not found
      409:
        description: Accommodation already exists
      500:
        description: Internal server error
    """

    try:
        # Check admin role
        claims = get_jwt()
        role = claims.get("role")

        if role not in ["admin", "super_admin"]:
            return jsonify({
                "success": False,
                "message": "Admin access required"
            }), 403

        # Get request data
        data = request.get_json()

        if not data:
            return jsonify({
                "success": False,
                "message": "Request body is required"
            }), 400

        # Required fields
        destination_id = data.get("destination_id")
        name = data.get("name")
        accommodation_type = data.get("accommodation_type")

        if not destination_id:
            return jsonify({
                "success": False,
                "message": "destination_id is required"
            }), 400

        if not name:
            return jsonify({
                "success": False,
                "message": "Accommodation name is required"
            }), 400

        if not accommodation_type:
            return jsonify({
                "success": False,
                "message": "accommodation_type is required"
            }), 400

        # Clean values
        name = name.strip()
        accommodation_type = accommodation_type.strip()

        if not name:
            return jsonify({
                "success": False,
                "message": "Accommodation name cannot be empty"
            }), 400

        if not accommodation_type:
            return jsonify({
                "success": False,
                "message": "Accommodation type cannot be empty"
            }), 400

        # Check destination exists
        destination = Destination.query.get(destination_id)

        if not destination:
            return jsonify({
                "success": False,
                "message": "Destination not found"
            }), 404

        # Check duplicate accommodation within destination
        existing = Accommodation.query.filter(
            Accommodation.destination_id == destination.id,
            db.func.lower(Accommodation.name) == name.lower()
        ).first()

        if existing:
            return jsonify({
                "success": False,
                "message": "An accommodation with this name already exists for this destination"
            }), 409

        # Optional fields
        description = data.get("description")
        address = data.get("address")
        rating = data.get("rating")
        is_active = data.get("is_active", True)

        # Validate rating
        if rating is not None:
            try:
                rating = float(rating)
            except (TypeError, ValueError):
                return jsonify({
                    "success": False,
                    "message": "rating must be a number"
                }), 400

            if rating < 0 or rating > 5:
                return jsonify({
                    "success": False,
                    "message": "rating must be between 0 and 5"
                }), 400

        # Create accommodation
        accommodation = Accommodation(
            destination_id=destination.id,
            name=name,
            description=description,
            accommodation_type=accommodation_type,
            address=address,
            rating=rating,
            is_active=is_active
        )

        db.session.add(accommodation)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Accommodation created successfully",
            "accommodation": {
                "id": str(accommodation.id),
                "destination_id": str(accommodation.destination_id),
                "name": accommodation.name,
                "description": accommodation.description,
                "accommodation_type": accommodation.accommodation_type,
                "address": accommodation.address,
                "rating": float(accommodation.rating)
                    if accommodation.rating is not None
                    else None,
                "is_active": accommodation.is_active,
                "created_at": (
                    accommodation.created_at.isoformat()
                    if accommodation.created_at
                    else None
                ),
                "updated_at": (
                    accommodation.updated_at.isoformat()
                    if accommodation.updated_at
                    else None
                )
            }
        }), 201

    except Exception as e:
        db.session.rollback()

        return jsonify({
            "success": False,
            "message": "Failed to create accommodation",
            "error": str(e)
        }), 500

@itinerary_data_bp.route("/insert_accomadation_image", methods=["POST"])
@admin_required
def create_accommodation_image():
    """
    Add an image to an accommodation
    ---
    tags:
      - itinerary_data
    security:
      - Bearer: []
    consumes:
      - application/json

    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - accommodation_id
            - image_url
          properties:
            accommodation_id:
              type: string
              format: uuid
              example: "550e8400-e29b-41d4-a716-446655440000"
            image_url:
              type: string
              example: "https://example.com/images/lodge.jpg"
            caption:
              type: string
              example: "Luxury accommodation overlooking the Nile"
            alt_text:
              type: string
              example: "Safari lodge overlooking the Nile River"
            sort_order:
              type: integer
              example: 0
            is_active:
              type: boolean
              example: true

    responses:
      201:
        description: Accommodation image created successfully
      400:
        description: Validation error
      401:
        description: Authentication required
      403:
        description: Admin access required
      404:
        description: Accommodation not found
      500:
        description: Internal server error
    """

    try:
        # Check admin role
        claims = get_jwt()
        role = claims.get("role")

        if role not in ["admin", "super_admin"]:
            return jsonify({
                "success": False,
                "message": "Admin access required"
            }), 403

        # Get request data
        data = request.get_json()

        if not data:
            return jsonify({
                "success": False,
                "message": "Request body is required"
            }), 400

        # Required fields
        accommodation_id = data.get("accommodation_id")
        image_url = data.get("image_url")

        if not accommodation_id:
            return jsonify({
                "success": False,
                "message": "accommodation_id is required"
            }), 400

        if not image_url:
            return jsonify({
                "success": False,
                "message": "image_url is required"
            }), 400

        image_url = image_url.strip()

        if not image_url:
            return jsonify({
                "success": False,
                "message": "image_url cannot be empty"
            }), 400

        # Check accommodation exists
        accommodation = Accommodation.query.get(accommodation_id)

        if not accommodation:
            return jsonify({
                "success": False,
                "message": "Accommodation not found"
            }), 404

        # Optional fields
        caption = data.get("caption")
        alt_text = data.get("alt_text")
        sort_order = data.get("sort_order", 0)
        is_active = data.get("is_active", True)

        # Validate sort_order
        try:
            sort_order = int(sort_order)
        except (TypeError, ValueError):
            return jsonify({
                "success": False,
                "message": "sort_order must be an integer"
            }), 400

        # Create accommodation image
        accommodation_image = AccommodationImage(
            accommodation_id=accommodation.id,
            image_url=image_url,
            caption=caption,
            alt_text=alt_text,
            sort_order=sort_order,
            is_active=is_active
        )

        db.session.add(accommodation_image)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Accommodation image created successfully",
            "image": {
                "id": str(accommodation_image.id),
                "accommodation_id": str(
                    accommodation_image.accommodation_id
                ),
                "image_url": accommodation_image.image_url,
                "caption": accommodation_image.caption,
                "alt_text": accommodation_image.alt_text,
                "sort_order": accommodation_image.sort_order,
                "is_active": accommodation_image.is_active,
                "created_at": (
                    accommodation_image.created_at.isoformat()
                    if accommodation_image.created_at
                    else None
                )
            }
        }), 201

    except Exception as e:
        db.session.rollback()

        return jsonify({
            "success": False,
            "message": "Failed to create accommodation image",
            "error": str(e)
        }), 500

@itinerary_data_bp.route("/create_accomadation_rate", methods=["POST"])
@admin_required
def create_accommodation_rate():
    """
    Create an accommodation rate
    ---
    tags:
      - itinerary_data
    security:
      - Bearer: []
    consumes:
      - application/json

    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - accommodation_id
            - room_type
            - price_per_night
          properties:
            accommodation_id:
              type: string
              format: uuid
              example: "550e8400-e29b-41d4-a716-446655440000"
            room_type:
              type: string
              example: Deluxe Room
            meal_plan:
              type: string
              example: Full Board
            price_per_night:
              type: number
              format: float
              example: 250.00
            currency:
              type: string
              example: USD
            max_guests:
              type: integer
              example: 2
            season:
              type: string
              example: Peak Season
            is_active:
              type: boolean
              example: true

    responses:
      201:
        description: Accommodation rate created successfully
      400:
        description: Validation error
      401:
        description: Authentication required
      403:
        description: Admin access required
      404:
        description: Accommodation not found
      409:
        description: Rate already exists
      500:
        description: Internal server error
    """

    try:
        # Check admin role
        claims = get_jwt()
        role = claims.get("role")

        if role not in ["admin", "super_admin"]:
            return jsonify({
                "success": False,
                "message": "Admin access required"
            }), 403

        # Get request data
        data = request.get_json()

        if not data:
            return jsonify({
                "success": False,
                "message": "Request body is required"
            }), 400

        # Required fields
        accommodation_id = data.get("accommodation_id")
        room_type = data.get("room_type")
        price_per_night = data.get("price_per_night")

        if not accommodation_id:
            return jsonify({
                "success": False,
                "message": "accommodation_id is required"
            }), 400

        if not room_type:
            return jsonify({
                "success": False,
                "message": "room_type is required"
            }), 400

        if price_per_night is None:
            return jsonify({
                "success": False,
                "message": "price_per_night is required"
            }), 400

        # Clean values
        room_type = room_type.strip()

        if not room_type:
            return jsonify({
                "success": False,
                "message": "room_type cannot be empty"
            }), 400

        # Check accommodation exists
        accommodation = Accommodation.query.get(accommodation_id)

        if not accommodation:
            return jsonify({
                "success": False,
                "message": "Accommodation not found"
            }), 404

        # Validate price
        try:
            price_per_night = float(price_per_night)
        except (TypeError, ValueError):
            return jsonify({
                "success": False,
                "message": "price_per_night must be a number"
            }), 400

        if price_per_night <= 0:
            return jsonify({
                "success": False,
                "message": "price_per_night must be greater than 0"
            }), 400

        # Optional fields
        meal_plan = data.get("meal_plan")
        currency = data.get("currency", "USD")
        max_guests = data.get("max_guests", 2)
        season = data.get("season")
        is_active = data.get("is_active", True)

        # Clean currency
        if currency:
            currency = currency.strip().upper()

        # Validate max guests
        try:
            max_guests = int(max_guests)
        except (TypeError, ValueError):
            return jsonify({
                "success": False,
                "message": "max_guests must be an integer"
            }), 400

        if max_guests < 1:
            return jsonify({
                "success": False,
                "message": "max_guests must be at least 1"
            }), 400

        # Check for duplicate rate
        existing_rate = AccommodationRate.query.filter(
            AccommodationRate.accommodation_id == accommodation.id,
            db.func.lower(AccommodationRate.room_type) == room_type.lower(),
            db.func.lower(AccommodationRate.meal_plan) ==
            (meal_plan.lower() if meal_plan else None),
            db.func.lower(AccommodationRate.season) ==
            (season.lower() if season else None)
        ).first()

        if existing_rate:
            return jsonify({
                "success": False,
                "message": "A rate with the same room type, meal plan and season already exists"
            }), 409

        # Create rate
        accommodation_rate = AccommodationRate(
            accommodation_id=accommodation.id,
            room_type=room_type,
            meal_plan=meal_plan,
            price_per_night=price_per_night,
            currency=currency,
            max_guests=max_guests,
            season=season,
            is_active=is_active
        )

        db.session.add(accommodation_rate)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Accommodation rate created successfully",
            "rate": {
                "id": str(accommodation_rate.id),
                "accommodation_id": str(
                    accommodation_rate.accommodation_id
                ),
                "room_type": accommodation_rate.room_type,
                "meal_plan": accommodation_rate.meal_plan,
                "price_per_night": float(
                    accommodation_rate.price_per_night
                ),
                "currency": accommodation_rate.currency,
                "max_guests": accommodation_rate.max_guests,
                "season": accommodation_rate.season,
                "is_active": accommodation_rate.is_active,
                "created_at": (
                    accommodation_rate.created_at.isoformat()
                    if accommodation_rate.created_at
                    else None
                ),
                "updated_at": (
                    accommodation_rate.updated_at.isoformat()
                    if accommodation_rate.updated_at
                    else None
                )
            }
        }), 201

    except Exception as e:
        db.session.rollback()

        return jsonify({
            "success": False,
            "message": "Failed to create accommodation rate",
            "error": str(e)
        }), 500

@itinerary_data_bp.route("/create_activity", methods=["POST"])
@admin_required
def create_activity():
    """
    Create a new activity
    ---
    tags:
      - itinerary_data
    security:
      - Bearer: []
    consumes:
      - application/json

    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - destination_id
            - name
            - activity_type
          properties:
            destination_id:
              type: string
              format: uuid
              example: "550e8400-e29b-41d4-a716-446655440000"
            name:
              type: string
              example: Game Drive
            description:
              type: string
              example: Experience the wildlife of the national park on a guided game drive.
            activity_type:
              type: string
              example: Wildlife
            duration_minutes:
              type: integer
              example: 180
            is_active:
              type: boolean
              example: true

    responses:
      201:
        description: Activity created successfully
      400:
        description: Validation error
      401:
        description: Authentication required
      403:
        description: Admin access required
      404:
        description: Destination not found
      409:
        description: Activity already exists
      500:
        description: Internal server error
    """

    try:
        # Check admin role
        claims = get_jwt()
        role = claims.get("role")

        if role not in ["admin", "super_admin"]:
            return jsonify({
                "success": False,
                "message": "Admin access required"
            }), 403

        # Get request data
        data = request.get_json()

        if not data:
            return jsonify({
                "success": False,
                "message": "Request body is required"
            }), 400

        # Required fields
        destination_id = data.get("destination_id")
        name = data.get("name")
        activity_type = data.get("activity_type")

        if not destination_id:
            return jsonify({
                "success": False,
                "message": "destination_id is required"
            }), 400

        if not name:
            return jsonify({
                "success": False,
                "message": "Activity name is required"
            }), 400

        if not activity_type:
            return jsonify({
                "success": False,
                "message": "activity_type is required"
            }), 400

        # Clean values
        name = name.strip()
        activity_type = activity_type.strip()

        if not name:
            return jsonify({
                "success": False,
                "message": "Activity name cannot be empty"
            }), 400

        if not activity_type:
            return jsonify({
                "success": False,
                "message": "activity_type cannot be empty"
            }), 400

        # Check destination exists
        destination = Destination.query.get(destination_id)

        if not destination:
            return jsonify({
                "success": False,
                "message": "Destination not found"
            }), 404

        # Check duplicate activity within destination
        existing_activity = Activity.query.filter(
            Activity.destination_id == destination.id,
            db.func.lower(Activity.name) == name.lower()
        ).first()

        if existing_activity:
            return jsonify({
                "success": False,
                "message": "An activity with this name already exists for this destination"
            }), 409

        # Optional fields
        description = data.get("description")
        duration_minutes = data.get("duration_minutes")
        is_active = data.get("is_active", True)

        # Validate duration
        if duration_minutes is not None:
            try:
                duration_minutes = int(duration_minutes)
            except (TypeError, ValueError):
                return jsonify({
                    "success": False,
                    "message": "duration_minutes must be an integer"
                }), 400

            if duration_minutes <= 0:
                return jsonify({
                    "success": False,
                    "message": "duration_minutes must be greater than 0"
                }), 400

        # Create activity
        activity = Activity(
            destination_id=destination.id,
            name=name,
            description=description,
            activity_type=activity_type,
            duration_minutes=duration_minutes,
            is_active=is_active
        )

        db.session.add(activity)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Activity created successfully",
            "activity": {
                "id": str(activity.id),
                "destination_id": str(activity.destination_id),
                "name": activity.name,
                "description": activity.description,
                "activity_type": activity.activity_type,
                "duration_minutes": activity.duration_minutes,
                "is_active": activity.is_active,
                "created_at": (
                    activity.created_at.isoformat()
                    if activity.created_at
                    else None
                ),
                "updated_at": (
                    activity.updated_at.isoformat()
                    if activity.updated_at
                    else None
                )
            }
        }), 201

    except Exception as e:
        db.session.rollback()

        return jsonify({
            "success": False,
            "message": "Failed to create activity",
            "error": str(e)
        }), 500

@itinerary_data_bp.route("/insert_actvity_image", methods=["POST"])
@admin_required
def create_activity_image():
    """
    Add an image to an activity
    ---
    tags:
      - itinerary_data
    security:
      - Bearer: []
    consumes:
      - application/json

    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - activity_id
            - image_url
          properties:
            activity_id:
              type: string
              format: uuid
              example: "550e8400-e29b-41d4-a716-446655440000"
            image_url:
              type: string
              example: "https://example.com/images/game-drive.jpg"
            caption:
              type: string
              example: "Morning game drive through the national park"
            alt_text:
              type: string
              example: "Tourists viewing wildlife during a game drive"
            sort_order:
              type: integer
              example: 0
            is_active:
              type: boolean
              example: true

    responses:
      201:
        description: Activity image created successfully
      400:
        description: Validation error
      401:
        description: Authentication required
      403:
        description: Admin access required
      404:
        description: Activity not found
      500:
        description: Internal server error
    """

    try:
        # Check admin role
        claims = get_jwt()
        role = claims.get("role")

        if role not in ["admin", "super_admin"]:
            return jsonify({
                "success": False,
                "message": "Admin access required"
            }), 403

        # Get request data
        data = request.get_json()

        if not data:
            return jsonify({
                "success": False,
                "message": "Request body is required"
            }), 400

        # Required fields
        activity_id = data.get("activity_id")
        image_url = data.get("image_url")

        if not activity_id:
            return jsonify({
                "success": False,
                "message": "activity_id is required"
            }), 400

        if not image_url:
            return jsonify({
                "success": False,
                "message": "image_url is required"
            }), 400

        image_url = image_url.strip()

        if not image_url:
            return jsonify({
                "success": False,
                "message": "image_url cannot be empty"
            }), 400

        # Check activity exists
        activity = Activity.query.get(activity_id)

        if not activity:
            return jsonify({
                "success": False,
                "message": "Activity not found"
            }), 404

        # Optional fields
        caption = data.get("caption")
        alt_text = data.get("alt_text")
        sort_order = data.get("sort_order", 0)
        is_active = data.get("is_active", True)

        # Validate sort_order
        try:
            sort_order = int(sort_order)
        except (TypeError, ValueError):
            return jsonify({
                "success": False,
                "message": "sort_order must be an integer"
            }), 400

        # Create activity image
        activity_image = ActivityImage(
            activity_id=activity.id,
            image_url=image_url,
            caption=caption,
            alt_text=alt_text,
            sort_order=sort_order,
            is_active=is_active
        )

        db.session.add(activity_image)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Activity image created successfully",
            "image": {
                "id": str(activity_image.id),
                "activity_id": str(activity_image.activity_id),
                "image_url": activity_image.image_url,
                "caption": activity_image.caption,
                "alt_text": activity_image.alt_text,
                "sort_order": activity_image.sort_order,
                "is_active": activity_image.is_active,
                "created_at": (
                    activity_image.created_at.isoformat()
                    if activity_image.created_at
                    else None
                )
            }
        }), 201

    except Exception as e:
        db.session.rollback()

        return jsonify({
            "success": False,
            "message": "Failed to create activity image",
            "error": str(e)
        }), 500


@itinerary_data_bp.route("/create_actvity_rate", methods=["POST"])
@admin_required
def create_activity_rate():
    """
    Create an activity rate
    ---
    tags:
      - itinerary_data
    security:
      - Bearer: []
    consumes:
      - application/json

    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - activity_id
            - price
          properties:
            activity_id:
              type: string
              format: uuid
              example: "550e8400-e29b-41d4-a716-446655440000"
            price:
              type: number
              format: float
              example: 50.00
            currency:
              type: string
              example: USD
            pricing_type:
              type: string
              example: per_person
            min_people:
              type: integer
              example: 1
            max_people:
              type: integer
              example: 10
            is_active:
              type: boolean
              example: true

    responses:
      201:
        description: Activity rate created successfully
      400:
        description: Validation error
      401:
        description: Authentication required
      403:
        description: Admin access required
      404:
        description: Activity not found
      409:
        description: Activity rate already exists
      500:
        description: Internal server error
    """

    try:
        # Check admin role
        claims = get_jwt()
        role = claims.get("role")

        if role not in ["admin", "super_admin"]:
            return jsonify({
                "success": False,
                "message": "Admin access required"
            }), 403

        # Get request data
        data = request.get_json()

        if not data:
            return jsonify({
                "success": False,
                "message": "Request body is required"
            }), 400

        # Required fields
        activity_id = data.get("activity_id")
        price = data.get("price")

        if not activity_id:
            return jsonify({
                "success": False,
                "message": "activity_id is required"
            }), 400

        if price is None:
            return jsonify({
                "success": False,
                "message": "price is required"
            }), 400

        # Check activity exists
        activity = Activity.query.get(activity_id)

        if not activity:
            return jsonify({
                "success": False,
                "message": "Activity not found"
            }), 404

        # Validate price
        try:
            price = float(price)
        except (TypeError, ValueError):
            return jsonify({
                "success": False,
                "message": "price must be a number"
            }), 400

        if price <= 0:
            return jsonify({
                "success": False,
                "message": "price must be greater than 0"
            }), 400

        # Optional fields
        currency = data.get("currency", "USD")
        pricing_type = data.get("pricing_type", "per_person")
        min_people = data.get("min_people")
        max_people = data.get("max_people")
        is_active = data.get("is_active", True)

        # Clean values
        if currency:
            currency = currency.strip().upper()

        if pricing_type:
            pricing_type = pricing_type.strip().lower()

        # Validate pricing type
        allowed_pricing_types = [
            "per_person",
            "per_group",
            "per_vehicle",
            "per_trip",
            "flat_rate"
        ]

        if pricing_type not in allowed_pricing_types:
            return jsonify({
                "success": False,
                "message": (
                    "Invalid pricing_type. Allowed values are: "
                    + ", ".join(allowed_pricing_types)
                )
            }), 400

        # Validate min_people
        if min_people is not None:
            try:
                min_people = int(min_people)
            except (TypeError, ValueError):
                return jsonify({
                    "success": False,
                    "message": "min_people must be an integer"
                }), 400

            if min_people < 1:
                return jsonify({
                    "success": False,
                    "message": "min_people must be at least 1"
                }), 400

        # Validate max_people
        if max_people is not None:
            try:
                max_people = int(max_people)
            except (TypeError, ValueError):
                return jsonify({
                    "success": False,
                    "message": "max_people must be an integer"
                }), 400

            if max_people < 1:
                return jsonify({
                    "success": False,
                    "message": "max_people must be at least 1"
                }), 400

        # Validate people range
        if (
            min_people is not None
            and max_people is not None
            and min_people > max_people
        ):
            return jsonify({
                "success": False,
                "message": "min_people cannot be greater than max_people"
            }), 400

        # Check duplicate rate
        existing_rate = ActivityRate.query.filter(
            ActivityRate.activity_id == activity.id,
            db.func.lower(ActivityRate.currency) == currency.lower(),
            db.func.lower(ActivityRate.pricing_type) ==
            pricing_type.lower(),
            ActivityRate.min_people == min_people,
            ActivityRate.max_people == max_people
        ).first()

        if existing_rate:
            return jsonify({
                "success": False,
                "message": "An activity rate with the same pricing configuration already exists"
            }), 409

        # Create activity rate
        activity_rate = ActivityRate(
            activity_id=activity.id,
            price=price,
            currency=currency,
            pricing_type=pricing_type,
            min_people=min_people,
            max_people=max_people,
            is_active=is_active
        )

        db.session.add(activity_rate)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Activity rate created successfully",
            "rate": {
                "id": str(activity_rate.id),
                "activity_id": str(activity_rate.activity_id),
                "price": float(activity_rate.price),
                "currency": activity_rate.currency,
                "pricing_type": activity_rate.pricing_type,
                "min_people": activity_rate.min_people,
                "max_people": activity_rate.max_people,
                "is_active": activity_rate.is_active,
                "created_at": (
                    activity_rate.created_at.isoformat()
                    if activity_rate.created_at
                    else None
                ),
                "updated_at": (
                    activity_rate.updated_at.isoformat()
                    if activity_rate.updated_at
                    else None
                )
            }
        }), 201

    except Exception as e:
        db.session.rollback()

        return jsonify({
            "success": False,
            "message": "Failed to create activity rate",
            "error": str(e)
        }), 500

# FETCH THE DATA
@itinerary_data_bp.route("/destinations", methods=["GET"])
@any_authenticated_required
def get_destinations():
    """
    Get all destinations
    ---
    tags:
      - itinerary_data
    security:
      - Bearer: []

    responses:
      200:
        description: Destinations fetched successfully
      401:
        description: Authentication required
      500:
        description: Internal server error
    """

    try:
        destinations = Destination.query.filter_by(
            is_active=True
        ).order_by(
            Destination.name.asc()
        ).all()

        destination_list = []

        for destination in destinations:
            destination_list.append({
                "id": str(destination.id),
                "name": destination.name,
                "slug": destination.slug,
                "description": destination.description,
                "short_description": destination.short_description,
                "destination_type": destination.destination_type,
                "region": destination.region,
                "district": destination.district,
                "is_active": destination.is_active,

                "images": [
                    {
                        "id": str(image.id),
                        "image_url": image.image_url,
                        "caption": image.caption,
                        "alt_text": image.alt_text,
                        "sort_order": image.sort_order
                    }
                    for image in destination.images
                    if image.is_active
                ],

                "accommodations": [
                    {
                        "id": str(accommodation.id),
                        "name": accommodation.name,
                        "description": accommodation.description,
                        "accommodation_type": accommodation.accommodation_type,
                        "address": accommodation.address,
                        "rating": (
                            float(accommodation.rating)
                            if accommodation.rating is not None
                            else None
                        )
                    }
                    for accommodation in destination.accommodations
                    if accommodation.is_active
                ],

                "activities": [
                    {
                        "id": str(activity.id),
                        "name": activity.name,
                        "description": activity.description,
                        "activity_type": activity.activity_type,
                        "duration_minutes": activity.duration_minutes
                    }
                    for activity in destination.activities
                    if activity.is_active
                ],

                "created_at": (
                    destination.created_at.isoformat()
                    if destination.created_at
                    else None
                ),

                "updated_at": (
                    destination.updated_at.isoformat()
                    if destination.updated_at
                    else None
                )
            })

        return jsonify({
            "success": True,
            "count": len(destination_list),
            "destinations": destination_list
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Failed to fetch destinations",
            "error": str(e)
        }), 500

@itinerary_data_bp.route("/accommodations", methods=["GET"])
@any_authenticated_required
def get_accommodations():
    """
    Get all active accommodations
    ---
    tags:
      - itinerary_data
    security:
      - Bearer: []

    responses:
      200:
        description: Accommodations fetched successfully
      401:
        description: Authentication required
      500:
        description: Internal server error
    """

    try:
        accommodations = Accommodation.query.filter_by(
            is_active=True
        ).order_by(
            Accommodation.name.asc()
        ).all()

        accommodation_list = []

        for accommodation in accommodations:

            accommodation_list.append({
                "id": str(accommodation.id),
                "destination_id": str(accommodation.destination_id),

                "name": accommodation.name,
                "description": accommodation.description,
                "accommodation_type": accommodation.accommodation_type,
                "address": accommodation.address,

                "rating": (
                    float(accommodation.rating)
                    if accommodation.rating is not None
                    else None
                ),

                "is_active": accommodation.is_active,

                "images": [
                    {
                        "id": str(image.id),
                        "image_url": image.image_url,
                        "caption": image.caption,
                        "alt_text": image.alt_text,
                        "sort_order": image.sort_order
                    }
                    for image in accommodation.images
                    if image.is_active
                ],

                "rates": [
                    {
                        "id": str(rate.id),
                        "room_type": rate.room_type,
                        "meal_plan": rate.meal_plan,
                        "price_per_night": float(rate.price_per_night),
                        "currency": rate.currency,
                        "max_guests": rate.max_guests,
                        "season": rate.season,
                        "is_active": rate.is_active
                    }
                    for rate in accommodation.rates
                    if rate.is_active
                ],

                "created_at": (
                    accommodation.created_at.isoformat()
                    if accommodation.created_at
                    else None
                ),

                "updated_at": (
                    accommodation.updated_at.isoformat()
                    if accommodation.updated_at
                    else None
                )
            })

        return jsonify({
            "success": True,
            "count": len(accommodation_list),
            "accommodations": accommodation_list
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Failed to fetch accommodations",
            "error": str(e)
        }), 500

@itinerary_data_bp.route("/accommodation-rates", methods=["GET"])
@any_authenticated_required
def get_accommodation_rates():
    """
    Get all active accommodation rates
    ---
    tags:
      - itinerary_data
    security:
      - Bearer: []

    responses:
      200:
        description: Accommodation rates fetched successfully
      401:
        description: Authentication required
      500:
        description: Internal server error
    """

    try:
        rates = AccommodationRate.query.filter_by(
            is_active=True
        ).order_by(
            AccommodationRate.room_type.asc()
        ).all()

        rate_list = []

        for rate in rates:
            rate_list.append({
                "id": str(rate.id),
                "accommodation_id": str(rate.accommodation_id),

                "room_type": rate.room_type,
                "meal_plan": rate.meal_plan,
                "price_per_night": float(rate.price_per_night),
                "currency": rate.currency,
                "max_guests": rate.max_guests,
                "season": rate.season,
                "is_active": rate.is_active,

                "accommodation": {
                    "id": str(rate.accommodation.id),
                    "name": rate.accommodation.name,
                    "destination_id": str(
                        rate.accommodation.destination_id
                    )
                } if rate.accommodation else None,

                "created_at": (
                    rate.created_at.isoformat()
                    if rate.created_at
                    else None
                ),

                "updated_at": (
                    rate.updated_at.isoformat()
                    if rate.updated_at
                    else None
                )
            })

        return jsonify({
            "success": True,
            "count": len(rate_list),
            "accommodation_rates": rate_list
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Failed to fetch accommodation rates",
            "error": str(e)
        }), 500


@itinerary_data_bp.route("/activities", methods=["GET"])
@any_authenticated_required
def get_activities():
    """
    Get all active activities
    ---
    tags:
      - itinerary_data
    security:
      - Bearer: []

    responses:
      200:
        description: Activities fetched successfully
      401:
        description: Authentication required
      500:
        description: Internal server error
    """

    try:
        activities = Activity.query.filter_by(
            is_active=True
        ).order_by(
            Activity.name.asc()
        ).all()

        activity_list = []

        for activity in activities:
            activity_list.append({
                "id": str(activity.id),
                "destination_id": str(activity.destination_id),

                "name": activity.name,
                "description": activity.description,
                "activity_type": activity.activity_type,
                "duration_minutes": activity.duration_minutes,
                "is_active": activity.is_active,

                "images": [
                    {
                        "id": str(image.id),
                        "image_url": image.image_url,
                        "caption": image.caption,
                        "alt_text": image.alt_text,
                        "sort_order": image.sort_order
                    }
                    for image in activity.images
                    if image.is_active
                ],

                "rates": [
                    {
                        "id": str(rate.id),
                        "price": float(rate.price),
                        "currency": rate.currency,
                        "pricing_type": rate.pricing_type,
                        "min_people": rate.min_people,
                        "max_people": rate.max_people
                    }
                    for rate in activity.rates
                    if rate.is_active
                ],

                "destination": {
                    "id": str(activity.destination.id),
                    "name": activity.destination.name,
                    "slug": activity.destination.slug
                } if activity.destination else None,

                "created_at": (
                    activity.created_at.isoformat()
                    if activity.created_at
                    else None
                ),

                "updated_at": (
                    activity.updated_at.isoformat()
                    if activity.updated_at
                    else None
                )
            })

        return jsonify({
            "success": True,
            "count": len(activity_list),
            "activities": activity_list
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Failed to fetch activities",
            "error": str(e)
        }), 500

@itinerary_data_bp.route("/activity-rates", methods=["GET"])
@any_authenticated_required
def get_activity_rates():
    """
    Get all active activity rates
    ---
    tags:
      - itinerary_data
    security:
      - Bearer: []

    responses:
      200:
        description: Activity rates fetched successfully
      401:
        description: Authentication required
      500:
        description: Internal server error
    """

    try:
        rates = ActivityRate.query.filter_by(
            is_active=True
        ).order_by(
            ActivityRate.price.asc()
        ).all()

        rate_list = []

        for rate in rates:
            rate_list.append({
                "id": str(rate.id),
                "activity_id": str(rate.activity_id),

                "price": float(rate.price),
                "currency": rate.currency,
                "pricing_type": rate.pricing_type,
                "min_people": rate.min_people,
                "max_people": rate.max_people,
                "is_active": rate.is_active,

                "activity": {
                    "id": str(rate.activity.id),
                    "name": rate.activity.name,
                    "activity_type": rate.activity.activity_type,
                    "destination_id": str(
                        rate.activity.destination_id
                    )
                } if rate.activity else None,

                "created_at": (
                    rate.created_at.isoformat()
                    if rate.created_at
                    else None
                ),

                "updated_at": (
                    rate.updated_at.isoformat()
                    if rate.updated_at
                    else None
                )
            })

        return jsonify({
            "success": True,
            "count": len(rate_list),
            "activity_rates": rate_list
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Failed to fetch activity rates",
            "error": str(e)
        }), 500
    
