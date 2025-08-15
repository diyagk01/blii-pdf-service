#!/usr/bin/env python3
"""
Docling PDF Extraction Service
A simplified Python microservice using Docling for PDF text extraction
"""

import os
import sys
import logging
import tempfile
import gc
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

# Install requirements if not already installed
try:
    from docling.document_converter import DocumentConverter
except ImportError:
    print("Installing docling...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "docling", "flask", "flask-cors", "requests"])
    from docling.document_converter import DocumentConverter

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for React Native

# Set memory optimization for PyTorch if available
try:
    import torch
    torch.set_grad_enabled(False)  # Disable gradients for inference
    os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "max_split_size_mb:64"
except ImportError:
    pass

# Lazy loading for Docling converter to reduce memory usage
_converter = None

def get_converter():
    """Get or create Docling converter singleton"""
    global _converter
    if _converter is None:
        logger.info("🔄 Initializing Docling DocumentConverter...")
        _converter = DocumentConverter()
        logger.info("✅ Docling DocumentConverter initialized")
    return _converter

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        import psutil
        memory_info = {
            'memory_percent': psutil.virtual_memory().percent,
            'memory_used_mb': psutil.virtual_memory().used // (1024 * 1024),
            'memory_available_mb': psutil.virtual_memory().available // (1024 * 1024)
        }
    except ImportError:
        memory_info = {'error': 'psutil not available'}
    
    return jsonify({
        'status': 'healthy',
        'service': 'docling_extraction_service',
        'docling_available': True,
        'memory': memory_info
    })

@app.route('/healthz', methods=['GET'])
def healthz():
    """Simple health check for Render"""
    return jsonify({"ok": True})

@app.route('/upload', methods=['POST'])
def upload_and_extract():
    """Upload and extract content from PDF file using Docling"""
    try:
        # Check if file was uploaded
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Check file extension
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({'error': 'Only PDF files are supported'}), 400
        
        logger.info(f"🔄 Processing uploaded PDF: {file.filename}")
        
        # Save uploaded file temporarily
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        file.save(temp_file.name)
        
        try:
            # Use Docling's conversion on the temp file
            converter = get_converter()
            result = converter.convert(temp_file.name)
            
            # Export to markdown - this is the main content
            markdown_content = result.document.export_to_markdown()
            
            # Extract title from filename if not available from document
            doc_title = file.filename.replace('.pdf', '').replace('_', ' ').replace('-', ' ').title()
            
            # Calculate basic statistics
            word_count = len(markdown_content.split())
            
            logger.info(f"✅ Successfully extracted {word_count} words from uploaded {file.filename}")
            
            # Force garbage collection to free memory
            gc.collect()
            
            return jsonify({
                'success': True,
                'title': doc_title,
                'content': markdown_content,
                'metadata': {
                    'filename': file.filename,
                    'word_count': word_count,
                    'character_count': len(markdown_content),
                    'extraction_method': 'docling_upload',
                },
                'extraction_confidence': 0.95
            })
            
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_file.name)
            except:
                pass
                
    except Exception as e:
        logger.error(f"❌ Upload extraction error: {e}")
        return jsonify({
            'error': f'PDF upload extraction failed: {str(e)}',
            'success': False
        }), 500

@app.route('/extract', methods=['POST'])
def extract_pdf_content():
    """Extract content from PDF using simple Docling approach"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        pdf_url = data.get('pdf_url')
        filename = data.get('filename', 'document.pdf')
        
        if not pdf_url:
            return jsonify({'error': 'pdf_url must be provided'}), 400
        
        logger.info(f"🔄 Processing PDF: {filename} from {pdf_url}")
        
        # Handle different URL types
        processed_url = process_pdf_url(pdf_url)
        
        if not processed_url:
            return jsonify({
                'error': f'Cannot access PDF file at: {pdf_url}',
                'success': False
            }), 400
        
        # Use Docling's conversion
        converter = get_converter()
        result = converter.convert(processed_url)
        
        # Export to markdown - this is the main content
        markdown_content = result.document.export_to_markdown()
        
        # Extract title from filename if not available from document
        doc_title = filename.replace('.pdf', '').replace('_', ' ').replace('-', ' ').title()
        
        # Calculate basic statistics
        word_count = len(markdown_content.split())
        
        logger.info(f"✅ Successfully extracted {word_count} words from {filename}")
        
        # Force garbage collection to free memory
        gc.collect()
        
        return jsonify({
            'success': True,
            'title': doc_title,
            'content': markdown_content,
            'metadata': {
                'filename': filename,
                'word_count': word_count,
                'character_count': len(markdown_content),
                'extraction_method': 'docling_simple',
            },
            'extraction_confidence': 0.95
        })
        
    except Exception as e:
        logger.error(f"❌ Extraction error: {e}")
        return jsonify({
            'error': f'PDF extraction failed: {str(e)}',
            'success': False
        }), 500

def process_pdf_url(pdf_url):
    """Process and validate PDF URL for different sources"""
    try:
        # Handle file:// URLs
        if pdf_url.startswith('file://'):
            file_path = pdf_url.replace('file://', '')
            logger.info(f"🔍 Checking file path: {file_path}")
            
            # Check if file exists
            if os.path.exists(file_path):
                logger.info(f"✅ File found at: {file_path}")
                return file_path
            else:
                logger.warning(f"❌ File not found at: {file_path}")
                return None
        
        # Handle HTTP/HTTPS URLs
        elif pdf_url.startswith(('http://', 'https://')):
            logger.info(f"🌐 Processing HTTP URL: {pdf_url}")
            return pdf_url
        
        # Handle direct file paths
        elif os.path.exists(pdf_url):
            logger.info(f"✅ Direct file path found: {pdf_url}")
            return pdf_url
        
        else:
            logger.warning(f"❌ Unsupported URL format: {pdf_url}")
            return None
            
    except Exception as e:
        logger.error(f"❌ Error processing URL: {e}")
        return None

@app.route('/batch_extract', methods=['POST'])
def batch_extract():
    """Extract content from multiple PDFs"""
    try:
        data = request.get_json()
        pdfs = data.get('pdfs', [])
        
        if not pdfs:
            return jsonify({'error': 'No PDFs provided'}), 400
        
        results = []
        
        for pdf_data in pdfs:
            try:
                # Process each PDF individually
                individual_result = extract_pdf_content()
                if individual_result[1] == 200:  # Success
                    results.append(individual_result[0].get_json())
                else:
                    results.append({
                        'success': False,
                        'error': individual_result[0].get_json().get('error'),
                        'filename': pdf_data.get('filename', 'unknown')
                    })
            except Exception as e:
                results.append({
                    'success': False,
                    'error': str(e),
                    'filename': pdf_data.get('filename', 'unknown')
                })
        
        return jsonify({
            'success': True,
            'results': results,
            'total_processed': len(results),
            'successful_extractions': len([r for r in results if r.get('success')])
        })
        
    except Exception as e:
        logger.error(f"❌ Batch extraction error: {e}")
        return jsonify({'error': str(e), 'success': False}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    debug_mode = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    logger.info(f"🚀 Starting Docling PDF Extraction Service on port {port}")
    logger.info(f"� Debug mode: {debug_mode}")
    logger.info(f"✅ Docling converter ready: {converter is not None}")
    
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
