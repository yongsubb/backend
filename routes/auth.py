"""
Authentication routes - Login, Logout, Token management
"""
from datetime import datetime
import re
from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity,
    get_jwt
)
from sqlalchemy.exc import SQLAlchemyError
from extensions import db
from models.user import User

auth_bp = Blueprint('auth', __name__)


_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _is_valid_email(value: str) -> bool:
    return bool(_EMAIL_RE.match((value or "").strip()))


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Login endpoint
    Supports both password and PIN authentication
    
    Request body:
    {
        "username": "string",
        "password": "string" (optional),
        "pin": "string" (optional),
        "role": "cashier" | "supervisor" (optional, for validation)
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': 'No data provided'
            }), 400
        
        username = data.get('username', '').strip()
        password = data.get('password')
        pin = data.get('pin')
        requested_role = data.get('role')
        
        # Validate input
        if not username:
            return jsonify({
                'success': False,
                'message': 'Username is required'
            }), 400
        
        if not password and not pin:
            return jsonify({
                'success': False,
                'message': 'Password or PIN is required'
            }), 400
        
        # Find user
        user = User.query.filter_by(username=username).first()
        
        if not user:
            return jsonify({
                'success': False,
                'message': 'Invalid username or password'
            }), 401
        
        # Check if user is active
        if not user.is_active:
            return jsonify({
                'success': False,
                'message': 'Account is deactivated. Please contact supervisor.'
            }), 403
        
        # Authenticate
        authenticated = False
        auth_method = None
        
        if password:
            authenticated = user.check_password(password)
            auth_method = 'password'
        elif pin:
            authenticated = user.check_pin(pin)
            auth_method = 'pin'
        
        if not authenticated:
            return jsonify({
                'success': False,
                'message': 'Invalid credentials'
            }), 401
        
        # Validate role if specified
        if requested_role and user.role != requested_role:
            return jsonify({
                'success': False,
                'message': f'You do not have {requested_role} privileges'
            }), 403
        
        # Update login status
        user.is_logged_in = True
        user.last_login = datetime.now()
        db.session.commit()
        
        # Create tokens
        access_token = create_access_token(
            identity=str(user.id),
            additional_claims={
                'username': user.username,
                'role': user.role,
                'full_name': user.full_name,
                'nickname': user.nickname,
                'display_name': user.display_name,
            }
        )
        refresh_token = create_refresh_token(identity=str(user.id))
        
        return jsonify({
            'success': True,
            'message': 'Login successful',
            'data': {
                'access_token': access_token,
                'refresh_token': refresh_token,
                'user': user.to_dict(),
                'auth_method': auth_method
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Login failed: {str(e)}'
        }), 500


@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """Logout endpoint - Updates user login status"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if user:
            user.is_logged_in = False
            db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Logout successful'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Logout failed: {str(e)}'
        }), 500


@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """Refresh access token"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({
                'success': False,
                'message': 'User not found'
            }), 404
        
        if not user.is_active:
            return jsonify({
                'success': False,
                'message': 'Account is deactivated'
            }), 403
        
        access_token = create_access_token(
            identity=str(user.id),
            additional_claims={
                'username': user.username,
                'role': user.role,
                'full_name': user.full_name,
                'nickname': user.nickname,
                'display_name': user.display_name,
            }
        )
        
        return jsonify({
            'success': True,
            'data': {
                'access_token': access_token
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Token refresh failed: {str(e)}'
        }), 500


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """Get current authenticated user"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({
                'success': False,
                'message': 'User not found'
            }), 404
        
        return jsonify({
            'success': True,
            'data': user.to_dict(include_sensitive=True)
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Failed to get user: {str(e)}'
        }), 500


@auth_bp.route('/me', methods=['PUT'])
@jwt_required()
def update_current_user():
    """Update current authenticated user profile (nickname/full name/email/etc)."""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({
                'success': False,
                'message': 'User not found'
            }), 404

        data = request.get_json() or {}

        # Allow either full_name or first_name/last_name
        full_name = (data.get('full_name') or '').strip()
        if full_name:
            parts = [p for p in full_name.split(' ') if p.strip()]
            if len(parts) >= 2:
                user.first_name = parts[0]
                user.last_name = ' '.join(parts[1:])
            else:
                # Keep last_name unchanged to satisfy NOT NULL
                user.first_name = parts[0]

        if 'first_name' in data and (data.get('first_name') or '').strip():
            user.first_name = data['first_name'].strip()
        if 'last_name' in data and (data.get('last_name') or '').strip():
            user.last_name = data['last_name'].strip()

        if 'nickname' in data:
            nickname = (data.get('nickname') or '').strip()
            user.nickname = nickname if nickname else None

        if 'email' in data:
            email = (data.get('email') or '').strip()
            if email and not _is_valid_email(email):
                return jsonify({
                    'success': False,
                    'message': 'Invalid email address'
                }), 400
            user.email = email if email else None
        if 'phone' in data:
            phone = (data.get('phone') or '').strip()
            user.phone = phone if phone else None
        if 'avatar_url' in data:
            avatar_url = (data.get('avatar_url') or '').strip()
            user.avatar_url = avatar_url if avatar_url else None

        db.session.commit()
        return jsonify({
            'success': True,
            'message': 'Profile updated successfully',
            'data': user.to_dict(include_sensitive=True)
        }), 200

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Failed to update profile: {str(e)}'
        }), 500
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Failed to update profile: {str(e)}'
        }), 500


@auth_bp.route('/verify', methods=['GET'])
@jwt_required()
def verify_token():
    """Verify if the current token is valid"""
    try:
        user_id = get_jwt_identity()
        claims = get_jwt()
        
        return jsonify({
            'success': True,
            'data': {
                'user_id': user_id,
                'username': claims.get('username'),
                'role': claims.get('role'),
                'full_name': claims.get('full_name')
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Token verification failed: {str(e)}'
        }), 500


@auth_bp.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    """Change user password"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        data = request.get_json()
        
        if not user:
            return jsonify({
                'success': False,
                'message': 'User not found'
            }), 404
        
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        
        if not current_password or not new_password:
            return jsonify({
                'success': False,
                'message': 'Current and new password are required'
            }), 400
        
        if not user.check_password(current_password):
            return jsonify({
                'success': False,
                'message': 'Current password is incorrect'
            }), 401
        
        if len(new_password) < 6:
            return jsonify({
                'success': False,
                'message': 'Password must be at least 6 characters'
            }), 400
        
        user.set_password(new_password)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Password changed successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Password change failed: {str(e)}'
        }), 500


@auth_bp.route('/set-pin', methods=['POST'])
@jwt_required()
def set_pin():
    """Set or update user PIN"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        data = request.get_json()
        
        if not user:
            return jsonify({
                'success': False,
                'message': 'User not found'
            }), 404
        
        password = data.get('password')
        new_pin = data.get('pin')
        
        if not password:
            return jsonify({
                'success': False,
                'message': 'Password is required to set PIN'
            }), 400
        
        if not user.check_password(password):
            return jsonify({
                'success': False,
                'message': 'Password is incorrect'
            }), 401
        
        try:
            user.set_pin(new_pin)
            db.session.commit()
        except ValueError as e:
            return jsonify({
                'success': False,
                'message': str(e)
            }), 400
        
        return jsonify({
            'success': True,
            'message': 'PIN set successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Failed to set PIN: {str(e)}'
        }), 500


@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Register a new cashier account (pending approval)
    
    Request body:
    {
        "username": "string",
        "password": "string",
        "first_name": "string",
        "last_name": "string",
        "email": "string" (optional),
        "phone": "string" (optional)
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': 'No data provided'
            }), 400
        
        # Validate required fields
        required = ['username', 'password', 'first_name', 'last_name']
        for field in required:
            if not data.get(field, '').strip():
                return jsonify({
                    'success': False,
                    'message': f'{field.replace("_", " ").title()} is required'
                }), 400
        
        username = data['username'].strip()
        password = data['password']
        first_name = data['first_name'].strip()
        last_name = data['last_name'].strip()

        email = (data.get('email') or '').strip()
        if email:
            # Basic email format validation (kept intentionally simple)
            if len(email) > 254 or not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email, re.IGNORECASE):
                return jsonify({
                    'success': False,
                    'message': 'Invalid email address'
                }), 400
        
        # Validate username length
        if len(username) < 3:
            return jsonify({
                'success': False,
                'message': 'Username must be at least 3 characters'
            }), 400
        
        # Validate password length
        if len(password) < 8:
            return jsonify({
                'success': False,
                'message': 'Password must be at least 8 characters'
            }), 400

        # Validate password strength: uppercase, number, special character
        if not re.search(r'[A-Z]', password):
            return jsonify({
                'success': False,
                'message': 'Password must contain at least 1 uppercase letter'
            }), 400
        if not re.search(r'\d', password):
            return jsonify({
                'success': False,
                'message': 'Password must contain at least 1 number'
            }), 400
        if not re.search(r'[^A-Za-z0-9]', password):
            return jsonify({
                'success': False,
                'message': 'Password must contain at least 1 special character'
            }), 400
        
        # Check if username already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            return jsonify({
                'success': False,
                'message': 'Username already exists'
            }), 409
        
        # Validate phone number (optional): digits only, length 11-12
        phone = (data.get('phone') or '').strip()
        if phone:
            if not re.fullmatch(r'\d{11,12}', phone):
                return jsonify({
                    'success': False,
                    'message': 'Invalid phone number'
                }), 400

        # Create new user with pending status (is_active=False)
        user = User(
            username=username,
            first_name=first_name,
            last_name=last_name,
            password=password,
            role='cashier',  # Always register as cashier
            email=email or None,
            phone=phone or None,
            address=data.get('address', '').strip() or None,
            is_active=False  # Pending approval - cannot login until approved
        )
        
        db.session.add(user)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Account created successfully. Waiting for supervisor approval.',
            'data': {
                'user_id': user.id,
                'username': user.username,
                'status': 'pending'
            }
        }), 201
        
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Registration failed: {str(e)}'
        }), 500
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Registration failed: {str(e)}'
        }), 500


@auth_bp.route('/pending-accounts', methods=['GET'])
@jwt_required()
def get_pending_accounts():
    """Get all pending account approvals (supervisor only)"""
    try:
        claims = get_jwt()
        if claims.get('role') != 'supervisor':
            return jsonify({
                'success': False,
                'message': 'Supervisor access required'
            }), 403
        
        # Get all inactive users (pending approval)
        pending_users = User.query.filter_by(is_active=False, role='cashier').all()
        
        return jsonify({
            'success': True,
            'data': [{
                'id': user.id,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'full_name': user.full_name,
                'email': user.email,
                'phone': user.phone,
                'address': user.address,
                'created_at': user.created_at.isoformat() if user.created_at else None
            } for user in pending_users],
            'count': len(pending_users)
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Failed to get pending accounts: {str(e)}'
        }), 500


@auth_bp.route('/approve-account/<int:user_id>', methods=['POST'])
@jwt_required()
def approve_account(user_id):
    """Approve a pending account (supervisor only)"""
    try:
        claims = get_jwt()
        if claims.get('role') != 'supervisor':
            return jsonify({
                'success': False,
                'message': 'Supervisor access required'
            }), 403
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({
                'success': False,
                'message': 'User not found'
            }), 404
        
        if user.is_active:
            return jsonify({
                'success': False,
                'message': 'Account is already active'
            }), 400
        
        user.is_active = True
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Account for {user.full_name} has been approved',
            'data': user.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Failed to approve account: {str(e)}'
        }), 500


@auth_bp.route('/reject-account/<int:user_id>', methods=['POST'])
@jwt_required()
def reject_account(user_id):
    """Reject and delete a pending account (supervisor only)"""
    try:
        claims = get_jwt()
        if claims.get('role') != 'supervisor':
            return jsonify({
                'success': False,
                'message': 'Supervisor access required'
            }), 403
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({
                'success': False,
                'message': 'User not found'
            }), 404
        
        if user.is_active:
            return jsonify({
                'success': False,
                'message': 'Cannot reject an active account. Deactivate instead.'
            }), 400
        
        username = user.username
        full_name = user.full_name
        db.session.delete(user)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Account request for {full_name} ({username}) has been rejected'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Failed to reject account: {str(e)}'
        }), 500
