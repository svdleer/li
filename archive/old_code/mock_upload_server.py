#!/usr/bin/env python3
"""
Mock EVE LI Upload API Server
==============================

A simple Flask server that simulates the EVE LI XML upload API endpoint
for local testing without needing access to the real upload server.

This server accepts XML file uploads and simulates the response,
allowing you to test the complete workflow locally.

Usage:
    python mock_upload_server.py

Then update your .env:
    UPLOAD_API_BASE_URL=http://localhost:2305
    UPLOAD_VERIFICATION_MODE=false

Author: Silvester van der Leer
Version: 1.0
"""

import os
import logging
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify, make_response
import gzip

# Initialize Flask app
app = Flask(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('mock_upload_api')

# Storage directory for uploaded files
UPLOAD_DIR = Path('mock_uploads')
UPLOAD_DIR.mkdir(exist_ok=True)


@app.route('/')
def index():
    """Root endpoint"""
    return jsonify({
        'service': 'Mock EVE LI Upload API',
        'version': '1.0',
        'status': 'running',
        'endpoints': {
            'upload': '/api/1/iaps/actions/import_xml/',
            'health': '/health'
        }
    })


@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/1/iaps/actions/import_xml/', methods=['POST'])
def import_xml():
    """
    Mock XML import endpoint
    Simulates the EVE LI XML upload API
    """
    try:
        # Log request details
        logger.info("=" * 60)
        logger.info("Received XML upload request")
        logger.info(f"Content-Type: {request.content_type}")
        logger.info(f"Content-Length: {request.content_length}")
        
        # Check authentication
        auth = request.authorization
        if auth:
            logger.info(f"Authentication: {auth.username}")
        else:
            logger.warning("No authentication provided")
        
        # Get uploaded file
        if 'file' not in request.files:
            logger.error("No file in request")
            return jsonify({
                'success': False,
                'error': 'No file provided'
            }), 400
        
        file = request.files['file']
        
        if file.filename == '':
            logger.error("Empty filename")
            return jsonify({
                'success': False,
                'error': 'Empty filename'
            }), 400
        
        # Generate timestamp for unique filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Determine if file is gzipped
        is_gzipped = file.filename.endswith('.gz')
        
        # Save the uploaded file
        save_filename = f"{timestamp}_{file.filename}"
        save_path = UPLOAD_DIR / save_filename
        file.save(save_path)
        
        file_size = save_path.stat().st_size
        logger.info(f"Saved file: {save_filename} ({file_size} bytes)")
        
        # If gzipped, also save decompressed version
        if is_gzipped:
            try:
                decompressed_path = UPLOAD_DIR / f"{timestamp}_{file.filename[:-3]}"
                with gzip.open(save_path, 'rb') as f_in:
                    with open(decompressed_path, 'wb') as f_out:
                        content = f_in.read()
                        f_out.write(content)
                
                decompressed_size = len(content)
                logger.info(f"Decompressed file: {decompressed_path.name} ({decompressed_size} bytes)")
                
                # Basic XML validation
                if content.startswith(b'<?xml') or content.startswith(b'<iaps'):
                    logger.info("✓ Valid XML structure detected")
                else:
                    logger.warning("⚠ Content does not appear to be XML")
                
            except Exception as e:
                logger.error(f"Failed to decompress: {e}")
        
        # Log success
        logger.info("✓ Upload processed successfully")
        logger.info("=" * 60)
        
        # Simulate successful response
        response_data = {
            'success': True,
            'message': 'XML file imported successfully (mock)',
            'filename': file.filename,
            'size': file_size,
            'timestamp': datetime.now().isoformat(),
            'storage_path': str(save_path),
            'note': 'This is a mock response - no actual processing was done'
        }
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Error processing upload: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/1/iaps/actions/import_xml/', methods=['GET'])
def import_xml_info():
    """Info about the upload endpoint"""
    return jsonify({
        'endpoint': '/api/1/iaps/actions/import_xml/',
        'method': 'POST',
        'description': 'Mock XML upload endpoint for testing',
        'accepts': 'multipart/form-data',
        'file_parameter': 'file',
        'authentication': 'Basic Auth (optional for mock)',
        'uploaded_files': len(list(UPLOAD_DIR.glob('*'))),
        'storage_directory': str(UPLOAD_DIR.absolute())
    })


@app.route('/api/1/uploads', methods=['GET'])
def list_uploads():
    """List all uploaded files"""
    files = []
    for file_path in sorted(UPLOAD_DIR.glob('*'), reverse=True):
        if file_path.is_file():
            stat = file_path.stat()
            files.append({
                'filename': file_path.name,
                'size': stat.st_size,
                'uploaded': datetime.fromtimestamp(stat.st_mtime).isoformat()
            })
    
    return jsonify({
        'count': len(files),
        'files': files
    })


@app.route('/api/1/uploads/clear', methods=['POST'])
def clear_uploads():
    """Clear all uploaded files"""
    try:
        count = 0
        for file_path in UPLOAD_DIR.glob('*'):
            if file_path.is_file():
                file_path.unlink()
                count += 1
        
        logger.info(f"Cleared {count} uploaded files")
        
        return jsonify({
            'success': True,
            'files_deleted': count
        })
    except Exception as e:
        logger.error(f"Error clearing uploads: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


if __name__ == '__main__':
    logger.info("=" * 60)
    logger.info("Starting Mock EVE LI Upload API Server")
    logger.info("=" * 60)
    logger.info(f"Upload storage: {UPLOAD_DIR.absolute()}")
    logger.info("")
    logger.info("Endpoints:")
    logger.info("  - http://localhost:2305/")
    logger.info("  - http://localhost:2305/health")
    logger.info("  - http://localhost:2305/api/1/iaps/actions/import_xml/  [POST]")
    logger.info("  - http://localhost:2305/api/1/uploads  [GET]")
    logger.info("  - http://localhost:2305/api/1/uploads/clear  [POST]")
    logger.info("")
    logger.info("Update your .env file:")
    logger.info("  UPLOAD_API_BASE_URL=http://localhost:2305")
    logger.info("  UPLOAD_VERIFICATION_MODE=false")
    logger.info("")
    logger.info("=" * 60)
    
    # Run server
    app.run(
        host='127.0.0.1',
        port=2305,
        debug=False
    )
