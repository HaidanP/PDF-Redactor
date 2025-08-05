"""
Setup script for PDF Redactor
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

# Read requirements
requirements = []
with open("requirements.txt", "r") as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#"):
            requirements.append(line)

setup(
    name="pdfredact",
    version="1.0.0",
    author="PDF Redactor",
    description="Securely remove sensitive content from PDFs",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    install_requires=[
        "PyMuPDF>=1.23.0",
        "pikepdf>=8.0.0", 
        "click>=8.0.0"
    ],
    extras_require={
        "ocr": [
            "opencv-python>=4.8.0",
            "pytesseract>=0.3.10",
            "Pillow>=10.0.0"
        ],
        "dev": [
            "pytest>=7.0.0",
            "black>=23.0.0",
            "flake8>=6.0.0"
        ]
    },
    entry_points={
        "console_scripts": [
            "pdfredact=pdfredact.cli:cli",
        ],
    },
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Legal Industry",
        "Intended Audience :: Information Technology",
        "Topic :: Security",
        "Topic :: Office/Business",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    keywords="pdf redaction security privacy document",
    project_urls={
        "Bug Reports": "https://github.com/your-repo/pdfredact/issues",
        "Source": "https://github.com/your-repo/pdfredact",
    },
)