"""Tests for the file monitoring component."""

import os
import tempfile
from datetime import datetime
from pathlib import Path
from time import sleep

import pytest

from fireflies_to_bear.file_monitor import FileMonitor, MonitoredFile


@pytest.fixture
def test_dirs():
    """Create temporary directories for testing."""
    with tempfile.TemporaryDirectory() as summary_dir, tempfile.TemporaryDirectory() as transcript_dir:
        yield summary_dir, transcript_dir


def create_pdf_file(directory: str, filename: str, content: str = "test") -> Path:
    """Helper to create a test PDF file."""
    file_path = Path(directory) / filename
    with open(file_path, "w") as f:
        f.write(content)
    return file_path


def test_file_monitor_initialization(test_dirs):
    """Test FileMonitor initialization with valid directories."""
    summary_dir, transcript_dir = test_dirs
    monitor = FileMonitor(summary_dir, transcript_dir)
    assert monitor.summary_dir == Path(summary_dir)
    assert monitor.transcript_dir == Path(transcript_dir)


def test_file_monitor_invalid_directories():
    """Test FileMonitor initialization with invalid directories."""
    with pytest.raises(ValueError, match="Summary directory does not exist"):
        FileMonitor("/nonexistent/summary", "/nonexistent/transcript")


def test_scan_directories_new_files(test_dirs):
    """Test detection of new PDF files."""
    summary_dir, transcript_dir = test_dirs
    monitor = FileMonitor(summary_dir, transcript_dir)

    # Create test files
    summary_file = create_pdf_file(summary_dir, "test1.pdf")
    transcript_file = create_pdf_file(transcript_dir, "test2.pdf")

    # First scan should detect both files as new
    changed_files = monitor.scan_directories()
    assert len(changed_files) == 2
    paths = {f.path for f in changed_files}
    assert summary_file in paths
    assert transcript_file in paths

    # Second scan should detect no changes
    changed_files = monitor.scan_directories()
    assert len(changed_files) == 0


def test_scan_directories_modified_files(test_dirs):
    """Test detection of modified PDF files."""
    summary_dir, _ = test_dirs
    monitor = FileMonitor(summary_dir, summary_dir)  # Use same dir for simplicity

    # Create initial file
    file_path = create_pdf_file(summary_dir, "test.pdf", "initial content")

    # First scan to register the file
    monitor.scan_directories()

    # Modify the file
    sleep(0.1)  # Ensure modification time changes
    with open(file_path, "w") as f:
        f.write("modified content")

    # Scan should detect the modification
    changed_files = monitor.scan_directories()
    assert len(changed_files) == 1
    assert changed_files[0].path == file_path


def test_scan_directories_removed_files(test_dirs):
    """Test handling of removed PDF files."""
    summary_dir, _ = test_dirs
    monitor = FileMonitor(summary_dir, summary_dir)

    # Create and scan initial file
    file_path = create_pdf_file(summary_dir, "test.pdf")
    monitor.scan_directories()
    assert len(monitor._known_files) == 1

    # Remove the file
    os.remove(file_path)

    # Scan should remove the file from tracking
    changed_files = monitor.scan_directories()
    assert len(changed_files) == 0
    assert len(monitor._known_files) == 0


def test_scan_directories_error_handling(test_dirs):
    """Test error handling during directory scanning."""
    summary_dir, transcript_dir = test_dirs
    monitor = FileMonitor(summary_dir, transcript_dir)

    # Create a file and remove read permissions
    file_path = create_pdf_file(summary_dir, "test.pdf")
    os.chmod(summary_dir, 0o000)  # Remove all permissions

    try:
        # Should handle the permission error gracefully
        changed_files = monitor.scan_directories()
        assert len(changed_files) == 0
    finally:
        # Restore permissions for cleanup
        os.chmod(summary_dir, 0o755)


def test_monitored_file_dataclass():
    """Test MonitoredFile dataclass functionality."""
    now = datetime.now()
    file = MonitoredFile(path=Path("/test/path.pdf"), last_modified=now, file_size=1024)

    assert file.path == Path("/test/path.pdf")
    assert file.last_modified == now
    assert file.file_size == 1024
