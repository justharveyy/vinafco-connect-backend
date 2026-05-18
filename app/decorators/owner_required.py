from functools import wraps
from flask import jsonify, request
from app.models import Users
import jwt

def owner_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None
        user = None
        
        # Get token from header
        if 'Authorization' in request.headers:
            token = request.headers['Authorization']
        
        if not token:
            return jsonify({
                "success": False,
                "message": "Token is missing"
            }), 401
        
        try:
            # Decode token
            from app import app
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user = Users.query.filter_by(user_id=data['user_id']).first()
            
            if not current_user:
                return jsonify({
                    "success": False,
                    "message": "User not found"
                }), 401
                
            # Check if user is owner
            if current_user.role != 'Owner':
                return jsonify({
                    "success": False,
                    "message": "Owner access required"
                }), 403
                
            user = current_user
            
        except jwt.ExpiredSignatureError:
            return jsonify({
                "success": False,
                "message": "Token has expired"
            }), 401
        except jwt.InvalidTokenError:
            return jsonify({
                "success": False,
                "message": "Token is invalid"
            }), 401
        
        # Pass user to the decorated function
        return f(user, *args, **kwargs)
    
    return decorated_function
