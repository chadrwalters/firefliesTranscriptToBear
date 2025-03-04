#!/bin/bash

# Exit on error
set -e

# Configuration
APP_NAME="fireflies-to-bear"
CONFIG_DIR="$HOME/.config/$APP_NAME"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
PLIST_FILE="com.$APP_NAME.plist"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Installing $APP_NAME...${NC}"

# Check if running on macOS
if [[ "$(uname)" != "Darwin" ]]; then
    echo -e "${RED}Error: This application only runs on macOS${NC}"
    exit 1
fi

# Check if Python 3.8+ is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed${NC}"
    exit 1
fi

# Get Python version and compare
PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
MAJOR_VERSION=$(echo $PYTHON_VERSION | cut -d. -f1)
MINOR_VERSION=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$MAJOR_VERSION" -lt 3 ] || ([ "$MAJOR_VERSION" -eq 3 ] && [ "$MINOR_VERSION" -lt 8 ]); then
    echo -e "${RED}Error: Python 3.8 or higher is required (current version: $PYTHON_VERSION)${NC}"
    exit 1
fi

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo -e "${RED}Error: uv is not installed. Please install it first:${NC}"
    echo -e "${YELLOW}pip install uv${NC}"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    uv venv
fi

# Activate virtual environment
source .venv/bin/activate

# Install the package
echo -e "${YELLOW}Installing $APP_NAME...${NC}"
uv pip install -e .

# Create configuration directory
echo -e "${YELLOW}Creating configuration directory...${NC}"
mkdir -p "$CONFIG_DIR"

# Create default configuration if it doesn't exist
if [ ! -f "$CONFIG_DIR/config.ini" ]; then
    echo -e "${YELLOW}Creating default configuration...${NC}"
    # Run the application with --init flag to create default config
    fireflies-to-bear --init
fi

# Create LaunchAgent
echo -e "${YELLOW}Creating LaunchAgent...${NC}"
mkdir -p "$LAUNCH_AGENTS_DIR"

cat > "$LAUNCH_AGENTS_DIR/$PLIST_FILE" << EOL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.$APP_NAME</string>
    <key>ProgramArguments</key>
    <array>
        <string>$(which python3)</string>
        <string>-m</string>
        <string>fireflies_to_bear</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$HOME/Library/Logs/$APP_NAME/output.log</string>
    <key>StandardErrorPath</key>
    <string>$HOME/Library/Logs/$APP_NAME/error.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
        <key>PYTHONPATH</key>
        <string>$(pwd)</string>
    </dict>
</dict>
</plist>
EOL

# Create logs directory
mkdir -p "$HOME/Library/Logs/$APP_NAME"

# Set permissions
chmod 644 "$LAUNCH_AGENTS_DIR/$PLIST_FILE"

# Load the LaunchAgent
echo -e "${YELLOW}Loading LaunchAgent...${NC}"
launchctl unload "$LAUNCH_AGENTS_DIR/$PLIST_FILE" 2>/dev/null || true
launchctl load "$LAUNCH_AGENTS_DIR/$PLIST_FILE"

echo -e "${GREEN}Installation complete!${NC}"
echo -e "${YELLOW}Please edit $CONFIG_DIR/config.ini to configure your directories and preferences.${NC}"
