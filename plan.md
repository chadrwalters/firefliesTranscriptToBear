# Implementation Plan: Convert to CLI-driven Application

## Overview
Convert Fireflies to Bear from a TSR (Terminate and Stay Resident) application to a pure command-line tool that stores configuration and state locally.

## Changes Required

### 1. Configuration Structure
- Create a `.f2b` subdirectory in the current working directory for configuration and state
- Move configuration from `~/.config/fireflies-to-bear/config.ini` to `.f2b/config.ini`
- Move state file from `~/.fireflies_processor/state.json` to `.f2b/state.json`
- Update `.gitignore` to ignore the `.f2b` directory

### 2. Command-line Interface
- Implement argument parsing with argparse in `main.py`
- Create subcommands: `init`, `run`, `list`
- Support options for specific file processing, watch mode, verbose output

### 3. Application Logic
- Modify `Application` class to remove continuous monitoring by default
- Add support for processing specific files
- Make the watch functionality optional with `--watch` flag

### 4. File Modifications

#### `src/fireflies_to_bear/config.py`
- Add `get_config_directory()` and `ensure_config_directory()` methods
- Modify config validation to handle relative paths

#### `src/fireflies_to_bear/state_manager.py`
- Update to use local `.f2b/state.json` by default
- Support relative paths in state tracking

#### `src/fireflies_to_bear/main.py`
- Implement argument parsing
- Create `initialize_config()` function to create default config
- Modify `main()` to handle different commands

#### `src/fireflies_to_bear/app.py`
- Add `process_specific_files()` method
- Update `run()` to be used only with explicit watch flag

#### `.gitignore`
- Add `.f2b/` entry

#### `README.md`
- Update to reflect CLI usage
- Document new command structure and configuration
- Remove TSR/background service documentation

## Implementation Steps

1. Add `.f2b` to `.gitignore`
2. Update the configuration management code
3. Modify state management to use local paths
4. Implement command-line argument parsing
5. Update application logic to support commands
6. Rewrite README.md with new documentation
7. Test all functionality to ensure it works

## Commands Structure

```
fireflies-to-bear init                              # Initialize configuration
fireflies-to-bear run                               # Process files once
fireflies-to-bear run --watch                       # Monitor for changes
fireflies-to-bear run --summary FILE --transcript FILE  # Process specific files
fireflies-to-bear list                              # List processed notes
```