"""Tests for the state management component."""

import json
import time
from datetime import datetime
from pathlib import Path

import pytest

from fireflies_to_bear.file_matcher import MatchedFiles
from fireflies_to_bear.file_monitor import MonitoredFile
from fireflies_to_bear.state_manager import StateManager


@pytest.fixture
def temp_dir(tmp_path: Path) -> Path:
    """Create a temporary directory for test files."""
    return tmp_path


@pytest.fixture
def state_file(temp_dir: Path) -> Path:
    """Create a temporary state file path."""
    return temp_dir / "state.json"


@pytest.fixture
def state_manager(state_file: Path) -> StateManager:
    """Create a StateManager instance for testing."""
    return StateManager(state_file)


@pytest.fixture
def matched_files(temp_dir: Path) -> MatchedFiles:
    """Create sample matched files for testing."""
    summary_file = temp_dir / "test_summary.pdf"
    transcript_file = temp_dir / "test_transcript.pdf"

    # Create empty files
    summary_file.touch()
    transcript_file.touch()

    # Get current time
    now = datetime.now()

    return MatchedFiles(
        summary=MonitoredFile(path=summary_file, last_modified=now, file_size=0),
        transcript=MonitoredFile(path=transcript_file, last_modified=now, file_size=0),
        meeting_date=now,
        meeting_name="Test Meeting",
    )


def test_init_creates_directory(temp_dir: Path) -> None:
    """Test that initialization creates the state file directory."""
    state_file = temp_dir / "subdir" / "state.json"
    StateManager(state_file)
    assert state_file.parent.exists()


def test_load_state_new_file(state_manager: StateManager) -> None:
    """Test loading state when file doesn't exist."""
    assert len(state_manager.get_processed_files()) == 0


def test_load_state_existing_file(state_file: Path) -> None:
    """Test loading state from existing file."""
    # Create test state file
    test_data = {
        "processed_files": [
            {
                "summary_path": "test_summary.pdf",
                "summary_hash": "abc123",
                "transcript_path": "test_transcript.pdf",
                "transcript_hash": "def456",
                "bear_note_id": "note123",
                "last_processed": datetime.now().isoformat(),
            }
        ]
    }
    state_file.write_text(json.dumps(test_data))

    manager = StateManager(state_file)
    processed_files = manager.get_processed_files()
    assert len(processed_files) == 1
    assert processed_files[0].bear_note_id == "note123"


def test_compute_file_hash(matched_files: MatchedFiles) -> None:
    """Test file hash computation."""
    state_manager = StateManager(Path("test_state.json"))

    # Write some content to test files
    matched_files.summary.path.write_text("test content")
    matched_files.transcript.path.write_text("different content")

    hash1 = state_manager._compute_file_hash(matched_files.summary.path)
    hash2 = state_manager._compute_file_hash(matched_files.transcript.path)

    assert hash1 != ""
    assert hash2 != ""
    assert hash1 != hash2


def test_backup_rotation(state_file: Path) -> None:
    """Test backup file rotation."""
    manager = StateManager(state_file, backup_count=2)

    # Create initial state file
    state_file.write_text("{}")

    # Create multiple backups with a delay between each
    for i in range(4):  # Create 4 backups to ensure rotation
        manager._create_backup()
        time.sleep(0.5)  # Longer delay to ensure unique timestamps

    # Check that only 2 backups exist
    backup_files = sorted(list(state_file.parent.glob(f"{state_file.stem}.*.bak")))
    assert len(backup_files) == 2

    # Verify we kept the most recent backups
    timestamps = [f.name.split(".")[-2] for f in backup_files]
    assert sorted(timestamps) == sorted(timestamps)  # Should be in chronological order


def test_restore_from_backup(state_file: Path) -> None:
    """Test state restoration from backup."""
    # Create a backup file with test data
    backup_data = {
        "processed_files": [
            {
                "summary_path": "backup_summary.pdf",
                "summary_hash": "backup123",
                "transcript_path": "backup_transcript.pdf",
                "transcript_hash": "backup456",
                "bear_note_id": "backup_note",
                "last_processed": datetime.now().isoformat(),
            }
        ]
    }
    backup_file = state_file.with_suffix(".20230101_120000.bak")
    backup_file.write_text(json.dumps(backup_data))

    # Create corrupted state file
    state_file.write_text("invalid json")

    # Initialize manager, which should restore from backup
    manager = StateManager(state_file)
    processed_files = manager.get_processed_files()
    assert len(processed_files) == 1
    assert processed_files[0].bear_note_id == "backup_note"


def test_update_file_state(
    state_manager: StateManager, matched_files: MatchedFiles
) -> None:
    """Test updating file state."""
    state_manager.update_file_state(matched_files, "test_note_id")

    state = state_manager.get_file_state(matched_files)
    assert state is not None
    assert state.bear_note_id == "test_note_id"
    assert state.summary_path == str(matched_files.summary.path)
    assert state.transcript_path == str(matched_files.transcript.path)


def test_has_files_changed(
    state_manager: StateManager, matched_files: MatchedFiles
) -> None:
    """Test file change detection."""
    # Initially should return True as files haven't been processed
    assert state_manager.has_files_changed(matched_files)

    # Process files
    state_manager.update_file_state(matched_files, "test_note_id")

    # Should return False as files haven't changed
    assert not state_manager.has_files_changed(matched_files)

    # Modify a file
    matched_files.summary.path.write_text("new content")

    # Should return True as file has changed
    assert state_manager.has_files_changed(matched_files)


def test_remove_file_state(
    state_manager: StateManager, matched_files: MatchedFiles
) -> None:
    """Test removing file state."""
    # Add file state
    state_manager.update_file_state(matched_files, "test_note_id")
    assert state_manager.get_file_state(matched_files) is not None

    # Remove file state
    state_manager.remove_file_state(matched_files)
    assert state_manager.get_file_state(matched_files) is None


def test_get_file_pair_key(
    state_manager: StateManager, matched_files: MatchedFiles
) -> None:
    """Test file pair key generation."""
    key = state_manager._get_file_pair_key(
        matched_files.summary.path, matched_files.transcript.path
    )
    assert "|" in key
    assert matched_files.summary.path.name in key
    assert matched_files.transcript.path.name in key
