#!/usr/bin/env python3
"""
Example usage of the PDF Redactor library

This script demonstrates various ways to use the PDF redaction functionality.
"""

import os
import tempfile
from pathlib import Path

# Add the pdfredact module to path
import sys
sys.path.insert(0, "pdfredact")

try:
    import fitz  # PyMuPDF
    from pdfredact import (
        find_boxes, apply_boxes, hard_sanitize, 
        validate_pdf, get_pdf_info, verify_redaction,
        get_common_patterns, analyze_pdf_security
    )
    DEPS_AVAILABLE = True
except ImportError as e:
    print(f"Dependencies not available: {e}")
    print("Install with: pip install -r requirements.txt")
    DEPS_AVAILABLE = False


def create_sample_pdf(output_path: str) -> bool:
    """Create a sample PDF with sensitive content for testing"""
    try:
        doc = fitz.open()  # New PDF
        
        # Page 1: Mixed sensitive content
        page1 = doc.new_page()
        content1 = [
            "CONFIDENTIAL DOCUMENT",
            "",
            "Employee Information:",
            "Name: John Q. Public",
            "SSN: 123-45-6789", 
            "Email: john.public@company.com",
            "Phone: (555) 123-4567",
            "",
            "This document contains sensitive information.",
            "Handle with care and redact before sharing.",
        ]
        
        y_pos = 750
        for line in content1:
            page1.insert_text((72, y_pos), line, fontsize=12)
            y_pos -= 20
        
        # Page 2: More content
        page2 = doc.new_page()
        content2 = [
            "Additional Information",
            "",
            "Credit Card: 4532 1234 5678 9012",
            "Date of Birth: 01/15/1980",
            "Address: 123 Main St, Anytown, ST 12345",
            "",
            "INTERNAL USE ONLY",
            "Classification: SECRET",
        ]
        
        y_pos = 750
        for line in content2:
            page2.insert_text((72, y_pos), line, fontsize=12)
            y_pos -= 20
        
        # Save the PDF
        doc.save(output_path)
        doc.close()
        
        print(f"✓ Created sample PDF: {output_path}")
        return True
        
    except Exception as e:
        print(f"Error creating sample PDF: {e}")
        return False


def example_basic_redaction():
    """Demonstrate basic redaction functionality"""
    print("\n=== Basic Redaction Example ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create sample PDF
        input_pdf = os.path.join(temp_dir, "sample_input.pdf")
        output_pdf = os.path.join(temp_dir, "redacted_output.pdf")
        
        if not create_sample_pdf(input_pdf):
            return
        
        # Define content to redact
        terms_to_redact = [
            "John Q. Public",
            "CONFIDENTIAL",
            "SECRET",
            "INTERNAL USE ONLY"
        ]
        
        regex_patterns = [
            r"\b\d{3}-\d{2}-\d{4}\b",  # SSN
            r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",  # Email
            r"\b\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\b",  # Credit card
        ]
        
        print(f"Searching for {len(terms_to_redact)} terms and {len(regex_patterns)} patterns...")
        
        # Find content to redact
        boxes = find_boxes(
            input_pdf,
            terms=terms_to_redact,
            regex_patterns=regex_patterns,
            verbose=True
        )
        
        # Apply redactions
        temp_redacted = output_pdf + ".tmp"
        success = apply_boxes(input_pdf, temp_redacted, boxes, verbose=True)
        
        if success:
            # Sanitize the PDF
            success = hard_sanitize(temp_redacted, output_pdf, verbose=True)
            
            if success:
                print(f"✓ Redaction complete: {output_pdf}")
                
                # Verify redaction
                remaining = verify_redaction(output_pdf, terms_to_redact, regex_patterns)
                if remaining:
                    print(f"⚠️  Warning: {len(remaining)} items may not be fully redacted:")
                    for item in remaining:
                        print(f"   - {item}")
                else:
                    print("✓ Verification passed: no target content found in output")
        
        # Cleanup temp file
        if os.path.exists(temp_redacted):
            os.remove(temp_redacted)


def example_security_analysis():
    """Demonstrate PDF security analysis"""
    print("\n=== Security Analysis Example ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        input_pdf = os.path.join(temp_dir, "sample_for_analysis.pdf")
        
        if not create_sample_pdf(input_pdf):
            return
        
        # Analyze PDF security
        analysis = analyze_pdf_security(input_pdf)
        
        print("Security Analysis Results:")
        print(f"  Metadata found: {len(analysis['metadata_found'])} items")
        print(f"  JavaScript present: {analysis['javascript_found']}")
        print(f"  Embedded files: {analysis['embedded_files_count']}")
        print(f"  External links: {analysis['links_count']}")
        print(f"  Form fields: {analysis['forms_found']}")
        print(f"  Annotations: {analysis['annotations_count']}")
        
        if analysis['warnings']:
            print("  Warnings:")
            for warning in analysis['warnings']:
                print(f"    - {warning}")


def example_common_patterns():
    """Demonstrate using common regex patterns"""
    print("\n=== Common Patterns Example ===")
    
    patterns = get_common_patterns()
    
    print("Available common patterns:")
    for name, pattern in patterns.items():
        print(f"  {name}: {pattern}")
    
    # Test patterns with sample text
    sample_text = """
    Contact John at john@email.com or call (555) 123-4567.
    His SSN is 123-45-6789 and credit card is 4532 1234 5678 9012.
    IP address: 192.168.1.1, ZIP: 12345
    """
    
    print("\nTesting patterns against sample text:")
    import re
    for name, pattern in patterns.items():
        matches = re.findall(pattern, sample_text)
        if matches:
            print(f"  {name}: {matches}")


def example_pdf_info():
    """Demonstrate PDF information extraction"""
    print("\n=== PDF Info Example ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        input_pdf = os.path.join(temp_dir, "sample_info.pdf")
        
        if not create_sample_pdf(input_pdf):
            return
        
        # Get PDF information
        info = get_pdf_info(input_pdf)
        
        print("PDF Information:")
        print(f"  Valid: {info['valid']}")
        print(f"  Pages: {info['pages']}")
        print(f"  Encrypted: {info['encrypted']}")
        print(f"  File size: {info['file_size']} bytes")
        
        if info.get('title'):
            print(f"  Title: {info['title']}")
        if info.get('author'):
            print(f"  Author: {info['author']}")


def main():
    """Run all examples"""
    print("PDF Redactor - Example Usage")
    print("=" * 40)
    
    if not DEPS_AVAILABLE:
        print("Please install dependencies first:")
        print("pip install -r requirements.txt")
        return
    
    try:
        example_basic_redaction()
        example_security_analysis() 
        example_common_patterns()
        example_pdf_info()
        
        print("\n" + "=" * 40)
        print("All examples completed successfully!")
        print("\nFor command-line usage, try:")
        print("python pdfredact/cli.py --help")
        
    except Exception as e:
        print(f"Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()