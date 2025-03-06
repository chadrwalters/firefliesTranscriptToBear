"""Main entry point for the Fireflies to Bear application."""

import argparse
import configparser
import logging
import os
from pathlib import Path
from typing import List, Optional

from .app import AppConfig, Application
from .config import (
    ConfigValidationError,
    ConfigValidator,
    create_default_config,
    get_config_file_path,
    get_state_file_path,
    load_config,
)

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


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description="Process Fireflies.ai PDFs and create Bear notes"
    )

    # General options
    parser.add_argument(
        "--config",
        "-c",
        help="Path to config file (default: .f2b/config.ini or ~/.config/fireflies-to-bear/config.ini)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output"
    )

    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Init command
    init_parser = subparsers.add_parser("init", help="Initialize configuration")
    init_parser.add_argument(
        "--force", "-f", action="store_true", help="Overwrite existing configuration"
    )

    # Run command
    run_parser = subparsers.add_parser("run", help="Process PDF files")
    run_parser.add_argument(
        "--summary", "-s", help="Path to a specific summary PDF file to process"
    )
    run_parser.add_argument(
        "--transcript", "-t", help="Path to a specific transcript PDF file to process"
    )
    run_parser.add_argument(
        "--watch",
        "-w",
        action="store_true",
        help="Watch directories for changes (continuous mode)",
    )

    # List command
    list_parser = subparsers.add_parser("list", help="List processed notes")

    return parser.parse_args()


def initialize_config(force: bool = False) -> None:
    """Initialize configuration in the .f2b directory.

    Args:
        force: Whether to overwrite existing configuration
    """
    config_path = get_config_file_path()

    if config_path.exists() and not force:
        logger.info(f"Configuration already exists at {config_path}")
        logger.info("Use --force to overwrite")
        return

    path, config = create_default_config()
    logger.info(f"Created default configuration at {path}")


def list_processed_notes(app: Application) -> None:
    """List all processed notes.

    Args:
        app: Application instance
    """
    processed_files = app.state_manager.get_processed_files()

    if not processed_files:
        logger.info("No processed files found")
        return

    logger.info(f"Found {len(processed_files)} processed files:")
    for i, file in enumerate(processed_files, 1):
        logger.info(
            f"{i}. Summary: {Path(file.summary_path).name}, "
            f"Transcript: {Path(file.transcript_path).name}, "
            f"Bear ID: {file.bear_note_id}, "
            f"Last processed: {file.last_processed}"
        )


def process_specific_files(
    app: Application, summary_path: str, transcript_path: str
) -> None:
    """Process specific PDF files.

    Args:
        app: Application instance
        summary_path: Path to summary PDF
        transcript_path: Path to transcript PDF
    """
    app.process_specific_files(Path(summary_path), Path(transcript_path))


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

        # Get state file path
        state_file = get_state_file_path()

        # Create AppConfig from validated configurations
        return AppConfig(
            watch_directory=str(dir_config.summary_dir),
            transcript_directory=str(dir_config.transcript_dir),
            state_file=state_file,
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
    args = parse_arguments()

    # Set up basic logging
    log_level = "DEBUG" if args.verbose else "INFO"
    setup_logging(log_level=log_level)

    try:
        # Handle init command
        if args.command == "init":
            initialize_config(force=args.force)
            return

        # Load and validate configuration
        config = load_config(args.config)
        app_config = validate_config(config)

        # Update logging with validated configuration
        if "logging" in config:
            log_config = config["logging"]
            log_file = log_config.get("file")

            # If log file is relative, make it relative to .f2b dir
            if (
                log_file
                and not log_file.startswith("/")
                and not log_file.startswith("~")
            ):
                log_file = str(Path.cwd() / ".f2b" / log_file)

            setup_logging(
                log_file=log_file,
                log_level=log_config.get("level", log_level),
            )

        # Create application instance
        app = Application(app_config)

        if args.command == "list":
            # List processed notes
            list_processed_notes(app)
        elif args.command == "run":
            if args.summary and args.transcript:
                # Process specific files
                process_specific_files(app, args.summary, args.transcript)
            elif args.watch:
                # Run in continuous watch mode
                app.run()
            else:
                # Single processing run
                app.process_directory()
        else:
            # Default behavior with no command - single process run
            app.process_directory()

    except ConfigValidationError as e:
        logging.error(f"Configuration error: {e}")
        raise SystemExit(1)
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
