"""Tests for the note generation component."""

import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Generator, Tuple

import fitz
import pytest

from fireflies_to_bear.file_matcher import MatchedFiles
from fireflies_to_bear.file_monitor import MonitoredFile
from fireflies_to_bear.note_generator import GeneratedNote, NoteGenerator


@pytest.fixture
def note_generator() -> NoteGenerator:
    """Create a NoteGenerator instance for testing."""
    return NoteGenerator()


@pytest.fixture
def sample_pdfs() -> Generator[Tuple[Path, Path], None, None]:
    """Create sample summary and transcript PDFs for testing."""
    with (
        tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as summary_file,
        tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as transcript_file,
    ):
        # Create summary PDF
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((50, 50), "Meeting Summary")
        page.insert_text((50, 100), "Key points discussed:")
        page.insert_text((50, 150), "1. Project updates")
        page.insert_text((50, 200), "2. Action items")
        doc.save(summary_file.name)
        doc.close()

        # Create transcript PDF
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((50, 50), "Meeting Transcript")
        page.insert_text((50, 100), "John: Hello everyone")
        page.insert_text((50, 150), "Jane: Hi John")
        page.insert_text((50, 200), "John: Let's begin")
        doc.save(transcript_file.name)
        doc.close()

        yield Path(summary_file.name), Path(transcript_file.name)

        # Cleanup
        os.unlink(summary_file.name)
        os.unlink(transcript_file.name)


@pytest.fixture
def matched_files(sample_pdfs: Tuple[Path, Path]) -> MatchedFiles:
    """Create a MatchedFiles instance for testing."""
    summary_path, transcript_path = sample_pdfs
    now = datetime.now()

    return MatchedFiles(
        summary=MonitoredFile(path=summary_path, last_modified=now, file_size=1024),
        transcript=MonitoredFile(
            path=transcript_path, last_modified=now, file_size=2048
        ),
        meeting_date=datetime(2024, 3, 4),
        meeting_name="Team Meeting",
    )


def test_generate_note_valid(
    note_generator: NoteGenerator, matched_files: MatchedFiles
) -> None:
    """Test note generation with valid input files."""
    note = note_generator.generate_note(matched_files)

    assert isinstance(note, GeneratedNote)
    assert note.title == "20240304 - Team Meeting"
    assert note.error is None

    # Check content structure
    assert "## Summary" in note.content
    assert "## Transcript" in note.content
    assert "--==RAW NOTES==--" in note.content
    assert "Key points discussed" in note.content
    assert "John: Hello everyone" in note.content


def test_generate_note_custom_template(matched_files: MatchedFiles) -> None:
    """Test note generation with custom title template."""
    generator = NoteGenerator(
        title_template="{date} - {name}", separator="===TRANSCRIPT==="
    )
    note = generator.generate_note(matched_files)

    assert note.title == "20240304 - Team Meeting"
    assert "===TRANSCRIPT===" in note.content


def test_generate_note_invalid_template(matched_files: MatchedFiles) -> None:
    """Test note generation with invalid title template."""
    generator = NoteGenerator(title_template="{invalid} - {variables}")
    note = generator.generate_note(matched_files)

    # Should fall back to basic format
    assert "Team Meeting" in note.title
    assert note.error is None


def test_generate_note_missing_summary(
    note_generator: NoteGenerator, matched_files: MatchedFiles
) -> None:
    """Test note generation with missing summary file."""
    matched_files.summary.path = Path("nonexistent.pdf")
    note = note_generator.generate_note(matched_files)

    assert note.title == "Error"
    assert note.content == ""
    assert note.error is not None
    assert "Error parsing summary PDF" in note.error


def test_generate_note_missing_transcript(
    note_generator: NoteGenerator, matched_files: MatchedFiles
) -> None:
    """Test note generation with missing transcript file."""
    matched_files.transcript.path = Path("nonexistent.pdf")
    note = note_generator.generate_note(matched_files)

    assert note.title == "Error"
    assert note.content == ""
    assert note.error is not None
    assert "Error parsing transcript PDF" in note.error


def test_format_content_sections(note_generator: NoteGenerator) -> None:
    """Test content formatting with different section contents."""
    from fireflies_to_bear.pdf_parser import PDFContent

    summary = PDFContent(title="Summary", content="Summary content", page_count=1)
    transcript = PDFContent(
        title="Transcript", content="Transcript content", page_count=1
    )

    content = note_generator._format_content(summary, transcript)

    # Check section order and formatting
    sections = content.split(note_generator.separator)
    assert len(sections) == 2
    assert "## Summary" in sections[0]
    assert "Summary content" in sections[0]
    assert "## Transcript" in sections[1]
    assert "Transcript content" in sections[1]
