"""
Redaction Application Module - Apply redactions to remove content
"""

import fitz  # PyMuPDF
from typing import Dict, List, Tuple, Optional


def _get_fill_color(fill: str) -> Tuple[float, float, float]:
    """
    Convert fill color name to RGB tuple
    """
    colors = {
        "black": (0.0, 0.0, 0.0),
        "white": (1.0, 1.0, 1.0),
        "red": (1.0, 0.0, 0.0),
        "blue": (0.0, 0.0, 1.0),
        "green": (0.0, 1.0, 0.0),
        "gray": (0.5, 0.5, 0.5),
        "grey": (0.5, 0.5, 0.5),
    }
    
    return colors.get(fill.lower(), (0.0, 0.0, 0.0))  # Default to black


def _merge_overlapping_rects(rects: List[fitz.Rect], 
                           overlap_threshold: float = 0.1) -> List[fitz.Rect]:
    """
    Merge overlapping or nearby rectangles to avoid redundant redactions
    
    Args:
        rects: List of rectangles to merge
        overlap_threshold: Minimum overlap ratio to trigger merge
        
    Returns:
        List of merged rectangles
    """
    if not rects:
        return []
    
    # Sort rectangles by position (top-left to bottom-right)
    sorted_rects = sorted(rects, key=lambda r: (r.y0, r.x0))
    merged = [sorted_rects[0]]
    
    for current in sorted_rects[1:]:
        merged_any = False
        
        for i, existing in enumerate(merged):
            # Check if rectangles overlap or are very close
            intersection = existing & current
            union = existing | current
            
            if intersection.is_empty:
                # Check if they're close enough to merge (within a small distance)
                if (abs(existing.x1 - current.x0) < 5 or 
                    abs(existing.x0 - current.x1) < 5 or
                    abs(existing.y1 - current.y0) < 5 or 
                    abs(existing.y0 - current.y1) < 5):
                    merged[i] = union
                    merged_any = True
                    break
            else:
                # Calculate overlap ratio
                overlap_ratio = intersection.get_area() / min(existing.get_area(), current.get_area())
                if overlap_ratio > overlap_threshold:
                    merged[i] = union
                    merged_any = True
                    break
        
        if not merged_any:
            merged.append(current)
    
    return merged


def _validate_rectangles(rects: List[fitz.Rect], page: fitz.Page) -> List[fitz.Rect]:
    """
    Validate and clip rectangles to page boundaries
    """
    page_rect = page.rect
    valid_rects = []
    
    for rect in rects:
        # Clip to page boundaries
        clipped = rect & page_rect
        
        # Only keep rectangles with meaningful area
        if not clipped.is_empty and clipped.get_area() > 1:
            valid_rects.append(clipped)
    
    return valid_rects


def apply_boxes(input_path: str, 
                output_path: str, 
                boxes_by_page: Dict[int, List[fitz.Rect]], 
                fill: str = "black",
                merge_overlaps: bool = True,
                verbose: bool = False) -> bool:
    """
    Apply redaction boxes to a PDF, removing underlying content
    
    Args:
        input_path: Path to input PDF
        output_path: Path to output PDF
        boxes_by_page: Dictionary mapping page numbers to redaction rectangles
        fill: Fill color for redacted areas
        merge_overlaps: Whether to merge overlapping rectangles
        verbose: Enable verbose output
        
    Returns:
        True if successful, False otherwise
    """
    try:
        doc = fitz.open(input_path)
        fill_color = _get_fill_color(fill)
        total_redactions = 0
        
        for page_num, rects in boxes_by_page.items():
            if not rects:
                continue
                
            # Page numbers are 1-based in our API, 0-based in PyMuPDF
            if page_num < 1 or page_num > len(doc):
                if verbose:
                    print(f"Warning: Page {page_num} out of range, skipping")
                continue
                
            page = doc[page_num - 1]
            
            # Validate rectangles
            valid_rects = _validate_rectangles(rects, page)
            
            if not valid_rects:
                if verbose:
                    print(f"Page {page_num}: No valid rectangles to redact")
                continue
            
            # Merge overlapping rectangles if requested
            if merge_overlaps:
                valid_rects = _merge_overlapping_rects(valid_rects)
            
            # Apply redaction annotations
            redaction_count = 0
            for rect in valid_rects:
                try:
                    # Add redaction annotation
                    # The fill parameter sets the color of the redacted area
                    annot = page.add_redact_annot(rect, fill=fill_color)
                    
                    # Optional: add a label or cross-out pattern
                    # annot.set_info(title="REDACTED")
                    
                    redaction_count += 1
                    
                except Exception as e:
                    if verbose:
                        print(f"Warning: Failed to add redaction annotation: {e}")
            
            # Apply all redactions on this page
            # This actually removes the content underneath
            if redaction_count > 0:
                page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_REMOVE)
                total_redactions += redaction_count
                
                if verbose:
                    print(f"Page {page_num}: Applied {redaction_count} redactions")
        
        # Save the redacted document
        # Use garbage collection and compression for smaller file size
        doc.save(
            output_path,
            garbage=4,  # Remove unused objects
            deflate=True,  # Compress streams
            clean=True,  # Clean up the file structure
            pretty=False,  # Don't format for readability (smaller file)
            linear=False,  # Don't linearize (we'll do final optimization later)
        )
        
        doc.close()
        
        if verbose:
            print(f"Applied {total_redactions} total redactions")
        
        return True
        
    except Exception as e:
        print(f"Error applying redactions: {e}")
        return False


def apply_raster_redaction(input_path: str,
                          output_path: str, 
                          boxes_by_page: Dict[int, List[fitz.Rect]],
                          dpi: int = 300,
                          fill: str = "black",
                          verbose: bool = False) -> bool:
    """
    Apply redactions by rasterizing pages and drawing filled rectangles
    
    This is useful for scanned PDFs or when you want to ensure complete
    removal of content by converting pages to images.
    
    Args:
        input_path: Path to input PDF
        output_path: Path to output PDF  
        boxes_by_page: Dictionary mapping page numbers to redaction rectangles
        dpi: Resolution for rasterization
        fill: Fill color for redacted areas
        verbose: Enable verbose output
        
    Returns:
        True if successful, False otherwise
    """
    try:
        doc = fitz.open(input_path)
        fill_color = _get_fill_color(fill)
        
        # Convert fill color to 255-based RGB for image operations
        fill_rgb = tuple(int(c * 255) for c in fill_color)
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            page_number = page_num + 1
            
            rects = boxes_by_page.get(page_number, [])
            if not rects:
                continue
            
            # Render page to image
            mat = fitz.Matrix(dpi / 72, dpi / 72)  # Scale matrix for DPI
            pix = page.get_pixmap(matrix=mat, alpha=False)
            
            # Convert to PIL Image for easier manipulation
            img_data = pix.tobytes("ppm")
            
            # Draw filled rectangles over redaction areas
            # Scale rectangles to match the image DPI
            scale = dpi / 72
            
            for rect in rects:
                # Scale rectangle coordinates
                x0 = int(rect.x0 * scale)
                y0 = int(rect.y0 * scale)
                x1 = int(rect.x1 * scale)
                y1 = int(rect.y1 * scale)
                
                # Draw filled rectangle directly on pixmap
                # Note: This is a simplified approach - for production,
                # you might want to use PIL or OpenCV for better drawing
                draw_rect = fitz.Rect(x0, y0, x1, y1)
                pix.set_rect(draw_rect, fill_rgb)
            
            # Replace page content with the rasterized image
            page.clean_contents()  # Remove existing content
            
            # Insert the modified image
            img_rect = page.rect
            page.insert_image(img_rect, pixmap=pix)
            
            if verbose:
                print(f"Page {page_number}: Rasterized with {len(rects)} redactions at {dpi} DPI")
        
        # Save the document
        doc.save(
            output_path,
            garbage=4,
            deflate=True,
            clean=True
        )
        
        doc.close()
        
        if verbose:
            total_redactions = sum(len(rects) for rects in boxes_by_page.values())
            print(f"Raster redaction complete: {total_redactions} areas redacted")
        
        return True
        
    except Exception as e:
        print(f"Error applying raster redactions: {e}")
        return False


def preview_redactions(input_path: str, 
                      boxes_by_page: Dict[int, List[fitz.Rect]],
                      output_path: str,
                      highlight_color: Tuple[float, float, float] = (1.0, 1.0, 0.0)) -> bool:
    """
    Create a preview PDF showing what will be redacted (highlighted, not removed)
    
    Args:
        input_path: Path to input PDF
        boxes_by_page: Dictionary mapping page numbers to redaction rectangles
        output_path: Path to preview PDF
        highlight_color: RGB color for highlighting (default: yellow)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        doc = fitz.open(input_path)
        
        for page_num, rects in boxes_by_page.items():
            if not rects or page_num < 1 or page_num > len(doc):
                continue
                
            page = doc[page_num - 1]
            
            # Add highlight annotations instead of redactions
            for rect in rects:
                # Add a semi-transparent highlight
                annot = page.add_highlight_annot(rect)
                annot.set_colors({"stroke": highlight_color, "fill": highlight_color})
                annot.set_opacity(0.5)
                annot.update()
        
        doc.save(output_path)
        doc.close()
        
        return True
        
    except Exception as e:
        print(f"Error creating redaction preview: {e}")
        return False