# Fireflies to Bear

A command-line tool that processes Fireflies.ai meeting PDFs and creates organized notes in Bear.

## Features

- Process Fireflies.ai summary and transcript PDFs
- Creates organized notes in Bear with proper formatting
- Maintains state to avoid duplicate processing
- Handles file updates and modifications
- Configurable note formatting and organization
- Works in both single-run and watch modes

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

2. Install the package:
   ```bash
   pip install -e .
   ```

## Configuration

Initialize the configuration in your current directory:

```bash
fireflies-to-bear init
```

This creates a `.f2b` directory with configuration files. Edit `.f2b/config.ini` to customize:

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
# Interval between directory scans (in seconds) - only used with --watch
interval = 300
# Location of the state file (relative to .f2b directory)
state_file = state.json
# Number of state file backups to keep
backup_count = 3

[logging]
# Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
level = INFO
# Optional log file location (relative to .f2b directory)
file = logs/processor.log
```

## Usage

### Process Files Once

```bash
# Process all files based on configuration
fireflies-to-bear run

# Process specific files
fireflies-to-bear run --summary path/to/summary.pdf --transcript path/to/transcript.pdf
```

### Watch for New Files

```bash
# Continuously monitor configured directories
fireflies-to-bear run --watch
```

### List Processed Notes

```bash
# List all notes that have been processed
fireflies-to-bear list
```

### Other Commands

```bash
# Show help
fireflies-to-bear --help

# Run with specific config file
fireflies-to-bear --config /path/to/config.ini run

# Enable verbose logging
fireflies-to-bear --verbose run
```

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

### Project Structure

```
fireflies-to-bear/
├── .f2b/                    # Local configuration & state (not checked into git)
│   ├── config.ini           # Configuration file
│   ├── state.json           # State tracking file  
│   └── logs/                # Log files
├── src/
│   └── fireflies_to_bear/   # Main application code
├── tests/                   # Test suite
└── README.md
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
