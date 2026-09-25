from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from graph.service import run_itinerary_agent
from config.model_engine import llm


itin_agent_bp = Blueprint(
    "itin_agent",
    __name__,
    url_prefix="/api/itinerary",
)


@itin_agent_bp.post("/chat")
@jwt_required()
def itinerary_chat():
    """
    Send a message to the Everything Uganda itinerary agent.

    ---
    tags:
      - Itinerary Agent

    security:
      - BearerAuth: []

    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required:
              - message
            properties:
              message:
                type: string
                description: User's travel request or question.
                example: "I want a 5 day Uganda safari for two people. We love wildlife and want luxury accommodation."
              conversation_id:
                type: string
                format: uuid
                nullable: true
                description: Optional conversation ID for continuing an existing conversation.
                example: "550e8400-e29b-41d4-a716-446655440000"

    responses:
      200:
        description: Itinerary agent response.
        content:
          application/json:
            schema:
              type: object
              properties:
                success:
                  type: boolean
                  example: true
                answer:
                  type: string
                  nullable: true
                  example: "For a 5-day Uganda safari, I recommend..."
                itinerary:
                  type: object
                  nullable: true
                  description: Generated itinerary data.

      400:
        description: Invalid request.
        content:
          application/json:
            schema:
              type: object
              properties:
                success:
                  type: boolean
                  example: false
                message:
                  type: string
                  example: "Message is required."

      401:
        description: Authentication required.

      500:
        description: Failed to process itinerary request.
        content:
          application/json:
            schema:
              type: object
              properties:
                success:
                  type: boolean
                  example: false
                message:
                  type: string
                  example: "Failed to process itinerary request."
                error:
                  type: string
    """

    data = request.get_json(silent=True) or {}

    message = data.get("message")
    conversation_id = data.get("conversation_id")

    if not message:
        return jsonify({
            "success": False,
            "message": "Message is required.",
        }), 400

    user_id = get_jwt_identity()

    try:
        result = run_itinerary_agent(
            llm=llm,
            user_id=str(user_id),
            message=message,
            conversation_id=conversation_id,
        )

        return jsonify({
            "success": True,
            "answer": result.get("answer"),
            "itinerary": result.get("itinerary"),
        }), 200

    except Exception as exc:
        return jsonify({
            "success": False,
            "message": "Failed to process itinerary request.",
            "error": str(exc),
        }), 500