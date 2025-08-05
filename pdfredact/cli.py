#!/usr/bin/env python3
"""
PDF Redactor CLI - Securely remove sensitive content from PDFs
"""

import click
import json
import os
import sys
from pathlib import Path

from detect import find_boxes
from redact import apply_boxes
from sanitize import hard_sanitize
from utils import validate_pdf, verify_redaction


@click.command()
@click.argument("input_pdf", type=click.Path(exists=True, path_type=Path))
@click.argument("output_pdf", type=click.Path(path_type=Path))
@click.option("--term", multiple=True, help="Text terms to redact (can be used multiple times)")
@click.option("--regex", multiple=True, help="Regex patterns to redact (can be used multiple times)")
@click.option("--rects", type=click.Path(exists=True, path_type=Path), help="JSON file with rectangle coordinates")
@click.option("--fill", default="black", type=click.Choice(["black", "white"]), help="Fill color for redacted areas")
@click.option("--verify", is_flag=True, help="Verify redaction by checking output for remaining terms")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def redact(input_pdf, output_pdf, term, regex, rects, fill, verify, verbose):
    """
    Redact sensitive content from PDFs by actually removing it, not just covering it.
    
    Examples:
    
    \b
    # Redact by keywords and regex
    pdfredact input.pdf output.pdf \\
      --term "John Q. Public" \\
      --regex "\\b\\d{3}-\\d{2}-\\d{4}\\b" \\
      --regex "[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}"
    
    \b
    # Use rectangles from JSON
    pdfredact input.pdf output.pdf --rects spec.json
    
    \b
    # Sanitize only (no redaction)
    pdfredact sanitize input.pdf output.pdf
    """
    try:
        if verbose:
            click.echo(f"Processing: {input_pdf}")
        
        # Validate input PDF
        if not validate_pdf(input_pdf):
            click.echo(f"Error: {input_pdf} is not a valid PDF file", err=True)
            sys.exit(1)
        
        # Find content to redact
        if verbose:
            click.echo("Detecting content to redact...")
        
        boxes = find_boxes(
            str(input_pdf), 
            terms=list(term), 
            regex_patterns=list(regex), 
            rects_path=str(rects) if rects else None,
            verbose=verbose
        )
        
        # Count total redactions
        total_redactions = sum(len(rects) for rects in boxes.values())
        if verbose:
            click.echo(f"Found {total_redactions} areas to redact across {len([p for p, r in boxes.items() if r])} pages")
        
        # Create temporary file for redaction
        temp_file = str(output_pdf) + ".tmp.pdf"
        
        try:
            # Apply redactions
            if verbose:
                click.echo("Applying redactions...")
            apply_boxes(str(input_pdf), temp_file, boxes, fill=fill, verbose=verbose)
            
            # Sanitize the PDF
            if verbose:
                click.echo("Sanitizing PDF...")
            hard_sanitize(temp_file, str(output_pdf), verbose=verbose)
            
            # Verify redaction if requested
            if verify and (term or regex):
                if verbose:
                    click.echo("Verifying redaction...")
                remaining = verify_redaction(str(output_pdf), list(term), list(regex))
                if remaining:
                    click.echo(f"Warning: Found {len(remaining)} potentially unredacted terms:", err=True)
                    for r in remaining:
                        click.echo(f"  - {r}", err=True)
                else:
                    click.echo("✓ Verification passed: no target terms found in output")
            
            click.echo(f"✓ Redaction complete: {output_pdf}")
            
        finally:
            # Clean up temporary file
            if os.path.exists(temp_file):
                os.remove(temp_file)
                
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@click.command()
@click.argument("input_pdf", type=click.Path(exists=True, path_type=Path))
@click.argument("output_pdf", type=click.Path(path_type=Path))
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def sanitize(input_pdf, output_pdf, verbose):
    """
    Sanitize PDF metadata and embedded content without redacting text.
    Useful after manual redaction or as a standalone cleanup.
    """
    try:
        if verbose:
            click.echo(f"Sanitizing: {input_pdf}")
        
        # Validate input PDF
        if not validate_pdf(input_pdf):
            click.echo(f"Error: {input_pdf} is not a valid PDF file", err=True)
            sys.exit(1)
        
        # Direct sanitization
        hard_sanitize(str(input_pdf), str(output_pdf), verbose=verbose)
        
        click.echo(f"✓ Sanitization complete: {output_pdf}")
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@click.group()
def cli():
    """PDF Redactor - Securely remove sensitive content from PDFs"""
    pass


# Add commands to the group
cli.add_command(redact)
cli.add_command(sanitize)


if __name__ == "__main__":
    # If called directly, assume redact command
    if len(sys.argv) > 1 and sys.argv[1] not in ["redact", "sanitize", "--help", "-h"]:
        sys.argv.insert(1, "redact")
    cli()