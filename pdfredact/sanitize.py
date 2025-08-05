"""
PDF Sanitization Module - Remove metadata, embedded content, and security risks
"""

import pikepdf
import fitz
from typing import Optional, List, Dict, Any
import tempfile
import os


def _remove_metadata(pdf: pikepdf.Pdf, verbose: bool = False) -> int:
    """
    Remove all metadata from PDF
    
    Returns:
        Number of metadata items removed
    """
    removed_count = 0
    
    # Clear document info dictionary
    if pdf.docinfo:
        original_count = len(pdf.docinfo)
        pdf.docinfo.clear()
        removed_count += original_count
        if verbose and original_count > 0:
            print(f"Removed {original_count} document info entries")
    
    # Remove XMP metadata
    if "/Metadata" in pdf.root:
        del pdf.root["/Metadata"]
        removed_count += 1
        if verbose:
            print("Removed XMP metadata stream")
    
    return removed_count


def _remove_javascript_and_actions(pdf: pikepdf.Pdf, verbose: bool = False) -> int:
    """
    Remove JavaScript and automatic actions that could be security risks
    
    Returns:
        Number of items removed
    """
    removed_count = 0
    
    # Remove document-level JavaScript and actions
    dangerous_keys = ["/OpenAction", "/AA", "/JS", "/JavaScript"]
    
    for key in dangerous_keys:
        if key in pdf.root:
            del pdf.root[key]
            removed_count += 1
            if verbose:
                print(f"Removed {key}")
    
    # Remove page-level actions
    for page in pdf.pages:
        page_actions_removed = 0
        action_keys = ["/AA", "/A"]
        
        for key in action_keys:
            if key in page:
                del page[key]
                page_actions_removed += 1
        
        if page_actions_removed > 0:
            removed_count += page_actions_removed
            if verbose:
                print(f"Removed {page_actions_removed} actions from page")
    
    return removed_count


def _remove_embedded_files(pdf: pikepdf.Pdf, verbose: bool = False) -> int:
    """
    Remove embedded files and attachments
    
    Returns:
        Number of embedded files removed
    """
    removed_count = 0
    
    # Remove embedded files from Names dictionary
    if "/Names" in pdf.root:
        names = pdf.root["/Names"]
        
        if "/EmbeddedFiles" in names:
            # Count embedded files before removal
            try:
                embedded_files = names["/EmbeddedFiles"]
                if "/Names" in embedded_files:
                    file_list = embedded_files["/Names"]
                    removed_count = len(file_list) // 2  # Names come in pairs
            except:
                removed_count = 1  # At least one embedded file structure
            
            del names["/EmbeddedFiles"]
            if verbose:
                print(f"Removed {removed_count} embedded files")
        
        # Clean up empty Names dictionary
        if len(names) == 0:
            del pdf.root["/Names"]
    
    # Remove file attachments from annotations
    for page in pdf.pages:
        if "/Annots" not in page:
            continue
            
        annots_to_remove = []
        for i, annot_ref in enumerate(page["/Annots"]):
            try:
                annot = annot_ref.resolve()
                if annot.get("/Subtype") == "/FileAttachment":
                    annots_to_remove.append(i)
            except:
                continue
        
        # Remove file attachment annotations (in reverse order to maintain indices)
        for i in reversed(annots_to_remove):
            del page["/Annots"][i]
            removed_count += 1
            if verbose:
                print("Removed file attachment annotation")
        
        # Clean up empty annotations array
        if len(page["/Annots"]) == 0:
            del page["/Annots"]
    
    return removed_count


def _remove_links_and_uris(pdf: pikepdf.Pdf, verbose: bool = False) -> int:
    """
    Remove or neutralize hyperlinks and URI actions
    
    Returns:
        Number of links removed/modified
    """
    removed_count = 0
    
    for page in pdf.pages:
        if "/Annots" not in page:
            continue
        
        annots_to_remove = []
        for i, annot_ref in enumerate(page["/Annots"]):
            try:
                annot = annot_ref.resolve()
                subtype = annot.get("/Subtype")
                
                # Remove link annotations
                if subtype == "/Link":
                    # Check if it has a URI action
                    action = annot.get("/A")
                    if action and action.resolve().get("/S") == "/URI":
                        annots_to_remove.append(i)
                        removed_count += 1
                
            except:
                continue
        
        # Remove link annotations (in reverse order)
        for i in reversed(annots_to_remove):
            del page["/Annots"][i]
        
        # Clean up empty annotations array
        if "/Annots" in page and len(page["/Annots"]) == 0:
            del page["/Annots"]
    
    if verbose and removed_count > 0:
        print(f"Removed {removed_count} hyperlinks")
    
    return removed_count


def _remove_forms(pdf: pikepdf.Pdf, verbose: bool = False) -> int:
    """
    Remove interactive forms (AcroForms)
    
    Returns:
        Number of form elements removed
    """
    removed_count = 0
    
    # Remove AcroForm dictionary
    if "/AcroForm" in pdf.root:
        try:
            acroform = pdf.root["/AcroForm"]
            if "/Fields" in acroform:
                fields = acroform["/Fields"]
                removed_count = len(fields)
        except:
            removed_count = 1  # At least the AcroForm structure
        
        del pdf.root["/AcroForm"]
        if verbose:
            print(f"Removed AcroForm with {removed_count} fields")
    
    # Remove form field annotations
    for page in pdf.pages:
        if "/Annots" not in page:
            continue
        
        annots_to_remove = []
        for i, annot_ref in enumerate(page["/Annots"]):
            try:
                annot = annot_ref.resolve()
                subtype = annot.get("/Subtype")
                
                # Remove form field annotations
                if subtype in ["/Widget", "/Tx", "/Btn", "/Ch"]:
                    annots_to_remove.append(i)
            except:
                continue
        
        # Remove form annotations
        for i in reversed(annots_to_remove):
            del page["/Annots"][i]
            removed_count += 1
        
        # Clean up empty annotations array
        if "/Annots" in page and len(page["/Annots"]) == 0:
            del page["/Annots"]
    
    return removed_count


def _remove_thumbnails_and_pieceinfo(pdf: pikepdf.Pdf, verbose: bool = False) -> int:
    """
    Remove page thumbnails and piece info
    
    Returns:
        Number of items removed
    """
    removed_count = 0
    
    for page in pdf.pages:
        items_removed_this_page = 0
        
        # Remove thumbnails
        if "/Thumb" in page:
            del page["/Thumb"]
            items_removed_this_page += 1
        
        # Remove piece info (private application data)
        if "/PieceInfo" in page:
            del page["/PieceInfo"]
            items_removed_this_page += 1
        
        removed_count += items_removed_this_page
    
    if verbose and removed_count > 0:
        print(f"Removed {removed_count} thumbnail/pieceinfo items")
    
    return removed_count


def _remove_remaining_annotations(pdf: pikepdf.Pdf, verbose: bool = False) -> int:
    """
    Remove any remaining annotations (except redactions which should already be applied)
    
    Returns:
        Number of annotations removed
    """
    removed_count = 0
    
    for page in pdf.pages:
        if "/Annots" not in page:
            continue
        
        # Count annotations before removal
        try:
            annots_count = len(page["/Annots"])
            if annots_count > 0:
                del page["/Annots"]
                removed_count += annots_count
        except:
            pass
    
    if verbose and removed_count > 0:
        print(f"Removed {removed_count} remaining annotations")
    
    return removed_count


def _optimize_structure(pdf: pikepdf.Pdf, verbose: bool = False) -> None:
    """
    Optimize PDF structure by removing unused objects and compressing
    """
    # pikepdf will handle optimization during save with appropriate parameters
    if verbose:
        print("Optimizing PDF structure...")


def hard_sanitize(input_path: str, 
                 output_path: str, 
                 remove_annotations: bool = True,
                 verbose: bool = False) -> bool:
    """
    Perform comprehensive sanitization of a PDF
    
    Args:
        input_path: Path to input PDF
        output_path: Path to output PDF
        remove_annotations: Whether to remove all annotations
        verbose: Enable verbose output
        
    Returns:
        True if successful, False otherwise
    """
    try:
        with pikepdf.open(input_path, allow_overwriting_input=False) as pdf:
            total_removed = 0
            
            if verbose:
                print("Starting PDF sanitization...")
            
            # Remove metadata
            total_removed += _remove_metadata(pdf, verbose)
            
            # Remove JavaScript and actions
            total_removed += _remove_javascript_and_actions(pdf, verbose)
            
            # Remove embedded files
            total_removed += _remove_embedded_files(pdf, verbose)
            
            # Remove links and URIs
            total_removed += _remove_links_and_uris(pdf, verbose)
            
            # Remove forms
            total_removed += _remove_forms(pdf, verbose)
            
            # Remove thumbnails and piece info
            total_removed += _remove_thumbnails_and_pieceinfo(pdf, verbose)
            
            # Remove remaining annotations if requested
            if remove_annotations:
                total_removed += _remove_remaining_annotations(pdf, verbose)
            
            # Optimize structure
            _optimize_structure(pdf, verbose)
            
            # Save with optimization
            pdf.save(
                output_path,
                linearize=False,  # Don't linearize (web optimization)
                fix_metadata_version=True,  # Fix PDF version in metadata
                compress_streams=True,  # Compress content streams
                stream_decode_level=pikepdf.StreamDecodeLevel.generalized,  # Decode and re-encode streams
                object_stream_mode=pikepdf.ObjectStreamMode.generate,  # Use object streams for compression
                normalize_content=True,  # Normalize content streams
                # Remove incremental updates by doing a full rewrite
                deterministic_id=False,  # Don't use deterministic IDs (for security)
            )
            
            if verbose:
                print(f"Sanitization complete: removed {total_removed} items")
        
        return True
        
    except Exception as e:
        print(f"Error during sanitization: {e}")
        return False


def analyze_pdf_security(pdf_path: str) -> Dict[str, Any]:
    """
    Analyze a PDF for potential security issues and privacy leaks
    
    Returns:
        Dictionary with analysis results
    """
    analysis = {
        "metadata_found": [],
        "javascript_found": False,
        "embedded_files_count": 0,
        "links_count": 0,
        "forms_found": False,
        "annotations_count": 0,
        "thumbnails_count": 0,
        "encryption": None,
        "warnings": []
    }
    
    try:
        with pikepdf.open(pdf_path) as pdf:
            # Check metadata
            if pdf.docinfo:
                analysis["metadata_found"] = list(pdf.docinfo.keys())
            
            if "/Metadata" in pdf.root:
                analysis["metadata_found"].append("XMP_metadata")
            
            # Check for JavaScript
            js_keys = ["/OpenAction", "/AA", "/JS", "/JavaScript"]
            for key in js_keys:
                if key in pdf.root:
                    analysis["javascript_found"] = True
                    break
            
            # Check embedded files
            if "/Names" in pdf.root and "/EmbeddedFiles" in pdf.root["/Names"]:
                try:
                    embedded = pdf.root["/Names"]["/EmbeddedFiles"]
                    if "/Names" in embedded:
                        analysis["embedded_files_count"] = len(embedded["/Names"]) // 2
                except:
                    analysis["embedded_files_count"] = 1
            
            # Check forms
            if "/AcroForm" in pdf.root:
                analysis["forms_found"] = True
            
            # Count annotations, links, thumbnails per page
            for page in pdf.pages:
                if "/Annots" in page:
                    for annot_ref in page["/Annots"]:
                        try:
                            annot = annot_ref.resolve()
                            analysis["annotations_count"] += 1
                            
                            if annot.get("/Subtype") == "/Link":
                                analysis["links_count"] += 1
                                
                        except:
                            continue
                
                if "/Thumb" in page:
                    analysis["thumbnails_count"] += 1
            
            # Check encryption
            if pdf.is_encrypted:
                analysis["encryption"] = "encrypted"
            
            # Generate warnings
            if analysis["metadata_found"]:
                analysis["warnings"].append("Document contains metadata that may reveal sensitive information")
            
            if analysis["javascript_found"]:
                analysis["warnings"].append("Document contains JavaScript which could be a security risk")
            
            if analysis["embedded_files_count"] > 0:
                analysis["warnings"].append(f"Document contains {analysis['embedded_files_count']} embedded files")
            
            if analysis["links_count"] > 0:
                analysis["warnings"].append(f"Document contains {analysis['links_count']} external links")
            
    except Exception as e:
        analysis["warnings"].append(f"Error analyzing PDF: {e}")
    
    return analysis


def quick_sanitize_metadata_only(input_path: str, output_path: str) -> bool:
    """
    Quick sanitization that only removes metadata (preserves functionality)
    
    Returns:
        True if successful, False otherwise
    """
    try:
        with pikepdf.open(input_path) as pdf:
            # Only remove metadata
            _remove_metadata(pdf, verbose=False)
            
            # Save with minimal changes
            pdf.save(output_path, linearize=False)
        
        return True
        
    except Exception as e:
        print(f"Error during quick sanitization: {e}")
        return False