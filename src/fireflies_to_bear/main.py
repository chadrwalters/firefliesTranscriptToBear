"""Main entry point for the Fireflies to Bear application."""

import configparser
import logging
import os
from pathlib import Path
from typing import List, Optional

from .app import AppConfig, Application
from .config import ConfigValidationError, ConfigValidator

logger = logging.getLogger(__name__)


def setup_logging(log_file: Optional[str] = None, log_level: str = "INFO") -> None:
    """Set up logging configuration.

    Args:
        log_file: Optional path to log file
        log_level: Logging level (default: INFO)
    """
    handlers: List[logging.Handler] = [logging.StreamHandler()]

    if log_file:
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=handlers,
    )


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

    # Default config file location
    if not config_file:
        config_file = os.path.expanduser("~/.config/fireflies-to-bear/config.ini")

    try:
        with open(config_file, "r", encoding="utf-8") as f:
            config.read_file(f)
            logger.debug("Raw config directories: %s", dict(config["directories"]))
            return config
    except Exception as e:
        raise ConfigValidationError(f"Error loading config file: {e}")


def validate_config(config: configparser.ConfigParser) -> AppConfig:
    """Validate configuration and create AppConfig.

    Args:
        config: ConfigParser object with loaded configuration

    Returns:
        Validated AppConfig object

    Raises:
        ConfigValidationError: If validation fails
    """
    validator = ConfigValidator()

    try:
        # Validate directories section
        dir_config = validator.validate_directory_config(dict(config["directories"]))
        logger.debug("Validated directory config: %s", dir_config)

        # Validate note format section
        note_config = validator.validate_note_format_config(dict(config["note_format"]))
        logger.debug("Validated note format config: %s", note_config)

        # Validate service section
        service_config = validator.validate_service_config(dict(config["service"]))
        logger.debug("Validated service config: %s", service_config)

        # Validate logging section
        logging_config = validator.validate_logging_config(dict(config["logging"]))
        logger.debug("Validated logging config: %s", logging_config)

        # Create AppConfig from validated configurations
        return AppConfig(
            watch_directory=str(dir_config.summary_dir),
            transcript_directory=str(dir_config.transcript_dir),
            state_file=Path(os.path.expanduser("~/.fireflies_processor/state.json")),
            sleep_interval=service_config.interval,
            title_template=note_config.title_template,
            backup_count=service_config.backup_count,
            tags=note_config.tags,
        )

    except KeyError as e:
        raise ConfigValidationError(f"Missing required configuration section: {e}")
    except Exception as e:
        raise ConfigValidationError(f"Error validating configuration: {e}")


def init_logging(config: AppConfig) -> None:
    """Initialize logging configuration.

    Args:
        config: Application configuration
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def main() -> None:
    """Main entry point for the application."""
    # Set up basic logging first
    setup_logging()

    try:
        # Load and validate configuration
        config = load_config()
        app_config = validate_config(config)

        # Update logging with validated configuration
        log_config = config["logging"]
        setup_logging(
            log_file=log_config.get("file"),
            log_level=log_config.get("level", "INFO"),
        )

        # Create and run application
        app = Application(app_config)
        app.run()

    except ConfigValidationError as e:
        logging.error(f"Configuration error: {e}")
        raise SystemExit(1)
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
