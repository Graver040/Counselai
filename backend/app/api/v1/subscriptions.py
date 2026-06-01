from flask import Blueprint, jsonify

bp = Blueprint('subscriptions', __name__, url_prefix='/api/v1/subscriptions')

@bp.route('/')
def list_subs():
    return jsonify([])
