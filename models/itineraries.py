import uuid

from config.extensions import db


class Itinerary(db.Model):
    __tablename__ = "itineraries"
    id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(50), nullable=False, default="draft")
    start_date = db.Column( db.Date, nullable=True)
    end_date = db.Column( db.Date, nullable=True)
    travelers = db.Column(db.Integer, nullable=True)
    total_price = db.Column( db.Numeric(12, 2), nullable=True)
    currency = db.Column(db.String(10), nullable=False, default="USD")
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now(), onupdate=db.func.now())
    user = db.relationship( "User", back_populates="itineraries")
    conversations = db.relationship ("Conversation", back_populates="itinerary")
    def __repr__(self):
        return f"<Itinerary {self.id}>"