from flask import Blueprint, jsonify

bp = Blueprint('chat', __name__, url_prefix='/api/v1/chat')

@bp.route('/health')
def health():
    return jsonify({'status': 'chat ok'})
