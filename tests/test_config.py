"""Tests for configuration validation."""

import os
import tempfile
from pathlib import Path
from typing import Dict, Generator, Union

import pytest

from fireflies_to_bear.config import (
    ConfigValidationError,
    ConfigValidator,
    DirectoryConfig,
    LoggingConfig,
    NoteFormatConfig,
    ServiceConfig,
)


@pytest.fixture
def temp_dirs() -> Generator[Dict[str, Path], None, None]:
    """Create temporary directories for testing."""
    with tempfile.TemporaryDirectory() as summary_dir, tempfile.TemporaryDirectory() as transcript_dir, tempfile.TemporaryDirectory() as state_dir, tempfile.TemporaryDirectory() as log_dir:
        yield {
            "summary_dir": Path(summary_dir),
            "transcript_dir": Path(transcript_dir),
            "state_dir": Path(state_dir),
            "log_dir": Path(log_dir),
        }


@pytest.fixture
def validator() -> ConfigValidator:
    """Create a ConfigValidator instance."""
    return ConfigValidator()


def test_validate_directory_config_valid(
    validator: ConfigValidator, temp_dirs: Dict[str, Path]
) -> None:
    """Test directory configuration validation with valid inputs."""
    config = {
        "summary_dir": str(temp_dirs["summary_dir"]),
        "transcript_dir": str(temp_dirs["transcript_dir"]),
    }

    result = validator.validate_directory_config(config)
    assert isinstance(result, DirectoryConfig)
    assert result.summary_dir == temp_dirs["summary_dir"]
    assert result.transcript_dir == temp_dirs["transcript_dir"]


def test_validate_directory_config_missing_dirs(validator: ConfigValidator) -> None:
    """Test directory configuration validation with missing directories."""
    config = {
        "summary_dir": "/nonexistent/summary",
        "transcript_dir": "/nonexistent/transcript",
    }

    with pytest.raises(ConfigValidationError, match="Summary directory does not exist"):
        validator.validate_directory_config(config)


def test_validate_directory_config_missing_keys(validator: ConfigValidator) -> None:
    """Test directory configuration validation with missing required keys."""
    config = {"summary_dir": "/some/path"}

    with pytest.raises(
        ConfigValidationError, match="Missing required directory configuration"
    ):
        validator.validate_directory_config(config)


def test_validate_note_format_config_valid(validator: ConfigValidator) -> None:
    """Test note format configuration validation with valid inputs."""
    config = {
        "title_template": "{date} - {name}",
        "separator": "--==RAW NOTES==--",
        "tags": "meeting,notes",
    }

    result = validator.validate_note_format_config(config)
    assert isinstance(result, NoteFormatConfig)
    assert result.title_template == config["title_template"]
    assert result.separator == config["separator"]
    assert result.tags == config["tags"]


def test_validate_note_format_config_missing_placeholders(
    validator: ConfigValidator, caplog: pytest.LogCaptureFixture
) -> None:
    """Test note format configuration validation with missing placeholders."""
    config = {
        "title_template": "Meeting Notes",
        "separator": "--==RAW NOTES==--",
    }

    result = validator.validate_note_format_config(config)
    assert "Title template does not contain {date} placeholder" in caplog.text
    assert "Title template does not contain meeting name placeholder" in caplog.text


def test_validate_note_format_config_missing_title(validator: ConfigValidator) -> None:
    """Test note format configuration validation with missing title template."""
    config = {"separator": "--==RAW NOTES==--"}

    with pytest.raises(
        ConfigValidationError, match="Missing required note format configuration"
    ):
        validator.validate_note_format_config(config)


def test_validate_service_config_valid(
    validator: ConfigValidator, temp_dirs: Dict[str, Path]
) -> None:
    """Test service configuration validation with valid inputs."""
    state_file = temp_dirs["state_dir"] / "state.json"
    config: Dict[str, Union[str, int]] = {
        "interval": "300",
        "state_file": str(state_file),
        "backup_count": "3",
    }

    result = validator.validate_service_config(config)
    assert isinstance(result, ServiceConfig)
    assert result.interval == 300
    assert result.state_file == state_file
    assert result.backup_count == 3


def test_validate_service_config_invalid_interval(
    validator: ConfigValidator, temp_dirs: Dict[str, Path]
) -> None:
    """Test service configuration validation with invalid interval."""
    state_file = temp_dirs["state_dir"] / "state.json"
    config: Dict[str, Union[str, int]] = {
        "interval": "invalid",
        "state_file": str(state_file),
    }

    with pytest.raises(
        ConfigValidationError, match="Invalid service configuration value"
    ):
        validator.validate_service_config(config)


def test_validate_service_config_invalid_backup_count(
    validator: ConfigValidator, temp_dirs: Dict[str, Path]
) -> None:
    """Test service configuration validation with invalid backup count."""
    state_file = temp_dirs["state_dir"] / "state.json"
    config: Dict[str, Union[str, int]] = {
        "interval": "300",
        "state_file": str(state_file),
        "backup_count": "0",
    }

    with pytest.raises(ConfigValidationError, match="Backup count must be at least 1"):
        validator.validate_service_config(config)


def test_validate_logging_config_valid(
    validator: ConfigValidator, temp_dirs: Dict[str, Path]
) -> None:
    """Test logging configuration validation with valid inputs."""
    log_file = temp_dirs["log_dir"] / "app.log"
    config = {
        "level": "INFO",
        "file": str(log_file),
    }

    result = validator.validate_logging_config(config)
    assert isinstance(result, LoggingConfig)
    assert result.level == "INFO"
    assert result.file == log_file


def test_validate_logging_config_invalid_level(validator: ConfigValidator) -> None:
    """Test logging configuration validation with invalid log level."""
    config = {
        "level": "INVALID",
    }

    with pytest.raises(ConfigValidationError, match="Invalid log level"):
        validator.validate_logging_config(config)


def test_validate_logging_config_no_file(validator: ConfigValidator) -> None:
    """Test logging configuration validation without log file."""
    config = {
        "level": "INFO",
    }

    result = validator.validate_logging_config(config)
    assert isinstance(result, LoggingConfig)
    assert result.level == "INFO"
    assert result.file is None


def test_validate_logging_config_unwritable_log_dir(
    validator: ConfigValidator, temp_dirs: Dict[str, Path]
) -> None:
    """Test logging configuration validation with unwritable log directory."""
    log_dir = temp_dirs["log_dir"]
    os.chmod(log_dir, 0o444)  # Read-only

    try:
        config = {
            "level": "INFO",
            "file": str(log_dir / "app.log"),
        }

        with pytest.raises(
            ConfigValidationError, match="Cannot write to log directory"
        ):
            validator.validate_logging_config(config)
    finally:
        os.chmod(log_dir, 0o755)  # Restore permissions for cleanup
