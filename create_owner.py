#!/usr/bin/env python3
"""
Script to create an owner user for testing the admin functionality
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from app.models import db, Users
from hashlib import sha256
from uuid import uuid4

def create_owner_user():
    """Create an owner user for testing"""
    with app.app_context():
        # Check if owner already exists
        existing_owner = Users.query.filter_by(email='owner@vinafco.com').first()
        if existing_owner:
            print("Owner user already exists!")
            print(f"Email: {existing_owner.email}")
            print(f"Role: {existing_owner.role}")
            return
        
        # Create owner user
        owner_user = Users(
            email='owner@vinafco.com',
            password=sha256(f"{app.config['SECRET_KEY']}owner123".encode()).hexdigest(),
            fullname='Company Owner',
            user_id=str(uuid4()),
            is_customer="False",
            balance=0,
            email_verified=True,
            role='Owner',
            address='VINAFCO Headquarters',
            tax_id='123456789'
        )
        
        db.session.add(owner_user)
        db.session.commit()
        
        print("Owner user created successfully!")
        print("Login credentials:")
        print("Email: owner@vinafco.com")
        print("Password: owner123")
        print("Role: Owner")

if __name__ == "__main__":
    create_owner_user()
