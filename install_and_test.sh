#!/bin/bash

echo "=== PDF Redactor Installation and Test Script ==="
echo

# Check Python version
echo "Checking Python version..."
python3 --version
echo

# Install core dependencies
echo "Installing core dependencies..."
pip3 install PyMuPDF>=1.23.0 pikepdf>=8.0.0 click>=8.0.0
echo

# Test core functionality
echo "Testing core functionality..."
python3 -c "
import sys
sys.path.insert(0, 'pdfredact')
try:
    from utils import get_common_patterns, validate_pdf
    from detect import find_boxes
    from sanitize import analyze_pdf_security
    from redact import apply_boxes
    print('✓ All core modules imported successfully')
    
    patterns = get_common_patterns()
    print(f'✓ Found {len(patterns)} common PII patterns')
    
    print('✓ Installation complete!')
    print()
    print('Try these commands:')
    print('  python3 pdfredact/cli.py --help')
    print('  python3 example_usage.py')
    
except ImportError as e:
    print(f'✗ Import error: {e}')
    print('Please check the installation')
except Exception as e:
    print(f'✗ Error: {e}')
"

echo
echo "=== Optional OCR Dependencies ==="
echo "For scanned PDF support, install:"
echo "  pip3 install opencv-python pytesseract pillow"
echo
echo "Note: You may also need to install Tesseract OCR system package:"
echo "  macOS: brew install tesseract"
echo "  Ubuntu: sudo apt-get install tesseract-ocr"
echo "  Windows: Download from https://github.com/tesseract-ocr/tesseract"