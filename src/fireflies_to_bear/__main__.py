"""Main entry point for the fireflies-to-bear package."""

from fireflies_to_bear.app import Application
from fireflies_to_bear.main import load_config, validate_config


def main() -> None:
    """Run the application."""
    config_parser = load_config()
    config = validate_config(config_parser)
    app = Application(config)
    app.run()


if __name__ == "__main__":
    main()
