from flask import Blueprint, jsonify

bp = Blueprint('drafts', __name__, url_prefix='/api/v1/drafts')

@bp.route('/')
def list_drafts():
    return jsonify([])
