"""Tests for the main application component."""

import os
import signal
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Generator, Tuple
from unittest.mock import ANY, MagicMock, patch

import fitz  # type: ignore  # Missing stubs
import pytest

from fireflies_to_bear.app import (
    AppConfig,
    Application,
    NonRetryableError,
)
from fireflies_to_bear.bear_integration import BearResponse
from fireflies_to_bear.file_matcher import MatchedFiles
from fireflies_to_bear.file_monitor import MonitoredFile
from fireflies_to_bear.note_generator import GeneratedNote
from fireflies_to_bear.pdf_parser import PDFContent


@pytest.fixture
def temp_dirs() -> Generator[Tuple[str, str], None, None]:
    """Create temporary directories for testing."""
    with tempfile.TemporaryDirectory() as summary_dir, tempfile.TemporaryDirectory() as transcript_dir:
        yield summary_dir, transcript_dir


@pytest.fixture
def state_file(tmp_path: Path) -> Path:
    """Create a temporary state file path."""
    return tmp_path / "state.json"


@pytest.fixture
def app_config(temp_dirs: Tuple[str, str], state_file: Path) -> AppConfig:
    """Create an application configuration for testing."""
    summary_dir, transcript_dir = temp_dirs
    return AppConfig(
        watch_directory=summary_dir,
        transcript_directory=transcript_dir,
        state_file=state_file,
        title_template="{date} - {name}",
        backup_count=2,
        tags="meeting,notes",
    )


@pytest.fixture
def app(app_config: AppConfig) -> Application:
    """Create an Application instance for testing."""
    return Application(app_config)


@pytest.fixture
def sample_pdfs(temp_dirs: Tuple[str, str]) -> Generator[Tuple[Path, Path], None, None]:
    """Create sample PDF files for testing."""
    summary_dir, transcript_dir = temp_dirs

    # Create summary PDF
    summary_path = Path(summary_dir) / "20240304 - Team Meeting (Summary).pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Meeting Summary")
    page.insert_text((50, 100), "Key points discussed")
    doc.save(str(summary_path))
    doc.close()

    # Create transcript PDF
    transcript_path = Path(transcript_dir) / "20240304 - Team Meeting (Transcript).pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Meeting Transcript")
    page.insert_text((50, 100), "Discussion content")
    doc.save(str(transcript_path))
    doc.close()

    yield summary_path, transcript_path

    # Cleanup
    os.unlink(summary_path)
    os.unlink(transcript_path)


@pytest.fixture
def sample_pdf(sample_pdfs: Tuple[Path, Path]) -> Path:
    """Fixture that returns a single sample PDF path."""
    return sample_pdfs[0]


@pytest.fixture
def matched_files(sample_pdfs: Tuple[Path, Path]) -> MatchedFiles:
    """Fixture that returns a MatchedFiles object with sample PDFs."""
    summary_path, transcript_path = sample_pdfs
    summary = MonitoredFile(
        path=summary_path, last_modified=datetime(2024, 1, 1), file_size=1000
    )
    transcript = MonitoredFile(
        path=transcript_path, last_modified=datetime(2024, 1, 1), file_size=1000
    )
    return MatchedFiles(
        summary=summary,
        transcript=transcript,
        meeting_date=datetime(2024, 1, 1),
        meeting_name="Test Meeting",
    )


def test_init(app: Application) -> None:
    """Test application initialization."""
    assert app.file_monitor is not None
    assert app.file_matcher is not None
    assert app.pdf_parser is not None
    assert app.note_generator is not None
    assert app.bear_integration is not None
    assert app.state_manager is not None


@patch("fireflies_to_bear.file_monitor.FileMonitor.scan_directories")
@patch("fireflies_to_bear.file_matcher.FileMatcher.match_files")
def test_process_directory_no_files(
    mock_match_files: MagicMock, mock_scan_directories: MagicMock, app: Application
) -> None:
    """Test directory processing with no files."""
    mock_scan_directories.return_value = []
    mock_match_files.return_value = []

    app.process_directory()

    mock_scan_directories.assert_called_once()
    mock_match_files.assert_called_once_with([])


@patch("fireflies_to_bear.file_monitor.FileMonitor.scan_directories")
@patch("fireflies_to_bear.file_matcher.FileMatcher.match_files")
@patch("fireflies_to_bear.state_manager.StateManager.has_files_changed")
@patch("fireflies_to_bear.pdf_parser.PDFParser.parse_pdf")
@patch("fireflies_to_bear.note_generator.NoteGenerator.generate_note")
@patch("fireflies_to_bear.bear_integration.BearIntegration.create_note")
@patch("fireflies_to_bear.state_manager.StateManager.update_file_state")
def test_process_directory_new_files(
    mock_update_state: MagicMock,
    mock_create_note: MagicMock,
    mock_generate_note: MagicMock,
    mock_parse_pdf: MagicMock,
    mock_has_changed: MagicMock,
    mock_match_files: MagicMock,
    mock_scan_directories: MagicMock,
    app: Application,
    sample_pdfs: Tuple[Path, Path],
) -> None:
    """Test directory processing with new files."""
    summary_path, transcript_path = sample_pdfs
    now = datetime.now()

    # Mock file monitoring
    monitored_files = [
        MonitoredFile(path=summary_path, last_modified=now, file_size=1024),
        MonitoredFile(path=transcript_path, last_modified=now, file_size=2048),
    ]
    mock_scan_directories.return_value = monitored_files

    # Mock file matching
    matched_files = MatchedFiles(
        summary=monitored_files[0],
        transcript=monitored_files[1],
        meeting_date=now,
        meeting_name="Team Meeting",
    )
    mock_match_files.return_value = [matched_files]

    # Mock processing
    mock_has_changed.return_value = True
    mock_parse_pdf.return_value = PDFContent(
        title="Test", content="Test content", page_count=1
    )
    mock_generate_note.return_value = GeneratedNote(
        title="20240304 - Team Meeting", content="Test note content"
    )
    mock_create_note.return_value = BearResponse(success=True, note_identifier="ABC123")

    # Run test
    app.process_directory()

    # Verify calls
    mock_scan_directories.assert_called_once()
    mock_match_files.assert_called_once_with(monitored_files)
    mock_has_changed.assert_called_once()
    assert mock_parse_pdf.call_count == 2
    mock_generate_note.assert_called_once_with(matched_files)
    mock_create_note.assert_called_once()
    mock_update_state.assert_called_once_with(matched_files, "ABC123")


@patch("fireflies_to_bear.file_monitor.FileMonitor.scan_directories")
@patch("fireflies_to_bear.file_matcher.FileMatcher.match_files")
@patch("fireflies_to_bear.state_manager.StateManager.has_files_changed")
def test_process_directory_unchanged_files(
    mock_has_changed: MagicMock,
    mock_match_files: MagicMock,
    mock_scan_directories: MagicMock,
    app: Application,
    sample_pdfs: Tuple[Path, Path],
) -> None:
    """Test directory processing with unchanged files."""
    summary_path, transcript_path = sample_pdfs
    now = datetime.now()

    # Mock file monitoring
    monitored_files = [
        MonitoredFile(path=summary_path, last_modified=now, file_size=1024),
        MonitoredFile(path=transcript_path, last_modified=now, file_size=2048),
    ]
    mock_scan_directories.return_value = monitored_files

    # Mock file matching
    matched_files = MatchedFiles(
        summary=monitored_files[0],
        transcript=monitored_files[1],
        meeting_date=now,
        meeting_name="Team Meeting",
    )
    mock_match_files.return_value = [matched_files]

    # Mock unchanged files
    mock_has_changed.return_value = False

    # Run test
    app.process_directory()

    # Verify that processing stops after checking file changes
    mock_scan_directories.assert_called_once()
    mock_match_files.assert_called_once_with(monitored_files)
    mock_has_changed.assert_called_once()


@patch("fireflies_to_bear.file_monitor.FileMonitor.scan_directories")
def test_process_directory_error_handling(
    mock_scan_directories: MagicMock, app: Application
) -> None:
    """Test error handling during directory processing."""
    mock_scan_directories.side_effect = Exception("Test error")

    # Run test
    app.process_directory()  # Should not raise exception

    # Verify error was logged
    mock_scan_directories.assert_called_once()


@patch("fireflies_to_bear.app.time.sleep")
@patch(
    "fireflies_to_bear.app.time.time"
)  # Keep the patch to ensure time.time() is not called
def test_run_with_sleep_interval(
    mock_time: MagicMock, mock_sleep: MagicMock, app: Application
) -> None:
    """Test application run loop with sleep interval."""
    # Set up mocks
    app.process_directory = MagicMock()  # type: ignore

    # Set up sleep to trigger shutdown
    def trigger_shutdown(*args: object) -> None:
        app._shutdown_requested = True

    mock_sleep.side_effect = trigger_shutdown

    # Run application
    app.run()

    # Verify behavior
    app.process_directory.assert_called_once()
    mock_sleep.assert_called_once_with(300)  # Should sleep for full interval
    assert mock_time.call_count == 0  # Should not call time.time()


@patch("signal.signal")
def test_signal_handler_registration(
    mock_signal: MagicMock, app_config: AppConfig
) -> None:
    """Test that signal handlers are registered correctly."""
    Application(app_config)

    # Verify SIGINT and SIGTERM handlers were registered
    assert mock_signal.call_count == 2
    mock_signal.assert_any_call(signal.SIGINT, ANY)
    mock_signal.assert_any_call(signal.SIGTERM, ANY)


def test_signal_handler(app: Application) -> None:
    """Test that signal handler sets shutdown flag."""
    assert not app._shutdown_requested
    app._handle_shutdown(signal.SIGINT, None)
    assert app._shutdown_requested


@patch("fireflies_to_bear.app.time.sleep")
@patch(
    "fireflies_to_bear.app.time.time"
)  # Keep the patch to ensure time.time() is not called
def test_run_graceful_shutdown(
    mock_time: MagicMock, mock_sleep: MagicMock, app: Application
) -> None:
    """Test graceful shutdown during sleep interval."""
    # Set up mocks
    app.process_directory = MagicMock()  # type: ignore

    # Set up sleep to trigger shutdown
    def trigger_shutdown(*args: object) -> None:
        app._shutdown_requested = True

    mock_sleep.side_effect = trigger_shutdown

    # Run application
    app.run()

    # Verify behavior
    app.process_directory.assert_called_once()
    assert app._shutdown_requested
    mock_sleep.assert_called_once_with(300)  # Should sleep for full interval
    assert mock_time.call_count == 0  # Should not call time.time()


def test_parse_pdf_with_retry_success(app: Application, sample_pdf: Path) -> None:
    """Test successful PDF parsing with retry logic."""
    content = app._parse_pdf_with_retry(sample_pdf)
    assert isinstance(content, PDFContent)
    assert content.error is None


def test_parse_pdf_with_retry_retryable_error(
    app: Application, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test PDF parsing with retryable error."""
    # Mock the parse_pdf method to fail twice then succeed
    mock_content = PDFContent(title="Test", content="Content", page_count=1)
    mock_parse = MagicMock(
        side_effect=[IOError("Test error"), IOError("Test error"), mock_content]
    )
    monkeypatch.setattr(app.pdf_parser, "parse_pdf", mock_parse)

    content = app._parse_pdf_with_retry(Path("test.pdf"))
    assert content == mock_content
    assert mock_parse.call_count == 3


def test_parse_pdf_with_retry_non_retryable_error(
    app: Application, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test PDF parsing with non-retryable error."""
    mock_parse = MagicMock(side_effect=ValueError("Test error"))
    monkeypatch.setattr(app.pdf_parser, "parse_pdf", mock_parse)

    with pytest.raises(NonRetryableError, match="Error parsing PDF file"):
        app._parse_pdf_with_retry(Path("test.pdf"))

    assert mock_parse.call_count == 1


def test_create_or_update_note_success_create(
    app: Application, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test successful note creation with retry logic."""
    note = GeneratedNote(title="Test", content="Content")
    response = BearResponse(success=True, note_identifier="test123")
    mock_create = MagicMock(return_value=response)
    monkeypatch.setattr(app.bear_integration, "create_note", mock_create)

    success, note_id = app._create_or_update_note(note)
    assert success
    assert note_id == "test123"
    mock_create.assert_called_once_with(note, tags=app.config.tags)


def test_create_or_update_note_success_update(
    app: Application, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test successful note update with retry logic."""
    note = GeneratedNote(title="Test", content="Content")
    response = BearResponse(success=True, note_identifier="test123")
    mock_update = MagicMock(return_value=response)
    monkeypatch.setattr(app.bear_integration, "update_note", mock_update)

    success, note_id = app._create_or_update_note(
        note, existing_state={"bear_note_id": "test123"}
    )
    assert success
    assert note_id == "test123"
    mock_update.assert_called_once_with("test123", note, tags=app.config.tags)


def test_create_or_update_note_retryable_error(
    app: Application, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test note creation with retryable error."""
    note = GeneratedNote(title="Test", content="Content")
    fail_response = BearResponse(success=False, error="Test error")
    success_response = BearResponse(success=True, note_identifier="test123")

    mock_create = MagicMock(
        side_effect=[fail_response, fail_response, success_response]
    )
    monkeypatch.setattr(app.bear_integration, "create_note", mock_create)

    success, note_id = app._create_or_update_note(note)
    assert success
    assert note_id == "test123"
    assert mock_create.call_count == 3


def test_create_or_update_note_non_retryable_error(
    app: Application, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test note creation with non-retryable error."""
    note = GeneratedNote(title="Test", content="Content")
    mock_create = MagicMock(side_effect=ValueError("Test error"))
    monkeypatch.setattr(app.bear_integration, "create_note", mock_create)

    with pytest.raises(NonRetryableError, match="Error interacting with Bear"):
        app._create_or_update_note(note)

    assert mock_create.call_count == 1


@patch("fireflies_to_bear.app.time.sleep")  # Patch sleep to speed up tests
def test_retry_exponential_backoff(
    mock_sleep: MagicMock, app: Application, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test exponential backoff in retry logic."""
    note = GeneratedNote(title="Test", content="Content")
    fail_response = BearResponse(success=False, error="Test error")
    success_response = BearResponse(success=True, note_identifier="test123")

    mock_create = MagicMock(
        side_effect=[fail_response, fail_response, success_response]
    )
    monkeypatch.setattr(app.bear_integration, "create_note", mock_create)

    success, note_id = app._create_or_update_note(note)
    assert success
    assert note_id == "test123"

    # Check exponential backoff delays
    assert mock_sleep.call_count == 2
    mock_sleep.assert_any_call(1.0)  # First retry
    mock_sleep.assert_any_call(2.0)  # Second retry with doubled delay


def test_process_file_pair_with_retries(
    app: Application, matched_files: MatchedFiles, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test file pair processing with retries."""
    # Mock PDF parsing to fail once then succeed
    mock_content = PDFContent(title="Test", content="Content", page_count=1)
    mock_parse = MagicMock(
        side_effect=[IOError("Test error"), mock_content, mock_content]
    )
    monkeypatch.setattr(app.pdf_parser, "parse_pdf", mock_parse)

    # Mock Bear integration to fail once then succeed
    fail_response = BearResponse(success=False, error="Test error")
    success_response = BearResponse(success=True, note_identifier="test123")
    mock_create = MagicMock(side_effect=[fail_response, success_response])
    monkeypatch.setattr(app.bear_integration, "create_note", mock_create)

    # Mock state manager methods
    mock_has_changed = MagicMock(return_value=True)
    mock_get_state = MagicMock(return_value=None)
    mock_update_state = MagicMock()
    monkeypatch.setattr(app.state_manager, "has_files_changed", mock_has_changed)
    monkeypatch.setattr(app.state_manager, "get_file_state", mock_get_state)
    monkeypatch.setattr(app.state_manager, "update_file_state", mock_update_state)

    # Process the file pair
    app._process_file_pair(matched_files)

    # Verify retries and final success
    assert mock_parse.call_count == 3  # One failure, two successes
    assert mock_create.call_count == 2  # One failure, one success
    mock_update_state.assert_called_once()
