
from flask import Blueprint, jsonify
from utils.analyzer import get_thematic_stats

stats_bp = Blueprint('stats', __name__)

@stats_bp.route('/api/stats/thematic', methods=['GET'])
def get_thematic_stats_api():
    try:
        stats = get_thematic_stats()
        return jsonify(stats), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
