"""Main application component that orchestrates the PDF processing workflow."""

import logging
import signal
import time
from dataclasses import dataclass
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Optional, Tuple, TypeVar

from .bear_integration import BearIntegration
from .file_matcher import FileMatcher, MatchedFiles
from .file_monitor import FileMonitor
from .note_generator import GeneratedNote, NoteGenerator
from .pdf_parser import PDFContent, PDFParser
from .state_manager import StateManager

# Type variable for generic function return type
T = TypeVar("T")


class ApplicationError(Exception):
    """Base class for application-specific exceptions."""

    pass


class RetryableError(ApplicationError):
    """Error that can be retried."""

    pass


class NonRetryableError(ApplicationError):
    """Error that should not be retried."""

    pass


@dataclass
class AppConfig:
    """Application configuration."""

    watch_directory: str  # Directory containing summary PDFs
    transcript_directory: str  # Directory containing transcript PDFs
    state_file: Path
    sleep_interval: int = 300  # Default to 5 minutes
    title_template: Optional[str] = None
    backup_count: int = 3
    tags: Optional[str] = None
    max_retries: int = 3  # Maximum number of retry attempts
    retry_delay: float = 1.0  # Initial delay between retries in seconds


def with_retry(max_retries: int = 3, delay: float = 1.0) -> Callable:
    """Decorator for retrying operations that may fail transiently.

    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries in seconds (doubles after each attempt)

    Returns:
        Decorated function
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_error = None
            current_delay = delay

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except RetryableError as e:
                    last_error = e
                    if attempt < max_retries:
                        logging.warning(
                            f"Attempt {attempt + 1}/{max_retries + 1} failed: {e}. "
                            f"Retrying in {current_delay:.1f} seconds..."
                        )
                        time.sleep(current_delay)
                        current_delay *= 2  # Exponential backoff
                    continue
                except NonRetryableError:
                    raise
                except Exception as e:
                    raise NonRetryableError(f"Unexpected error: {e}") from e

            raise NonRetryableError(
                f"Operation failed after {max_retries + 1} attempts: {last_error}"
            )

        return wrapper

    return decorator


class Application:
    """Main application class that orchestrates the PDF processing workflow."""

    def __init__(self, config: AppConfig) -> None:
        """Initialize the application.

        Args:
            config: Application configuration
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self._shutdown_requested = False

        # Set up signal handlers
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

        # Initialize components
        self.file_monitor = FileMonitor(
            self.config.watch_directory, self.config.transcript_directory
        )
        self.file_matcher = FileMatcher()
        self.pdf_parser = PDFParser()
        self.note_generator = NoteGenerator()
        if self.config.title_template:
            self.note_generator.title_template = self.config.title_template
        self.bear_integration = BearIntegration()
        self.state_manager = StateManager(
            self.config.state_file, backup_count=self.config.backup_count
        )

    @with_retry()
    def _parse_pdf_with_retry(self, path: Path) -> PDFContent:
        """Parse PDF content with retry logic.

        Args:
            path: Path to the PDF file

        Returns:
            PDFContent object containing the extracted content

        Raises:
            RetryableError: If parsing fails but can be retried
            NonRetryableError: If parsing fails and should not be retried
        """
        try:
            return self.pdf_parser.parse_pdf(path)
        except (IOError, OSError) as e:
            raise RetryableError(f"Error reading PDF file {path}: {e}")
        except Exception as e:
            raise NonRetryableError(f"Error parsing PDF file {path}: {e}")

    @with_retry()
    def _create_or_update_note(
        self, note: GeneratedNote, existing_state: Optional[Any] = None
    ) -> Tuple[bool, str]:
        """Create or update a Bear note with retry logic.

        Args:
            note: Note content to create or update
            existing_state: Optional existing state for the note

        Returns:
            Tuple of (success, note_identifier)

        Raises:
            RetryableError: If operation fails but can be retried
            NonRetryableError: If operation fails and should not be retried
        """
        try:
            if existing_state:
                response = self.bear_integration.update_note(
                    existing_state["bear_note_id"], note, tags=self.config.tags
                )
            else:
                response = self.bear_integration.create_note(
                    note, tags=self.config.tags
                )

            if not response.success:
                raise RetryableError(f"Bear operation failed: {response.error}")

            return response.success, response.note_identifier or ""

        except RetryableError:
            raise
        except Exception as e:
            raise NonRetryableError(f"Error interacting with Bear: {e}")

    def _process_file_pair(self, matched_files: MatchedFiles) -> None:
        """Process a matched pair of PDF files.

        Args:
            matched_files: Matched summary and transcript files
        """
        try:
            # Check if files have changed since last processing
            if not self.state_manager.has_files_changed(matched_files):
                self.logger.debug(
                    f"Files have not changed since last processing: "
                    f"{matched_files.summary.path.name}, {matched_files.transcript.path.name}"
                )
                return

            # Parse PDFs
            self.logger.info(
                f"Processing files: {matched_files.summary.path.name}, {matched_files.transcript.path.name}"
            )

            try:
                summary_content = self._parse_pdf_with_retry(matched_files.summary.path)
                if summary_content.error:
                    self.logger.error(f"Error in summary PDF: {summary_content.error}")
                    return

                transcript_content = self._parse_pdf_with_retry(
                    matched_files.transcript.path
                )
                if transcript_content.error:
                    self.logger.error(
                        f"Error in transcript PDF: {transcript_content.error}"
                    )
                    return

            except NonRetryableError as e:
                self.logger.error(f"Failed to parse PDFs: {e}")
                return

            # Generate note
            note = self.note_generator.generate_note(matched_files)
            if note.error:
                self.logger.error(f"Error generating note: {note.error}")
                return

            # Check if note exists in Bear
            existing_state = self.state_manager.get_file_state(matched_files)

            try:
                success, note_id = self._create_or_update_note(note, existing_state)
                if success:
                    # Update state
                    self.state_manager.update_file_state(matched_files, note_id)
                    self.logger.info("Successfully processed files")
            except NonRetryableError as e:
                self.logger.error(f"Failed to create/update Bear note: {e}")

        except Exception as e:
            self.logger.error(f"Error processing files: {e}")

    def process_specific_files(self, summary_path: Path, transcript_path: Path) -> None:
        """Process a specific pair of PDF files.

        Args:
            summary_path: Path to summary PDF file
            transcript_path: Path to transcript PDF file
        """
        try:
            if not summary_path.exists() or not transcript_path.exists():
                self.logger.error("One or both files do not exist")
                return

            # Create monitored file objects
            from datetime import datetime

            from .file_monitor import MonitoredFile

            # Get the current time for the modification time
            now = datetime.now()

            summary_file = MonitoredFile(
                path=summary_path,
                last_modified=now,
                file_size=summary_path.stat().st_size,
            )
            transcript_file = MonitoredFile(
                path=transcript_path,
                last_modified=now,
                file_size=transcript_path.stat().st_size,
            )

            # Create matched files object
            from .file_matcher import MatchedFiles

            matched_files = MatchedFiles(
                summary=summary_file,
                transcript=transcript_file,
                meeting_date=now,
                meeting_name=summary_path.stem.replace(" (Summary)", ""),
            )

            # Process the file pair
            self._process_file_pair(matched_files)

        except Exception as e:
            self.logger.error(f"Error processing specific files: {e}")

    def process_directory(self) -> None:
        """Process all PDF files in the watch directory."""
        try:
            # Monitor directory for PDF files
            monitored_files = self.file_monitor.scan_directories()
            self.logger.info(f"Found {len(monitored_files)} PDF files")

            # Match summary and transcript files
            matched_pairs = self.file_matcher.match_files(monitored_files)
            self.logger.info(f"Found {len(matched_pairs)} matched file pairs")

            # Process each pair
            for matched_files in matched_pairs:
                if self._shutdown_requested:
                    break
                self._process_file_pair(matched_files)

        except Exception as e:
            self.logger.error(f"Error processing directory: {e}")

    def _handle_shutdown(self, signum: int, frame: Optional[object]) -> None:
        """Handle shutdown signals gracefully.

        Args:
            signum: Signal number
            frame: Current stack frame (unused)
        """
        signal_name = signal.Signals(signum).name
        self.logger.info(f"Received {signal_name}, initiating graceful shutdown...")
        self._shutdown_requested = True

    def run(self) -> None:
        """Run the application processing loop."""
        self.logger.info(
            f"Starting PDF processor, watching directory: {self.config.watch_directory}"
        )
        self.logger.info(f"Using state file: {self.config.state_file}")
        self.logger.info(f"Sleep interval: {self.config.sleep_interval} seconds")

        try:
            while not self._shutdown_requested:
                try:
                    self.process_directory()
                except Exception as e:
                    self.logger.error(f"Error in processing loop: {e}")
                    # Continue running unless shutdown was requested
                    if not self._shutdown_requested:
                        continue

                if not self._shutdown_requested:
                    # Sleep for the configured interval
                    time.sleep(self.config.sleep_interval)

        except KeyboardInterrupt:
            self.logger.info("Received keyboard interrupt")
            self._shutdown_requested = True
        except Exception as e:
            self.logger.error(f"Fatal error: {e}")
            raise
        finally:
            self.logger.info("Shutting down...")
