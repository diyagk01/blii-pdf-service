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
    """Extract text using PyPDF2 with improved error handling"""
    try:
        # Check if file exists and is readable
        if not os.path.exists(pdf_path):
            logger.error(f"File does not exist: {pdf_path}")
            return None
            
        if os.path.getsize(pdf_path) == 0:
            logger.error(f"File is empty: {pdf_path}")
            return None
        
        with open(pdf_path, 'rb') as file:
            # Try to create PDF reader with error handling
            try:
                pdf_reader = PyPDF2.PdfReader(file, strict=False)  # Use non-strict mode
            except PyPDF2.errors.PdfReadError as pdf_error:
                logger.error(f"PyPDF2 failed to read PDF structure: {str(pdf_error)}")
                return None
            
            # Check if PDF is encrypted
            if pdf_reader.is_encrypted:
                logger.error("PDF is password protected")
                return None
            
            # Check if PDF has pages
            if len(pdf_reader.pages) == 0:
                logger.error("PDF has no pages")
                return None
            
            # Extract text page by page with error handling
            text = ""
            page_count = len(pdf_reader.pages)
            
            for page_num, page in enumerate(pdf_reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                except Exception as page_error:
                    logger.warning(f"Failed to extract text from page {page_num + 1}: {str(page_error)}")
                    continue
            
            return {
                'text': text.strip(),
                'page_count': page_count,
                'method': 'PyPDF2'
            }
            
    except Exception as e:
        error_msg = str(e).lower()
        if "eof" in error_msg or "marker" in error_msg:
            logger.error(f"PyPDF2 extraction failed - Truncated PDF: {str(e)}")
        elif "password" in error_msg or "encrypted" in error_msg:
            logger.error(f"PyPDF2 extraction failed - Password protected PDF: {str(e)}")
        else:
            logger.error(f"PyPDF2 extraction failed: {str(e)}")
        return None

def extract_with_pymupdf(pdf_path):
    """Extract text using PyMuPDF (fitz) with improved error handling"""
    doc = None
    try:
        # Check if file exists and is readable
        if not os.path.exists(pdf_path):
            logger.error(f"File does not exist: {pdf_path}")
            return None
            
        if os.path.getsize(pdf_path) == 0:
            logger.error(f"File is empty: {pdf_path}")
            return None
        
        # Try to open the document with error handling
        doc = fitz.open(pdf_path)
        
        # Check if document is valid
        if doc.is_closed:
            logger.error("Document was closed immediately after opening")
            return None
            
        if doc.page_count == 0:
            logger.error("Document has no pages")
            return None
        
        # Extract text page by page with error handling
        text = ""
        page_count = doc.page_count
        metadata = doc.metadata or {}
        
        for page_num in range(page_count):
            try:
                page = doc[page_num]
                page_text = page.get_text()
                if page_text:
                    text += page_text + "\n"
            except Exception as page_error:
                logger.warning(f"Failed to extract text from page {page_num + 1}: {str(page_error)}")
                continue
        
        return {
            'text': text.strip(),
            'page_count': page_count,
            'metadata': metadata,
            'method': 'PyMuPDF'
        }
        
    except Exception as e:
        error_msg = str(e).lower()
        if "broken" in error_msg or "corrupt" in error_msg:
            logger.error(f"PyMuPDF extraction failed - Corrupted PDF: {str(e)}")
        elif "password" in error_msg or "encrypted" in error_msg:
            logger.error(f"PyMuPDF extraction failed - Password protected PDF: {str(e)}")
        else:
            logger.error(f"PyMuPDF extraction failed: {str(e)}")
        return None
    finally:
        # Ensure document is properly closed
        if doc and not doc.is_closed:
            try:
                doc.close()
            except:
                pass

@app.route('/upload', methods=['POST'])
def upload_and_extract():
    """Upload and extract text from PDF file"""
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
        
        # Save uploaded file temporarily
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        file.save(temp_file.name)
        
        try:
            # Try PyMuPDF first (better extraction)
            result = extract_with_pymupdf(temp_file.name)
            if not result:
                # Fallback to PyPDF2
                logger.info("🔄 Falling back to PyPDF2...")
                result = extract_with_pypdf2(temp_file.name)
            
            if not result:
                return jsonify({'error': 'Failed to extract text from PDF'}), 500
            
            # Calculate basic metrics
            text = result['text']
            word_count = len(text.split()) if text else 0
            char_count = len(text) if text else 0
            
            response_data = {
                'success': True,
                'content': text,
                'title': file.filename.replace('.pdf', '') if file.filename else 'PDF Document',
                'method': result.get('method', 'unknown'),
                'extraction_method': result.get('method', 'unknown'),
                'word_count': word_count,
                'char_count': char_count,
                'page_count': result.get('page_count', 0),
                'metadata': result.get('metadata', {}),
                'summary': f"Extracted {word_count} words from {result.get('page_count', 0)} pages"
            }
            
            logger.info(f"✅ Successfully extracted {word_count} words from uploaded PDF: {file.filename}")
            return jsonify(response_data)
            
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_file.name)
            except:
                pass
                
    except Exception as e:
        logger.error(f"❌ Error processing uploaded PDF: {str(e)}")
        return jsonify({
            'error': f'PDF processing failed: {str(e)}',
            'success': False
        }), 500

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
                # Download file from URL with improved error handling
                logger.info(f"📥 Downloading PDF from URL: {file_path}")
                
                try:
                    response = requests.get(file_path, timeout=30, headers={
                        'User-Agent': 'Mozilla/5.0 (compatible; PDFExtractor/1.0)'
                    })
                    response.raise_for_status()
                    
                    # Check if response content is actually a PDF
                    content_type = response.headers.get('content-type', '').lower()
                    if content_type and 'pdf' not in content_type and not content_type.startswith('application/'):
                        logger.warning(f"Unexpected content type: {content_type}")
                    
                    # Check if we got actual content
                    if len(response.content) == 0:
                        return jsonify({'error': 'Downloaded file is empty'}), 400
                    
                    # Check for PDF magic number
                    if not response.content.startswith(b'%PDF'):
                        logger.warning("Downloaded content doesn't appear to be a valid PDF")
                    
                except requests.exceptions.RequestException as req_error:
                    logger.error(f"Failed to download PDF: {str(req_error)}")
                    return jsonify({'error': f'Failed to download PDF: {str(req_error)}'}), 400
                
                # Create temp file
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
                temp_file.write(response.content)
                temp_file.close()
                pdf_path = temp_file.name
                
            elif file_path.startswith('file://'):
                # Handle file:// URLs (local file paths from mobile apps)
                logger.info(f"🔄 Attempting to forward local file to Docling service: {file_path}")
                
                # Try to forward to Docling service if available
                try:
                    docling_url = os.environ.get('DOCLING_SERVICE_URL', 'https://blii-pdf-extraction-production.up.railway.app')
                    
                    # Check if Docling service is available
                    health_response = requests.get(f"{docling_url}/health", timeout=5)
                    if health_response.ok and health_response.json().get('docling_available'):
                        logger.info("✅ Docling service is available, suggesting file upload")
                        return jsonify({
                            'error': 'Local file paths require direct upload. Please use the upload endpoint or select the file again.',
                            'code': 'LOCAL_FILE_UPLOAD_REQUIRED',
                            'suggestion': 'Use the /upload endpoint with multipart/form-data to upload the file directly.',
                            'docling_available': True,
                            'upload_endpoint': f"{docling_url}/upload"
                        }), 400
                    else:
                        logger.warning("⚠️ Docling service not available")
                        return jsonify({
                            'error': 'Local file paths are not accessible from the server. Please upload the file directly.',
                            'code': 'LOCAL_FILE_ACCESS_DENIED',
                            'docling_available': False
                        }), 400
                        
                except Exception as docling_error:
                    logger.warning(f"⚠️ Could not reach Docling service: {docling_error}")
                    return jsonify({
                        'error': 'Local file paths are not accessible from the server. Please upload the file directly.',
                        'code': 'LOCAL_FILE_ACCESS_DENIED',
                        'docling_available': False
                    }), 400
                
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
            '/extract': 'Extract text from PDF (POST with file_path or pdf_url)',
            '/upload': 'Upload and extract text from PDF file (POST with multipart/form-data)'
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
