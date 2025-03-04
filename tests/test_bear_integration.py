"""Tests for the Bear.app integration component."""

import subprocess
import urllib.parse
from unittest.mock import MagicMock, patch

import pytest

from fireflies_to_bear.bear_integration import BearIntegration
from fireflies_to_bear.note_generator import GeneratedNote


@pytest.fixture
def bear_integration() -> BearIntegration:
    """Create a BearIntegration instance for testing."""
    return BearIntegration()


@pytest.fixture
def sample_note() -> GeneratedNote:
    """Create a sample GeneratedNote for testing."""
    return GeneratedNote(
        title="Test Meeting",
        content="## Summary\nTest content\n\n--==RAW NOTES==--\n\n## Transcript\nTest transcript",
    )


def test_encode_parameters() -> None:
    """Test parameter encoding for x-callback-url."""
    integration = BearIntegration()
    params = {
        "title": "Test & Title",
        "text": "Some content",
    }
    encoded = integration._encode_parameters(**params)
    assert "title=Test%20%26%20Title" in encoded
    assert "text=Some%20content" in encoded


def test_create_bear_url() -> None:
    """Test Bear.app x-callback-url creation."""
    integration = BearIntegration()
    url = integration._create_bear_url(
        "create", title="Test & Title", text="Some content"
    )
    assert url.startswith("bear://x-callback-url/create?")
    assert "title=Test%20%26%20Title" in url
    assert "text=Some%20content" in url


def test_extract_note_identifier(bear_integration: BearIntegration) -> None:
    """Test extraction of Bear note identifiers."""
    # Valid identifier
    assert bear_integration._extract_note_identifier("Note Title [1A2B3C]") == "1A2B3C"

    # No identifier
    assert bear_integration._extract_note_identifier("Note Title") is None

    # Invalid format
    assert bear_integration._extract_note_identifier("Note Title [XYZ]") is None


@patch("subprocess.run")
def test_create_note_success(
    mock_run: MagicMock, bear_integration: BearIntegration, sample_note: GeneratedNote
) -> None:
    """Test successful note creation."""
    # Mock successful command execution
    mock_run.return_value = subprocess.CompletedProcess(
        args=["open", "bear://..."], returncode=0, stdout="", stderr=""
    )

    response = bear_integration.create_note(sample_note, tags="meeting,notes")

    assert response.success
    assert not response.error

    # Verify command execution
    mock_run.assert_called_once()
    cmd_args = mock_run.call_args[0][0]
    assert cmd_args[0] == "open"
    assert cmd_args[1].startswith("bear://x-callback-url/create")


@patch("subprocess.run")
def test_create_note_with_tags(
    mock_run: MagicMock, bear_integration: BearIntegration, sample_note: GeneratedNote
) -> None:
    """Test note creation with tags."""
    mock_run.return_value = subprocess.CompletedProcess(
        args=["open", "bear://..."], returncode=0, stdout="", stderr=""
    )

    bear_integration.create_note(sample_note, tags="meeting,notes")

    cmd_args = mock_run.call_args[0][0]
    assert "text=" in cmd_args[1]
    assert "#meeting #notes" in urllib.parse.unquote(cmd_args[1])


@patch("subprocess.run")
def test_create_note_failure(
    mock_run: MagicMock, bear_integration: BearIntegration, sample_note: GeneratedNote
) -> None:
    """Test note creation failure handling."""
    # Mock command failure
    mock_run.side_effect = subprocess.CalledProcessError(
        returncode=1, cmd=["open", "bear://..."], stderr="Failed to execute command"
    )

    response = bear_integration.create_note(sample_note)

    assert not response.success
    assert response.error is not None
    assert "Error creating note in Bear" in response.error


@patch("subprocess.run")
def test_update_note_success(mock_subprocess_run: MagicMock) -> None:
    """Test successful note update."""
    integration = BearIntegration()
    note = GeneratedNote(title="Test Note", content="Updated content")
    response = integration.update_note("ABC123", note)

    assert response.success
    assert response.note_identifier == "ABC123"
    assert response.error is None

    mock_subprocess_run.assert_called_once()
    cmd_args = mock_subprocess_run.call_args[0][0]
    assert "mode=replace" in cmd_args[1]
    assert "title=Test%20Note" in cmd_args[1]
    assert "text=Updated%20content" in cmd_args[1]


@patch("subprocess.run")
def test_update_note_with_tags(
    mock_run: MagicMock, bear_integration: BearIntegration, sample_note: GeneratedNote
) -> None:
    """Test note update with tags."""
    mock_run.return_value = subprocess.CompletedProcess(
        args=["open", "bear://..."], returncode=0, stdout="", stderr=""
    )

    response = bear_integration.update_note("1A2B3C", sample_note, tags="meeting,notes")

    assert response.success
    assert response.note_identifier == "1A2B3C"
    assert not response.error

    # Verify command execution
    mock_run.assert_called_once()
    cmd_args = mock_run.call_args[0][0]
    assert cmd_args[0] == "open"
    assert cmd_args[1].startswith("bear://x-callback-url/add-text")
    assert "mode=replace" in cmd_args[1]
    assert "#meeting #notes" in urllib.parse.unquote(cmd_args[1])


@patch("subprocess.run")
def test_search_note(mock_run: MagicMock, bear_integration: BearIntegration) -> None:
    """Test note search functionality."""
    mock_run.return_value = subprocess.CompletedProcess(
        args=["open", "bear://..."], returncode=0, stdout="", stderr=""
    )

    # Test with a note title that should have an identifier
    identifier = bear_integration.search_note("Test Note [1A2B3C]")
    assert identifier == "1A2B3C"

    # Test with a note title that doesn't have an identifier
    identifier = bear_integration.search_note("Unknown Note")
    assert identifier is None

    # Verify search command was executed
    assert mock_run.call_count == 2
    search_cmd = mock_run.call_args_list[1][0][0][1]
    assert search_cmd.startswith("bear://x-callback-url/search")


@patch("subprocess.run")
def test_update_note_failure(
    mock_run: MagicMock, bear_integration: BearIntegration, sample_note: GeneratedNote
) -> None:
    """Test note update failure handling."""
    mock_run.side_effect = subprocess.CalledProcessError(
        returncode=1, cmd=["open", "bear://..."], stderr="Failed to execute command"
    )

    response = bear_integration.update_note("1A2B3C", sample_note)

    assert not response.success
    assert response.error is not None
    assert "Error updating note in Bear" in response.error
