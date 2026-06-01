from flask import Blueprint, jsonify

bp = Blueprint('workspaces', __name__, url_prefix='/api/v1/workspaces')

@bp.route('/')
def list_workspaces():
    return jsonify([])
