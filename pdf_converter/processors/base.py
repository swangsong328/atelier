"""Base processor class for PDF processing."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional

from ..models import ProcessingJob, ProcessingResult


class BaseProcessor(ABC):
    """Abstract base class for PDF processors."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the processor.
        
        Args:
            config: Configuration dictionary for the processor
        """
        self.config = config or {}
        self._progress_callback: Optional[Callable[[int, str], float]] = None
    
    @abstractmethod
    def can_process(self, file_path: str) -> bool:
        """Check if this processor can handle the given file.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            True if the processor can handle this file type
        """
        pass
    
    @abstractmethod
    def process(self, job: ProcessingJob) -> ProcessingResult:
        """Process the PDF file according to the job specifications.
        
        Args:
            job: Processing job with all necessary parameters
            
        Returns:
            Processing result with extracted data and metadata
        """
        pass
    
    def set_progress_callback(self, callback: Callable[[int, str], float]) -> None:
        """Set the progress callback function.
        
        Args:
            callback: Function to call with progress updates
        """
        self._progress_callback = callback
    
    def update_progress(self, current_page: int, message: str = "") -> float:
        """Update progress and call the progress callback if set.
        
        Args:
            current_page: Current page being processed
            message: Progress message
            
        Returns:
            Progress percentage
        """
        if self._progress_callback:
            return self._progress_callback(current_page, message)
        return 0.0
    
    def validate_job(self, job: ProcessingJob) -> tuple[bool, Optional[str]]:
        """Validate a processing job.
        
        Args:
            job: Job to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Basic validation
            if not job.input_file.exists():
                return False, f"Input file does not exist: {job.input_file}"
            
            if not self.can_process(str(job.input_file)):
                return False, f"Cannot process file type: {job.input_file.suffix}"
            
            return True, None
            
        except Exception as e:
            return False, f"Validation error: {str(e)}"
    
    def get_processor_info(self) -> Dict[str, Any]:
        """Get information about this processor.
        
        Returns:
            Dictionary with processor information
        """
        return {
            "name": self.__class__.__name__,
            "description": self.__doc__ or "No description available",
            "config": self.config,
        } 