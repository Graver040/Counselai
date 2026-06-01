from flask import Blueprint, jsonify

bp = Blueprint('auth', __name__, url_prefix='/api/v1/auth')

@bp.route('/health')
def health():
    return jsonify({'status': 'auth ok'})
