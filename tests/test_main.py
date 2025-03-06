"""Tests for the main module and CLI functionality."""

import argparse
from pathlib import Path
from unittest.mock import MagicMock, patch

from fireflies_to_bear.main import (
    initialize_config,
    list_processed_notes,
    main,
    parse_arguments,
    process_specific_files,
)


def test_parse_arguments() -> None:
    """Test argument parsing."""
    with patch("argparse.ArgumentParser.parse_args") as mock_parse_args:
        # Test with init command
        mock_parse_args.return_value = argparse.Namespace(
            command="init",
            force=True,
            config=None,
            verbose=False,
        )
        args = parse_arguments()
        assert args.command == "init"
        assert args.force is True

        # Test with run command
        mock_parse_args.return_value = argparse.Namespace(
            command="run",
            watch=True,
            summary=None,
            transcript=None,
            config=None,
            verbose=True,
        )
        args = parse_arguments()
        assert args.command == "run"
        assert args.watch is True
        assert args.verbose is True

        # Test with list command
        mock_parse_args.return_value = argparse.Namespace(
            command="list",
            config="/custom/config.ini",
            verbose=False,
        )
        args = parse_arguments()
        assert args.command == "list"
        assert args.config == "/custom/config.ini"


@patch("fireflies_to_bear.main.get_config_file_path")
@patch("fireflies_to_bear.main.create_default_config")
def test_initialize_config(
    mock_create_default: MagicMock, mock_get_path: MagicMock
) -> None:
    """Test initialize_config function."""
    # Setup the mock to return a tuple with expected values
    mock_create_default.return_value = (Path("/mock/path/config.ini"), MagicMock())

    # Mock config path doesn't exist
    mock_path = MagicMock()
    mock_path.exists.return_value = False
    mock_get_path.return_value = mock_path

    # Call function
    initialize_config()

    # Should create default config
    mock_create_default.assert_called_once()

    # Reset mocks
    mock_create_default.reset_mock()

    # Mock config path exists and force=False
    mock_path.exists.return_value = True
    initialize_config(force=False)

    # Should not create default config
    mock_create_default.assert_not_called()

    # Reset mocks
    mock_create_default.reset_mock()

    # Mock config path exists but force=True
    mock_path.exists.return_value = True
    initialize_config(force=True)

    # Should create default config
    mock_create_default.assert_called_once()


@patch("fireflies_to_bear.main.logger")
def test_list_processed_notes(mock_logger: MagicMock) -> None:
    """Test list_processed_notes function."""
    # Mock app with empty state
    mock_app = MagicMock()
    mock_app.state_manager.get_processed_files.return_value = []

    # Call function
    list_processed_notes(mock_app)

    # Should log message
    mock_logger.info.assert_any_call("No processed files found")

    # Reset mocks
    mock_logger.reset_mock()

    # Mock app with populated state
    mock_file = MagicMock()
    mock_file.summary_path = "/path/to/summary.pdf"
    mock_file.transcript_path = "/path/to/transcript.pdf"
    mock_file.bear_note_id = "note123"
    mock_file.last_processed = "2023-01-01T12:00:00"

    mock_app.state_manager.get_processed_files.return_value = [mock_file]

    # Call function
    list_processed_notes(mock_app)

    # Should log files info
    mock_logger.info.assert_any_call("Found 1 processed files:")
    mock_logger.info.assert_any_call(
        "1. Summary: summary.pdf, "
        "Transcript: transcript.pdf, "
        "Bear ID: note123, "
        "Last processed: 2023-01-01T12:00:00"
    )


def test_process_specific_files() -> None:
    """Test process_specific_files function."""
    mock_app = MagicMock()

    # Call function
    process_specific_files(mock_app, "/path/to/summary.pdf", "/path/to/transcript.pdf")

    # Should call app.process_specific_files
    mock_app.process_specific_files.assert_called_once_with(
        Path("/path/to/summary.pdf"), Path("/path/to/transcript.pdf")
    )


@patch("fireflies_to_bear.main.parse_arguments")
@patch("fireflies_to_bear.main.initialize_config")
@patch("fireflies_to_bear.main.load_config")
@patch("fireflies_to_bear.main.validate_config")
@patch("fireflies_to_bear.main.setup_logging")
@patch("fireflies_to_bear.main.Application")
@patch("fireflies_to_bear.main.list_processed_notes")
@patch("fireflies_to_bear.main.process_specific_files")
def test_main_init_command(
    mock_process_specific: MagicMock,
    mock_list_notes: MagicMock,
    mock_application: MagicMock,
    mock_setup_logging: MagicMock,
    mock_validate_config: MagicMock,
    mock_load_config: MagicMock,
    mock_initialize: MagicMock,
    mock_parse_args: MagicMock,
) -> None:
    """Test main function with init command."""
    # Mock args
    mock_args = MagicMock()
    mock_args.command = "init"
    mock_args.force = True
    mock_args.verbose = False
    mock_parse_args.return_value = mock_args

    # Call main
    main()

    # Should initialize config
    mock_initialize.assert_called_once_with(force=True)

    # Should not call other functions
    mock_load_config.assert_not_called()
    mock_validate_config.assert_not_called()
    mock_application.assert_not_called()


@patch("fireflies_to_bear.main.parse_arguments")
@patch("fireflies_to_bear.main.load_config")
@patch("fireflies_to_bear.main.validate_config")
@patch("fireflies_to_bear.main.setup_logging")
@patch("fireflies_to_bear.main.Application")
@patch("fireflies_to_bear.main.list_processed_notes")
def test_main_list_command(
    mock_list_notes: MagicMock,
    mock_application: MagicMock,
    mock_setup_logging: MagicMock,
    mock_validate_config: MagicMock,
    mock_load_config: MagicMock,
    mock_parse_args: MagicMock,
) -> None:
    """Test main function with list command."""
    # Mock args
    mock_args = MagicMock()
    mock_args.command = "list"
    mock_args.config = None
    mock_args.verbose = False
    mock_parse_args.return_value = mock_args

    # Mock config and app
    mock_config = MagicMock()
    mock_config.__getitem__.return_value = {}
    mock_load_config.return_value = mock_config

    mock_app_instance = MagicMock()
    mock_application.return_value = mock_app_instance

    # Call main
    main()

    # Should create app and list notes
    mock_load_config.assert_called_once_with(None)
    mock_validate_config.assert_called_once_with(mock_config)
    mock_application.assert_called_once()
    mock_list_notes.assert_called_once_with(mock_app_instance)

    # Should not process directory
    mock_app_instance.process_directory.assert_not_called()
    mock_app_instance.run.assert_not_called()


@patch("fireflies_to_bear.main.parse_arguments")
@patch("fireflies_to_bear.main.load_config")
@patch("fireflies_to_bear.main.validate_config")
@patch("fireflies_to_bear.main.setup_logging")
@patch("fireflies_to_bear.main.Application")
@patch("fireflies_to_bear.main.process_specific_files")
def test_main_run_specific_files(
    mock_process_specific: MagicMock,
    mock_application: MagicMock,
    mock_setup_logging: MagicMock,
    mock_validate_config: MagicMock,
    mock_load_config: MagicMock,
    mock_parse_args: MagicMock,
) -> None:
    """Test main function with run command for specific files."""
    # Mock args
    mock_args = MagicMock()
    mock_args.command = "run"
    mock_args.config = None
    mock_args.verbose = False
    mock_args.summary = "/path/to/summary.pdf"
    mock_args.transcript = "/path/to/transcript.pdf"
    mock_args.watch = False
    mock_parse_args.return_value = mock_args

    # Mock config and app
    mock_config = MagicMock()
    mock_config.__getitem__.return_value = {}
    mock_load_config.return_value = mock_config

    mock_app_instance = MagicMock()
    mock_application.return_value = mock_app_instance

    # Call main
    main()

    # Should create app and process specific files
    mock_load_config.assert_called_once_with(None)
    mock_validate_config.assert_called_once_with(mock_config)
    mock_application.assert_called_once()
    mock_process_specific.assert_called_once_with(
        mock_app_instance, "/path/to/summary.pdf", "/path/to/transcript.pdf"
    )

    # Should not process directory or run in watch mode
    mock_app_instance.process_directory.assert_not_called()
    mock_app_instance.run.assert_not_called()


@patch("fireflies_to_bear.main.parse_arguments")
@patch("fireflies_to_bear.main.load_config")
@patch("fireflies_to_bear.main.validate_config")
@patch("fireflies_to_bear.main.setup_logging")
@patch("fireflies_to_bear.main.Application")
def test_main_run_watch_mode(
    mock_application: MagicMock,
    mock_setup_logging: MagicMock,
    mock_validate_config: MagicMock,
    mock_load_config: MagicMock,
    mock_parse_args: MagicMock,
) -> None:
    """Test main function with run command in watch mode."""
    # Mock args
    mock_args = MagicMock()
    mock_args.command = "run"
    mock_args.config = None
    mock_args.verbose = False
    mock_args.summary = None
    mock_args.transcript = None
    mock_args.watch = True
    mock_parse_args.return_value = mock_args

    # Mock config and app
    mock_config = MagicMock()
    mock_config.__getitem__.return_value = {}
    mock_load_config.return_value = mock_config

    mock_app_instance = MagicMock()
    mock_application.return_value = mock_app_instance

    # Call main
    main()

    # Should create app and run in watch mode
    mock_load_config.assert_called_once_with(None)
    mock_validate_config.assert_called_once_with(mock_config)
    mock_application.assert_called_once()
    mock_app_instance.run.assert_called_once()

    # Should not process directory
    mock_app_instance.process_directory.assert_not_called()
