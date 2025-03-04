"""Tests for the PDF parsing component."""

import os
import tempfile
from pathlib import Path
from typing import Generator

import fitz
import pytest

from fireflies_to_bear.pdf_parser import PDFContent, PDFParser


@pytest.fixture
def pdf_parser() -> PDFParser:
    """Create a PDFParser instance for testing."""
    return PDFParser()


@pytest.fixture
def sample_pdf() -> Generator[Path, None, None]:
    """Create a sample PDF file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        # Create a PDF with some test content
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((50, 50), "Test Document Title")
        page.insert_text((50, 100), "This is a test document.")
        page.insert_text((50, 150), "It contains multiple lines")
        page.insert_text((50, 200), "of text for testing.")
        doc.save(tmp.name)
        doc.close()

        yield Path(tmp.name)

        # Cleanup
        os.unlink(tmp.name)


@pytest.fixture
def empty_pdf() -> Generator[Path, None, None]:
    """Create an empty PDF file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        doc = fitz.open()
        doc.new_page()  # Add empty page
        doc.save(tmp.name)
        doc.close()

        yield Path(tmp.name)

        # Cleanup
        os.unlink(tmp.name)


def test_parse_pdf_valid(pdf_parser: PDFParser, sample_pdf: Path) -> None:
    """Test parsing of a valid PDF file."""
    content = pdf_parser.parse_pdf(sample_pdf)

    assert isinstance(content, PDFContent)
    assert content.title == "Test Document Title"
    assert "This is a test document" in content.content
    assert content.page_count == 1
    assert content.error is None


def test_parse_pdf_empty(pdf_parser: PDFParser, empty_pdf: Path) -> None:
    """Test parsing of an empty PDF file."""
    content = pdf_parser.parse_pdf(empty_pdf)

    assert isinstance(content, PDFContent)
    assert content.title == "Empty Document"
    assert content.content == ""
    assert content.page_count == 1
    assert content.error == "No text content could be extracted"


def test_parse_pdf_nonexistent(pdf_parser: PDFParser) -> None:
    """Test parsing of a nonexistent PDF file."""
    content = pdf_parser.parse_pdf(Path("nonexistent.pdf"))

    assert isinstance(content, PDFContent)
    assert content.title == "Error"
    assert content.content == ""
    assert content.page_count == 0
    assert content.error is not None
    if content.error is not None:  # Type guard for mypy
        assert "Error parsing PDF" in content.error


def test_clean_text(pdf_parser: PDFParser) -> None:
    """Test text cleaning functionality."""
    raw_text = """
    Multiple    spaces    between    words


    Multiple newlines above

    CamelCaseWithoutSpaces
    """

    cleaned = pdf_parser._clean_text(raw_text)

    assert "Multiple spaces between words" in cleaned
    assert "Multiple newlines above" in cleaned
    assert "Camel Case Without Spaces" in cleaned
    assert "\n\n\n" not in cleaned  # No triple newlines
    assert "    " not in cleaned  # No multiple spaces


def test_extract_title(pdf_parser: PDFParser) -> None:
    """Test title extraction functionality."""
    # Test with valid title
    text = "Document Title\nContent line 1\nContent line 2"
    assert pdf_parser._extract_title(text) == "Document Title"

    # Test with empty lines before title
    text = "\n\n  \nDocument Title\nContent"
    assert pdf_parser._extract_title(text) == "Document Title"

    # Test with no valid title
    text = "\n\n  \n"
    assert pdf_parser._extract_title(text) == "Untitled"
