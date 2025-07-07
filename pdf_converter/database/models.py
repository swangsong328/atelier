"""
Database models for storing PDF processing data.
"""

from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean, Float,
    ForeignKey, JSON, Index, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func

Base = declarative_base()

class ProcessingJobDB(Base):
    __tablename__ = "processing_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    input_file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    input_file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    input_file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    input_file_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    processing_mode: Mapped[str] = mapped_column(String(50), nullable=False)
    extract_text: Mapped[bool] = mapped_column(Boolean, default=True)
    extract_tables: Mapped[bool] = mapped_column(Boolean, default=True)
    extract_images: Mapped[bool] = mapped_column(Boolean, default=False)
    page_range: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    pages_processed: Mapped[int] = mapped_column(Integer, default=0)
    tables_extracted: Mapped[int] = mapped_column(Integer, default=0)
    text_blocks_extracted: Mapped[int] = mapped_column(Integer, default=0)
    processing_time: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    output_file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    output_file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    pdf_metadata: Mapped[List["PDFMetadataDB"]] = relationship("PDFMetadataDB", back_populates="job", cascade="all, delete-orphan")
    extracted_texts: Mapped[List["ExtractedTextDB"]] = relationship("ExtractedTextDB", back_populates="job", cascade="all, delete-orphan")
    extracted_tables: Mapped[List["ExtractedTableDB"]] = relationship("ExtractedTableDB", back_populates="job", cascade="all, delete-orphan")
    __table_args__ = (
        Index('idx_job_status', 'status'),
        Index('idx_job_created', 'created_at'),
        Index('idx_file_hash', 'input_file_hash'),
    )

class PDFMetadataDB(Base):
    __tablename__ = "pdf_metadata"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(Integer, ForeignKey("processing_jobs.id"), nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    author: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    subject: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    creator: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    producer: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    creation_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    modification_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    total_pages: Mapped[int] = mapped_column(Integer, nullable=False)
    pdf_version: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    encryption: Mapped[bool] = mapped_column(Boolean, default=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    custom_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    job: Mapped["ProcessingJobDB"] = relationship("ProcessingJobDB", back_populates="pdf_metadata")
    __table_args__ = (
        Index('idx_metadata_job', 'job_id'),
        Index('idx_metadata_title', 'title'),
    )

class ExtractedTextDB(Base):
    __tablename__ = "extracted_text"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(Integer, ForeignKey("processing_jobs.id"), nullable=False)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    text_content: Mapped[str] = mapped_column(Text, nullable=False)
    text_length: Mapped[int] = mapped_column(Integer, nullable=False)
    word_count: Mapped[int] = mapped_column(Integer, nullable=False)
    line_count: Mapped[int] = mapped_column(Integer, nullable=False)
    paragraph_count: Mapped[int] = mapped_column(Integer, nullable=False)
    has_numbers: Mapped[bool] = mapped_column(Boolean, default=False)
    has_emails: Mapped[bool] = mapped_column(Boolean, default=False)
    has_urls: Mapped[bool] = mapped_column(Boolean, default=False)
    has_phone_numbers: Mapped[bool] = mapped_column(Boolean, default=False)
    extraction_method: Mapped[str] = mapped_column(String(50), nullable=False)
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    extraction_time: Mapped[float] = mapped_column(Float, nullable=False)
    job: Mapped["ProcessingJobDB"] = relationship("ProcessingJobDB", back_populates="extracted_texts")
    __table_args__ = (
        Index('idx_text_job_page', 'job_id', 'page_number'),
        Index('idx_text_length', 'text_length'),
        Index('idx_text_word_count', 'word_count'),
    )

class ExtractedTableDB(Base):
    __tablename__ = "extracted_tables"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(Integer, ForeignKey("processing_jobs.id"), nullable=False)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    table_index: Mapped[int] = mapped_column(Integer, nullable=False)
    table_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    rows: Mapped[int] = mapped_column(Integer, nullable=False)
    columns: Mapped[int] = mapped_column(Integer, nullable=False)
    total_cells: Mapped[int] = mapped_column(Integer, nullable=False)
    empty_cells: Mapped[int] = mapped_column(Integer, nullable=False)
    table_data: Mapped[List[List[str]]] = mapped_column(JSON, nullable=False)
    headers: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    has_headers: Mapped[bool] = mapped_column(Boolean, default=True)
    has_numeric_data: Mapped[bool] = mapped_column(Boolean, default=False)
    has_date_data: Mapped[bool] = mapped_column(Boolean, default=False)
    has_currency_data: Mapped[bool] = mapped_column(Boolean, default=False)
    table_type: Mapped[str] = mapped_column(String(50), default="data_table")
    detection_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    extraction_method: Mapped[str] = mapped_column(String(50), nullable=False)
    extraction_time: Mapped[float] = mapped_column(Float, nullable=False)
    table_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    job: Mapped["ProcessingJobDB"] = relationship("ProcessingJobDB", back_populates="extracted_tables")
    __table_args__ = (
        Index('idx_table_job_page', 'job_id', 'page_number'),
        Index('idx_table_structure', 'rows', 'columns'),
        Index('idx_table_type', 'table_type'),
        UniqueConstraint('job_id', 'page_number', 'table_index', name='uq_table_job_page_index'),
    )

class FileHashDB(Base):
    __tablename__ = "file_hashes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    file_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    first_processed_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    last_processed_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    processing_count: Mapped[int] = mapped_column(Integer, default=1)
    last_job_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("processing_jobs.id"), nullable=True)
    __table_args__ = (
        Index('idx_hash_file_path', 'file_path'),
        Index('idx_hash_last_processed', 'last_processed_at'),
    )

class ProcessingSessionDB(Base):
    __tablename__ = "processing_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    session_name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    total_files: Mapped[int] = mapped_column(Integer, default=0)
    processed_files: Mapped[int] = mapped_column(Integer, default=0)
    failed_files: Mapped[int] = mapped_column(Integer, default=0)
    total_processing_time: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    session_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    __table_args__ = (
        Index('idx_session_status', 'status'),
        Index('idx_session_created', 'created_at'),
    ) 