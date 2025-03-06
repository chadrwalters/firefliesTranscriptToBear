"""Configuration validation and management for the Fireflies to Bear application."""

import configparser
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple, Union


class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""

    pass


@dataclass
class DirectoryConfig:
    """Configuration for watched directories."""

    summary_dir: Path
    transcript_dir: Path


@dataclass
class NoteFormatConfig:
    """Configuration for note formatting."""

    title_template: str
    separator: str
    tags: Optional[str] = None


@dataclass
class ServiceConfig:
    """Configuration for service operation."""

    interval: int
    state_file: Path
    backup_count: int = 3


@dataclass
class LoggingConfig:
    """Configuration for logging."""

    level: str
    file: Optional[Path] = None


def get_config_directory() -> Path:
    """Get the configuration directory path.

    Prioritizes local .f2b directory, falls back to global config.

    Returns:
        Path to the configuration directory
    """
    local_config_dir = Path.cwd() / ".f2b"
    if local_config_dir.exists():
        return local_config_dir
    return Path(os.path.expanduser("~/.config/fireflies-to-bear"))


def ensure_config_directory() -> Path:
    """Ensure the config directory exists and return its path.

    Creates .f2b directory in current working directory if it doesn't exist.

    Returns:
        Path to the configuration directory
    """
    config_dir = Path.cwd() / ".f2b"
    config_dir.mkdir(exist_ok=True)
    return config_dir


def get_state_file_path() -> Path:
    """Get the state file path, prioritizing local directory.

    Returns:
        Path to the state file
    """
    local_state_file = Path.cwd() / ".f2b" / "state.json"
    if local_state_file.parent.exists():
        return local_state_file
    return Path(os.path.expanduser("~/.fireflies_processor/state.json"))


def get_config_file_path(config_file: Optional[str] = None) -> Path:
    """Get the configuration file path.

    Args:
        config_file: Optional explicit config file path

    Returns:
        Path to the configuration file
    """
    if config_file:
        return Path(os.path.expanduser(config_file))

    local_config_file = Path.cwd() / ".f2b" / "config.ini"
    if local_config_file.exists():
        return local_config_file

    # Fall back to the global config
    return Path(os.path.expanduser("~/.config/fireflies-to-bear/config.ini"))


def create_default_config() -> Tuple[Path, configparser.ConfigParser]:
    """Create a default configuration file in the .f2b directory.

    Returns:
        Tuple of (config_path, config_parser)
    """
    config_dir = ensure_config_directory()
    config_path = config_dir / "config.ini"

    config = configparser.ConfigParser()

    # Default configuration sections
    config["directories"] = {
        "summary_dir": "~/Library/CloudStorage/GoogleDrive/My Drive/Fireflies Meetings/Summaries",
        "transcript_dir": "~/Library/CloudStorage/GoogleDrive/My Drive/Fireflies Meetings/Transcripts",
    }

    config["note_format"] = {
        "title_template": "{date} - {meeting_name}",
        "separator": "--==RAW NOTES==--",
        "tags": "meeting,notes",
    }

    config["service"] = {
        "interval": "300",
        "state_file": ".f2b/state.json",
        "backup_count": "3",
    }

    config["logging"] = {
        "level": "INFO",
        "file": ".f2b/logs/processor.log",
    }

    # Create logs directory
    logs_dir = config_dir / "logs"
    logs_dir.mkdir(exist_ok=True)

    # Write the configuration file
    with open(config_path, "w", encoding="utf-8") as f:
        config.write(f)

    return config_path, config


def load_config(config_file: Optional[str] = None) -> configparser.ConfigParser:
    """Load configuration from file.

    Args:
        config_file: Optional path to config file. If not provided, uses default location.

    Returns:
        ConfigParser object with loaded configuration

    Raises:
        ConfigValidationError: If config file cannot be loaded
    """
    config = configparser.ConfigParser()
    config_path = get_config_file_path(config_file)

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config.read_file(f)
            return config
    except FileNotFoundError:
        # If config doesn't exist, create default one
        if not config_file:  # Only create default if no specific path was requested
            path, config = create_default_config()
            logging.info(f"Created default configuration at {path}")
            return config
        else:
            raise ConfigValidationError(f"Config file not found: {config_path}")
    except Exception as e:
        raise ConfigValidationError(f"Error loading config file: {e}")


class ConfigValidator:
    """Validates and manages application configuration."""

    def __init__(self) -> None:
        """Initialize the configuration validator."""
        self.logger = logging.getLogger(__name__)

    def validate_directory_config(self, config: Dict[str, str]) -> DirectoryConfig:
        """Validate directory configuration.

        Args:
            config: Directory configuration dictionary

        Returns:
            Validated DirectoryConfig object

        Raises:
            ConfigValidationError: If validation fails
        """
        try:
            summary_dir = Path(os.path.expanduser(config["summary_dir"]))
            transcript_dir = Path(os.path.expanduser(config["transcript_dir"]))

            # Validate directory existence
            if not summary_dir.exists():
                raise ConfigValidationError(
                    f"Summary directory does not exist: {summary_dir}"
                )
            if not transcript_dir.exists():
                raise ConfigValidationError(
                    f"Transcript directory does not exist: {transcript_dir}"
                )

            # Validate directory permissions
            if not os.access(summary_dir, os.R_OK):
                raise ConfigValidationError(
                    f"Cannot read from summary directory: {summary_dir}"
                )
            if not os.access(transcript_dir, os.R_OK):
                raise ConfigValidationError(
                    f"Cannot read from transcript directory: {transcript_dir}"
                )

            return DirectoryConfig(
                summary_dir=summary_dir, transcript_dir=transcript_dir
            )

        except KeyError as e:
            raise ConfigValidationError(
                f"Missing required directory configuration: {e}"
            )

    def validate_note_format_config(self, config: Dict[str, str]) -> NoteFormatConfig:
        """Validate note format configuration.

        Args:
            config: Note format configuration dictionary

        Returns:
            Validated NoteFormatConfig object

        Raises:
            ConfigValidationError: If validation fails
        """
        try:
            title_template = config["title_template"]
            separator = config.get("separator", "--==RAW NOTES==--")

            # Validate title template
            if not title_template:
                raise ConfigValidationError("Title template cannot be empty")
            if "{date}" not in title_template:
                self.logger.warning(
                    "Title template does not contain {date} placeholder"
                )
            if (
                "{meeting_name}" not in title_template
                and "{name}" not in title_template
            ):
                self.logger.warning(
                    "Title template does not contain meeting name placeholder"
                )

            return NoteFormatConfig(
                title_template=title_template,
                separator=separator,
                tags=config.get("tags"),
            )

        except KeyError as e:
            raise ConfigValidationError(
                f"Missing required note format configuration: {e}"
            )

    def validate_service_config(
        self, config: Dict[str, Union[str, int]]
    ) -> ServiceConfig:
        """Validate service configuration.

        Args:
            config: Service configuration dictionary

        Returns:
            Validated ServiceConfig object

        Raises:
            ConfigValidationError: If validation fails
        """
        try:
            # Get and validate interval
            interval = int(config.get("interval", 300))
            if interval < 60:
                self.logger.warning("Sleep interval is less than 60 seconds")

            # Get and validate state file
            state_file = Path(os.path.expanduser(str(config["state_file"])))
            state_dir = state_file.parent

            # Create state directory if it doesn't exist
            try:
                state_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                raise ConfigValidationError(
                    f"Cannot create state directory {state_dir}: {e}"
                )

            # Validate state directory permissions
            if not os.access(state_dir, os.W_OK):
                raise ConfigValidationError(
                    f"Cannot write to state directory: {state_dir}"
                )

            # Get backup count
            backup_count = int(config.get("backup_count", 3))
            if backup_count < 1:
                raise ConfigValidationError("Backup count must be at least 1")

            return ServiceConfig(
                interval=interval, state_file=state_file, backup_count=backup_count
            )

        except KeyError as e:
            raise ConfigValidationError(f"Missing required service configuration: {e}")
        except ValueError as e:
            raise ConfigValidationError(f"Invalid service configuration value: {e}")

    def validate_logging_config(self, config: Dict[str, str]) -> LoggingConfig:
        """Validate logging configuration.

        Args:
            config: Logging configuration dictionary

        Returns:
            Validated LoggingConfig object

        Raises:
            ConfigValidationError: If validation fails
        """
        try:
            # Validate log level
            level = config.get("level", "INFO").upper()
            valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
            if level not in valid_levels:
                raise ConfigValidationError(
                    f"Invalid log level: {level}. Must be one of {valid_levels}"
                )

            # Validate log file if specified
            log_file = config.get("file")
            if log_file:
                log_path = Path(os.path.expanduser(log_file))
                log_dir = log_path.parent

                # Create log directory if it doesn't exist
                try:
                    log_dir.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    raise ConfigValidationError(
                        f"Cannot create log directory {log_dir}: {e}"
                    )

                # Validate log directory permissions
                if not os.access(log_dir, os.W_OK):
                    raise ConfigValidationError(
                        f"Cannot write to log directory: {log_dir}"
                    )

                return LoggingConfig(level=level, file=log_path)

            return LoggingConfig(level=level)

        except Exception as e:
            raise ConfigValidationError(f"Error validating logging configuration: {e}")
