import uuid

from config.extensions import db

class Conversation(db.Model):
    __tablename__ = "conversations"

    id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    itinerary = db.relationship("Itinerary", back_populates="conversations")
    title = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(50), nullable=False, default="active")
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now(), onupdate=db.func.now())
    user = db.relationship(
        "User",
        back_populates="conversations"
    )

    itinerary = db.relationship(
        "Itinerary",
        back_populates="conversation"
    )

    def __repr__(self):
        return f"<Conversation {self.id}>"