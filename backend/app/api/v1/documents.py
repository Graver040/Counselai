from flask import Blueprint, jsonify

bp = Blueprint('documents', __name__, url_prefix='/api/v1/documents')

@bp.route('/')
def list_docs():
    return jsonify([])
