"""Component for extracting and cleaning text content from PDF files."""

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import fitz  # PyMuPDF


@dataclass
class PDFContent:
    """Represents the extracted and cleaned content from a PDF file."""

    title: str
    content: str
    page_count: int
    error: Optional[str] = None


class PDFParser:
    """Extracts and cleans text content from PDF files."""

    def __init__(self) -> None:
        """Initialize the PDFParser."""
        self.logger = logging.getLogger(__name__)

    def _clean_text(self, text: str) -> str:
        """Clean extracted text content.

        Args:
            text: Raw text content from PDF

        Returns:
            Cleaned text content with normalized whitespace and removed artifacts
        """
        # Replace multiple newlines with a single newline
        text = re.sub(r"\n{3,}", "\n\n", text)

        # Remove repeated whitespace
        text = re.sub(r" +", " ", text)

        # Remove empty lines at start and end
        text = text.strip()

        # Fix common OCR/PDF artifacts
        text = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", text)  # Add space between words
        text = re.sub(r"[^\S\n]+", " ", text)  # Normalize spaces but preserve newlines

        return text

    def _extract_title(self, text: str) -> str:
        """Extract a title from the text content.

        Args:
            text: Text content to extract title from

        Returns:
            First non-empty line of text, or "Untitled" if none found
        """
        lines = text.split("\n")
        for line in lines:
            line = line.strip()
            if line:
                return line
        return "Untitled"

    def parse_pdf(self, pdf_path: Path) -> PDFContent:
        """Parse a PDF file and extract its content.

        Args:
            pdf_path: Path to the PDF file to parse

        Returns:
            PDFContent object containing the extracted and cleaned content
        """
        try:
            # Open PDF file
            with fitz.open(pdf_path) as doc:
                page_count = len(doc)
                text_content: List[str] = []

                # Extract text from each page
                for page_num in range(page_count):
                    try:
                        page = doc[page_num]
                        text = page.get_text()
                        if text.strip():
                            text_content.append(text)
                    except Exception as e:
                        self.logger.warning(
                            f"Error extracting text from page {page_num + 1} of {pdf_path}: {e}"
                        )
                        continue

                if not text_content:
                    return PDFContent(
                        title="Empty Document",
                        content="",
                        page_count=page_count,
                        error="No text content could be extracted",
                    )

                # Join and clean the text
                full_text = "\n".join(text_content)
                cleaned_text = self._clean_text(full_text)
                title = self._extract_title(cleaned_text)

                return PDFContent(
                    title=title, content=cleaned_text, page_count=page_count
                )

        except fitz.FileDataError as e:
            error_msg = f"Invalid or corrupted PDF file: {e}"
            self.logger.error(f"{error_msg} - {pdf_path}")
            return PDFContent(title="Error", content="", page_count=0, error=error_msg)

        except Exception as e:
            error_msg = f"Error parsing PDF: {e}"
            self.logger.error(f"{error_msg} - {pdf_path}")
            return PDFContent(title="Error", content="", page_count=0, error=error_msg)
