"""Main entry point for the PDF to Excel converter application."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

try:
    from PyQt6.QtWidgets import QApplication
except ImportError:
    QApplication = None

from .config import config
from .gui import MainWindow
from .database import DatabaseManager


def setup_logging() -> None:
    """Set up application logging."""
    try:
        from loguru import logger
        
        # Remove default handler
        logger.remove()
        
        # Add console handler
        logger.add(
            sys.stderr,
            level=config.log_level,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
        )
        
        # Add file handler
        logger.add(
            config.log_file,
            level=config.log_level,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            rotation="10 MB",
            retention="30 days"
        )
        
        logger.info("Logging initialized")
        
    except ImportError:
        # Fallback to basic logging if loguru is not available
        import logging
        logging.basicConfig(
            level=getattr(logging, config.log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(config.log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )


def check_dependencies() -> bool:
    """Check if all required dependencies are available."""
    missing_deps = []
    
    # Check PyQt6
    if QApplication is None:
        missing_deps.append("PyQt6")
    
    # Check PDF processing libraries
    try:
        import pdfplumber
    except ImportError:
        missing_deps.append("pdfplumber")
    
    try:
        import PyPDF2
    except ImportError:
        missing_deps.append("PyPDF2")
    
    # Check Excel writing libraries
    try:
        import pandas
    except ImportError:
        missing_deps.append("pandas")
    
    try:
        import openpyxl
    except ImportError:
        missing_deps.append("openpyxl")
    
    if missing_deps:
        print("Missing required dependencies:")
        for dep in missing_deps:
            print(f"  - {dep}")
        print("\nPlease install missing dependencies:")
        print("pip install -r requirements.txt")
        return False
    
    return True


def create_directories() -> None:
    """Create necessary directories."""
    config.default_output_dir.mkdir(parents=True, exist_ok=True)
    config.temp_dir.mkdir(parents=True, exist_ok=True)
    config.log_file.parent.mkdir(parents=True, exist_ok=True)


def main() -> int:
    """Main application entry point."""
    try:
        # Setup logging
        setup_logging()
        
        # Check dependencies
        if not check_dependencies():
            return 1
        
        # Create directories
        create_directories()
        
        # Create Qt application
        if QApplication is None:
            print("PyQt6 is required to run the GUI application")
            return 1
        
        app = QApplication(sys.argv)
        app.setApplicationName(config.app_name)
        app.setApplicationVersion(config.app_version)
        app.setOrganizationName("PDF Converter")
        
        # Create and show main window
        window = MainWindow()
        window.show()
        
        # Run application
        return app.exec()
        
    except KeyboardInterrupt:
        print("\nApplication interrupted by user")
        return 0
    except Exception as e:
        print(f"Application error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 