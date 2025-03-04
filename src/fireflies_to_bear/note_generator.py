"""Component for generating structured notes from PDF content."""

import logging
from dataclasses import dataclass
from typing import Optional

from .file_matcher import MatchedFiles
from .pdf_parser import PDFContent, PDFParser


@dataclass
class GeneratedNote:
    """Represents a generated note with its metadata."""

    title: str
    content: str
    error: Optional[str] = None


class NoteGenerator:
    """Generates structured notes from PDF content."""

    def __init__(
        self,
        title_template: str = "{date} - {name}",
        separator: str = "--==RAW NOTES==--",
    ) -> None:
        """Initialize the NoteGenerator.

        Args:
            title_template: Template for note titles. Available variables:
                          {date} - Meeting date (YYYYMMDD)
                          {name} - Meeting name
            separator: Separator to use between summary and transcript content
        """
        self.title_template = title_template
        self.separator = separator
        self.logger = logging.getLogger(__name__)
        self.pdf_parser = PDFParser()

    def _format_title(self, matched_files: MatchedFiles) -> str:
        """Format the note title using the template.

        Args:
            matched_files: MatchedFiles object containing meeting metadata

        Returns:
            Formatted title string
        """
        try:
            return self.title_template.format(
                date=matched_files.meeting_date.strftime("%Y%m%d"),
                name=matched_files.meeting_name,
            )
        except KeyError as e:
            self.logger.error(f"Invalid template variable in title template: {e}")
            # Fallback to a basic title format
            return f"{matched_files.meeting_date.strftime('%Y%m%d')} - {matched_files.meeting_name}"
        except Exception as e:
            self.logger.error(f"Error formatting title: {e}")
            return matched_files.meeting_name

    def _format_content(
        self, summary_content: PDFContent, transcript_content: PDFContent
    ) -> str:
        """Format the note content with summary and transcript sections.

        Args:
            summary_content: Parsed summary PDF content
            transcript_content: Parsed transcript PDF content

        Returns:
            Formatted note content
        """
        sections = []

        # Add summary section
        sections.append("## Summary\n")
        sections.append(summary_content.content.strip())

        # Add separator
        sections.append(f"\n\n{self.separator}\n\n")

        # Add transcript section
        sections.append("## Transcript\n")
        sections.append(transcript_content.content.strip())

        return "\n".join(sections)

    def generate_note(self, matched_files: MatchedFiles) -> GeneratedNote:
        """Generate a structured note from matched PDF files.

        Args:
            matched_files: MatchedFiles object containing the files to process

        Returns:
            GeneratedNote object containing the formatted note
        """
        try:
            # Parse both PDFs
            summary_content = self.pdf_parser.parse_pdf(matched_files.summary.path)
            if summary_content.error:
                return GeneratedNote(
                    title="Error",
                    content="",
                    error=f"Error parsing summary PDF: {summary_content.error}",
                )

            transcript_content = self.pdf_parser.parse_pdf(
                matched_files.transcript.path
            )
            if transcript_content.error:
                return GeneratedNote(
                    title="Error",
                    content="",
                    error=f"Error parsing transcript PDF: {transcript_content.error}",
                )

            # Generate title and content
            title = self._format_title(matched_files)
            content = self._format_content(summary_content, transcript_content)

            return GeneratedNote(title=title, content=content)

        except Exception as e:
            error_msg = f"Error generating note: {e}"
            self.logger.error(error_msg)
            return GeneratedNote(title="Error", content="", error=error_msg)
