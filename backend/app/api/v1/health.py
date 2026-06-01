from flask import Blueprint, jsonify

bp = Blueprint('health', __name__, url_prefix='/api/v1/health')

@bp.route('/')
def health():
    return jsonify({'status': 'ok'})
