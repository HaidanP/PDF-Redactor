"""
Content Detection Module - Find text, patterns, and regions to redact
"""

import re
import json
import fitz  # PyMuPDF
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class TextMatch:
    """Represents a text match with its location"""
    text: str
    rect: fitz.Rect
    page_num: int
    match_type: str  # 'term', 'regex'


def _normalize_rect_coordinates(rect: fitz.Rect, page: fitz.Page) -> fitz.Rect:
    """
    Normalize rectangle coordinates to handle page rotation and transforms
    """
    # Get page transformation matrix
    matrix = page.transformation_matrix
    
    # If page is rotated, we need to transform coordinates
    if page.rotation != 0:
        # Apply inverse transformation to get proper coordinates
        return rect * ~matrix
    
    return rect


def _page_search_boxes(page: fitz.Page, term: str, page_num: int) -> List[TextMatch]:
    """
    Search for exact text terms on a page and return bounding boxes
    """
    matches = []
    
    # Use PyMuPDF's built-in search - it handles text spans properly
    rects = page.search_for(term, quads=False)
    
    for rect in rects:
        # Normalize coordinates for page rotation
        normalized_rect = _normalize_rect_coordinates(rect, page)
        matches.append(TextMatch(
            text=term,
            rect=normalized_rect,
            page_num=page_num,
            match_type='term'
        ))
    
    return matches


def _page_regex_boxes(page: fitz.Page, pattern: str, page_num: int) -> List[TextMatch]:
    """
    Search for regex patterns on a page and return bounding boxes
    
    This is more complex because we need to map regex matches back to 
    character positions and then to coordinates.
    """
    matches = []
    
    try:
        compiled_pattern = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
    except re.error as e:
        print(f"Warning: Invalid regex pattern '{pattern}': {e}")
        return matches
    
    # Get text blocks with position information
    blocks = page.get_text("dict")
    
    for block in blocks["blocks"]:
        if "lines" not in block:
            continue
            
        for line in block["lines"]:
            # Reconstruct line text and track character positions
            line_text = ""
            char_rects = []
            
            for span in line["spans"]:
                span_text = span["text"]
                span_bbox = fitz.Rect(span["bbox"])
                
                # Approximate character positions within the span
                if span_text:
                    char_width = span_bbox.width / len(span_text)
                    for i, char in enumerate(span_text):
                        char_rect = fitz.Rect(
                            span_bbox.x0 + i * char_width,
                            span_bbox.y0,
                            span_bbox.x0 + (i + 1) * char_width,
                            span_bbox.y1
                        )
                        char_rects.append(char_rect)
                        line_text += char
            
            # Find regex matches in the line text
            for match in compiled_pattern.finditer(line_text):
                start, end = match.span()
                
                # Get bounding box by unioning character rectangles
                if start < len(char_rects) and end <= len(char_rects):
                    match_rect = char_rects[start]
                    for i in range(start + 1, end):
                        match_rect = match_rect | char_rects[i]
                    
                    # Normalize coordinates
                    normalized_rect = _normalize_rect_coordinates(match_rect, page)
                    
                    matches.append(TextMatch(
                        text=match.group(),
                        rect=normalized_rect,
                        page_num=page_num,
                        match_type='regex'
                    ))
    
    return matches


def _is_scanned_page(page: fitz.Page) -> bool:
    """
    Determine if a page is scanned (image-based) by checking for extractable text
    """
    text = page.get_text().strip()
    return len(text) < 10  # Threshold for considering a page "text-less"


def _get_page_type(doc: fitz.Document) -> Dict[int, str]:
    """
    Classify each page as 'text' or 'scanned'
    """
    page_types = {}
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        if _is_scanned_page(page):
            page_types[page_num + 1] = 'scanned'
        else:
            page_types[page_num + 1] = 'text'
    
    return page_types


def find_boxes(pdf_path: str, 
               terms: Optional[List[str]] = None,
               regex_patterns: Optional[List[str]] = None,
               rects_path: Optional[str] = None,
               verbose: bool = False) -> Dict[int, List[fitz.Rect]]:
    """
    Find all content to redact and return bounding boxes organized by page
    
    Args:
        pdf_path: Path to input PDF
        terms: List of exact text terms to find
        regex_patterns: List of regex patterns to match
        rects_path: Path to JSON file with user-specified rectangles
        verbose: Enable verbose output
        
    Returns:
        Dictionary mapping page numbers to lists of rectangles to redact
    """
    terms = terms or []
    regex_patterns = regex_patterns or []
    
    all_matches = []
    page_boxes = {}
    
    try:
        doc = fitz.open(pdf_path)
        
        # Classify pages
        page_types = _get_page_type(doc)
        if verbose:
            text_pages = sum(1 for t in page_types.values() if t == 'text')
            scanned_pages = sum(1 for t in page_types.values() if t == 'scanned')
            print(f"Document analysis: {text_pages} text pages, {scanned_pages} scanned pages")
        
        # Initialize page boxes
        for i in range(len(doc)):
            page_boxes[i + 1] = []
        
        # Search text-based pages
        for page_num in range(len(doc)):
            page = doc[page_num]
            page_number = page_num + 1
            
            if page_types[page_number] == 'scanned':
                if verbose:
                    print(f"Skipping scanned page {page_number} (use OCR mode for text detection)")
                continue
            
            page_matches = []
            
            # Search for exact terms
            for term in terms:
                matches = _page_search_boxes(page, term, page_number)
                page_matches.extend(matches)
                all_matches.extend(matches)
            
            # Search for regex patterns
            for pattern in regex_patterns:
                matches = _page_regex_boxes(page, pattern, page_number)
                page_matches.extend(matches)
                all_matches.extend(matches)
            
            # Convert matches to rectangles
            page_boxes[page_number] = [match.rect for match in page_matches]
            
            if verbose and page_matches:
                print(f"Page {page_number}: found {len(page_matches)} matches")
        
        doc.close()
        
    except Exception as e:
        print(f"Error processing PDF: {e}")
        return {}
    
    # Load user-specified rectangles if provided
    if rects_path:
        try:
            with open(rects_path, 'r') as f:
                user_rects = json.load(f)
            
            for page_str, rect_dicts in user_rects.items():
                page_num = int(page_str)
                if page_num in page_boxes:
                    for rect_dict in rect_dicts:
                        rect = fitz.Rect(
                            rect_dict["x0"], 
                            rect_dict["y0"], 
                            rect_dict["x1"], 
                            rect_dict["y1"]
                        )
                        page_boxes[page_num].append(rect)
            
            if verbose:
                total_user_rects = sum(len(rects) for rects in user_rects.values())
                print(f"Added {total_user_rects} user-specified rectangles")
                
        except Exception as e:
            print(f"Error loading rectangles from {rects_path}: {e}")
    
    # Summary
    if verbose:
        total_boxes = sum(len(rects) for rects in page_boxes.values())
        pages_with_redactions = len([p for p, rects in page_boxes.items() if rects])
        print(f"Total: {total_boxes} redaction areas across {pages_with_redactions} pages")
    
    return page_boxes


def preview_matches(pdf_path: str, 
                   terms: Optional[List[str]] = None,
                   regex_patterns: Optional[List[str]] = None) -> List[TextMatch]:
    """
    Preview what would be redacted without actually redacting
    Useful for verification and debugging
    """
    terms = terms or []
    regex_patterns = regex_patterns or []
    all_matches = []
    
    try:
        doc = fitz.open(pdf_path)
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            page_number = page_num + 1
            
            # Skip scanned pages for text search
            if _is_scanned_page(page):
                continue
            
            # Search for terms
            for term in terms:
                matches = _page_search_boxes(page, term, page_number)
                all_matches.extend(matches)
            
            # Search for regex patterns
            for pattern in regex_patterns:
                matches = _page_regex_boxes(page, pattern, page_number)
                all_matches.extend(matches)
        
        doc.close()
        
    except Exception as e:
        print(f"Error previewing matches: {e}")
    
    return all_matches