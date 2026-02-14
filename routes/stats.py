
from flask import Blueprint, jsonify
from utils.analyzer import get_top_people, get_genre_stats, get_thematic_stats

stats_bp = Blueprint('stats', __name__)

@stats_bp.route('/api/stats/people', methods=['GET'])
def get_people_stats():
    try:
        stats = get_top_people()
        return jsonify(stats), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@stats_bp.route('/api/stats/genres', methods=['GET'])
def get_genre_stats_api():
    try:
        stats = get_genre_stats()
        return jsonify(stats), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@stats_bp.route('/api/stats/thematic', methods=['GET'])
def get_thematic_stats_api():
    try:
        stats = get_thematic_stats()
        return jsonify(stats), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
