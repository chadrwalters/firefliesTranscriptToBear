"""Tests for the file matching component."""

from datetime import datetime
from pathlib import Path
from typing import List

import pytest

from fireflies_to_bear.file_matcher import FileMatcher, MatchedFiles
from fireflies_to_bear.file_monitor import MonitoredFile


@pytest.fixture
def file_matcher() -> FileMatcher:
    """Create a FileMatcher instance for testing."""
    return FileMatcher()


@pytest.fixture
def sample_files() -> List[MonitoredFile]:
    """Create sample MonitoredFile objects for testing."""
    now = datetime.now()
    return [
        MonitoredFile(
            path=Path("Team Meeting-summary-2024-03-04T10-00-00.000Z.pdf"),
            last_modified=now,
            file_size=1024,
        ),
        MonitoredFile(
            path=Path("Team Meeting-transcript-2024-03-04T10-00-00.000Z.pdf"),
            last_modified=now,
            file_size=2048,
        ),
        MonitoredFile(
            path=Path("Project Review-summary-2024-03-05T10-00-00.000Z.pdf"),
            last_modified=now,
            file_size=1536,
        ),
        # No matching transcript for this summary
    ]


def test_parse_filename_valid(file_matcher: FileMatcher) -> None:
    """Test parsing of valid filenames."""
    file = MonitoredFile(
        path=Path("Team Meeting-summary-2024-03-04T10-00-00.000Z.pdf"),
        last_modified=datetime.now(),
        file_size=1024,
    )

    result = file_matcher._parse_filename(file)
    assert result is not None

    date, name, file_type = result
    assert date == datetime(2024, 3, 4, 10)
    assert name == "Team Meeting"
    assert file_type == "summary"


def test_parse_filename_invalid(file_matcher: FileMatcher) -> None:
    """Test parsing of invalid filenames."""
    invalid_files = [
        "invalid.pdf",
        "2024-03-04T10-00-00.000Z.pdf",
        "Team Meeting-invalid-2024-03-04T10-00-00.000Z.pdf",
        "Team Meeting-summary-invalid-date.pdf",
        "Team Meeting-summary-2024-03-04T10:00:00.000Z.pdf",  # Wrong timestamp format
    ]

    for filename in invalid_files:
        file = MonitoredFile(
            path=Path(filename), last_modified=datetime.now(), file_size=1024
        )
        assert file_matcher._parse_filename(file) is None


def test_match_files_complete_pair(
    file_matcher: FileMatcher, sample_files: List[MonitoredFile]
) -> None:
    """Test matching of complete file pairs."""
    matched = file_matcher.match_files(sample_files)
    assert len(matched) == 1

    pair = matched[0]
    assert isinstance(pair, MatchedFiles)
    assert pair.meeting_name == "Team Meeting"
    assert pair.meeting_date.date() == datetime(2024, 3, 4).date()
    assert "Team Meeting-summary-2024-03-04" in pair.summary.path.name
    assert "Team Meeting-transcript-2024-03-04" in pair.transcript.path.name


def test_match_files_incomplete_pair(file_matcher: FileMatcher) -> None:
    """Test handling of incomplete file pairs."""
    files = [
        MonitoredFile(
            path=Path("Team Meeting-summary-2024-03-04T10-00-00.000Z.pdf"),
            last_modified=datetime.now(),
            file_size=1024,
        )
    ]

    matched = file_matcher.match_files(files)
    assert len(matched) == 0


def test_match_files_case_insensitive(file_matcher: FileMatcher) -> None:
    """Test case-insensitive matching of file types."""
    now = datetime.now()
    files = [
        MonitoredFile(
            path=Path("Team Meeting-SUMMARY-2024-03-04T10-00-00.000Z.pdf"),
            last_modified=now,
            file_size=1024,
        ),
        MonitoredFile(
            path=Path("Team Meeting-transcript-2024-03-04T10-00-00.000Z.pdf"),
            last_modified=now,
            file_size=2048,
        ),
    ]

    matched = file_matcher.match_files(files)
    assert len(matched) == 1


def test_match_files_whitespace_handling(file_matcher: FileMatcher) -> None:
    """Test handling of varying whitespace in filenames."""
    now = datetime.now()
    files = [
        MonitoredFile(
            path=Path("Team  Meeting-summary-2024-03-04T10-00-00.000Z.pdf"),
            last_modified=now,
            file_size=1024,
        ),
        MonitoredFile(
            path=Path("Team  Meeting-transcript-2024-03-04T10-00-00.000Z.pdf"),
            last_modified=now,
            file_size=2048,
        ),
    ]

    matched = file_matcher.match_files(files)
    assert len(matched) == 1
    assert matched[0].meeting_name == "Team  Meeting"
