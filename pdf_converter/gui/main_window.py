"""Main application window for the PDF to Excel converter."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

try:
    from PyQt6.QtCore import QThread, pyqtSignal, Qt, QTimer
    from PyQt6.QtGui import QAction, QIcon, QFont
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QSplitter, QTabWidget, QStatusBar, QMessageBox, QFileDialog,
        QMenuBar, QToolBar, QLabel, QFrame, QPushButton, QComboBox,
        QListWidget
    )
except ImportError:
    # Fallback for development without PyQt6
    QThread = None
    pyqtSignal = None
    Qt = None
    QAction = None
    QIcon = None
    QFont = None
    QApplication = None
    QMainWindow = None
    QWidget = None
    QVBoxLayout = None
    QHBoxLayout = None
    QSplitter = None
    QTabWidget = None
    QStatusBar = None
    QMessageBox = None
    QFileDialog = None
    QMenuBar = None
    QToolBar = None
    QLabel = None
    QFrame = None
    QPushButton = None
    QComboBox = None

from ..config import config
from ..models import ProcessingJob, ProcessingStatus
from ..processors import PDFProcessor, ExcelWriter
from ..utils import generate_job_id, validate_pdf_file
from .widgets import FileSelectorWidget, ProcessingOptionsWidget, ProgressWidget


class ProcessingThread(QThread):
    """Background thread for PDF processing."""
    
    progress_updated = pyqtSignal(int, str)
    job_completed = pyqtSignal(object)
    job_failed = pyqtSignal(str)
    
    def __init__(self, job: ProcessingJob) -> None:
        """Initialize the processing thread."""
        super().__init__()
        self.job = job
        self.pdf_processor = PDFProcessor()
        self.excel_writer = ExcelWriter()
        
        # Set up progress callback
        self.pdf_processor.set_progress_callback(self._progress_callback)
    
    def _progress_callback(self, current_page: int, message: str) -> float:
        """Progress callback for the processor."""
        progress = (current_page / max(1, self.job.pages_processed)) * 100
        self.progress_updated.emit(int(progress), message)
        return progress
    
    def run(self) -> None:
        """Run the processing job."""
        try:
            # Process PDF
            result = self.pdf_processor.process(self.job)
            
            if result.job.status == ProcessingStatus.COMPLETED:
                # Write to Excel
                output_path = self.excel_writer.write_to_excel(result)
                result.job.output_file = output_path
                self.job_completed.emit(result)
            else:
                self.job_failed.emit(result.job.error_message or "Processing failed")
                
        except Exception as e:
            self.job_failed.emit(str(e))


class DragDropBox(QWidget):
    files_dropped = pyqtSignal(list)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMinimumHeight(160)
        self.setStyleSheet("border: 2px dashed #888; border-radius: 8px; background: #fafafa;")
        layout = QVBoxLayout(self)
        self.label = QLabel("Drag and drop PDF files here")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("font-size: 16px; color: #666;")
        layout.addWidget(self.label)
        self.file_list = QListWidget()
        self.file_list.setStyleSheet("background: #fff; border: none; font-size: 13px;")
        layout.addWidget(self.file_list)
        self.clear_button = QPushButton("Clear List")
        self.clear_button.clicked.connect(self.clear_files)
        layout.addWidget(self.clear_button)
        self.files = []
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    def dropEvent(self, event):
        files = [url.toLocalFile() for url in event.mimeData().urls() if url.toLocalFile().lower().endswith('.pdf')]
        if files:
            self.add_files(files)
            self.files_dropped.emit(files)
    def add_files(self, files):
        for f in files:
            if f not in self.files:
                self.files.append(f)
                self.file_list.addItem(f)
    def clear_files(self):
        self.files = []
        self.file_list.clear()


class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self) -> None:
        """Initialize the main window."""
        super().__init__()
        self.processing_thread: Optional[ProcessingThread] = None
        self.current_job: Optional[ProcessingJob] = None
        self.file_queue = []  # List of files to process
        self.setup_ui()
        self.setup_menu()
        self.setup_toolbar()
        self.setup_status_bar()
        self.apply_styles()
        # Enable drag and drop
        self.setAcceptDrops(True)
    
    def setup_ui(self) -> None:
        self.setWindowTitle(f"{config.app_name} v{config.app_version}")
        self.setGeometry(100, 100, config.window_width, config.window_height)
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Top: Large, centered Start Processing button
        self.start_button = QPushButton("Start Processing")
        self.start_button.setMinimumHeight(60)
        self.start_button.setStyleSheet("font-size: 24px; font-weight: bold;")
        self.start_button.clicked.connect(self.start_processing)
        main_layout.addWidget(self.start_button, alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)

        # Bottom: Horizontal split (left: report type, right: log/result)
        bottom_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(bottom_splitter, stretch=1)

        # Left: Report type selector (only DD enabled) + drag/drop box
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_layout.setSpacing(10)
        # Top: Report type
        self.options_widget = ProcessingOptionsWidget()
        self.options_widget.report_type_combo.clear()
        self.options_widget.report_type_combo.addItem("DD")
        self.options_widget.report_type_combo.setCurrentIndex(0)
        self.options_widget.report_type_combo.setEnabled(False)
        left_layout.addWidget(QLabel("Report Type:"))
        left_layout.addWidget(self.options_widget.report_type_combo)
        # Bottom: Drag/drop box
        self.drag_drop_box = DragDropBox()
        self.drag_drop_box.files_dropped.connect(self.on_files_dropped)
        left_layout.addWidget(self.drag_drop_box)
        left_layout.addStretch()
        bottom_splitter.addWidget(left_panel)

        # Right: Conversion log/result
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(10, 10, 10, 10)
        right_layout.setSpacing(10)
        self.progress_widget = ProgressWidget()
        right_layout.addWidget(self.progress_widget)
        bottom_splitter.addWidget(right_panel)

        # Hide file_selector visually but keep for logic
        self.file_selector = FileSelectorWidget()
        self.file_selector.hide()
        main_layout.addWidget(self.file_selector)

        # Connect signals
        self.file_selector.file_selected.connect(self.on_file_selected)
        self.progress_widget.cancel_processing.connect(self.cancel_processing)
    
    def create_header(self) -> QWidget:
        """Create the application header."""
        header = QFrame()
        header.setFrameStyle(QFrame.Shape.StyledPanel)
        header.setMaximumHeight(80)
        
        layout = QHBoxLayout(header)
        layout.setContentsMargins(20, 10, 20, 10)
        
        # App title
        title_label = QLabel(config.app_name)
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # Version
        version_label = QLabel(f"v{config.app_version}")
        version_font = QFont()
        version_font.setPointSize(10)
        version_label.setFont(version_font)
        layout.addWidget(version_label)
        
        layout.addStretch()
        
        return header
    
    def setup_menu(self) -> None:
        """Set up the menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("&File")
        
        open_action = QAction("&Open PDF", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Tools menu
        tools_menu = menubar.addMenu("&Tools")
        
        settings_action = QAction("&Settings", self)
        settings_action.triggered.connect(self.show_settings)
        tools_menu.addAction(settings_action)
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        
        about_action = QAction("&About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def setup_toolbar(self) -> None:
        """Set up the toolbar."""
        toolbar = QToolBar()
        self.addToolBar(toolbar)
        
        # Open file action
        open_action = QAction("Open", self)
        open_action.triggered.connect(self.open_file)
        toolbar.addAction(open_action)
        
        toolbar.addSeparator()
        
        # Start processing action
        self.start_action = QAction("Start Processing", self)
        self.start_action.triggered.connect(self.start_processing)
        self.start_action.setEnabled(False)
        toolbar.addAction(self.start_action)
    
    def setup_status_bar(self) -> None:
        """Set up the status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
    
    def apply_styles(self) -> None:
        """Apply application styling."""
        if config.theme == "dark":
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #2b2b2b;
                    color: #ffffff;
                }
                QWidget {
                    background-color: #2b2b2b;
                    color: #ffffff;
                }
                QFrame {
                    border: 1px solid #555555;
                    background-color: #3b3b3b;
                }
                QPushButton {
                    background-color: #4a4a4a;
                    border: 1px solid #555555;
                    padding: 8px 16px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #5a5a5a;
                }
                QPushButton:pressed {
                    background-color: #3a3a3a;
                }
                QLineEdit, QTextEdit {
                    background-color: #3b3b3b;
                    border: 1px solid #555555;
                    padding: 4px;
                    border-radius: 2px;
                }
                QTabWidget::pane {
                    border: 1px solid #555555;
                    background-color: #2b2b2b;
                }
                QTabBar::tab {
                    background-color: #3b3b3b;
                    padding: 8px 16px;
                    margin-right: 2px;
                }
                QTabBar::tab:selected {
                    background-color: #4a4a4a;
                }
            """)
    
    def open_file(self) -> None:
        """Open file dialog."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select PDF File",
            str(Path.home()),
            "PDF Files (*.pdf);;All Files (*)"
        )
        
        if file_path:
            self.file_selector.set_file_path(Path(file_path))
    
    def on_file_selected(self, file_path: Path) -> None:
        """Handle file selection."""
        # Validate file
        is_valid, error_msg = validate_pdf_file(file_path)
        
        if is_valid:
            self.status_bar.showMessage(f"File selected: {file_path.name}")
            self.start_action.setEnabled(True)
        else:
            QMessageBox.warning(self, "Invalid File", error_msg or "Invalid PDF file")
            self.start_action.setEnabled(False)
    
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        files = [url.toLocalFile() for url in event.mimeData().urls() if url.toLocalFile().lower().endswith('.pdf')]
        if files:
            self.file_queue.extend(files)
            self.status_bar.showMessage(f"Queued {len(files)} PDF(s) for processing.")
            self.start_button.setEnabled(True)

    def on_files_dropped(self, files):
        self.drag_drop_box.add_files(files)
        self.file_queue.extend(files)
        self.status_bar.showMessage(f"Queued {len(self.file_queue)} PDF(s) for processing.")
        self.start_button.setEnabled(True)

    def start_processing(self) -> None:
        if not self.file_queue:
            file_path = self.file_selector.get_file_path()
            if not file_path:
                QMessageBox.warning(self, "No File", "Please drag and drop PDF files or select one.")
                return
            self.file_queue.append(str(file_path))
        self.start_button.setEnabled(False)
        self.process_next_file()

    def process_next_file(self):
        if not self.file_queue:
            self.status_bar.showMessage("All files processed.")
            self.start_button.setEnabled(True)
            return
        file_path = Path(self.file_queue.pop(0))
        is_valid, error_msg = validate_pdf_file(file_path)
        if not is_valid:
            QMessageBox.warning(self, "Invalid File", error_msg or "Invalid PDF file")
            self.process_next_file()
            return
        job_id = generate_job_id()
        self.current_job = ProcessingJob(
            id=job_id,
            input_file=file_path,
            pdf_options=self.options_widget.get_pdf_options(),
            excel_options=self.options_widget.get_excel_options()
        )
        self.processing_thread = ProcessingThread(self.current_job)
        self.processing_thread.progress_updated.connect(self.progress_widget.update_progress)
        self.processing_thread.job_completed.connect(self.on_job_completed)
        self.processing_thread.job_failed.connect(self.on_job_failed)
        self.progress_widget.show()
        self.progress_widget.start_progress()
        self.status_bar.showMessage(f"Processing {file_path.name}...")
        self.processing_thread.start()

    def cancel_processing(self) -> None:
        """Cancel current processing job."""
        if self.processing_thread and self.processing_thread.isRunning():
            self.processing_thread.terminate()
            self.processing_thread.wait()
            
            if self.current_job:
                self.current_job.status = ProcessingStatus.CANCELLED
            
            self.progress_widget.stop_progress()
            self.start_action.setEnabled(True)
            self.status_bar.showMessage("Processing cancelled")
    
    def on_job_completed(self, result) -> None:
        """Handle job completion."""
        self.progress_widget.complete_progress(result)
        self.status_bar.showMessage(f"Completed: {result.job.output_file.name}")
        self.process_next_file()
    
    def on_job_failed(self, error_msg: str) -> None:
        """Handle job failure."""
        self.progress_widget.stop_progress()
        self.status_bar.showMessage("Processing failed")
        QMessageBox.critical(self, "Processing Failed", f"Error: {error_msg}")
        self.process_next_file()
    
    def show_settings(self) -> None:
        """Show settings dialog."""
        QMessageBox.information(self, "Settings", "Settings dialog not implemented yet")
    
    def show_about(self) -> None:
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About",
            f"{config.app_name} v{config.app_version}\n\n"
            "Enterprise-level PDF to Excel converter\n"
            "Built with Python and PyQt6"
        )
    
    def closeEvent(self, event) -> None:
        """Handle application close event."""
        if self.processing_thread and self.processing_thread.isRunning():
            reply = QMessageBox.question(
                self,
                "Confirm Exit",
                "Processing is in progress. Are you sure you want to exit?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.cancel_processing()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept() 

if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())