"""
OCR Module - Handle scanned PDFs with text detection
"""

import fitz  # PyMuPDF
from typing import List, Dict, Optional, Tuple
import tempfile
import os

try:
    import cv2
    import numpy as np
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False

try:
    import pytesseract
    from PIL import Image
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False


class OCRConfig:
    """Configuration for OCR processing"""
    def __init__(self):
        self.dpi = 300
        self.tesseract_config = "--oem 3 --psm 6"  # OCR Engine Mode 3, Page Segmentation Mode 6
        self.confidence_threshold = 30  # Minimum confidence for text detection
        self.preprocessing = True  # Apply image preprocessing


def _check_dependencies() -> Tuple[bool, List[str]]:
    """
    Check if OCR dependencies are available
    
    Returns:
        Tuple of (all_available, missing_dependencies)
    """
    missing = []
    
    if not OPENCV_AVAILABLE:
        missing.append("opencv-python")
    
    if not TESSERACT_AVAILABLE:
        missing.append("pytesseract and Pillow")
    
    return len(missing) == 0, missing


def _preprocess_image(image_array: np.ndarray) -> np.ndarray:
    """
    Preprocess image for better OCR results
    
    Args:
        image_array: Input image as numpy array
        
    Returns:
        Preprocessed image
    """
    if not OPENCV_AVAILABLE:
        return image_array
    
    # Convert to grayscale if needed
    if len(image_array.shape) == 3:
        gray = cv2.cvtColor(image_array, cv2.COLOR_RGB2GRAY)
    else:
        gray = image_array
    
    # Apply adaptive thresholding to handle varying lighting
    thresh = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )
    
    # Remove noise with morphological operations
    kernel = np.ones((1, 1), np.uint8)
    cleaned = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
    cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, kernel)
    
    return cleaned


def _extract_text_with_boxes(pix: fitz.Pixmap, 
                           config: OCRConfig) -> List[Dict]:
    """
    Extract text and bounding boxes from a pixmap using OCR
    
    Args:
        pix: PyMuPDF pixmap
        config: OCR configuration
        
    Returns:
        List of text boxes with coordinates and text
    """
    if not TESSERACT_AVAILABLE:
        return []
    
    try:
        # Convert pixmap to PIL Image
        img_data = pix.tobytes("ppm")
        image = Image.open(tempfile.NamedTemporaryFile(delete=False, suffix=".ppm"))
        with open(image.name, "wb") as f:
            f.write(img_data)
        image = Image.open(image.name)
        
        # Preprocess if OpenCV is available
        if config.preprocessing and OPENCV_AVAILABLE:
            img_array = np.array(image)
            img_array = _preprocess_image(img_array)
            image = Image.fromarray(img_array)
        
        # Run OCR with detailed output
        ocr_data = pytesseract.image_to_data(
            image, 
            config=config.tesseract_config,
            output_type=pytesseract.Output.DICT
        )
        
        # Extract text boxes with confidence filtering
        text_boxes = []
        n_boxes = len(ocr_data['level'])
        
        for i in range(n_boxes):
            confidence = int(ocr_data['conf'][i])
            text = ocr_data['text'][i].strip()
            
            if confidence > config.confidence_threshold and text:
                x = ocr_data['left'][i]
                y = ocr_data['top'][i]
                w = ocr_data['width'][i]
                h = ocr_data['height'][i]
                
                text_boxes.append({
                    'text': text,
                    'bbox': (x, y, x + w, y + h),
                    'confidence': confidence
                })
        
        # Cleanup
        os.unlink(image.name)
        
        return text_boxes
        
    except Exception as e:
        print(f"OCR extraction error: {e}")
        return []


def detect_text_in_scanned_pdf(pdf_path: str,
                              terms: Optional[List[str]] = None,
                              regex_patterns: Optional[List[str]] = None,
                              config: Optional[OCRConfig] = None,
                              verbose: bool = False) -> Dict[int, List[fitz.Rect]]:
    """
    Detect text in scanned PDF pages using OCR
    
    Args:
        pdf_path: Path to PDF file
        terms: List of exact terms to find
        regex_patterns: List of regex patterns to match
        config: OCR configuration
        verbose: Enable verbose output
        
    Returns:
        Dictionary mapping page numbers to redaction rectangles
    """
    # Check dependencies
    deps_available, missing = _check_dependencies()
    if not deps_available:
        print(f"OCR dependencies missing: {', '.join(missing)}")
        print("Install with: pip install opencv-python pytesseract pillow")
        return {}
    
    if config is None:
        config = OCRConfig()
    
    terms = terms or []
    regex_patterns = regex_patterns or []
    
    if not terms and not regex_patterns:
        print("No search terms or patterns provided")
        return {}
    
    # Compile regex patterns
    import re
    compiled_patterns = []
    for pattern in regex_patterns:
        try:
            compiled_patterns.append(re.compile(pattern, re.IGNORECASE))
        except re.error as e:
            print(f"Invalid regex pattern '{pattern}': {e}")
    
    boxes_by_page = {}
    
    try:
        doc = fitz.open(pdf_path)
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            page_number = page_num + 1
            boxes_by_page[page_number] = []
            
            # Check if page has extractable text
            existing_text = page.get_text().strip()
            if len(existing_text) > 50:  # Page has significant text, skip OCR
                if verbose:
                    print(f"Page {page_number}: Skipping OCR (has extractable text)")
                continue
            
            if verbose:
                print(f"Page {page_number}: Running OCR...")
            
            # Render page to image
            mat = fitz.Matrix(config.dpi / 72, config.dpi / 72)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            
            # Extract text with OCR
            text_boxes = _extract_text_with_boxes(pix, config)
            
            if verbose:
                print(f"Page {page_number}: OCR found {len(text_boxes)} text elements")
            
            # Search for terms and patterns
            page_matches = []
            
            for text_box in text_boxes:
                text = text_box['text']
                bbox = text_box['bbox']
                
                # Scale coordinates back to PDF space
                scale = 72 / config.dpi
                pdf_rect = fitz.Rect(
                    bbox[0] * scale,
                    bbox[1] * scale,
                    bbox[2] * scale,
                    bbox[3] * scale
                )
                
                # Check exact terms
                for term in terms:
                    if term.lower() in text.lower():
                        page_matches.append(pdf_rect)
                        if verbose:
                            print(f"  Found term '{term}' in: {text}")
                
                # Check regex patterns
                for pattern in compiled_patterns:
                    if pattern.search(text):
                        page_matches.append(pdf_rect)
                        if verbose:
                            print(f"  Found pattern match in: {text}")
            
            boxes_by_page[page_number] = page_matches
        
        doc.close()
        
    except Exception as e:
        print(f"Error during OCR processing: {e}")
    
    return boxes_by_page


def create_searchable_pdf(input_path: str,
                         output_path: str,
                         config: Optional[OCRConfig] = None,
                         verbose: bool = False) -> bool:
    """
    Convert scanned PDF to searchable PDF by adding OCR text layer
    
    Args:
        input_path: Path to input PDF
        output_path: Path to output PDF
        config: OCR configuration
        verbose: Enable verbose output
        
    Returns:
        True if successful, False otherwise
    """
    # Check dependencies
    deps_available, missing = _check_dependencies()
    if not deps_available:
        print(f"OCR dependencies missing: {', '.join(missing)}")
        return False
    
    if config is None:
        config = OCRConfig()
    
    try:
        doc = fitz.open(input_path)
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            page_number = page_num + 1
            
            # Check if page already has text
            existing_text = page.get_text().strip()
            if len(existing_text) > 50:
                if verbose:
                    print(f"Page {page_number}: Already has text, skipping OCR")
                continue
            
            if verbose:
                print(f"Page {page_number}: Adding OCR text layer...")
            
            # Render page to image
            mat = fitz.Matrix(config.dpi / 72, config.dpi / 72)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            
            # Extract text with OCR
            text_boxes = _extract_text_with_boxes(pix, config)
            
            # Add invisible text layer
            for text_box in text_boxes:
                text = text_box['text']
                bbox = text_box['bbox']
                
                # Scale coordinates back to PDF space
                scale = 72 / config.dpi
                pdf_rect = fitz.Rect(
                    bbox[0] * scale,
                    bbox[1] * scale,
                    bbox[2] * scale,
                    bbox[3] * scale
                )
                
                # Insert invisible text
                page.insert_text(
                    pdf_rect.tl,  # Top-left point
                    text,
                    fontsize=pdf_rect.height * 0.8,  # Scale font to box height
                    color=(1, 1, 1),  # White text (invisible)
                    overlay=False
                )
        
        # Save the searchable PDF
        doc.save(output_path, garbage=4, deflate=True)
        doc.close()
        
        if verbose:
            print(f"Created searchable PDF: {output_path}")
        
        return True
        
    except Exception as e:
        print(f"Error creating searchable PDF: {e}")
        return False


def is_scanned_pdf(pdf_path: str, text_threshold: int = 100) -> bool:
    """
    Determine if a PDF is primarily scanned (image-based)
    
    Args:
        pdf_path: Path to PDF file
        text_threshold: Minimum characters to consider "text-based"
        
    Returns:
        True if PDF appears to be scanned
    """
    try:
        doc = fitz.open(pdf_path)
        total_text_length = 0
        
        for page in doc:
            text = page.get_text()
            total_text_length += len(text.strip())
        
        doc.close()
        
        # If total text is below threshold, consider it scanned
        return total_text_length < text_threshold
        
    except Exception:
        return False


def get_ocr_capabilities() -> Dict[str, bool]:
    """
    Check what OCR capabilities are available
    
    Returns:
        Dictionary of available capabilities
    """
    capabilities = {
        "opencv_available": OPENCV_AVAILABLE,
        "tesseract_available": TESSERACT_AVAILABLE,
        "full_ocr_available": OPENCV_AVAILABLE and TESSERACT_AVAILABLE
    }
    
    if TESSERACT_AVAILABLE:
        try:
            capabilities["tesseract_version"] = pytesseract.get_tesseract_version()
        except:
            capabilities["tesseract_version"] = "unknown"
    
    return capabilities