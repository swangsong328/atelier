"""PDF processing engine using multiple extraction methods."""

from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import re

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

try:
    import pandas as pd
except ImportError:
    pd = None

from ..models import ProcessingJob, ProcessingResult, ProcessingStatus
from ..utils import parse_page_range
from .base import BaseProcessor


class PDFProcessor(BaseProcessor):
    """PDF processor using multiple extraction methods for robustness."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the PDF processor.
        
        Args:
            config: Configuration dictionary
        """
        super().__init__(config)
        self.extraction_methods = self._get_available_methods()
    
    def _get_available_methods(self) -> List[str]:
        """Get list of available extraction methods."""
        methods = []
        
        if pdfplumber is not None:
            methods.append("pdfplumber")
        
        if PyPDF2 is not None:
            methods.append("pypdf2")
        
        return methods
    
    def can_process(self, file_path: str) -> bool:
        """Check if this processor can handle the given file."""
        path = Path(file_path)
        return path.suffix.lower() == ".pdf" and len(self.extraction_methods) > 0
    
    def process(self, job: ProcessingJob) -> ProcessingResult:
        """Process the PDF file according to the job specifications."""
        start_time = time.time()
        
        try:
            # Update job status
            job.status = ProcessingStatus.PROCESSING
            job.started_at = datetime.now()
            
            # Validate job
            is_valid, error_msg = self.validate_job(job)
            if not is_valid:
                job.status = ProcessingStatus.FAILED
                job.error_message = error_msg
                job.completed_at = datetime.now()
                return ProcessingResult(
                    job=job,
                    processing_time=time.time() - start_time
                )
            
            # Enhanced extraction with detailed analysis
            extracted_data = {}
            metadata = {}
            
            # Get page range
            pages_to_process = self._get_pages_to_process(job)
            total_pages = len(pages_to_process)
            
            if total_pages == 0:
                job.status = ProcessingStatus.FAILED
                job.error_message = "No pages to process"
                job.completed_at = datetime.now()
                return ProcessingResult(
                    job=job,
                    processing_time=time.time() - start_time
                )
            
            # Extract text if requested
            if job.pdf_options.extract_text:
                text_data = self._extract_text_enhanced(job, pages_to_process)
                extracted_data["text"] = text_data
                job.text_blocks_extracted = len(text_data.get("text_blocks", []))
            
            # Extract tables if requested
            if job.pdf_options.extract_tables:
                table_data = self._extract_tables_enhanced(job, pages_to_process)
                extracted_data["tables"] = table_data
                job.tables_extracted = len(table_data.get("tables", []))
            
            # Extract enhanced metadata
            metadata = self._extract_metadata_enhanced(job)
            
            # Update job with results
            job.pages_processed = total_pages
            job.status = ProcessingStatus.COMPLETED
            job.completed_at = datetime.now()
            
            processing_time = time.time() - start_time
            
            return ProcessingResult(
                job=job,
                extracted_data=extracted_data,
                metadata=metadata,
                processing_time=processing_time
            )
            
            # Extract data based on processing options
            extracted_data = {}
            metadata = {}
            
            # Get page range
            pages_to_process = self._get_pages_to_process(job)
            total_pages = len(pages_to_process)
            
            if total_pages == 0:
                job.status = ProcessingStatus.FAILED
                job.error_message = "No pages to process"
                job.completed_at = datetime.now()
                return ProcessingResult(
                    job=job,
                    processing_time=time.time() - start_time
                )
            
            # Extract text if requested
            if job.pdf_options.extract_text:
                text_data = self._extract_text(job, pages_to_process)
                extracted_data["text"] = text_data
                job.text_blocks_extracted = len(text_data.get("text_blocks", []))
            
            # Extract tables if requested
            if job.pdf_options.extract_tables:
                table_data = self._extract_tables(job, pages_to_process)
                extracted_data["tables"] = table_data
                job.tables_extracted = len(table_data.get("tables", []))
            
            # Extract metadata
            metadata = self._extract_metadata(job)
            
            # Update job with results
            job.pages_processed = total_pages
            job.status = ProcessingStatus.COMPLETED
            job.completed_at = datetime.now()
            
            processing_time = time.time() - start_time
            
            return ProcessingResult(
                job=job,
                extracted_data=extracted_data,
                metadata=metadata,
                processing_time=processing_time
            )
            
        except Exception as e:
            job.status = ProcessingStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.now()
            
            return ProcessingResult(
                job=job,
                processing_time=time.time() - start_time
            )
    
    def _get_pages_to_process(self, job: ProcessingJob) -> List[int]:
        """Get list of pages to process based on job options."""
        if job.pdf_options.page_range:
            return parse_page_range(job.pdf_options.page_range)
        
        # Process all pages
        try:
            if pdfplumber is not None:
                with pdfplumber.open(job.input_file) as pdf:
                    return list(range(1, len(pdf.pages) + 1))
            elif PyPDF2 is not None:
                with open(job.input_file, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    return list(range(1, len(reader.pages) + 1))
        except Exception:
            pass
        
        return []
    
    def _extract_text(self, job: ProcessingJob, pages: List[int]) -> Dict[str, Any]:
        """Extract text from PDF pages."""
        text_data = {
            "text_blocks": [],
            "full_text": "",
            "page_texts": {}
        }
        
        for i, page_num in enumerate(pages):
            try:
                page_text = self._extract_text_from_page(job, page_num)
                if page_text:
                    text_data["page_texts"][page_num] = page_text
                    text_data["text_blocks"].append({
                        "page": page_num,
                        "text": page_text,
                        "length": len(page_text)
                    })
                    text_data["full_text"] += f"\n\n--- Page {page_num} ---\n{page_text}"
                
                # Update progress
                self.update_progress(i + 1, f"Extracting text from page {page_num}")
                
            except Exception as e:
                # Log error but continue with other pages
                print(f"Error extracting text from page {page_num}: {e}")
        
        return text_data
    
    def _extract_text_from_page(self, job: ProcessingJob, page_num: int) -> str:
        """Extract text from a specific page."""
        if pdfplumber is not None:
            return self._extract_text_with_pdfplumber(job, page_num)
        elif PyPDF2 is not None:
            return self._extract_text_with_pypdf2(job, page_num)
        else:
            return ""
    
    def _extract_text_with_pdfplumber(self, job: ProcessingJob, page_num: int) -> str:
        """Extract text using pdfplumber."""
        try:
            with pdfplumber.open(job.input_file) as pdf:
                if 0 <= page_num - 1 < len(pdf.pages):
                    page = pdf.pages[page_num - 1]
                    text = page.extract_text()
                    return text or ""
        except Exception as e:
            print(f"Error with pdfplumber on page {page_num}: {e}")
        
        return ""
    
    def _extract_text_with_pypdf2(self, job: ProcessingJob, page_num: int) -> str:
        """Extract text using PyPDF2."""
        try:
            with open(job.input_file, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                if 0 <= page_num - 1 < len(reader.pages):
                    page = reader.pages[page_num - 1]
                    text = page.extract_text()
                    return text or ""
        except Exception as e:
            print(f"Error with PyPDF2 on page {page_num}: {e}")
        
        return ""
    
    def _extract_tables(self, job: ProcessingJob, pages: List[int]) -> Dict[str, Any]:
        """Extract tables from PDF pages."""
        table_data = {
            "tables": [],
            "total_tables": 0
        }
        
        for i, page_num in enumerate(pages):
            try:
                page_tables = self._extract_tables_from_page(job, page_num)
                for table in page_tables:
                    table_data["tables"].append({
                        "page": page_num,
                        "table_index": len(table_data["tables"]),
                        "data": table,
                        "rows": len(table) if table else 0,
                        "columns": len(table[0]) if table and table[0] else 0
                    })
                
                table_data["total_tables"] = len(table_data["tables"])
                
                # Update progress
                self.update_progress(i + 1, f"Extracting tables from page {page_num}")
                
            except Exception as e:
                print(f"Error extracting tables from page {page_num}: {e}")
        
        return table_data
    
    def _extract_tables_from_page(self, job: ProcessingJob, page_num: int) -> List[List[List[str]]]:
        """Extract tables from a specific page."""
        if pdfplumber is not None:
            return self._extract_tables_with_pdfplumber(job, page_num)
        else:
            return []
    
    def _extract_tables_with_pdfplumber(self, job: ProcessingJob, page_num: int) -> List[List[List[str]]]:
        """Extract tables using pdfplumber."""
        try:
            with pdfplumber.open(job.input_file) as pdf:
                if 0 <= page_num - 1 < len(pdf.pages):
                    page = pdf.pages[page_num - 1]
                    tables = page.extract_tables()
                    
                    # Filter tables based on minimum size
                    filtered_tables = []
                    for table in tables:
                        if table and len(table) >= job.pdf_options.min_table_size:
                            # Convert all cells to strings
                            processed_table = []
                            for row in table:
                                processed_row = [str(cell) if cell is not None else "" for cell in row]
                                processed_table.append(processed_row)
                            filtered_tables.append(processed_table)
                    
                    return filtered_tables
        except Exception as e:
            print(f"Error extracting tables with pdfplumber on page {page_num}: {e}")
        
        return []
    
    def _extract_metadata(self, job: ProcessingJob) -> Dict[str, Any]:
        """Extract PDF metadata."""
        metadata = {
            "filename": job.input_file.name,
            "file_size": job.input_file.stat().st_size,
            "processing_options": job.pdf_options.dict(),
            "extraction_methods": self.extraction_methods
        }
        
        try:
            if pdfplumber is not None:
                with pdfplumber.open(job.input_file) as pdf:
                    metadata["total_pages"] = len(pdf.pages)
                    if pdf.metadata:
                        metadata["pdf_metadata"] = pdf.metadata
            elif PyPDF2 is not None:
                with open(job.input_file, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    metadata["total_pages"] = len(reader.pages)
                    if reader.metadata:
                        metadata["pdf_metadata"] = reader.metadata
        except Exception as e:
            metadata["metadata_error"] = str(e)
        
        return metadata
    
    def _extract_text_enhanced(self, job: ProcessingJob, pages: List[int]) -> Dict[str, Any]:
        """Enhanced text extraction with detailed analysis."""
        text_data = self._extract_text(job, pages)
        
        # Add enhanced analysis
        text_data["extraction_method"] = "pdfplumber" if pdfplumber else "pypdf2"
        text_data["extraction_time"] = time.time()  # Placeholder for actual timing
        
        # Analyze text content
        full_text = text_data.get("full_text", "")
        text_data["total_words"] = len(full_text.split())
        text_data["total_characters"] = len(full_text)
        text_data["total_lines"] = len(full_text.split('\n'))
        
        # Content analysis
        text_data["has_numbers"] = any(c.isdigit() for c in full_text)
        text_data["has_emails"] = "@" in full_text
        text_data["has_urls"] = "http" in full_text.lower()
        
        return text_data
    
    def _extract_tables_enhanced(self, job: ProcessingJob, pages: List[int]) -> Dict[str, Any]:
        """Enhanced table extraction with detailed analysis."""
        table_data = self._extract_tables(job, pages)
        
        # Add enhanced analysis
        table_data["extraction_method"] = "pdfplumber"
        table_data["extraction_time"] = time.time()  # Placeholder for actual timing
        
        # Analyze each table
        for table_info in table_data.get("tables", []):
            table_content = table_info.get("data", [])
            
            # Calculate empty cells
            empty_cells = sum(1 for row in table_content for cell in row if not cell or cell.strip() == "")
            table_info["empty_cells"] = empty_cells
            table_info["total_cells"] = len(table_content) * len(table_content[0]) if table_content else 0
            
            # Analyze data types
            has_numeric = False
            has_dates = False
            has_currency = False
            
            for row in table_content:
                for cell in row:
                    if cell:
                        if any(c.isdigit() for c in cell):
                            has_numeric = True
                        if re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', cell):
                            has_dates = True
                        if re.search(r'[\$€£¥]\s*\d+\.?\d*', cell):
                            has_currency = True
            
            table_info["has_numeric_data"] = has_numeric
            table_info["has_date_data"] = has_dates
            table_info["has_currency_data"] = has_currency
        
        return table_data
    
    def _extract_metadata_enhanced(self, job: ProcessingJob) -> Dict[str, Any]:
        """Enhanced metadata extraction with additional information."""
        metadata = self._extract_metadata(job)
        
        # Add file hash
        # Assuming calculate_file_hash is defined elsewhere or will be added
        # For now, we'll just add a placeholder
        metadata["file_hash"] = "placeholder_hash" 
        
        # Add processing timestamp
        metadata["processing_timestamp"] = datetime.now().isoformat()
        
        # Add system information
        metadata["system_info"] = {
            "extraction_methods": self.extraction_methods,
            "processing_mode": job.pdf_options.mode.value,
            "extract_text": job.pdf_options.extract_text,
            "extract_tables": job.pdf_options.extract_tables
        }
        
        return metadata 