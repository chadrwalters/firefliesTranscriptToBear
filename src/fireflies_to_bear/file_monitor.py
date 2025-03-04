"""File monitoring component for detecting PDF files in configured directories."""

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set


@dataclass
class MonitoredFile:
    """Represents a monitored PDF file with its metadata."""

    path: Path
    last_modified: datetime
    file_size: int


class FileMonitor:
    """Monitors specified directories for PDF files and detects changes."""

    def __init__(self, summary_dir: str, transcript_dir: str):
        """Initialize the FileMonitor.

        Args:
            summary_dir: Directory path containing summary PDFs
            transcript_dir: Directory path containing transcript PDFs
        """
        self.summary_dir = Path(summary_dir)
        self.transcript_dir = Path(transcript_dir)
        self.logger = logging.getLogger(__name__)

        # Validate directories exist
        if not self.summary_dir.exists():
            raise ValueError(f"Summary directory does not exist: {summary_dir}")
        if not self.transcript_dir.exists():
            raise ValueError(f"Transcript directory does not exist: {transcript_dir}")

        # Track known files and their metadata
        self._known_files: Dict[Path, MonitoredFile] = {}

    def scan_directories(self) -> List[MonitoredFile]:
        """Scan configured directories and return list of new or modified files.

        Returns:
            List of MonitoredFile objects that are new or modified since last scan
        """
        changed_files: List[MonitoredFile] = []
        current_files: Set[Path] = set()

        # Scan both directories
        for directory in [self.summary_dir, self.transcript_dir]:
            try:
                for file_path in directory.glob("*.pdf"):
                    current_files.add(file_path)
                    stat = file_path.stat()

                    monitored_file = MonitoredFile(
                        path=file_path,
                        last_modified=datetime.fromtimestamp(stat.st_mtime),
                        file_size=stat.st_size,
                    )

                    # Check if file is new or modified
                    if file_path not in self._known_files:
                        self.logger.info(f"New file detected: {file_path}")
                        changed_files.append(monitored_file)
                    elif (
                        self._known_files[file_path].last_modified
                        != monitored_file.last_modified
                        or self._known_files[file_path].file_size
                        != monitored_file.file_size
                    ):
                        self.logger.info(f"Modified file detected: {file_path}")
                        changed_files.append(monitored_file)

                    # Update known files
                    self._known_files[file_path] = monitored_file

            except Exception as e:
                self.logger.error(f"Error scanning directory {directory}: {e}")
                continue

        # Remove tracking for files that no longer exist
        removed_files = set(self._known_files.keys()) - current_files
        for file_path in removed_files:
            self.logger.info(
                f"File no longer exists, removing from tracking: {file_path}"
            )
            del self._known_files[file_path]

        return changed_files
