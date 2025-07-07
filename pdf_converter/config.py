"""Configuration management for the PDF to Excel converter."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, List, Dict

from dotenv import load_dotenv
from pydantic import BaseModel, Field, validator

# Load environment variables
load_dotenv()


class AppConfig(BaseModel):
    """Application configuration with type-safe validation."""
    
    # Application settings
    app_name: str = Field(default="PDF to Excel Converter", description="Application name")
    app_version: str = Field(default="1.0.0", description="Application version")
    
    # File paths
    default_output_dir: Path = Field(
        default=Path.home() / "Documents" / "PDF_Exports",
        description="Default output directory for Excel files"
    )
    temp_dir: Path = Field(
        default=Path.home() / ".pdf_converter" / "temp",
        description="Temporary directory for processing"
    )
    
    # Processing settings
    max_file_size_mb: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum PDF file size in MB"
    )
    supported_formats: List[str] = Field(
        default_factory=lambda: [".pdf"],
        description="Supported input file formats"
    )
    output_formats: List[str] = Field(
        default_factory=lambda: [".xlsx", ".xls"],
        description="Supported output file formats"
    )
    
    # UI settings
    window_width: int = Field(default=1200, ge=800, description="Main window width")
    window_height: int = Field(default=800, ge=600, description="Main window height")
    theme: str = Field(default="light", description="UI theme (light/dark)")
    
    # Logging settings
    log_level: str = Field(default="INFO", description="Logging level")
    log_file: Path = Field(
        default=Path.home() / ".pdf_converter" / "logs" / "app.log",
        description="Log file path"
    )
    
    @validator("default_output_dir", "temp_dir", "log_file")
    def create_directories(cls, v: Path) -> Path:
        """Create directories if they don't exist."""
        v.mkdir(parents=True, exist_ok=True)
        return v
    
    @validator("log_file")
    def create_log_directory(cls, v: Path) -> Path:
        """Create log directory if it doesn't exist."""
        v.parent.mkdir(parents=True, exist_ok=True)
        return v
    
    @classmethod
    def from_env(cls) -> AppConfig:
        """Create configuration from environment variables."""
        return cls(
            app_name=os.getenv("APP_NAME", "PDF to Excel Converter"),
            app_version=os.getenv("APP_VERSION", "1.0.0"),
            default_output_dir=Path(os.getenv("DEFAULT_OUTPUT_DIR", str(Path.home() / "Documents" / "PDF_Exports"))),
            temp_dir=Path(os.getenv("TEMP_DIR", str(Path.home() / ".pdf_converter" / "temp"))),
            max_file_size_mb=int(os.getenv("MAX_FILE_SIZE_MB", "100")),
            window_width=int(os.getenv("WINDOW_WIDTH", "1200")),
            window_height=int(os.getenv("WINDOW_HEIGHT", "800")),
            theme=os.getenv("THEME", "light"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            log_file=Path(os.getenv("LOG_FILE", str(Path.home() / ".pdf_converter" / "logs" / "app.log"))),
        )


# Global configuration instance
config = AppConfig.from_env() 