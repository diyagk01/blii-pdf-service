#!/usr/bin/env python3
"""
Enhanced PDF Extraction Service
Implements multiple extraction strategies based on Ploomber's recommendations:
1. PyPDF2 for native/digital PDFs
2. pytesseract + pdf2image for scanned PDFs
3. Docling as fallback
"""

import os
import sys
import logging
import tempfile
import re
import base64
import io
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Check for PDF processing libraries
PYPDF2_AVAILABLE = False
PYTESSERACT_AVAILABLE = False
PDF2IMAGE_AVAILABLE = False
DOCLING_AVAILABLE = False
FITZ_AVAILABLE = False
PIL_AVAILABLE = False

try:
    from PyPDF2 import PdfReader
    PYPDF2_AVAILABLE = True
    logger.info("✅ PyPDF2 successfully imported")
except ImportError as e:
    logger.warning(f"⚠️ PyPDF2 not available: {e}")

try:
    import pytesseract
    from pdf2image import convert_from_path
    PYTESSERACT_AVAILABLE = True
    PDF2IMAGE_AVAILABLE = True
    logger.info("✅ pytesseract and pdf2image successfully imported")
except ImportError as e:
    logger.warning(f"⚠️ OCR libraries not available: {e}")

try:
    from docling.document_converter import DocumentConverter
    converter = DocumentConverter()
    DOCLING_AVAILABLE = True
    logger.info("✅ Docling successfully imported as fallback")
except ImportError as e:
    converter = None
    logger.warning(f"⚠️ Docling not available: {e}")

try:
    import fitz  # PyMuPDF
    FITZ_AVAILABLE = True
    logger.info("✅ PyMuPDF (fitz) successfully imported for preview generation")
except ImportError as e:
    logger.warning(f"⚠️ PyMuPDF not available for preview generation: {e}")

try:
    from PIL import Image
    PIL_AVAILABLE = True
    logger.info("✅ PIL successfully imported for image processing")
except ImportError as e:
    logger.warning(f"⚠️ PIL not available for image processing: {e}")

def clean_text_for_database(text):
    """Clean text to remove problematic characters for database storage"""
    if not text:
        return ""
    
    # Remove null bytes and control characters that cause database issues
    cleaned = re.sub(r'\x00', '', text)  # Remove null bytes
    cleaned = re.sub(r'[\x01-\x08\x0B\x0C\x0E-\x1F\x7F]', '', cleaned)  # Remove control chars
    cleaned = re.sub(r'\uFFFD', '', cleaned)  # Remove replacement characters
    cleaned = re.sub(r'[\uE000-\uF8FF]', '', cleaned)  # Remove private use area
    cleaned = re.sub(r'[\uFFF0-\uFFFF]', '', cleaned)  # Remove specials
    
    # Clean up common PDF artifacts
    cleaned = re.sub(r'\s+', ' ', cleaned)  # Multiple whitespace to single space
    cleaned = re.sub(r'([.!?])\s*([.!?])+', r'\1', cleaned)  # Remove repeated punctuation
    cleaned = re.sub(r'\s+([.!?,:;])', r'\1', cleaned)  # Remove space before punctuation
    
    return cleaned.strip()

def generate_pdf_preview_image(pdf_path):
    """Generate a preview image of the first page of a PDF"""
    try:
        if not FITZ_AVAILABLE or not PIL_AVAILABLE:
            logger.warning("⚠️ PyMuPDF or PIL not available for preview generation")
            return None
            
        logger.info(f"🖼️ Generating preview image for PDF: {pdf_path}")
        
        # Open PDF with PyMuPDF
        doc = fitz.open(pdf_path)
        
        if len(doc) == 0:
            logger.warning("⚠️ PDF has no pages")
            return None
            
        # Get the first page
        page = doc[0]
        
        # Create a matrix for rendering (scale for better quality)
        mat = fitz.Matrix(2.0, 2.0)  # 2x zoom for better quality
        
        # Render page to pixmap
        pix = page.get_pixmap(matrix=mat)
        
        # Convert to PIL Image
        img_data = pix.tobytes("png")
        img = Image.open(io.BytesIO(img_data))
        
        # Resize to a reasonable preview size (maintaining aspect ratio)
        max_width, max_height = 300, 400
        img.thumbnail((max_width, max_height), Image.LANCZOS)
        
        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG', quality=85)
        img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        # Clean up
        doc.close()
        
        preview_data_uri = f"data:image/png;base64,{img_base64}"
        logger.info("✅ PDF preview image generated successfully")
        return preview_data_uri
        
    except Exception as e:
        logger.error(f"❌ Error generating PDF preview image: {str(e)}")
        return None

def extract_with_pypdf2(pdf_path, filename):
    """Extract text from native PDF using PyPDF2"""
    try:
        logger.info(f"📄 Extracting text using PyPDF2 for: {filename}")
        
        reader = PdfReader(pdf_path)
        text_content = ""
        
        for page_num, page in enumerate(reader.pages):
            page_text = page.extract_text()
            if page_text.strip():
                text_content += f"\n--- Page {page_num + 1} ---\n"
                text_content += page_text + "\n"
        
        if not text_content.strip():
            raise Exception("No text found in PDF - may be scanned")
        
        # Clean the extracted text
        text_content = clean_text_for_database(text_content)
        
        # Extract title from first meaningful line
        lines = text_content.split('\n')
        title = filename.replace('.pdf', '')
        for line in lines[:10]:
            clean_line = line.strip()
            if len(clean_line) > 10 and len(clean_line) < 100:
                if not clean_line.isdigit() and 'Page' not in clean_line:
                    title = clean_line
                    break
        
        # Calculate basic metadata
        word_count = len(text_content.split())
        page_count = len(reader.pages)
        
        return {
            'success': True,
            'method': 'pypdf2',
            'title': clean_text_for_database(title),
            'content': text_content.strip(),
            'raw_text': text_content.strip(),
            'metadata': {
                'word_count': word_count,
                'page_count': page_count,
                'extraction_method': 'pypdf2_native',
                'filename': filename,
                'has_tables': False,
                'has_images': False,
            },
            'extraction_confidence': 0.95
        }
        
    except Exception as e:
        logger.error(f"❌ PyPDF2 extraction failed: {str(e)}")
        raise e

def extract_with_ocr(pdf_path, filename):
    """Extract text from scanned PDF using OCR (pdf2image + pytesseract)"""
    try:
        logger.info(f"🔍 Extracting text using OCR for: {filename}")
        
        # Convert PDF pages to images with high resolution for better OCR
        pages = convert_from_path(pdf_path, dpi=300)
        
        text_content = ""
        
        for page_num, page in enumerate(pages):
            logger.info(f"Processing page {page_num + 1} with OCR...")
            
            # Extract text from image using pytesseract with optimized config
            page_text = pytesseract.image_to_string(page, config='--psm 6 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz .,!?;:()')
            
            if page_text.strip():
                text_content += f"\n--- Page {page_num + 1} ---\n"
                text_content += page_text.strip() + "\n"
        
        if not text_content.strip():
            raise Exception("No text extracted from PDF using OCR")
        
        # Clean the extracted text
        text_content = clean_text_for_database(text_content)
        
        # Extract title from first meaningful line
        lines = text_content.split('\n')
        title = filename.replace('.pdf', '')
        for line in lines[:10]:
            clean_line = line.strip()
            if len(clean_line) > 10 and len(clean_line) < 100:
                if not clean_line.isdigit() and 'Page' not in clean_line:
                    title = clean_line
                    break
        
        # Calculate basic metadata
        word_count = len(text_content.split())
        page_count = len(pages)
        
        return {
            'success': True,
            'method': 'ocr_pytesseract',
            'title': clean_text_for_database(title),
            'content': text_content.strip(),
            'raw_text': text_content.strip(),
            'metadata': {
                'word_count': word_count,
                'page_count': page_count,
                'extraction_method': 'ocr_pytesseract',
                'filename': filename,
                'has_tables': False,
                'has_images': False,
            },
            'extraction_confidence': 0.85  # OCR is generally less confident
        }
        
    except Exception as e:
        logger.error(f"❌ OCR extraction failed: {str(e)}")
        raise e

def extract_with_docling(pdf_path, filename):
    """Extract text using Docling as fallback"""
    try:
        logger.info(f"📄 Extracting text using Docling for: {filename}")
        
        result = converter.convert(pdf_path)
        content = result.document.export_to_markdown()
        
        # Clean the extracted text
        content = clean_text_for_database(content)
        
        # Extract title
        lines = content.split('\n')
        title = filename.replace('.pdf', '')
        for line in lines[:5]:
            clean_line = line.strip().replace('#', '').strip()
            if len(clean_line) > 5 and len(clean_line) < 100:
                title = clean_line
                break
        
        # Calculate metadata
        word_count = len(content.split())
        page_count = len(result.document.pages) if hasattr(result.document, 'pages') else 1
        
        return {
            'success': True,
            'method': 'docling',
            'title': clean_text_for_database(title),
            'content': content.strip(),
            'raw_text': content.strip(),
            'metadata': {
                'word_count': word_count,
                'page_count': page_count,
                'extraction_method': 'docling',
                'filename': filename,
                'has_tables': any('|' in line for line in content.split('\n')),
                'has_images': '![' in content,
            },
            'extraction_confidence': 0.90
        }
        
    except Exception as e:
        logger.error(f"❌ Docling extraction failed: {str(e)}")
        raise e

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'pypdf2_available': PYPDF2_AVAILABLE,
        'ocr_available': PYTESSERACT_AVAILABLE and PDF2IMAGE_AVAILABLE,
        'docling_available': DOCLING_AVAILABLE,
        'service': 'Enhanced PDF Extraction Service'
    })

@app.route('/extract', methods=['POST'])
def extract_pdf():
    """Extract content from PDF file using multiple methods"""
    try:
        data = request.get_json()
        
        if not data or 'pdf_url' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing pdf_url in request'
            }), 400
        
        pdf_url = data['pdf_url']
        filename = data.get('filename', 'document.pdf')
        generate_preview = data.get('generate_preview', True)
        
        logger.info(f"📄 Processing PDF extraction request for: {filename}")
        logger.info(f"📂 PDF URL: {pdf_url}")
        logger.info(f"🖼️ Generate preview: {generate_preview}")
        
        # Create temporary directory for processing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Download or process the PDF file
            if pdf_url.startswith('http'):
                # Download from URL
                logger.info("⬇️ Downloading PDF from URL...")
                response = requests.get(pdf_url, stream=True, timeout=30)
                response.raise_for_status()
                
                pdf_path = os.path.join(temp_dir, filename)
                with open(pdf_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
            else:
                # Handle file:// URLs or local paths
                if pdf_url.startswith('file://'):
                    pdf_path = pdf_url.replace('file://', '')
                else:
                    pdf_path = pdf_url
                
                if not os.path.exists(pdf_path):
                    return jsonify({
                        'success': False,
                        'error': f'PDF file not found: {pdf_path}'
                    }), 404
            
            logger.info(f"📄 Processing PDF file: {pdf_path}")
            
            # Generate preview image if requested
            preview_image = None
            if generate_preview:
                preview_image = generate_pdf_preview_image(pdf_path)
            
            # Strategy 1: Try PyPDF2 first (for native PDFs)
            if PYPDF2_AVAILABLE:
                try:
                    result = extract_with_pypdf2(pdf_path, filename)
                    if preview_image:
                        result['preview_image'] = preview_image
                    logger.info(f"✅ PyPDF2 extraction successful")
                    return jsonify(result)
                except Exception as pypdf2_error:
                    logger.warning(f"⚠️ PyPDF2 failed, trying OCR: {str(pypdf2_error)}")
            
            # Strategy 2: Try OCR (for scanned PDFs)
            if PYTESSERACT_AVAILABLE and PDF2IMAGE_AVAILABLE:
                try:
                    result = extract_with_ocr(pdf_path, filename)
                    if preview_image:
                        result['preview_image'] = preview_image
                    logger.info(f"✅ OCR extraction successful")
                    return jsonify(result)
                except Exception as ocr_error:
                    logger.warning(f"⚠️ OCR failed, trying Docling: {str(ocr_error)}")
            
            # Strategy 3: Fallback to Docling (if available)
            if DOCLING_AVAILABLE:
                try:
                    result = extract_with_docling(pdf_path, filename)
                    if preview_image:
                        result['preview_image'] = preview_image
                    logger.info(f"✅ Docling extraction successful")
                    return jsonify(result)
                except Exception as docling_error:
                    logger.error(f"❌ Docling extraction also failed: {str(docling_error)}")
            
            # All methods failed
            return jsonify({
                'success': False,
                'error': 'All extraction methods failed. PDF may be corrupted or unsupported format.'
            }), 500
    
    except Exception as e:
        logger.error(f"❌ PDF extraction failed: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    debug_mode = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    logger.info(f"🚀 Starting Enhanced PDF Extraction Service on port {port}")
    logger.info(f"🔧 Debug mode: {debug_mode}")
    logger.info(f"📄 PyPDF2 available: {PYPDF2_AVAILABLE}")
    logger.info(f"🔍 OCR available: {PYTESSERACT_AVAILABLE and PDF2IMAGE_AVAILABLE}")
    logger.info(f"📚 Docling available: {DOCLING_AVAILABLE}")
    
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
