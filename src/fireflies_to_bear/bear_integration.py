"""Component for integrating with Bear.app using x-callback-url scheme."""

import logging
import re
import subprocess
import urllib.parse
from dataclasses import dataclass
from typing import Optional

from .note_generator import GeneratedNote


@dataclass
class BearResponse:
    """Represents a response from Bear.app."""

    success: bool
    note_identifier: Optional[str] = None
    error: Optional[str] = None


class BearIntegration:
    """Handles communication with Bear.app using x-callback-url scheme."""

    def __init__(self) -> None:
        """Initialize the BearIntegration."""
        self.logger = logging.getLogger(__name__)

    def _encode_parameters(self, **params: str) -> str:
        """Encode parameters for x-callback-url.

        Args:
            **params: Keyword arguments to encode

        Returns:
            URL-encoded parameter string
        """
        encoded = {}
        for key, value in params.items():
            # Single encode with safe characters preserved
            encoded[key] = urllib.parse.quote(str(value), safe="")
        return "&".join(f"{k}={v}" for k, v in encoded.items())

    def _create_bear_url(self, action: str, **params: str) -> str:
        """Create a Bear.app x-callback-url.

        Args:
            action: The Bear action to perform (e.g., create, add-text)
            **params: Additional parameters for the action

        Returns:
            Complete x-callback-url
        """
        base_url = "bear://x-callback-url"
        params_str = self._encode_parameters(**params)
        return f"{base_url}/{action}?{params_str}"

    def _execute_bear_command(self, url: str) -> str:
        """Execute a Bear.app command using the URL scheme.

        Args:
            url: The x-callback-url to execute

        Returns:
            Command output or error message
        """
        try:
            # Use open command to trigger the URL scheme
            cmd = ["open", url]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return result.stdout
        except subprocess.CalledProcessError as e:
            error_msg = f"Error executing Bear command: {e.stderr}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)

    def _extract_note_identifier(self, title: str) -> Optional[str]:
        """Extract Bear note identifier from title if it exists.

        Args:
            title: Note title to check

        Returns:
            Note identifier if found, None otherwise
        """
        # Bear adds identifiers like "My Note [1A2B3C]"
        match = re.search(r"\[([A-F0-9]+)\]$", title)
        return match.group(1) if match else None

    def create_note(
        self, note: GeneratedNote, tags: Optional[str] = None
    ) -> BearResponse:
        """Create a new note in Bear.app.

        Args:
            note: GeneratedNote object containing title and content
            tags: Optional comma-separated list of tags (without #)

        Returns:
            BearResponse indicating success or failure
        """
        try:
            # Format content with tags at the end
            content = note.content
            if tags:
                # Add tags at the end of the content
                formatted_tags = " ".join(f"#{tag.strip()}" for tag in tags.split(","))
                content = f"{content}\n\n{formatted_tags}"

            params = {
                "title": note.title,
                "text": content,
                "open_note": "no",  # Don't open the note automatically
            }

            url = self._create_bear_url("create", **params)
            self._execute_bear_command(url)

            # Try to get the note identifier
            identifier = self._extract_note_identifier(note.title)
            return BearResponse(success=True, note_identifier=identifier)

        except Exception as e:
            error_msg = f"Error creating note in Bear: {e}"
            self.logger.error(error_msg)
            return BearResponse(success=False, error=error_msg)

    def update_note(
        self, note_identifier: str, note: GeneratedNote, tags: Optional[str] = None
    ) -> BearResponse:
        """Update an existing note in Bear.app.

        Args:
            note_identifier: Bear note identifier
            note: GeneratedNote object containing new content
            tags: Optional comma-separated list of tags (without #)

        Returns:
            BearResponse indicating success or failure
        """
        try:
            # Format content with tags at the end
            content = note.content
            if tags:
                # Add tags at the end of the content
                formatted_tags = " ".join(f"#{tag.strip()}" for tag in tags.split(","))
                content = f"{content}\n\n{formatted_tags}"

            params = {
                "id": note_identifier,
                "title": note.title,
                "text": content,
                "mode": "replace",  # Replace entire note content
                "open_note": "no",  # Don't open the note automatically
            }

            url = self._create_bear_url("add-text", **params)
            self._execute_bear_command(url)

            return BearResponse(success=True, note_identifier=note_identifier)

        except Exception as e:
            error_msg = f"Error updating note in Bear: {e}"
            self.logger.error(error_msg)
            return BearResponse(success=False, error=error_msg)

    def search_note(self, title: str) -> Optional[str]:
        """Search for a note in Bear.app by title.

        Args:
            title: Note title to search for

        Returns:
            Note identifier if found, None otherwise
        """
        try:
            # Search for the note using the search action
            params = {
                "term": title,
                "show_window": "no",
            }
            url = self._create_bear_url("search", **params)
            self._execute_bear_command(url)

            # Try to extract the identifier from the title
            return self._extract_note_identifier(title)

        except Exception as e:
            self.logger.error(f"Error searching for note in Bear: {e}")
            return None
