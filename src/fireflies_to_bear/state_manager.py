"""Component for managing application state and file tracking."""

import hashlib
import json
import logging
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .file_matcher import MatchedFiles


@dataclass
class ProcessedFile:
    """Represents a processed file pair and its metadata."""

    summary_path: str
    summary_hash: str
    transcript_path: str
    transcript_hash: str
    bear_note_id: str
    last_processed: str  # ISO format datetime string


class StateManager:
    """Manages application state and file tracking."""

    def __init__(self, state_file: Path, backup_count: int = 3) -> None:
        """Initialize the StateManager.

        Args:
            state_file: Path to the state file
            backup_count: Number of backup files to maintain
        """
        self.state_file = Path(state_file)
        self.backup_count = backup_count
        self.logger = logging.getLogger(__name__)

        # Create state file directory if it doesn't exist
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

        # Initialize or load state
        self.processed_files: Dict[str, ProcessedFile] = {}
        self._load_state()

    def _compute_file_hash(self, file_path: Path) -> str:
        """Compute SHA-256 hash of a file.

        Args:
            file_path: Path to the file to hash

        Returns:
            Hex digest of the file hash
        """
        sha256_hash = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                # Read file in chunks to handle large files
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception as e:
            self.logger.error(f"Error computing hash for {file_path}: {e}")
            return ""

    def _create_backup(self) -> None:
        """Create a backup of the state file."""
        if not self.state_file.exists():
            return

        try:
            # Create backup with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.state_file.with_suffix(f".{timestamp}.bak")
            shutil.copy2(self.state_file, backup_path)

            # Get list of all backup files sorted by timestamp (oldest first)
            backup_files = sorted(
                [
                    f
                    for f in self.state_file.parent.glob(
                        f"{self.state_file.stem}.*.bak"
                    )
                ]
            )

            # Remove oldest backups if we exceed backup_count
            while len(backup_files) > self.backup_count:
                try:
                    backup_files[0].unlink()
                    backup_files.pop(0)
                except Exception as e:
                    self.logger.error(
                        f"Error removing old backup {backup_files[0]}: {e}"
                    )
                    break

        except Exception as e:
            self.logger.error(f"Error creating state file backup: {e}")

    def _load_state(self) -> None:
        """Load state from the state file."""
        if not self.state_file.exists():
            self.logger.info(f"State file not found at {self.state_file}")
            return

        try:
            with open(self.state_file, "r") as f:
                data = json.load(f)
                for entry in data.get("processed_files", []):
                    processed_file = ProcessedFile(**entry)
                    key = self._get_file_pair_key(
                        Path(processed_file.summary_path),
                        Path(processed_file.transcript_path),
                    )
                    self.processed_files[key] = processed_file

        except Exception as e:
            self.logger.error(f"Error loading state file: {e}")
            # Try to restore from backup
            self._restore_from_backup()

    def _save_state(self) -> None:
        """Save current state to the state file."""
        try:
            # Create backup before saving
            self._create_backup()

            # Save current state
            data = {
                "processed_files": [
                    asdict(file) for file in self.processed_files.values()
                ]
            }
            with open(self.state_file, "w") as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            self.logger.error(f"Error saving state file: {e}")

    def _restore_from_backup(self) -> None:
        """Attempt to restore state from the most recent backup."""
        try:
            backup_files = sorted(
                self.state_file.parent.glob(f"{self.state_file.stem}.*.bak"),
                reverse=True,
            )
            if not backup_files:
                self.logger.warning("No backup files found")
                return

            self.logger.info(f"Attempting to restore from {backup_files[0]}")
            shutil.copy2(backup_files[0], self.state_file)
            self._load_state()

        except Exception as e:
            self.logger.error(f"Error restoring from backup: {e}")

    def _get_file_pair_key(self, summary_path: Path, transcript_path: Path) -> str:
        """Generate a unique key for a file pair.

        Args:
            summary_path: Path to the summary file
            transcript_path: Path to the transcript file

        Returns:
            Unique string key for the file pair
        """
        # Use relative paths to make the state file portable
        return f"{summary_path.name}|{transcript_path.name}"

    def get_processed_files(self) -> List[ProcessedFile]:
        """Get list of all processed files.

        Returns:
            List of ProcessedFile objects
        """
        return list(self.processed_files.values())

    def get_file_state(self, matched_files: MatchedFiles) -> Optional[ProcessedFile]:
        """Get the state of a matched file pair.

        Args:
            matched_files: MatchedFiles object to check

        Returns:
            ProcessedFile if the pair has been processed before, None otherwise
        """
        key = self._get_file_pair_key(
            matched_files.summary.path, matched_files.transcript.path
        )
        return self.processed_files.get(key)

    def has_files_changed(self, matched_files: MatchedFiles) -> bool:
        """Check if either file in a pair has changed since last processing.

        Args:
            matched_files: MatchedFiles object to check

        Returns:
            True if either file has changed, False otherwise
        """
        state = self.get_file_state(matched_files)
        if not state:
            return True

        summary_hash = self._compute_file_hash(matched_files.summary.path)
        transcript_hash = self._compute_file_hash(matched_files.transcript.path)

        return (
            summary_hash != state.summary_hash
            or transcript_hash != state.transcript_hash
        )

    def update_file_state(self, matched_files: MatchedFiles, bear_note_id: str) -> None:
        """Update the state for a processed file pair.

        Args:
            matched_files: MatchedFiles object that was processed
            bear_note_id: Bear note identifier for the created/updated note
        """
        key = self._get_file_pair_key(
            matched_files.summary.path, matched_files.transcript.path
        )

        self.processed_files[key] = ProcessedFile(
            summary_path=str(matched_files.summary.path),
            summary_hash=self._compute_file_hash(matched_files.summary.path),
            transcript_path=str(matched_files.transcript.path),
            transcript_hash=self._compute_file_hash(matched_files.transcript.path),
            bear_note_id=bear_note_id,
            last_processed=datetime.now().isoformat(),
        )

        self._save_state()

    def remove_file_state(self, matched_files: MatchedFiles) -> None:
        """Remove the state for a file pair.

        Args:
            matched_files: MatchedFiles object to remove
        """
        key = self._get_file_pair_key(
            matched_files.summary.path, matched_files.transcript.path
        )
        if key in self.processed_files:
            del self.processed_files[key]
            self._save_state()
