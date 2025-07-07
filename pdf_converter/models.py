"""Data models for the PDF to Excel converter."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator


class ProcessingStatus(str, Enum):
    """Status of PDF processing."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class OutputFormat(str, Enum):
    """Supported output formats."""
    XLSX = "xlsx"
    XLS = "xls"
    CSV = "csv"


class ProcessingMode(str, Enum):
    """PDF processing modes."""
    TEXT_ONLY = "text_only"
    TABLES_ONLY = "tables_only"
    MIXED = "mixed"
    CUSTOM = "custom"


class PDFProcessingOptions(BaseModel):
    """Options for PDF processing."""
    
    mode: ProcessingMode = Field(default=ProcessingMode.MIXED, description="Processing mode")
    extract_tables: bool = Field(default=True, description="Extract tables from PDF")
    extract_text: bool = Field(default=True, description="Extract text from PDF")
    extract_images: bool = Field(default=False, description="Extract images from PDF")
    page_range: Optional[str] = Field(default=None, description="Page range (e.g., '1-5, 10-15')")
    password: Optional[str] = Field(default=None, description="PDF password if encrypted")
    
    # Table extraction options
    table_detection_method: str = Field(default="auto", description="Table detection method")
    min_table_size: int = Field(default=2, ge=1, description="Minimum table size (rows)")
    merge_cells: bool = Field(default=True, description="Merge cells in tables")
    
    # Text extraction options
    preserve_formatting: bool = Field(default=True, description="Preserve text formatting")
    extract_headers: bool = Field(default=True, description="Extract headers")
    
    @validator("page_range")
    def validate_page_range(cls, v: Optional[str]) -> Optional[str]:
        """Validate page range format."""
        if v is None:
            return v
        
        # Simple validation for page range format
        import re
        pattern = r'^(\d+(-\d+)?)(,\s*\d+(-\d+)?)*$'
        if not re.match(pattern, v):
            raise ValueError("Invalid page range format. Use format like '1-5, 10-15'")
        return v


class ExcelOutputOptions(BaseModel):
    """Options for Excel output."""
    
    format: OutputFormat = Field(default=OutputFormat.XLSX, description="Output format")
    sheet_name: str = Field(default="PDF_Data", description="Default sheet name")
    include_metadata: bool = Field(default=True, description="Include PDF metadata")
    auto_adjust_columns: bool = Field(default=True, description="Auto-adjust column widths")
    include_page_numbers: bool = Field(default=True, description="Include page numbers")
    preserve_styling: bool = Field(default=True, description="Preserve cell styling")
    
    # Multiple sheets options
    separate_sheets: bool = Field(default=False, description="Create separate sheets for different content types")
    sheet_naming: str = Field(default="auto", description="Sheet naming strategy")

    # Report type (added for GUI selection)
    report_type: str = Field(default="Standard", description="Report type: Standard or DD (structured)")


class ProcessingJob(BaseModel):
    """Represents a PDF processing job."""
    
    id: str = Field(description="Unique job identifier")
    input_file: Path = Field(description="Input PDF file path")
    output_file: Optional[Path] = Field(default=None, description="Output Excel file path")
    status: ProcessingStatus = Field(default=ProcessingStatus.PENDING, description="Job status")
    created_at: datetime = Field(default_factory=datetime.now, description="Job creation time")
    started_at: Optional[datetime] = Field(default=None, description="Processing start time")
    completed_at: Optional[datetime] = Field(default=None, description="Processing completion time")
    
    # Processing options
    pdf_options: PDFProcessingOptions = Field(default_factory=PDFProcessingOptions, description="PDF processing options")
    excel_options: ExcelOutputOptions = Field(default_factory=ExcelOutputOptions, description="Excel output options")
    
    # Results
    pages_processed: int = Field(default=0, description="Number of pages processed")
    tables_extracted: int = Field(default=0, description="Number of tables extracted")
    text_blocks_extracted: int = Field(default=0, description="Number of text blocks extracted")
    error_message: Optional[str] = Field(default=None, description="Error message if failed")
    
    # Progress tracking
    progress_percentage: float = Field(default=0.0, ge=0.0, le=100.0, description="Processing progress percentage")
    current_page: int = Field(default=0, description="Current page being processed")
    
    @validator("id")
    def validate_id(cls, v: str) -> str:
        """Validate job ID format."""
        if not v or len(v) < 3:
            raise ValueError("Job ID must be at least 3 characters long")
        return v
    
    @validator("input_file")
    def validate_input_file(cls, v: Path) -> Path:
        """Validate input file exists and is a PDF."""
        if not v.exists():
            raise ValueError(f"Input file does not exist: {v}")
        if v.suffix.lower() != ".pdf":
            raise ValueError(f"Input file must be a PDF: {v}")
        return v
    
    def is_completed(self) -> bool:
        """Check if job is completed."""
        return self.status in [ProcessingStatus.COMPLETED, ProcessingStatus.FAILED, ProcessingStatus.CANCELLED]
    
    def is_running(self) -> bool:
        """Check if job is currently running."""
        return self.status == ProcessingStatus.PROCESSING
    
    def can_cancel(self) -> bool:
        """Check if job can be cancelled."""
        return self.status in [ProcessingStatus.PENDING, ProcessingStatus.PROCESSING]


class ProcessingResult(BaseModel):
    """Result of PDF processing."""
    
    job: ProcessingJob = Field(description="Associated processing job")
    extracted_data: Dict[str, Any] = Field(default_factory=dict, description="Extracted data")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="PDF metadata")
    processing_time: float = Field(description="Total processing time in seconds")
    file_size_reduction: Optional[float] = Field(default=None, description="File size reduction percentage")
    
    # Quality metrics
    text_quality_score: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Text extraction quality score")
    table_quality_score: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Table extraction quality score")
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the processing result."""
        return {
            "job_id": self.job.id,
            "status": self.job.status,
            "pages_processed": self.job.pages_processed,
            "tables_extracted": self.job.tables_extracted,
            "text_blocks_extracted": self.job.text_blocks_extracted,
            "processing_time": self.processing_time,
            "output_file": str(self.job.output_file) if self.job.output_file else None,
        }


class ApplicationState(BaseModel):
    """Application state management."""
    
    recent_files: List[Path] = Field(default_factory=list, description="Recently processed files")
    active_jobs: List[ProcessingJob] = Field(default_factory=list, description="Currently active jobs")
    completed_jobs: List[ProcessingJob] = Field(default_factory=list, description="Completed jobs")
    settings: Dict[str, Any] = Field(default_factory=dict, description="Application settings")
    
    @validator("recent_files")
    def validate_recent_files(cls, v: List[Path]) -> List[Path]:
        """Keep only existing files in recent files list."""
        return [f for f in v if f.exists()][:10]  # Keep only last 10 files
    
    def add_recent_file(self, file_path: Path) -> None:
        """Add a file to recent files list."""
        if file_path in self.recent_files:
            self.recent_files.remove(file_path)
        self.recent_files.insert(0, file_path)
        self.recent_files = self.recent_files[:10]  # Keep only last 10
    
    def get_active_job(self, job_id: str) -> Optional[ProcessingJob]:
        """Get active job by ID."""
        for job in self.active_jobs:
            if job.id == job_id:
                return job
        return None
    
    def remove_completed_jobs(self, max_count: int = 100) -> None:
        """Remove old completed jobs to prevent memory issues."""
        if len(self.completed_jobs) > max_count:
            self.completed_jobs = self.completed_jobs[-max_count:] 