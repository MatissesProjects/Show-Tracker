
from flask import Blueprint, jsonify
from utils.analyzer import get_thematic_stats
from utils.collections import get_smart_collections

stats_bp = Blueprint('stats', __name__)

@stats_bp.route('/api/stats/thematic', methods=['GET'])
def get_thematic_stats_api():
    try:
        stats = get_thematic_stats()
        return jsonify(stats), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@stats_bp.route('/api/collections', methods=['GET'])
def get_collections_api():
    try:
        collections = get_smart_collections()
        return jsonify(collections), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
