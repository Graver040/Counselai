from flask import Blueprint, jsonify

bp = Blueprint('users', __name__, url_prefix='/api/v1/users')

@bp.route('/')
def list_users():
    return jsonify([])
