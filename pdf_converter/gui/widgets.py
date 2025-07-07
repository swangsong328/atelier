"""GUI widgets for the PDF to Excel converter."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

try:
    from PyQt6.QtCore import pyqtSignal, Qt
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
        QLineEdit, QProgressBar, QTextEdit, QGroupBox, QCheckBox,
        QComboBox, QSpinBox, QFileDialog, QFrame, QScrollArea
    )
except ImportError:
    # Fallback for development without PyQt6
    pyqtSignal = None
    Qt = None
    QWidget = None
    QVBoxLayout = None
    QHBoxLayout = None
    QLabel = None
    QPushButton = None
    QLineEdit = None
    QProgressBar = None
    QTextEdit = None
    QGroupBox = None
    QCheckBox = None
    QComboBox = None
    QSpinBox = None
    QFileDialog = None
    QFrame = None
    QScrollArea = None

from ..models import PDFProcessingOptions, ExcelOutputOptions

# Move widget class definitions to the bottom, after all imports and checks

if all(x is not None for x in [QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, QGroupBox, QCheckBox, QComboBox, QFileDialog, QProgressBar, QTextEdit]):
    class FileSelectorWidget(QWidget):
        """Widget for selecting PDF files."""
        file_selected = pyqtSignal(Path)
        def __init__(self) -> None:
            super().__init__()
            self.file_path: Optional[Path] = None
            self.setup_ui()
        def setup_ui(self) -> None:
            layout = QVBoxLayout(self)
            layout.setContentsMargins(10, 10, 10, 10)
            title = QLabel("Select PDF File")
            title.setStyleSheet("font-weight: bold; font-size: 14px;")
            layout.addWidget(title)
            self.path_label = QLabel("No file selected")
            self.path_label.setStyleSheet("color: #666; padding: 5px; border: 1px solid #ccc; border-radius: 3px;")
            layout.addWidget(self.path_label)
            button_layout = QHBoxLayout()
            self.browse_button = QPushButton("Browse...")
            self.browse_button.clicked.connect(self.browse_file)
            button_layout.addWidget(self.browse_button)
            self.clear_button = QPushButton("Clear")
            self.clear_button.clicked.connect(self.clear_file)
            self.clear_button.setEnabled(False)
            button_layout.addWidget(self.clear_button)
            layout.addLayout(button_layout)
        def browse_file(self) -> None:
            if QFileDialog is not None:
                file_path, _ = QFileDialog.getOpenFileName(
                    self,
                    "Select PDF File",
                    str(Path.home()),
                    "PDF Files (*.pdf);;All Files (*)"
                )
                if file_path:
                    self.set_file_path(Path(file_path))
        def set_file_path(self, file_path: Path) -> None:
            self.file_path = file_path
            self.path_label.setText(str(file_path))
            self.clear_button.setEnabled(True)
            self.file_selected.emit(file_path)
        def clear_file(self) -> None:
            self.file_path = None
            self.path_label.setText("No file selected")
            self.clear_button.setEnabled(False)
        def get_file_path(self) -> Optional[Path]:
            return self.file_path

    class ProcessingOptionsWidget(QWidget):
        """Widget for configuring processing options."""
        def __init__(self) -> None:
            super().__init__()
            self.setup_ui()
        def setup_ui(self) -> None:
            layout = QVBoxLayout(self)
            layout.setContentsMargins(10, 10, 10, 10)
            title = QLabel("Processing Options")
            title.setStyleSheet("font-weight: bold; font-size: 14px;")
            layout.addWidget(title)
            # Only Report Type selector
            report_type_layout = QHBoxLayout()
            report_type_layout.addWidget(QLabel("Report Type:"))
            self.report_type_combo = QComboBox()
            self.report_type_combo.addItems(["Standard", "DD"])
            report_type_layout.addWidget(self.report_type_combo)
            layout.addLayout(report_type_layout)
            layout.addStretch()

        def get_pdf_options(self) -> PDFProcessingOptions:
            # Return default PDFProcessingOptions since PDF options are removed
            return PDFProcessingOptions()

        def get_excel_options(self) -> ExcelOutputOptions:
            return ExcelOutputOptions(report_type=self.report_type_combo.currentText())

    class ProgressWidget(QWidget):
        """Widget for displaying processing progress."""
        start_processing = pyqtSignal()
        cancel_processing = pyqtSignal()
        def __init__(self) -> None:
            super().__init__()
            self.setup_ui()
        def setup_ui(self) -> None:
            layout = QVBoxLayout(self)
            layout.setContentsMargins(10, 10, 10, 10)
            title = QLabel("Processing Progress")
            title.setStyleSheet("font-weight: bold; font-size: 14px;")
            layout.addWidget(title)
            self.progress_bar = QProgressBar()
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(0)
            layout.addWidget(self.progress_bar)
            self.status_label = QLabel("Ready")
            self.status_label.setStyleSheet("color: #666;")
            layout.addWidget(self.status_label)
            button_layout = QHBoxLayout()
            self.start_button = QPushButton("Start Processing")
            self.start_button.clicked.connect(self.start_processing.emit)
            self.start_button.setEnabled(False)
            button_layout.addWidget(self.start_button)
            self.cancel_button = QPushButton("Cancel")
            self.cancel_button.clicked.connect(self.cancel_processing.emit)
            self.cancel_button.setEnabled(False)
            button_layout.addWidget(self.cancel_button)
            layout.addLayout(button_layout)
            results_group = QGroupBox("Results")
            results_layout = QVBoxLayout(results_group)
            self.results_text = QTextEdit()
            self.results_text.setReadOnly(True)
            self.results_text.setMaximumHeight(200)
            results_layout.addWidget(self.results_text)
            layout.addWidget(results_group)
        def update_progress(self, percentage: int, message: str) -> None:
            self.progress_bar.setValue(percentage)
            self.status_label.setText(message)
        def start_progress(self) -> None:
            self.progress_bar.setValue(0)
            self.status_label.setText("Processing...")
            self.start_button.setEnabled(False)
            self.cancel_button.setEnabled(True)
            self.results_text.clear()
        def stop_progress(self) -> None:
            self.status_label.setText("Ready")
            self.start_button.setEnabled(True)
            self.cancel_button.setEnabled(False)
        def complete_progress(self, result: Any) -> None:
            self.progress_bar.setValue(100)
            self.status_label.setText("Completed")
            self.start_button.setEnabled(True)
            self.cancel_button.setEnabled(False)
            if hasattr(result, 'job') and result.job:
                summary = f"""
Processing completed successfully!

Job ID: {result.job.id}
Pages Processed: {result.job.pages_processed}
Tables Extracted: {result.job.tables_extracted}
Text Blocks Extracted: {result.job.text_blocks_extracted}
Processing Time: {result.processing_time:.2f} seconds

Output File: {result.job.output_file.name if result.job.output_file else 'Not available'}
                """
                self.results_text.setPlainText(summary.strip())
        def set_start_enabled(self, enabled: bool) -> None:
            self.start_button.setEnabled(enabled) 