#!/bin/bash

# Exit on error
set -e

# Configuration
APP_NAME="fireflies-to-bear"
CONFIG_DIR="$HOME/.config/$APP_NAME"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
PLIST_FILE="com.$APP_NAME.plist"
LOGS_DIR="$HOME/Library/Logs/$APP_NAME"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Uninstalling $APP_NAME...${NC}"

# Function to safely remove a file or directory
safe_remove() {
    if [ -e "$1" ]; then
        echo -e "${YELLOW}Removing $1...${NC}"
        rm -rf "$1"
    fi
}

# Unload LaunchAgent if it exists
if [ -f "$LAUNCH_AGENTS_DIR/$PLIST_FILE" ]; then
    echo -e "${YELLOW}Unloading LaunchAgent...${NC}"
    launchctl unload "$LAUNCH_AGENTS_DIR/$PLIST_FILE" 2>/dev/null || true
    safe_remove "$LAUNCH_AGENTS_DIR/$PLIST_FILE"
fi

# Remove configuration directory
if [ -d "$CONFIG_DIR" ]; then
    echo -e "${YELLOW}Do you want to remove the configuration directory? This will delete all settings.${NC}"
    read -p "Remove configuration? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        safe_remove "$CONFIG_DIR"
    else
        echo -e "${GREEN}Keeping configuration directory at $CONFIG_DIR${NC}"
    fi
fi

# Remove log files
if [ -d "$LOGS_DIR" ]; then
    echo -e "${YELLOW}Do you want to remove the log files?${NC}"
    read -p "Remove logs? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        safe_remove "$LOGS_DIR"
    else
        echo -e "${GREEN}Keeping log files at $LOGS_DIR${NC}"
    fi
fi

# Deactivate and remove virtual environment if it exists
if [ -d ".venv" ]; then
    echo -e "${YELLOW}Removing virtual environment...${NC}"
    deactivate 2>/dev/null || true
    safe_remove ".venv"
fi

# Remove package from pip if installed
if pip show $APP_NAME &>/dev/null; then
    echo -e "${YELLOW}Removing package...${NC}"
    pip uninstall -y $APP_NAME
fi

echo -e "${GREEN}Uninstallation complete!${NC}"
