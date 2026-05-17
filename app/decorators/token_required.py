from flask import request, jsonify

from app import app
from app.models import Users, db

from functools import wraps
import jwt

# Token verifier blueprint
def token_required():
    def wrapper(f):
        @wraps(f)
        def decorator(*args, **kwargs):
            try:
                token = request.headers.get('Authorization', '')
                if token == '':
                    return jsonify({
                        "success": False,
                        "message": "Missing token"
                    }), 401

                decoded = jwt.decode(
                    jwt=token,
                    key=app.config['SECRET_KEY'],
                    algorithms=['HS256']
                )
                user = Users.query.filter_by(
                    user_id=decoded['user_id']
                ).first()

                if not user:
                    return jsonify({
                        "success": False,
                        "message": "User not found"
                    }), 401

                db.session.merge(user)
                return f(user=user, *args, **kwargs)
            except jwt.exceptions.InvalidTokenError:
                return jsonify({
                    "success": False,
                    "message": "Invalid token"
                }), 401
        return decorator
    return wrapper