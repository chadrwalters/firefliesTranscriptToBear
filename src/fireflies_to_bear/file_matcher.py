"""Component for matching corresponding summary and transcript PDF files."""

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from .file_monitor import MonitoredFile


@dataclass
class MatchedFiles:
    """Represents a pair of matched summary and transcript files."""

    summary: MonitoredFile
    transcript: MonitoredFile
    meeting_date: datetime
    meeting_name: str


class FileMatcher:
    """Matches corresponding summary and transcript files based on filename patterns."""

    # Example filenames:
    # "Chad Walters and Makaela Gradowski-summary-2025-03-04T16-17-00.058Z.pdf"
    # "Chad Walters and Makaela Gradowski-transcript-2025-03-04T16-16-59.663Z.pdf"
    FILENAME_PATTERN = re.compile(
        r"^(?P<name>.*?)-(?P<type>summary|transcript)-(?P<timestamp>\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}\.\d{3}Z)\.pdf$",
        re.IGNORECASE,
    )

    def __init__(self) -> None:
        """Initialize the FileMatcher."""
        self.logger = logging.getLogger(__name__)

    def _parse_filename(
        self, file: MonitoredFile
    ) -> Optional[Tuple[datetime, str, str]]:
        """Parse a filename to extract date, meeting name, and file type.

        Args:
            file: MonitoredFile object to parse

        Returns:
            Tuple of (datetime, meeting_name, file_type) if successful, None if parsing fails
        """
        match = self.FILENAME_PATTERN.match(file.path.name)
        if not match:
            self.logger.warning(f"Failed to parse filename: {file.path.name}")
            return None

        try:
            timestamp_str = match.group("timestamp")
            meeting_date = datetime.strptime(timestamp_str, "%Y-%m-%dT%H-%M-%S.%fZ")
            meeting_name = match.group("name").strip()
            file_type = match.group("type").lower()
            return meeting_date, meeting_name, file_type
        except (ValueError, AttributeError) as e:
            self.logger.error(f"Error parsing filename {file.path.name}: {e}")
            return None

    def match_files(self, files: List[MonitoredFile]) -> List[MatchedFiles]:
        """Match corresponding summary and transcript files from a list of files.

        Args:
            files: List of MonitoredFile objects to match

        Returns:
            List of MatchedFiles objects containing paired files
        """
        # Group files by meeting name and approximate timestamp (within 5 seconds)
        FileGroup = Dict[str, Optional[MonitoredFile]]
        file_groups: Dict[Tuple[str, datetime], FileGroup] = {}

        for file in files:
            parsed = self._parse_filename(file)
            if not parsed:
                continue

            meeting_date, meeting_name, file_type = parsed

            # Find a matching group or create a new one
            matched_key = None
            for (existing_name, existing_date), group in file_groups.items():
                if (
                    existing_name == meeting_name
                    and abs((existing_date - meeting_date).total_seconds()) < 5
                ):
                    matched_key = (existing_name, existing_date)
                    break

            if not matched_key:
                matched_key = (meeting_name, meeting_date)
                file_groups[matched_key] = {"summary": None, "transcript": None}

            file_groups[matched_key][file_type] = file

        # Create MatchedFiles objects for complete pairs
        matched_files: List[MatchedFiles] = []
        for (name, date), group in file_groups.items():
            if group["summary"] and group["transcript"]:
                matched_files.append(
                    MatchedFiles(
                        summary=group["summary"],
                        transcript=group["transcript"],
                        meeting_date=date,
                        meeting_name=name,
                    )
                )
            else:
                self.logger.info(
                    f"Incomplete file pair for meeting '{name}' on {date.strftime('%Y-%m-%d %H:%M:%S')}"
                )

        return matched_files
