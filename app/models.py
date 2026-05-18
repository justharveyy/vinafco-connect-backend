from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

from app import app

# Create Models
db = SQLAlchemy(app)
Migrate(app, db)

class Users(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    user_id = db.Column(db.String(), nullable=False, unique=True)
    fullname = db.Column(db.String(), nullable=False)
    email = db.Column(db.String(), nullable=False)
    phone_number = db.Column(db.String(), nullable=True)
    phone_number_verified = db.Column(db.String(), nullable=False, default=False)
    password = db.Column(db.String(), nullable=False)
    is_customer = db.Column(db.String(), nullable=False)
    balance = db.Column(db.Integer(), nullable=False, default=0)
    email_verified = db.Column(db.Boolean(), nullable=False, default=False)
    role = db.Column(db.String(), default="User")
    created_at = db.Column(db.DateTime(), server_default=db.func.now())
    bookings = db.relationship('Bookings', backref='user', lazy=True)
    address = db.Column(db.String(), nullable=False, default="")
    tax_id = db.Column(db.String(), nullable=True)
    
    
    def to_dict(self):
        return {
            "user_id": self.user_id,
            "fullname": self.fullname,
            "email": self.email,
            "balance": self.balance,
            "email_verified": self.email_verified,
            "role": self.role,
            "created_at": self.created_at.isoformat()
        }
        

class Vessels(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    vessel_code = db.Column(db.String(), unique=True)
    vessel_name = db.Column(db.String(), nullable=False)
    latest_status = db.Column(db.String(), nullable=False)
    speed = db.Column(db.Float(), nullable=True)
    course = db.Column(db.Float(), nullable=True)
    true_heading = db.Column(db.Float(), nullable=True)
    draught = db.Column(db.Float(), nullable=True)
    reported_destination = db.Column(db.String(), nullable=False)
    reported_eta = db.Column(db.DateTime(), nullable=False)
    matched_destination = db.Column(db.String(), nullable=False)
    vessel_type = db.Column(db.String(), nullable=False)
    last_updated = db.Column(db.DateTime(), nullable=False)
    flag = db.Column(db.String(), nullable=False)
    photo = db.Column(db.String(), nullable=False, default="")
    call_sign = db.Column(db.String(), nullable=False)
    transponder_class = db.Column(db.String(), nullable=False)
    mmsi_number = db.Column(db.String(), nullable=False)
    

class Routes(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    vessel_id = db.Column(db.String(), nullable=False)
    quote_name = db.Column(db.String(), nullable=False)
    from_port = db.Column(db.String(), nullable=False)
    from_port_code = db.Column(db.String(), nullable=False)
    to_port = db.Column(db.String(), nullable=False)
    to_port_code = db.Column(db.String(), nullable=False)
    quote = db.Column(db.Float(), nullable=False)
    total_distance = db.Column(db.Float(), nullable=False)
    
    
class Bookings(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    booking_id = db.Column(db.String(), nullable=False)
    user_id = db.Column(db.String(), db.ForeignKey('users.user_id'), nullable=False)
    vessel_id = db.Column(db.String(), nullable=False)
    booking_date = db.Column(db.DateTime(), nullable=False)
    quote = db.Column(db.Float(), nullable=False)
    extra_fees = db.Column(db.Float(), nullable=False)
    total_price = db.Column(db.Float(), nullable=False)
    total_package_weight = db.Column(db.Float(), nullable=False)
    trip_length = db.Column(db.Float(), nullable=False)
    estimated_start_time = db.Column(db.DateTime(), nullable=False)
    estimated_time_to_destination = db.Column(db.DateTime(), nullable=False)
    status = db.Column(db.String(), nullable=False, default="Requested")
    payment = db.relationship('Payments', backref='booking', uselist=False)
    expire_in = db.Column(db.DateTime(), nullable=False)
    cargo_type = db.Column(db.String(), nullable=False)
    

class Items(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    booking_id = db.Column(db.String(), nullable=False)
    name = db.Column(db.String(), nullable=False)
    weight = db.Column(db.Float(), nullable=False)
    description = db.Column(db.String(), nullable=False)
    price = db.Column(db.Float(), nullable=False)
    

class Confirmations(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    booking_id = db.Column(db.String(), nullable=False)
    confirmation_id = db.Column(db.String(), nullable=False)
    created_at = db.Column(db.DateTime(), server_default=db.func.now())
    confirmation_key = db.Column(db.String(), nullable=False)
    recipient_phone_number = db.Column(db.String(), nullable=False)
    original_hash = db.Column(db.String(), nullable=False)
    signed_hash = db.Column(db.String(), nullable=False)
    
    
"""
Since this is just a school project, availability will be decided by
weight. In production, this table can be modified to accept multiple
patterns like types of cargo, dimensions, compliance, etc.
"""
class UpcomingAvailability(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    vessel_id = db.Column(db.String(), nullable=False)
    available_weight = db.Column(db.Float(), nullable=False)
    remaining_weight = db.Column(db.Float(), nullable=False)
    departure_date_time = db.Column(db.Float(), nullable=False)
    arrival_date_time = db.Column(db.Float(), nullable=False)
    depart_from = db.Column(db.String(), nullable=False)
    depart_from_port_code = db.Column(db.String(), nullable=False)
    arrive_to = db.Column(db.String(), nullable=False)
    arrive_to_port_code = db.Column(db.String(), nullable=False)
    last_updated = db.Column(db.DateTime(), nullable=False)
    

class Payments(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    booking_id = db.Column(db.Integer(), db.ForeignKey('bookings.id'), nullable=False)
    amount = db.Column(db.Float(), nullable=False)
    payment_date = db.Column(db.DateTime(), nullable=False)
    payment_method = db.Column(db.String(), nullable=False)
    payment_status = db.Column(db.String(), nullable=False, default="Pending")
    tx_id = db.Column(db.String(), nullable=False)
    beneficiary_name = db.Column(db.String(), nullable=False)
    beneficiary_account = db.Column(db.String(), nullable=False)


class Chats(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    user_id = db.Column(db.String(), nullable=False)
    chat_id = db.Column(db.String(), nullable=False)
    chat_title = db.Column(db.String(), nullable=False)
    

class ChatMessages(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    chat_id = db.Column(db.String(), nullable=False)
    sender = db.Column(db.String(), nullable=False)
    message = db.Column(db.String(), nullable=False)
    timestamp = db.Column(db.DateTime(), server_default=db.func.now())