"""
Basic tests for PDF redaction functionality
"""

import os
import tempfile
import unittest
from pathlib import Path

# Test if core dependencies are available
try:
    import fitz
    import pikepdf
    import click
    DEPS_AVAILABLE = True
except ImportError:
    DEPS_AVAILABLE = False

# Import our modules
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

if DEPS_AVAILABLE:
    from utils import validate_pdf, get_pdf_info, get_common_patterns
    from detect import find_boxes
    from sanitize import analyze_pdf_security
    from ocr import get_ocr_capabilities


class TestBasicFunctionality(unittest.TestCase):
    """Test basic functionality without requiring actual PDF files"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @unittest.skipUnless(DEPS_AVAILABLE, "Core dependencies not available")
    def test_common_patterns(self):
        """Test that common regex patterns are available"""
        patterns = get_common_patterns()
        
        self.assertIsInstance(patterns, dict)
        self.assertIn("ssn", patterns)
        self.assertIn("email", patterns)
        self.assertIn("phone", patterns)
        
        # Test SSN pattern
        import re
        ssn_pattern = patterns["ssn"]
        self.assertTrue(re.search(ssn_pattern, "123-45-6789"))
        self.assertFalse(re.search(ssn_pattern, "123456789"))  # Should not match without hyphens
    
    @unittest.skipUnless(DEPS_AVAILABLE, "Core dependencies not available")
    def test_ocr_capabilities(self):
        """Test OCR capability detection"""
        capabilities = get_ocr_capabilities()
        
        self.assertIsInstance(capabilities, dict)
        self.assertIn("opencv_available", capabilities)
        self.assertIn("tesseract_available", capabilities)
        self.assertIn("full_ocr_available", capabilities)
    
    @unittest.skipUnless(DEPS_AVAILABLE, "Core dependencies not available") 
    def test_validate_nonexistent_pdf(self):
        """Test PDF validation with non-existent file"""
        fake_path = os.path.join(self.temp_dir, "nonexistent.pdf")
        self.assertFalse(validate_pdf(fake_path))
    
    @unittest.skipUnless(DEPS_AVAILABLE, "Core dependencies not available")
    def test_create_minimal_pdf(self):
        """Test creating and validating a minimal PDF"""
        pdf_path = os.path.join(self.temp_dir, "test.pdf")
        
        # Create a minimal PDF with PyMuPDF
        doc = fitz.open()  # New empty PDF
        page = doc.new_page()
        page.insert_text((72, 72), "Test document with sensitive SSN: 123-45-6789")
        page.insert_text((72, 100), "Email: test@example.com")
        doc.save(pdf_path)
        doc.close()
        
        # Test validation
        self.assertTrue(validate_pdf(pdf_path))
        
        # Test PDF info
        info = get_pdf_info(pdf_path)
        self.assertTrue(info["valid"])
        self.assertEqual(info["pages"], 1)
        self.assertFalse(info["encrypted"])
        
        # Test content detection
        boxes = find_boxes(pdf_path, terms=["sensitive"], regex_patterns=[r"\d{3}-\d{2}-\d{4}"])
        self.assertIsInstance(boxes, dict)
        self.assertIn(1, boxes)  # Should have results for page 1
        
        # Test security analysis
        analysis = analyze_pdf_security(pdf_path)
        self.assertIsInstance(analysis, dict)
        self.assertIn("metadata_found", analysis)
        self.assertIn("javascript_found", analysis)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @unittest.skipUnless(DEPS_AVAILABLE, "Core dependencies not available")
    def test_empty_search_terms(self):
        """Test behavior with empty search terms"""
        pdf_path = os.path.join(self.temp_dir, "test.pdf")
        
        # Create minimal PDF
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), "Test content")
        doc.save(pdf_path)
        doc.close()
        
        # Test with empty terms
        boxes = find_boxes(pdf_path, terms=[], regex_patterns=[])
        self.assertIsInstance(boxes, dict)
        
        # Should have empty results
        for page_boxes in boxes.values():
            self.assertEqual(len(page_boxes), 0)
    
    @unittest.skipUnless(DEPS_AVAILABLE, "Core dependencies not available")
    def test_invalid_regex(self):
        """Test behavior with invalid regex patterns"""
        pdf_path = os.path.join(self.temp_dir, "test.pdf")
        
        # Create minimal PDF
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), "Test content")
        doc.save(pdf_path)
        doc.close()
        
        # Test with invalid regex (should not crash)
        boxes = find_boxes(pdf_path, terms=[], regex_patterns=["[invalid"])
        self.assertIsInstance(boxes, dict)


if __name__ == "__main__":
    if not DEPS_AVAILABLE:
        print("Warning: Core dependencies not available. Install with:")
        print("pip install PyMuPDF pikepdf click")
        print("Running limited tests...")
    
    unittest.main()