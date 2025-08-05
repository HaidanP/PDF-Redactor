"""
PDF Redactor - Securely remove sensitive content from PDFs

A tool for actually removing (not just covering) sensitive content from PDF files.
Includes support for text search, regex patterns, manual rectangles, and metadata sanitization.
"""

__version__ = "1.0.0"
__author__ = "PDF Redactor"
__email__ = ""

from .detect import find_boxes, preview_matches
from .redact import apply_boxes, apply_raster_redaction, preview_redactions
from .sanitize import hard_sanitize, analyze_pdf_security, quick_sanitize_metadata_only
from .utils import validate_pdf, get_pdf_info, verify_redaction, get_common_patterns
from .ocr import detect_text_in_scanned_pdf, is_scanned_pdf, get_ocr_capabilities

__all__ = [
    "find_boxes",
    "preview_matches", 
    "apply_boxes",
    "apply_raster_redaction",
    "preview_redactions",
    "hard_sanitize",
    "analyze_pdf_security",
    "quick_sanitize_metadata_only",
    "validate_pdf",
    "get_pdf_info",
    "verify_redaction",
    "get_common_patterns",
    "detect_text_in_scanned_pdf",
    "is_scanned_pdf",
    "get_ocr_capabilities"
]