# Fireflies to Bear

A macOS application that automatically processes Fireflies.ai meeting PDFs and creates organized notes in Bear.

## Features

- Automatically monitors Fireflies.ai PDF directories
- Processes both summary and transcript PDFs
- Creates organized notes in Bear with proper formatting
- Maintains state to avoid duplicate processing
- Handles file updates and modifications
- Runs as a background service with automatic startup
- Comprehensive error handling and recovery
- Configurable note formatting and organization

## Requirements

- macOS 10.15 or later
- Python 3.8 or later
- Bear note-taking app
- Fireflies.ai account with PDF export enabled

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/fireflies-to-bear.git
   cd fireflies-to-bear
   ```

2. Run the installation script:
   ```bash
   ./scripts/install.sh
   ```

   This will:
   - Create a Python virtual environment
   - Install all required dependencies
   - Set up configuration directories
   - Create and load the LaunchAgent for automatic startup

## Configuration

The configuration file is located at `~/.config/fireflies-to-bear/config.ini`. You can edit it to customize:

```ini
[directories]
# Directory containing Fireflies summary PDFs
summary_dir = ~/Library/CloudStorage/GoogleDrive/My Drive/Fireflies Meetings/Summaries
# Directory containing Fireflies transcript PDFs
transcript_dir = ~/Library/CloudStorage/GoogleDrive/My Drive/Fireflies Meetings/Transcripts

[note_format]
# Template for note titles. Available variables: {date}, {meeting_name}
title_template = {date} - {meeting_name}
# Separator between summary and transcript content
separator = --==RAW NOTES==--
# Optional tags for Bear notes
tags = meeting,notes

[service]
# Interval between directory scans (in seconds)
interval = 300
# Location of the state file
state_file = ~/.fireflies_processor/state.json
# Number of state file backups to keep
backup_count = 3

[logging]
# Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
level = INFO
# Optional log file location
file = ~/.fireflies_processor/logs/processor.log
```

## Usage

The application runs automatically in the background after installation. It will:

1. Monitor the configured directories for new or modified PDFs
2. Process matching summary and transcript files
3. Create or update Bear notes with the content
4. Maintain state to track processed files

### Manual Control

You can manually control the service using:

```bash
# Stop the service
launchctl unload ~/Library/LaunchAgents/com.fireflies-to-bear.plist

# Start the service
launchctl load ~/Library/LaunchAgents/com.fireflies-to-bear.plist
```

### Command Line Usage

You can also run the application directly:

```bash
# Run in the foreground
fireflies-to-bear

# Create default configuration
fireflies-to-bear --init

# Run with specific config file
fireflies-to-bear --config /path/to/config.ini

# Show help
fireflies-to-bear --help
```

## Uninstallation

To remove the application:

```bash
./scripts/uninstall.sh
```

This will:
- Stop and remove the background service
- Remove the virtual environment
- Optionally remove configuration and log files

## Development

### Setup Development Environment

1. Create a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Install development dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=fireflies_to_bear

# Run specific test file
pytest tests/test_app.py
```

### Code Quality

```bash
# Format code
black src/ tests/
isort src/ tests/

# Run linters
ruff check .
mypy src/

# Run all checks
pre-commit run --all-files
```

## Troubleshooting

### Common Issues

1. **Files not being processed**
   - Check directory permissions
   - Verify file naming patterns match
   - Check log files for errors

2. **Bear notes not being created**
   - Ensure Bear is installed and running
   - Check x-callback-url permissions
   - Verify Bear can be opened via URL scheme

3. **Service not starting**
   - Check LaunchAgent permissions
   - Verify Python environment is correct
   - Check log files for startup errors

### Log Files

- Application logs: `~/Library/Logs/fireflies-to-bear/output.log`
- Error logs: `~/Library/Logs/fireflies-to-bear/error.log`

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linters
5. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
