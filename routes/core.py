
from flask import Blueprint, jsonify
from utils.backup import backup_database

core_bp = Blueprint('core', __name__)

@core_bp.route('/api/backup', methods=['POST'])
def manual_backup():
    path = backup_database()
    if path:
        return jsonify({'message': f'Backup created at {path}'}), 200
    return jsonify({'error': 'Backup failed'}), 500

@core_bp.route('/api/health')
def health_check():
    return {'status': 'healthy', 'message': 'Show Tracker API is running'}
