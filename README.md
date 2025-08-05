# PDF Redactor

A secure PDF redaction tool that **actually removes** sensitive content instead of just covering it with black boxes. Perfect for legal documents, financial records, and any PDFs containing sensitive information that need to be shared safely.

## 🔒 What Makes This Different

- **True Redaction**: Content is permanently removed from the PDF structure, not just visually hidden
- **Comprehensive Sanitization**: Removes metadata, JavaScript, embedded files, and other potential information leaks
- **Smart Detection**: Supports exact text search, regex patterns, and manual rectangle specification
- **OCR Support**: Can handle scanned PDFs with optional OCR text detection
- **Verification**: Built-in verification to ensure redaction was successful
- **No Web Dependencies**: Runs completely offline for maximum security

## 🚀 Quick Start

### Installation

```bash
# Clone or download this repository
cd pdfredact

# Install core dependencies
pip install -r requirements.txt

# Optional: Install OCR dependencies for scanned PDFs
pip install opencv-python pytesseract pillow
```

### Basic Usage

```bash
# Make the CLI executable
chmod +x pdfredact/cli.py

# Redact by keywords and regex patterns
python pdfredact/cli.py input.pdf output.pdf \
  --term "John Q. Public" \
  --term "CONFIDENTIAL" \
  --regex "\b\d{3}-\d{2}-\d{4}\b" \
  --regex "[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}" \
  --verify --verbose

# Use pre-defined rectangles from JSON
python pdfredact/cli.py input.pdf output.pdf --rects rectangles.json

# Sanitize only (remove metadata without redacting content)
python pdfredact/cli.py sanitize input.pdf output.pdf
```

## 📋 Features

### Text-Based Redaction
- **Exact Term Search**: Find and redact specific words or phrases
- **Regex Patterns**: Use regular expressions for complex pattern matching
- **Common PII Patterns**: Built-in patterns for SSNs, emails, phone numbers, etc.

### Manual Redaction
- **Rectangle Specification**: Define exact areas to redact using JSON coordinates
- **Preview Mode**: Generate preview PDFs showing what will be redacted

### Scanned PDF Support
- **OCR Integration**: Detect text in scanned PDFs using Tesseract OCR
- **Raster Redaction**: Convert pages to images with redacted areas for maximum security
- **Hybrid Processing**: Automatically detect text vs. scanned pages

### Security & Sanitization
- **Metadata Removal**: Clear document info, XMP metadata, and creation details
- **JavaScript Removal**: Remove potentially malicious JavaScript and actions
- **Embedded File Removal**: Remove attached files and embedded content
- **Link Neutralization**: Remove or disable external links
- **Form Flattening**: Remove interactive form fields
- **Thumbnail Cleanup**: Remove page thumbnails and piece info

### Verification & Reporting
- **Content Verification**: Check output PDF to ensure target content was removed
- **String Analysis**: Optional `strings` command verification for hidden content
- **Detailed Reports**: Generate JSON reports of redaction activities
- **Impact Analysis**: Preview redaction impact before applying

## 🛠️ Advanced Usage

### Rectangle Specification

Create a JSON file with rectangle coordinates:

```json
{
  "1": [
    {"x0": 72, "y0": 540, "x1": 320, "y1": 565},
    {"x0": 100, "y0": 100, "x1": 400, "y1": 130}
  ],
  "3": [
    {"x0": 100, "y0": 700, "x1": 420, "y1": 740}
  ]
}
```

Coordinates are in points (72 points = 1 inch) from the bottom-left origin.

### Common Regex Patterns

The tool includes built-in patterns for common PII:

```python
from pdfredact.utils import get_common_patterns

patterns = get_common_patterns()
# patterns["ssn"] = r"\b\d{3}-\d{2}-\d{4}\b"
# patterns["email"] = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
# patterns["phone"] = r"\b\(?(\d{3})\)?[-.\s]?(\d{3})[-.\s]?(\d{4})\b"
```

### OCR Configuration

For scanned PDFs, configure OCR settings:

```python
from pdfredact.ocr import OCRConfig, detect_text_in_scanned_pdf

config = OCRConfig()
config.dpi = 300  # Higher DPI for better accuracy
config.confidence_threshold = 50  # Minimum confidence for text detection

boxes = detect_text_in_scanned_pdf("scanned.pdf", terms=["SECRET"], config=config)
```

### Programmatic Usage

Use as a Python library:

```python
from pdfredact import find_boxes, apply_boxes, hard_sanitize

# Find content to redact
boxes = find_boxes("input.pdf", terms=["CONFIDENTIAL"], regex_patterns=[r"\d{3}-\d{2}-\d{4}"])

# Apply redactions
apply_boxes("input.pdf", "temp.pdf", boxes)

# Sanitize and finalize
hard_sanitize("temp.pdf", "output.pdf")
```

## 🔧 Command Line Options

### Main Redaction Command

```bash
python pdfredact/cli.py input.pdf output.pdf [OPTIONS]
```

**Options:**
- `--term TEXT`: Text terms to redact (can be used multiple times)
- `--regex TEXT`: Regex patterns to redact (can be used multiple times)  
- `--rects PATH`: JSON file with rectangle coordinates
- `--fill [black|white]`: Fill color for redacted areas (default: black)
- `--verify`: Verify redaction by checking output for remaining terms
- `--verbose, -v`: Enable verbose output

### Sanitization Only

```bash
python pdfredact/cli.py sanitize input.pdf output.pdf [OPTIONS]
```

**Options:**
- `--verbose, -v`: Enable verbose output

## 📁 Project Structure

```
pdfredact/
├── cli.py          # Command-line interface
├── detect.py       # Text and pattern detection
├── redact.py       # Redaction application  
├── sanitize.py     # Metadata and content sanitization
├── ocr.py          # OCR support for scanned PDFs
├── utils.py        # Utility functions and validation
└── __init__.py     # Package initialization
```

## 🧪 Testing

### Create Test Files

```python
from pdfredact.utils import create_test_rectangles_json
create_test_rectangles_json("test_rects.json")
```

### Analyze PDF Security

```python
from pdfredact.sanitize import analyze_pdf_security

analysis = analyze_pdf_security("document.pdf")
print(f"Found {len(analysis['metadata_found'])} metadata items")
print(f"JavaScript present: {analysis['javascript_found']}")
print(f"Embedded files: {analysis['embedded_files_count']}")
```

### Preview Impact

```python
from pdfredact.utils import estimate_redaction_impact

impact = estimate_redaction_impact("document.pdf", ["SECRET"], [r"\d{3}-\d{2}-\d{4}"])
print(f"Would redact {impact['total_matches']} items across {impact['pages_affected']} pages")
```

## ⚠️ Important Security Notes

1. **Test Thoroughly**: Always test redaction on sample documents before processing important files
2. **Verify Results**: Use the `--verify` flag and manually review output PDFs
3. **Backup Originals**: Keep secure backups of original documents
4. **Multiple Passes**: For highly sensitive content, consider multiple redaction passes with different patterns
5. **Physical Security**: Ensure both input and output files are handled securely
6. **Memory Cleaning**: The tool processes PDFs in memory - ensure your system memory is secure

## 🔍 Verification Methods

The tool provides multiple verification approaches:

1. **Text Re-extraction**: Re-extracts text from output PDF and searches for target terms
2. **String Analysis**: Uses system `strings` command to find hidden content  
3. **Visual Inspection**: Generate preview PDFs to manually verify redaction areas
4. **Binary Analysis**: Optional deep inspection of PDF object structure

## 📄 Supported PDF Types

- **Text-based PDFs**: Full support for searchable text redaction
- **Scanned PDFs**: OCR-based text detection (requires additional dependencies)
- **Mixed Content**: Automatic detection and appropriate handling
- **Encrypted PDFs**: Supported if password is available
- **Form PDFs**: Form fields are flattened and removed during sanitization

## 🔄 Processing Flow

1. **Analysis**: Determine PDF type (text-based vs. scanned)
2. **Detection**: Find target content using text search, regex, or OCR
3. **Redaction**: Apply redaction annotations and remove underlying content
4. **Sanitization**: Remove metadata, JavaScript, embedded files, etc.
5. **Verification**: Check output to ensure redaction was successful
6. **Reporting**: Generate detailed reports of actions taken

## 🤝 Contributing

This tool is designed to be secure and reliable. When contributing:

1. Ensure all changes maintain security principles
2. Add appropriate tests for new functionality
3. Update documentation for new features
4. Consider edge cases and error handling

## 📜 License

This project is provided as-is for educational and security purposes. Users are responsible for compliance with applicable laws and regulations regarding document redaction and privacy.

---

**Remember**: True document security requires proper handling throughout the entire document lifecycle. This tool provides technical redaction capabilities, but organizational policies and procedures are equally important for maintaining information security.