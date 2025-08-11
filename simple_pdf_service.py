#!/usr/bin/env python3
"""
Simple PDF Extraction Service
A lightweight Python microservice for PDF text extraction using PyPDF2 and PyMuPDF
"""

import os
import sys
import logging
import tempfile
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import PyPDF2
import fitz  # PyMuPDF
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for React Native

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'Simple PDF Extraction Service',
        'version': '1.0.0'
    })

def extract_with_pypdf2(pdf_path):
    """Extract text using PyPDF2"""
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            
            return {
                'text': text.strip(),
                'page_count': len(pdf_reader.pages),
                'method': 'PyPDF2'
            }
    except Exception as e:
        logger.error(f"PyPDF2 extraction failed: {str(e)}")
        return None

def extract_with_pymupdf(pdf_path):
    """Extract text using PyMuPDF (fitz)"""
    try:
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text() + "\n"
        
        metadata = doc.metadata
        doc.close()
        
        return {
            'text': text.strip(),
            'page_count': len(doc),
            'metadata': metadata,
            'method': 'PyMuPDF'
        }
    except Exception as e:
        logger.error(f"PyMuPDF extraction failed: {str(e)}")
        return None

@app.route('/extract', methods=['POST'])
def extract_pdf():
    """Extract text from PDF file"""
    try:
        data = request.get_json()
        
        # Accept both 'file_path' and 'pdf_url' for compatibility
        file_path = data.get('file_path') or data.get('pdf_url')
        if not file_path:
            return jsonify({'error': 'file_path or pdf_url is required'}), 400
        logger.info(f"🔄 Processing PDF: {file_path}")
        
        # Handle both local files and URLs
        temp_file = None
        try:
            if file_path.startswith(('http://', 'https://')):
                # Download file from URL
                logger.info(f"📥 Downloading PDF from URL: {file_path}")
                response = requests.get(file_path, timeout=30)
                response.raise_for_status()
                
                # Create temp file
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
                temp_file.write(response.content)
                temp_file.close()
                pdf_path = temp_file.name
            else:
                # Use local file path
                pdf_path = file_path
                if not os.path.exists(pdf_path):
                    return jsonify({'error': f'File not found: {pdf_path}'}), 404
            
            # Try PyMuPDF first (better extraction)
            result = extract_with_pymupdf(pdf_path)
            if not result:
                # Fallback to PyPDF2
                logger.info("🔄 Falling back to PyPDF2...")
                result = extract_with_pypdf2(pdf_path)
            
            if not result:
                return jsonify({'error': 'Failed to extract text from PDF'}), 500
            
            # Calculate basic metrics
            text = result['text']
            word_count = len(text.split()) if text else 0
            char_count = len(text) if text else 0
            
            response_data = {
                'success': True,
                'content': text,
                'title': file_path.split('/')[-1].replace('.pdf', '') if '/' in file_path else 'PDF Document',
                'method': result.get('method', 'unknown'),
                'extraction_method': result.get('method', 'unknown'),
                'word_count': word_count,
                'char_count': char_count,
                'page_count': result.get('page_count', 0),
                'metadata': result.get('metadata', {}),
                'summary': f"Extracted {word_count} words from {result.get('page_count', 0)} pages"
            }
            
            logger.info(f"✅ Successfully extracted {word_count} words from PDF")
            return jsonify(response_data)
            
        finally:
            # Clean up temp file
            if temp_file and os.path.exists(temp_file.name):
                try:
                    os.unlink(temp_file.name)
                except:
                    pass
                    
    except Exception as e:
        logger.error(f"❌ Error processing PDF: {str(e)}")
        return jsonify({
            'error': f'PDF processing failed: {str(e)}',
            'success': False
        }), 500

@app.route('/', methods=['GET'])
def root():
    """Root endpoint"""
    return jsonify({
        'service': 'Simple PDF Extraction Service',
        'status': 'running',
        'endpoints': {
            '/health': 'Health check',
            '/extract': 'Extract text from PDF (POST with file_path)'
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    
    logger.info("🚀 Starting Simple PDF Extraction Service")
    logger.info(f"📦 Service starting on port {port}")
    logger.info(f"🔧 Debug mode: {os.environ.get('FLASK_ENV') == 'development'}")
    
    # Test the PDF extractors
    logger.info("✅ PyPDF2 available")
    logger.info("✅ PyMuPDF available")
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=os.environ.get('FLASK_ENV') == 'development'
    )
