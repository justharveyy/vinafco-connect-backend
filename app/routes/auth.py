# All comments are made by a human. Not AI.

"""
Auth Handler
THis blueprint handles user authentication and 2 Factor Authentication

Passwords are salted and hashed using SHA-512
"""


from flask import Blueprint, request, jsonify, redirect

from app import app
from app.models import db, Users
from app.helpers.send_email import send_sso_email, send_verification_email

from hashlib import sha256
from datetime import datetime, timedelta
import jwt
import time
import os
from uuid import uuid4

# Create Auth Blueprint
auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

# Routes
@auth_bp.route("/register", methods=["POST"])
def register_route():
    payload = request.get_json(silent=True)
    
    # Check if user already exists
    user_exists = Users.query.filter_by(
        email=payload['email'].strip()
    ).first()
    
    if user_exists:
        return jsonify({
            "success": False,
            "message": "User already exists. Please try again"
        }), 400
    
    # Add user
    user = Users(
        email=payload['email'].strip(),
        password=sha256(f"{app.config['SECRET_KEY']}{payload['password']}".encode()).hexdigest(),
        fullname=payload['fullname'].strip(),
        user_id=str(uuid4()),
        is_customer="True",
        balance=0
    )
    
    db.session.add(user)
    db.session.commit()
    
    # Sign verification token
    verif_token = jwt.encode(
        payload={
            "user_id": user.user_id,
            "purpose": "email_verification",
            "iat": int(time.mktime(datetime.now().timetuple())),
            "exp": int(time.mktime((datetime.now() + timedelta(days=1)).timetuple()))
        },
        key=app.config['SECRET_KEY'],
        algorithm='HS256'
    )
    
    # Send Verification Email
    send_status = send_verification_email(user.email, user.fullname, verif_token)
    
    if send_status == False:
        return jsonify({
            "success": False,
            "message": "Failed to send verification email. Please try again."
        }), 500
    return jsonify({
        "success": True,
        "message": "Registration complete, please check your email for a verification link."
    })
    
@auth_bp.route('/login', methods=['POST'])
def login_route():
    payload = request.get_json(silent=True)
    
    # Check if user exists
    user = Users.query.filter_by(
        email=payload['email'].strip()
    ).first()
    
    if not user:
        return jsonify({
            "success": False,
            "message": "User does not exist. Please try again"
        }), 400
    
    # Check password
    if user.password != sha256(f"{app.config['SECRET_KEY']}{payload['password']}".encode()).hexdigest():
        return jsonify({
            "success": False,
            "message": "Incorrect password. Please try again"
        }), 400
        
    # Check for email verification
    if user.email_verified != True:
        return jsonify({
            "success": False,
            "message": "Email not verified. Please check your email for a verification link or use Single Sign-On (SSO) if available."
        })
        
    # Sign a token, valid for 30 days
    token = jwt.encode(
        payload={
            "user_id": user.user_id,
            "iat": int(time.mktime(datetime.now().timetuple())),
            "exp": int(time.mktime((datetime.now() + timedelta(days=30)).timetuple()))
        },
        key=app.config['SECRET_KEY'],
        algorithm='HS256'
    )
    
    return jsonify({
        "success": True,
        "message": "Login successful",
        "token": token
    })
    
    
@auth_bp.route('/verify-email', methods=['GET'])
def verify_email_route():
    token = request.args.get('token')
    
    if not token:
        return jsonify({
            "success": False,
            "message": "Invalid verification link. Please try again."
        }), 400
    
    try:
        decoded_token = jwt.decode(token, key=app.config['SECRET_KEY'], algorithms=['HS256'])
        user_id = decoded_token['user_id']
        purpose = decoded_token['purpose']
        
        if user_id == "" or purpose != "email_verification":
            return jsonify({
                "success": False,
                "message": "Invalid verification link. Please try again."
            })
        
        user = Users.query.filter_by(user_id=user_id).first()
        
        if not user:
            return jsonify({
                "success": False,
                "message": "User does not exist. Please try again."
            }), 400
        
        user.email_verified = True
        db.session.commit()
        
        # Grant a token and redirect them to dashboard
        token = jwt.encode(
            payload={
                "user_id": user.user_id,
                "iat": int(time.mktime(datetime.now().timetuple())),
                "exp": int(time.mktime((datetime.now() + timedelta(hours=1)).timetuple()))
            },
            key=app.config['SECRET_KEY'],
            algorithm='HS256'
        )
        
        return redirect(
            f"{os.getenv('FRONTEND_URL')}/auth/callback?token={token}"
        )
        
    except jwt.ExpiredSignatureError:
        return jsonify({
            "success": False,
            "message": "Verification link has expired. Please request a new one."
        }), 400
    except jwt.InvalidTokenError:
        return jsonify({
            "success": False,
            "message": "Invalid verification link. Please try again."
        }), 400
    except KeyError as e:
        print(f"KeyError occurred: {e}")
        return jsonify({
            "success": False,
            "message": "Invalid verification link. Please try again."
        }), 400
        
@auth_bp.route('/login/with-email', methods=['POST'])
def login_with_email_route():
    payload = request.get_json(silent=True)
    
    # Check if user exists
    user = Users.query.filter_by(
        email=payload['email'].strip()
    ).first()
    
    if not user:
        return jsonify({
            "success": False,
            "message": "User does not exist. Please try again"
        }), 400
    
    # Send a login link to their email
    sso_token = jwt.encode(
        payload={
            "user_id": user.user_id,
            "purpose": "sso",
            "iat": int(time.mktime(datetime.now().timetuple())),
            "exp": int(time.mktime((datetime.now() + timedelta(days=1)).timetuple()))
        },
        key=app.config['SECRET_KEY'],
        algorithm='HS256'
    )
    
    send_status = send_sso_email(user.email, f"{os.getenv('BACKEND_URL')}/auth/sso-login?token={sso_token}")