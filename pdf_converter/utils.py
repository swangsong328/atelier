"""Utility functions for the PDF to Excel converter."""

from __future__ import annotations

import hashlib
import re
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import pandas as pd
except ImportError:
    pd = None

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


def generate_job_id() -> str:
    """Generate a unique job identifier."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    return f"job_{timestamp}_{unique_id}"


def validate_pdf_file(file_path: Path) -> Tuple[bool, Optional[str]]:
    """Validate PDF file for processing.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        if not file_path.exists():
            return False, f"File does not exist: {file_path}"
        
        if file_path.suffix.lower() != ".pdf":
            return False, f"File is not a PDF: {file_path}"
        
        # Check file size
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        if file_size_mb > 100:  # 100MB limit
            return False, f"File too large: {file_size_mb:.1f}MB (max 100MB)"
        
        # Check if file is readable
        if not file_path.is_file():
            return False, f"Path is not a file: {file_path}"
        
        # Try to open with PyPDF2 to check if it's a valid PDF
        try:
            try:
                import PyPDF2
                with open(file_path, 'rb') as f:
                    PyPDF2.PdfReader(f)
            except ImportError:
                # Fallback to basic file check if PyPDF2 is not available
                with open(file_path, 'rb') as f:
                    header = f.read(4)
                    if header != b'%PDF':
                        return False, "File is not a valid PDF"
        except Exception as e:
            return False, f"Invalid PDF file: {str(e)}"
        
        return True, None
        
    except Exception as e:
        return False, f"Error validating file: {str(e)}"


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe file system operations."""
    # Remove or replace invalid characters
    invalid_chars = r'[<>:"/\\|?*]'
    sanitized = re.sub(invalid_chars, '_', filename)
    
    # Remove leading/trailing spaces and dots
    sanitized = sanitized.strip(' .')
    
    # Ensure filename is not empty
    if not sanitized:
        sanitized = "unnamed_file"
    
    return sanitized


def generate_output_filename(input_file: Path, output_format: str, output_dir: Path) -> Path:
    """Generate output filename based on input file and format."""
    base_name = input_file.stem
    sanitized_name = sanitize_filename(base_name)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    filename = f"{sanitized_name}_{timestamp}.{output_format}"
    return output_dir / filename


def parse_page_range(page_range: str) -> List[int]:
    """Parse page range string into list of page numbers.
    
    Args:
        page_range: String like "1-5, 10-15, 20"
    
    Returns:
        List of page numbers (1-indexed)
    """
    if not page_range:
        return []
    
    pages = set()
    parts = page_range.split(',')
    
    for part in parts:
        part = part.strip()
        if '-' in part:
            start, end = part.split('-')
            try:
                start_num = int(start.strip())
                end_num = int(end.strip())
                pages.update(range(start_num, end_num + 1))
            except ValueError:
                logger.warning(f"Invalid page range: {part}")
        else:
            try:
                pages.add(int(part))
            except ValueError:
                logger.warning(f"Invalid page number: {part}")
    
    return sorted(list(pages))


def calculate_file_hash(file_path: Path) -> str:
    """Calculate SHA-256 hash of a file."""
    hash_sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    size_float = float(size_bytes)
    while size_float >= 1024 and i < len(size_names) - 1:
        size_float /= 1024.0
        i += 1
    
    return f"{size_float:.1f} {size_names[i]}"


def format_duration(seconds: float) -> str:
    """Format duration in human-readable format."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        remaining_seconds = seconds % 60
        return f"{minutes}m {remaining_seconds:.1f}s"
    else:
        hours = int(seconds // 3600)
        remaining_minutes = int((seconds % 3600) // 60)
        remaining_seconds = seconds % 60
        return f"{hours}h {remaining_minutes}m {remaining_seconds:.1f}s"


def clean_temp_files(temp_dir: Path) -> None:
    """Clean temporary files from the specified directory."""
    try:
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
            temp_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Cleaned temporary directory: {temp_dir}")
    except Exception as e:
        logger.error(f"Error cleaning temp directory: {e}")


def merge_dataframes(dfs: List[pd.DataFrame], strategy: str = "concat") -> pd.DataFrame:
    """Merge multiple dataframes using specified strategy.
    
    Args:
        dfs: List of dataframes to merge
        strategy: Merge strategy ('concat', 'union', 'intersection')
    
    Returns:
        Merged dataframe
    """
    if not dfs:
        return pd.DataFrame()
    
    if len(dfs) == 1:
        return dfs[0]
    
    if strategy == "concat":
        return pd.concat(dfs, ignore_index=True)
    elif strategy == "union":
        # Union of all columns
        all_columns = set()
        for df in dfs:
            all_columns.update(df.columns)
        
        # Add missing columns to each dataframe
        for df in dfs:
            for col in all_columns:
                if col not in df.columns:
                    df[col] = None
        
        return pd.concat(dfs, ignore_index=True)
    elif strategy == "intersection":
        # Only common columns
        common_columns = set(dfs[0].columns)
        for df in dfs[1:]:
            common_columns &= set(df.columns)
        
        if not common_columns:
            return pd.DataFrame()
        
        filtered_dfs = [df[list(common_columns)] for df in dfs]
        return pd.concat(filtered_dfs, ignore_index=True)
    else:
        raise ValueError(f"Unknown merge strategy: {strategy}")


def detect_table_structure(df: pd.DataFrame) -> Dict[str, Any]:
    """Detect table structure and provide metadata."""
    if df.empty:
        return {"type": "empty", "rows": 0, "columns": 0}
    
    structure = {
        "type": "table",
        "rows": len(df),
        "columns": len(df.columns),
        "column_types": df.dtypes.to_dict(),
        "has_headers": True,  # Assume first row is header
        "empty_cells": df.isnull().sum().sum(),
        "total_cells": df.size,
    }
    
    # Detect if table has meaningful structure
    if len(df.columns) < 2 or len(df) < 2:
        structure["type"] = "simple_list"
    
    # Check for common table patterns
    numeric_columns = df.select_dtypes(include=['number']).columns
    if len(numeric_columns) > len(df.columns) * 0.5:
        structure["type"] = "data_table"
    
    return structure


def create_progress_callback(total_pages: int) -> callable:
    """Create a progress callback function for processing updates."""
    def progress_callback(current_page: int, message: str = "") -> float:
        """Calculate progress percentage."""
        if total_pages == 0:
            return 0.0
        progress = (current_page / total_pages) * 100
        logger.info(f"Progress: {progress:.1f}% - {message}")
        return progress
    
    return progress_callback


def validate_excel_output_options(options: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Validate Excel output options."""
    try:
        # Validate format
        valid_formats = ["xlsx", "xls", "csv"]
        if "format" in options and options["format"] not in valid_formats:
            return False, f"Invalid output format: {options['format']}"
        
        # Validate sheet name
        if "sheet_name" in options:
            sheet_name = options["sheet_name"]
            if not sheet_name or len(sheet_name) > 31:  # Excel sheet name limit
                return False, "Sheet name must be 1-31 characters long"
            
            # Check for invalid characters in sheet name
            invalid_chars = r'[\\/*?:\[\]]'
            if re.search(invalid_chars, sheet_name):
                return False, "Sheet name contains invalid characters"
        
        return True, None
        
    except Exception as e:
        return False, f"Error validating options: {str(e)}"


def get_system_info() -> Dict[str, Any]:
    """Get system information for diagnostics."""
    import platform
    import sys
    
    return {
        "platform": platform.system(),
        "platform_version": platform.version(),
        "python_version": sys.version,
        "python_executable": sys.executable,
        "architecture": platform.architecture()[0],
        "processor": platform.processor(),
    } 