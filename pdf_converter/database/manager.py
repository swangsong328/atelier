"""Database manager for PDF processing data."""

from __future__ import annotations

import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker, Session
    from sqlalchemy.exc import SQLAlchemyError
except ImportError:
    create_engine = None
    text = None
    sessionmaker = None
    Session = None
    SQLAlchemyError = None

from ..config import config
from ..models import ProcessingJob, ProcessingResult
from ..utils import calculate_file_hash
from .models import (
    Base, ProcessingJobDB, ExtractedTextDB, ExtractedTableDB, 
    PDFMetadataDB, ProcessingSessionDB, FileHashDB
)


class DatabaseManager:
    """Manages database operations for PDF processing."""
    
    def __init__(self, database_url: Optional[str] = None) -> None:
        """Initialize the database manager.
        
        Args:
            database_url: SQLAlchemy database URL. If None, uses default SQLite.
        """
        if database_url is None:
            db_path = config.temp_dir.parent / "pdf_converter.db"
            database_url = f"sqlite:///{db_path}"
        
        self.database_url = database_url
        self.engine = None
        self.SessionLocal = None
        self._initialize_database()
    
    def _initialize_database(self) -> None:
        """Initialize the database engine and create tables."""
        try:
            self.engine = create_engine(
                self.database_url,
                echo=False,  # Set to True for SQL debugging
                pool_pre_ping=True,
                pool_recycle=300
            )
            
            # Create all tables
            Base.metadata.create_all(bind=self.engine)
            
            # Create session factory
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )
            
        except Exception as e:
            print(f"Database initialization error: {e}")
            raise
    
    def get_session(self) -> Session:
        """Get a database session."""
        if self.SessionLocal is None:
            raise RuntimeError("Database not initialized")
        return self.SessionLocal()
    
    def save_processing_job(self, job: ProcessingJob, result: ProcessingResult) -> int:
        """Save a processing job and its results to the database.
        
        Args:
            job: The processing job
            result: The processing result
            
        Returns:
            Database ID of the saved job
        """
        with self.get_session() as session:
            try:
                # Check if file was already processed
                file_hash = calculate_file_hash(job.input_file)
                existing_hash = session.query(FileHashDB).filter_by(file_hash=file_hash).first()
                
                if existing_hash:
                    # Update existing file hash record
                    existing_hash.last_processed_at = datetime.now()
                    existing_hash.processing_count += 1
                    existing_hash.file_path = str(job.input_file)
                    existing_hash.file_name = job.input_file.name
                    existing_hash.file_size = job.input_file.stat().st_size
                else:
                    # Create new file hash record
                    file_hash_record = FileHashDB(
                        file_hash=file_hash,
                        file_path=str(job.input_file),
                        file_name=job.input_file.name,
                        file_size=job.input_file.stat().st_size
                    )
                    session.add(file_hash_record)
                
                # Create processing job record
                job_db = ProcessingJobDB(
                    job_id=job.id,
                    input_file_path=str(job.input_file),
                    input_file_name=job.input_file.name,
                    input_file_size=job.input_file.stat().st_size,
                    input_file_hash=file_hash,
                    processing_mode=job.pdf_options.mode.value,
                    extract_text=job.pdf_options.extract_text,
                    extract_tables=job.pdf_options.extract_tables,
                    extract_images=job.pdf_options.extract_images,
                    page_range=job.pdf_options.page_range,
                    status=job.status.value,
                    created_at=job.created_at,
                    started_at=job.started_at,
                    completed_at=job.completed_at,
                    pages_processed=job.pages_processed,
                    tables_extracted=job.tables_extracted,
                    text_blocks_extracted=job.text_blocks_extracted,
                    processing_time=result.processing_time,
                    error_message=job.error_message,
                    output_file_path=str(job.output_file) if job.output_file else None,
                    output_file_size=job.output_file.stat().st_size if job.output_file and job.output_file.exists() else None
                )
                
                session.add(job_db)
                session.flush()  # Get the ID
                
                # Save metadata
                if result.metadata:
                    self._save_metadata(session, job_db.id, result.metadata)
                
                # Save extracted text
                if result.extracted_data.get("text"):
                    self._save_extracted_text(session, job_db.id, result.extracted_data["text"])
                
                # Save extracted tables
                if result.extracted_data.get("tables"):
                    self._save_extracted_tables(session, job_db.id, result.extracted_data["tables"])
                
                # Update file hash record with job reference
                if existing_hash:
                    existing_hash.last_job_id = job_db.id
                
                session.commit()
                return job_db.id
                
            except SQLAlchemyError as e:
                session.rollback()
                print(f"Database error saving job: {e}")
                raise
    
    def _save_metadata(self, session: Session, job_id: int, metadata: Dict[str, Any]) -> None:
        """Save PDF metadata to database."""
        try:
            # Parse dates if they exist
            creation_date = None
            modification_date = None
            
            if metadata.get("pdf_metadata"):
                pdf_meta = metadata["pdf_metadata"]
                
                # Try to parse creation date
                if pdf_meta.get("/CreationDate"):
                    try:
                        creation_date = self._parse_pdf_date(pdf_meta["/CreationDate"])
                    except:
                        pass
                
                # Try to parse modification date
                if pdf_meta.get("/ModDate"):
                    try:
                        modification_date = self._parse_pdf_date(pdf_meta["/ModDate"])
                    except:
                        pass
            
            metadata_db = PDFMetadataDB(
                job_id=job_id,
                title=metadata.get("pdf_metadata", {}).get("/Title"),
                author=metadata.get("pdf_metadata", {}).get("/Author"),
                subject=metadata.get("pdf_metadata", {}).get("/Subject"),
                creator=metadata.get("pdf_metadata", {}).get("/Creator"),
                producer=metadata.get("pdf_metadata", {}).get("/Producer"),
                creation_date=creation_date,
                modification_date=modification_date,
                total_pages=metadata.get("total_pages", 0),
                pdf_version=metadata.get("pdf_version"),
                encryption=metadata.get("encryption", False),
                file_size=metadata.get("file_size", 0),
                custom_metadata=metadata
            )
            
            session.add(metadata_db)
            
        except Exception as e:
            print(f"Error saving metadata: {e}")
    
    def _save_extracted_text(self, session: Session, job_id: int, text_data: Dict[str, Any]) -> None:
        """Save extracted text to database."""
        try:
            for text_block in text_data.get("text_blocks", []):
                text_content = text_block.get("text", "")
                
                # Analyze text content
                word_count = len(text_content.split())
                line_count = len(text_content.split('\n'))
                paragraph_count = len([p for p in text_content.split('\n\n') if p.strip()])
                
                # Check for specific content types
                has_numbers = bool(re.search(r'\d', text_content))
                has_emails = bool(re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text_content))
                has_urls = bool(re.search(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', text_content))
                has_phone_numbers = bool(re.search(r'(\+\d{1,2}\s)?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}', text_content))
                
                text_db = ExtractedTextDB(
                    job_id=job_id,
                    page_number=text_block.get("page", 1),
                    text_content=text_content,
                    text_length=len(text_content),
                    word_count=word_count,
                    line_count=line_count,
                    paragraph_count=paragraph_count,
                    has_numbers=has_numbers,
                    has_emails=has_emails,
                    has_urls=has_urls,
                    has_phone_numbers=has_phone_numbers,
                    extraction_method=text_data.get("extraction_method", "pdfplumber"),
                    confidence_score=text_data.get("confidence_score"),
                    extraction_time=text_data.get("extraction_time", 0.0)
                )
                
                session.add(text_db)
                
        except Exception as e:
            print(f"Error saving extracted text: {e}")
    
    def _save_extracted_tables(self, session: Session, job_id: int, table_data: Dict[str, Any]) -> None:
        """Save extracted tables to database."""
        try:
            for table_info in table_data.get("tables", []):
                table_content = table_info.get("data", [])
                
                if not table_content:
                    continue
                
                # Analyze table structure
                rows = len(table_content)
                columns = len(table_content[0]) if table_content else 0
                total_cells = rows * columns
                empty_cells = sum(1 for row in table_content for cell in row if not cell or cell.strip() == "")
                
                # Analyze table content
                headers = table_content[0] if table_content else []
                has_headers = bool(headers)
                
                # Check for data types
                has_numeric_data = False
                has_date_data = False
                has_currency_data = False
                
                for row in table_content[1:]:  # Skip header row
                    for cell in row:
                        if cell:
                            # Check for numbers
                            if re.search(r'\d+\.?\d*', cell):
                                has_numeric_data = True
                            
                            # Check for dates
                            if re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', cell):
                                has_date_data = True
                            
                            # Check for currency
                            if re.search(r'[\$€£¥]\s*\d+\.?\d*', cell):
                                has_currency_data = True
                
                # Determine table type
                table_type = "data_table"
                if columns < 2:
                    table_type = "simple_list"
                elif has_numeric_data and has_numeric_data > total_cells * 0.3:
                    table_type = "numeric_table"
                
                table_db = ExtractedTableDB(
                    job_id=job_id,
                    page_number=table_info.get("page", 1),
                    table_index=table_info.get("table_index", 0),
                    table_name=f"Table_{table_info.get('table_index', 0)}",
                    rows=rows,
                    columns=columns,
                    total_cells=total_cells,
                    empty_cells=empty_cells,
                    table_data=table_content,
                    headers=headers if has_headers else None,
                    has_headers=has_headers,
                    has_numeric_data=has_numeric_data,
                    has_date_data=has_date_data,
                    has_currency_data=has_currency_data,
                    table_type=table_type,
                    detection_confidence=table_data.get("detection_confidence"),
                    extraction_method=table_data.get("extraction_method", "pdfplumber"),
                    extraction_time=table_data.get("extraction_time", 0.0),
                    table_metadata=table_info
                )
                
                session.add(table_db)
                
        except Exception as e:
            print(f"Error saving extracted tables: {e}")
    
    def _parse_pdf_date(self, date_str: str) -> Optional[datetime]:
        """Parse PDF date string to datetime object."""
        try:
            # PDF dates are in format: D:YYYYMMDDHHmmSSOHH'mm'
            if date_str.startswith('D:'):
                date_str = date_str[2:]
            
            # Extract year, month, day
            year = int(date_str[:4])
            month = int(date_str[4:6])
            day = int(date_str[6:8])
            
            # Extract time if available
            hour = int(date_str[8:10]) if len(date_str) > 8 else 0
            minute = int(date_str[10:12]) if len(date_str) > 10 else 0
            second = int(date_str[12:14]) if len(date_str) > 12 else 0
            
            return datetime(year, month, day, hour, minute, second)
            
        except (ValueError, IndexError):
            return None
    
    def get_job_by_id(self, job_id: str) -> Optional[ProcessingJobDB]:
        """Get a processing job by its ID."""
        with self.get_session() as session:
            return session.query(ProcessingJobDB).filter_by(job_id=job_id).first()
    
    def get_jobs_by_status(self, status: str) -> List[ProcessingJobDB]:
        """Get all jobs with a specific status."""
        with self.get_session() as session:
            return session.query(ProcessingJobDB).filter_by(status=status).all()
    
    def get_recent_jobs(self, limit: int = 10) -> List[ProcessingJobDB]:
        """Get recent processing jobs."""
        with self.get_session() as session:
            return session.query(ProcessingJobDB).order_by(
                ProcessingJobDB.created_at.desc()
            ).limit(limit).all()
    
    def get_job_statistics(self) -> Dict[str, Any]:
        """Get processing statistics."""
        with self.get_session() as session:
            total_jobs = session.query(ProcessingJobDB).count()
            completed_jobs = session.query(ProcessingJobDB).filter_by(status="completed").count()
            failed_jobs = session.query(ProcessingJobDB).filter_by(status="failed").count()
            
            total_files = session.query(FileHashDB).count()
            total_text_blocks = session.query(ExtractedTextDB).count()
            total_tables = session.query(ExtractedTableDB).count()
            
            return {
                "total_jobs": total_jobs,
                "completed_jobs": completed_jobs,
                "failed_jobs": failed_jobs,
                "success_rate": (completed_jobs / total_jobs * 100) if total_jobs > 0 else 0,
                "total_files_processed": total_files,
                "total_text_blocks": total_text_blocks,
                "total_tables": total_tables
            }
    
    def search_text_content(self, search_term: str, limit: int = 50) -> List[ExtractedTextDB]:
        """Search for text content containing the search term."""
        with self.get_session() as session:
            return session.query(ExtractedTextDB).filter(
                ExtractedTextDB.text_content.contains(search_term)
            ).limit(limit).all()
    
    def get_duplicate_files(self) -> List[FileHashDB]:
        """Get files that have been processed multiple times."""
        with self.get_session() as session:
            return session.query(FileHashDB).filter(
                FileHashDB.processing_count > 1
            ).order_by(FileHashDB.processing_count.desc()).all()
    
    def cleanup_old_data(self, days: int = 30) -> int:
        """Clean up old processing data."""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        with self.get_session() as session:
            try:
                # Delete old jobs and related data (cascade will handle related records)
                deleted_count = session.query(ProcessingJobDB).filter(
                    ProcessingJobDB.created_at < cutoff_date
                ).delete()
                
                session.commit()
                return deleted_count
                
            except SQLAlchemyError as e:
                session.rollback()
                print(f"Error cleaning up old data: {e}")
                return 0 