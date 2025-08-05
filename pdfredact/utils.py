"""
Utility functions for PDF redaction
"""

import fitz  # PyMuPDF
import re
import os
import subprocess
from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path


def validate_pdf(pdf_path: str) -> bool:
    """
    Validate that a file is a readable PDF
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        True if valid PDF, False otherwise
    """
    try:
        doc = fitz.open(pdf_path)
        # Try to access basic properties
        page_count = len(doc)
        doc.close()
        return page_count > 0
    except Exception:
        return False


def get_pdf_info(pdf_path: str) -> Dict[str, Any]:
    """
    Get basic information about a PDF
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        Dictionary with PDF information
    """
    info = {
        "valid": False,
        "pages": 0,
        "encrypted": False,
        "title": "",
        "author": "",
        "subject": "",
        "keywords": "",
        "creator": "",
        "producer": "",
        "creation_date": "",
        "modification_date": "",
        "file_size": 0
    }
    
    try:
        # File size
        info["file_size"] = os.path.getsize(pdf_path)
        
        doc = fitz.open(pdf_path)
        info["valid"] = True
        info["pages"] = len(doc)
        info["encrypted"] = doc.is_encrypted
        
        # Metadata
        metadata = doc.metadata
        if metadata:
            info["title"] = metadata.get("title", "")
            info["author"] = metadata.get("author", "")
            info["subject"] = metadata.get("subject", "")
            info["keywords"] = metadata.get("keywords", "")
            info["creator"] = metadata.get("creator", "")
            info["producer"] = metadata.get("producer", "")
            info["creation_date"] = metadata.get("creationDate", "")
            info["modification_date"] = metadata.get("modDate", "")
        
        doc.close()
        
    except Exception as e:
        info["error"] = str(e)
    
    return info


def verify_redaction(pdf_path: str, 
                    terms: List[str], 
                    regex_patterns: List[str]) -> List[str]:
    """
    Verify that redaction was successful by checking for remaining target content
    
    Args:
        pdf_path: Path to redacted PDF
        terms: List of terms that should be redacted
        regex_patterns: List of regex patterns that should be redacted
        
    Returns:
        List of terms/patterns still found in the document
    """
    remaining = []
    
    try:
        doc = fitz.open(pdf_path)
        
        # Extract all text from the document
        full_text = ""
        for page in doc:
            full_text += page.get_text() + "\n"
        
        doc.close()
        
        # Check for exact terms
        full_text_lower = full_text.lower()
        for term in terms:
            if term.lower() in full_text_lower:
                remaining.append(f"term: {term}")
        
        # Check for regex patterns
        for pattern in regex_patterns:
            try:
                if re.search(pattern, full_text, re.IGNORECASE | re.MULTILINE):
                    remaining.append(f"regex: {pattern}")
            except re.error:
                # Skip invalid regex patterns
                pass
                
    except Exception as e:
        remaining.append(f"verification_error: {e}")
    
    return remaining


def run_strings_check(pdf_path: str, 
                     terms: List[str],
                     min_length: int = 4) -> List[str]:
    """
    Run the 'strings' command on the PDF to check for hidden text
    
    Args:
        pdf_path: Path to PDF file
        terms: List of terms to search for
        min_length: Minimum string length for strings command
        
    Returns:
        List of terms found in strings output
    """
    found_terms = []
    
    try:
        # Run strings command
        result = subprocess.run(
            ["strings", "-n", str(min_length), pdf_path],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            strings_output = result.stdout.lower()
            
            # Check each term
            for term in terms:
                if term.lower() in strings_output:
                    found_terms.append(term)
        
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
        # strings command not available or failed
        pass
    
    return found_terms


def create_test_rectangles_json(output_path: str) -> None:
    """
    Create a sample rectangles JSON file for testing
    
    Args:
        output_path: Path where to save the JSON file
    """
    sample_rects = {
        "1": [
            {"x0": 72, "y0": 540, "x1": 320, "y1": 565},
            {"x0": 100, "y0": 100, "x1": 400, "y1": 130}
        ],
        "2": [
            {"x0": 50, "y0": 200, "x1": 250, "y1": 220}
        ],
        "3": [
            {"x0": 100, "y0": 700, "x1": 420, "y1": 740},
            {"x0": 72, "y0": 100, "x1": 300, "y1": 140}
        ]
    }
    
    import json
    with open(output_path, 'w') as f:
        json.dump(sample_rects, f, indent=2)


def estimate_redaction_impact(pdf_path: str,
                             terms: List[str],
                             regex_patterns: List[str]) -> Dict[str, Any]:
    """
    Estimate the impact of redaction without actually performing it
    
    Args:
        pdf_path: Path to PDF file
        terms: List of terms to redact
        regex_patterns: List of regex patterns to redact
        
    Returns:
        Dictionary with impact estimation
    """
    from detect import find_boxes, preview_matches
    
    impact = {
        "total_matches": 0,
        "pages_affected": 0,
        "matches_by_page": {},
        "matches_by_term": {},
        "matches_by_pattern": {},
        "estimated_text_removed_percent": 0.0
    }
    
    try:
        # Find all matches
        matches = preview_matches(pdf_path, terms, regex_patterns)
        impact["total_matches"] = len(matches)
        
        # Group by page
        pages_with_matches = set()
        for match in matches:
            page_num = match.page_num
            pages_with_matches.add(page_num)
            
            if page_num not in impact["matches_by_page"]:
                impact["matches_by_page"][page_num] = 0
            impact["matches_by_page"][page_num] += 1
        
        impact["pages_affected"] = len(pages_with_matches)
        
        # Group by term/pattern
        for match in matches:
            if match.match_type == "term":
                key = match.text
                if key not in impact["matches_by_term"]:
                    impact["matches_by_term"][key] = 0
                impact["matches_by_term"][key] += 1
            elif match.match_type == "regex":
                key = f"pattern_match: {match.text}"
                if key not in impact["matches_by_pattern"]:
                    impact["matches_by_pattern"][key] = 0
                impact["matches_by_pattern"][key] += 1
        
        # Estimate percentage of text that would be removed
        if matches:
            doc = fitz.open(pdf_path)
            total_text_length = 0
            removed_text_length = 0
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                page_text = page.get_text()
                total_text_length += len(page_text)
                
                # Estimate removed text for this page
                page_matches = [m for m in matches if m.page_num == page_num + 1]
                for match in page_matches:
                    removed_text_length += len(match.text)
            
            doc.close()
            
            if total_text_length > 0:
                impact["estimated_text_removed_percent"] = (removed_text_length / total_text_length) * 100
        
    except Exception as e:
        impact["error"] = str(e)
    
    return impact


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted size string
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def create_redaction_report(input_path: str,
                           output_path: str,
                           boxes_by_page: Dict[int, List],
                           terms: List[str],
                           regex_patterns: List[str]) -> Dict[str, Any]:
    """
    Create a detailed report of redaction activities
    
    Args:
        input_path: Path to input PDF
        output_path: Path to output PDF
        boxes_by_page: Redaction boxes applied
        terms: Terms that were redacted
        regex_patterns: Regex patterns that were redacted
        
    Returns:
        Dictionary with redaction report
    """
    report = {
        "input_file": input_path,
        "output_file": output_path,
        "timestamp": "",
        "redaction_summary": {
            "total_redactions": 0,
            "pages_modified": 0,
            "terms_searched": len(terms),
            "patterns_searched": len(regex_patterns)
        },
        "file_analysis": {
            "input_size": 0,
            "output_size": 0,
            "size_reduction": 0
        },
        "redaction_details": {},
        "verification": {}
    }
    
    try:
        import datetime
        report["timestamp"] = datetime.datetime.now().isoformat()
        
        # Calculate redaction summary
        total_redactions = sum(len(rects) for rects in boxes_by_page.values())
        pages_modified = len([p for p, rects in boxes_by_page.items() if rects])
        
        report["redaction_summary"]["total_redactions"] = total_redactions
        report["redaction_summary"]["pages_modified"] = pages_modified
        
        # File size analysis
        if os.path.exists(input_path):
            report["file_analysis"]["input_size"] = os.path.getsize(input_path)
        
        if os.path.exists(output_path):
            report["file_analysis"]["output_size"] = os.path.getsize(output_path)
            
            size_diff = (report["file_analysis"]["input_size"] - 
                        report["file_analysis"]["output_size"])
            report["file_analysis"]["size_reduction"] = size_diff
        
        # Redaction details by page
        for page_num, rects in boxes_by_page.items():
            if rects:
                report["redaction_details"][f"page_{page_num}"] = {
                    "redaction_count": len(rects),
                    "rectangles": [
                        {"x0": r.x0, "y0": r.y0, "x1": r.x1, "y1": r.y1} 
                        for r in rects
                    ]
                }
        
        # Verification
        if os.path.exists(output_path):
            remaining = verify_redaction(output_path, terms, regex_patterns)
            report["verification"]["remaining_terms"] = remaining
            report["verification"]["verification_passed"] = len(remaining) == 0
        
    except Exception as e:
        report["error"] = str(e)
    
    return report


def save_redaction_report(report: Dict[str, Any], report_path: str) -> bool:
    """
    Save redaction report to JSON file
    
    Args:
        report: Report dictionary
        report_path: Path to save report
        
    Returns:
        True if successful, False otherwise
    """
    try:
        import json
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        return True
    except Exception:
        return False


# Common regex patterns for PII detection
COMMON_PATTERNS = {
    "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
    "ssn_nohyphen": r"\b\d{9}\b",
    "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
    "phone": r"\b\(?(\d{3})\)?[-.\s]?(\d{3})[-.\s]?(\d{4})\b",
    "credit_card": r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",
    "ip_address": r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",
    "date": r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
    "zip_code": r"\b\d{5}(?:-\d{4})?\b",
}


def get_common_patterns() -> Dict[str, str]:
    """
    Get dictionary of common PII regex patterns
    
    Returns:
        Dictionary mapping pattern names to regex strings
    """
    return COMMON_PATTERNS.copy()