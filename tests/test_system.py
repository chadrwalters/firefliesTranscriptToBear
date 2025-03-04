"""System tests for the Fireflies to Bear application."""

import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Generator, Tuple

import fitz  # type: ignore
import psutil  # type: ignore
import pytest

from fireflies_to_bear.app import AppConfig, Application
from fireflies_to_bear.bear_integration import BearResponse


@pytest.fixture
def test_dirs() -> Generator[Tuple[Path, Path], None, None]:
    """Create temporary test directories."""
    with tempfile.TemporaryDirectory() as summary_dir, tempfile.TemporaryDirectory() as transcript_dir:
        yield Path(summary_dir), Path(transcript_dir)


@pytest.fixture
def state_dir(tmp_path: Path) -> Path:
    """Create a temporary state directory."""
    state_dir = tmp_path / "state"
    state_dir.mkdir(exist_ok=True)
    return state_dir


@pytest.fixture
def app_config(test_dirs: Tuple[Path, Path], state_dir: Path) -> AppConfig:
    """Create test application configuration."""
    summary_dir, transcript_dir = test_dirs
    return AppConfig(
        watch_directory=str(summary_dir),
        transcript_directory=str(transcript_dir),
        state_file=state_dir / "state.json",
        sleep_interval=1,  # Short interval for testing
        title_template="{date} - {name}",
        tags="test,meeting",
    )


@pytest.fixture
def sample_pdfs(
    test_dirs: Tuple[Path, Path],
) -> Generator[Tuple[Path, Path], None, None]:
    """Create sample PDF files for testing."""
    summary_dir, transcript_dir = test_dirs

    # Create summary PDF
    summary_path = summary_dir / "Team Meeting-summary-2024-03-04T10-00-00.000Z.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Meeting Summary")
    page.insert_text((50, 100), "Key points discussed")
    doc.save(str(summary_path))
    doc.close()

    # Create transcript PDF
    transcript_path = (
        transcript_dir / "Team Meeting-transcript-2024-03-04T10-00-00.000Z.pdf"
    )
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Meeting Transcript")
    page.insert_text((50, 100), "Discussion content")
    doc.save(str(transcript_path))
    doc.close()

    yield summary_path, transcript_path


def test_full_workflow(
    app_config: AppConfig,
    sample_pdfs: Tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test the complete application workflow."""
    summary_path, transcript_path = sample_pdfs

    # Mock Bear integration
    mock_responses: Dict[str, BearResponse] = {
        "create": BearResponse(success=True, note_identifier="test123"),
        "update": BearResponse(success=True, note_identifier="test123"),
    }

    def mock_create_note(*args: Any, **kwargs: Any) -> BearResponse:
        return mock_responses["create"]

    def mock_update_note(*args: Any, **kwargs: Any) -> BearResponse:
        return mock_responses["update"]

    # Create application instance
    app = Application(app_config)
    monkeypatch.setattr(app.bear_integration, "create_note", mock_create_note)
    monkeypatch.setattr(app.bear_integration, "update_note", mock_update_note)

    # Process directory once
    app.process_directory()

    # Verify state file was created
    assert app.config.state_file.exists()

    # Modify PDFs and process again
    time.sleep(1)  # Ensure modification time is different
    with open(summary_path, "a") as f:
        f.write("Additional content")

    app.process_directory()


def test_memory_usage(
    app_config: AppConfig,
    sample_pdfs: Tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test memory usage during processing."""
    summary_path, transcript_path = sample_pdfs

    # Mock Bear integration
    def mock_create_note(*args: Any, **kwargs: Any) -> BearResponse:
        return BearResponse(success=True, note_identifier="test123")

    # Create application instance
    app = Application(app_config)
    monkeypatch.setattr(app.bear_integration, "create_note", mock_create_note)

    # Get initial memory usage
    process = psutil.Process()
    initial_memory = process.memory_info().rss

    # Process directory multiple times
    for _ in range(5):
        app.process_directory()
        time.sleep(1)  # Allow time for garbage collection

    # Get final memory usage
    final_memory = process.memory_info().rss
    memory_increase = final_memory - initial_memory

    # Check memory usage (allow for some increase but not excessive)
    # 50MB is a reasonable threshold for our application
    assert memory_increase < 50 * 1024 * 1024, "Memory usage increased significantly"


def test_file_handling_stability(
    app_config: AppConfig, test_dirs: Tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test stability with various file operations."""
    summary_dir, transcript_dir = test_dirs

    # Mock Bear integration
    def mock_create_note(*args: Any, **kwargs: Any) -> BearResponse:
        return BearResponse(success=True, note_identifier="test123")

    # Create application instance
    app = Application(app_config)
    monkeypatch.setattr(app.bear_integration, "create_note", mock_create_note)

    # Test with various file operations
    for i in range(5):
        # Create PDFs
        summary_path = summary_dir / f"test{i}_summary.pdf"
        transcript_path = transcript_dir / f"test{i}_transcript.pdf"

        # Create PDFs with content
        for path in [summary_path, transcript_path]:
            doc = fitz.open()
            page = doc.new_page()
            page.insert_text((50, 50), f"Test content {i}")
            doc.save(str(path))
            doc.close()

        # Process directory
        app.process_directory()

        # Modify files
        if i % 2 == 0:
            # Modify content
            with open(summary_path, "a") as f:
                f.write("Modified content")
        else:
            # Delete files
            os.unlink(str(summary_path))
            os.unlink(str(transcript_path))

        # Process again
        app.process_directory()


def test_concurrent_file_operations(
    app_config: AppConfig, test_dirs: Tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test handling of concurrent file operations."""
    summary_dir, transcript_dir = test_dirs

    # Mock Bear integration
    def mock_create_note(*args: Any, **kwargs: Any) -> BearResponse:
        return BearResponse(success=True, note_identifier="test123")

    # Create application instance
    app = Application(app_config)
    monkeypatch.setattr(app.bear_integration, "create_note", mock_create_note)

    # Create initial files
    summary_path = summary_dir / "test_summary.pdf"
    transcript_path = transcript_dir / "test_transcript.pdf"

    for path in [summary_path, transcript_path]:
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((50, 50), "Initial content")
        doc.save(str(path))
        doc.close()

    # Start processing
    app.process_directory()

    # Simulate concurrent operations
    # 1. Create temporary copy
    temp_summary = summary_dir / "temp_summary.pdf"
    shutil.copy2(str(summary_path), str(temp_summary))

    # 2. Delete original
    os.unlink(str(summary_path))

    # 3. Process (should handle missing file gracefully)
    app.process_directory()

    # 4. Move temporary to original
    shutil.move(str(temp_summary), str(summary_path))

    # 5. Process again (should handle restored file)
    app.process_directory()


def test_macos_integration(
    app_config: AppConfig,
    sample_pdfs: Tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test macOS-specific integration."""
    if not os.uname().sysname == "Darwin":
        pytest.skip("Test requires macOS")

    summary_path, transcript_path = sample_pdfs

    # Mock Bear integration
    def mock_create_note(*args: Any, **kwargs: Any) -> BearResponse:
        return BearResponse(success=True, note_identifier="test123")

    # Create application instance
    app = Application(app_config)
    monkeypatch.setattr(app.bear_integration, "create_note", mock_create_note)

    # Test .DS_Store handling
    ds_store_path = Path(app_config.watch_directory) / ".DS_Store"
    with open(ds_store_path, "w") as f:
        f.write("Mock .DS_Store file")

    # Process directory (should ignore .DS_Store)
    app.process_directory()

    # Test with resource forks
    resource_fork_path = summary_path.parent / "._test.pdf"
    with open(resource_fork_path, "w") as f:
        f.write("Mock resource fork")

    # Process directory (should ignore resource fork)
    app.process_directory()
