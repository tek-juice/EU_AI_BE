import uuid
from config.extensions import db


class Destination(db.Model):
    __tablename__ = "destinations"

    id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = db.Column(db.String(150), nullable=False, unique=True, index=True)
    slug = db.Column(db.String(180), nullable=False, unique=True, index=True)
    description = db.Column(db.Text, nullable=True)
    short_description = db.Column(db.String(500), nullable=True)
    destination_type = db.Column(db.String(100), nullable=False)
    region = db.Column(db.String(100), nullable=True)
    district = db.Column(db.String(100), nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now(), onupdate=db.func.now())

    # Relationships
    images = db.relationship(
        "DestinationImage",
        back_populates="destination",
        cascade="all, delete-orphan",
        lazy=True
    )

    accommodations = db.relationship(
        "Accommodation",
        back_populates="destination",
        cascade="all, delete-orphan",
        lazy=True
    )

    activities = db.relationship(
        "Activity",
        back_populates="destination",
        cascade="all, delete-orphan",
        lazy=True
    )

    def __repr__(self):
        return f"<Destination {self.name}>"

class DestinationImage(db.Model):
    __tablename__ = "destination_images"

    id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    destination_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey("destinations.id", ondelete="CASCADE" ), nullable=False, index=True)
    image_url = db.Column(db.String(500), nullable=False)
    caption = db.Column(db.String(500),nullable=True)
    alt_text = db.Column(db.String(500),nullable=True)
    sort_order = db.Column(db.Integer,nullable=False,default=0)
    is_active = db.Column(db.Boolean,nullable=False,default=True)
    created_at = db.Column(db.DateTime,nullable=False,server_default=db.func.now())
    destination = db.relationship("Destination",back_populates="images")

    def __repr__(self):
        return f"<DestinationImage {self.id}>"


class Accommodation(db.Model):
    __tablename__ = "accommodations"

    id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    destination_id = db.Column( db.UUID(as_uuid=True), db.ForeignKey(     "destinations.id",     ondelete="CASCADE" ), nullable=False, index=True)
    name = db.Column( db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    accommodation_type = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(255), nullable=True)
    rating = db.Column(db.Numeric(2, 1), nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now(), onupdate=db.func.now())

    # Relationships
    destination = db.relationship(
        "Destination",
        back_populates="accommodations"
    )

    rates = db.relationship(
        "AccommodationRate",
        back_populates="accommodation",
        cascade="all, delete-orphan",
        lazy=True
    )

    images = db.relationship(
        "AccommodationImage",
        back_populates="accommodation",
        cascade="all, delete-orphan",
        lazy=True
    )

    def __repr__(self):
        return f"<Accommodation {self.name}>"

class AccommodationImage(db.Model):
    __tablename__ = "accommodation_images"

    id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    accommodation_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey(     "accommodations.id",     ondelete="CASCADE" ), nullable=False, index=True)
    image_url = db.Column(db.String(500), nullable=False)
    caption = db.Column(db.String(500), nullable=True)
    alt_text = db.Column(db.String(500), nullable=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now())

    # Relationship
    accommodation = db.relationship(
        "Accommodation",
        back_populates="images"
    )

    def __repr__(self):
        return f"<AccommodationImage {self.id}>"


class AccommodationRate(db.Model):
    __tablename__ = "accommodation_rates"

    id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    accommodation_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey("accommodations.id", ondelete="CASCADE"), nullable=False, index=True)
    room_type = db.Column(db.String(100), nullable=False)
    meal_plan = db.Column(db.String(100), nullable=True)
    price_per_night = db.Column(db.Numeric(12, 2), nullable=False)
    currency = db.Column(db.String(10), nullable=False, default="USD")
    max_guests = db.Column(db.Integer, nullable=False, default=2)
    season = db.Column(db.String(100), nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now(), onupdate=db.func.now())

    # Relationship
    accommodation = db.relationship(
        "Accommodation",
        back_populates="rates"
    )

    def __repr__(self):
        return f"<AccommodationRate {self.room_type}>"


class Activity(db.Model):
    __tablename__ = "activities"
    id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    destination_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey(     "destinations.id",     ondelete="CASCADE" ), nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    activity_type = db.Column(db.String(100), nullable=False)
    duration_minutes = db.Column(db.Integer, nullable=True)
    is_active = db.Column(db.Boolean,nullable=False,default=True)
    created_at = db.Column(db.DateTime,nullable=False,server_default=db.func.now())
    updated_at = db.Column(db.DateTime,nullable=False,server_default=db.func.now(),onupdate=db.func.now())

    # Relationships
    destination = db.relationship(
        "Destination",
        back_populates="activities"
    )

    rates = db.relationship(
        "ActivityRate",
        back_populates="activity",
        cascade="all, delete-orphan",
        lazy=True
    )

    images = db.relationship(
        "ActivityImage",
        back_populates="activity",
        cascade="all, delete-orphan",
        lazy=True
    )

    def __repr__(self):
        return f"<Activity {self.name}>"

class ActivityImage(db.Model):
    __tablename__ = "activity_images"

    id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    activity_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey("activities.id", ondelete="CASCADE" ), nullable=False, index=True)
    image_url = db.Column(db.String(500), nullable=False)
    caption = db.Column(db.String(500), nullable=True)
    alt_text = db.Column(db.String(500), nullable=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime,nullable=False,server_default=db.func.now())

    # Relationship
    activity = db.relationship(
    "Activity",
    back_populates="images"
    )

    def __repr__(self):
        return f"<ActivityImage {self.id}>"


class ActivityRate(db.Model):
    __tablename__ = "activity_rates"

    id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    activity_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey("activities.id", ondelete="CASCADE"), nullable=False, index=True)
    price = db.Column(db.Numeric(12, 2), nullable=False)
    currency = db.Column(db.String(10), nullable=False, default="USD")
    pricing_type = db.Column(db.String(50), nullable=False, default="per_person")
    min_people = db.Column(db.Integer, nullable=True)
    max_people = db.Column(db.Integer, nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now(), onupdate=db.func.now())

    # Relationship
    activity = db.relationship(
        "Activity",
        back_populates="rates"
    )

    def __repr__(self):
        return f"<ActivityRate {self.price} {self.currency}>"


class Transport(db.Model):
    __tablename__ = "transports"

    id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    transport_type = db.Column(db.String(100), nullable=False)
    # safari_vehicle, car, van, bus, boat, domestic_flight, etc.
    capacity = db.Column(db.Integer, nullable=True)
    price = db.Column(db.Numeric(12, 2), nullable=True)
    currency = db.Column(db.String(10), nullable=False, default="USD")
    pricing_type = db.Column(db.String(50), nullable=False, default="per_trip")
    # per_trip, per_day, per_person, etc.
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now(), onupdate=db.func.now())

    def __repr__(self):
        return f"<Transport {self.name}>"