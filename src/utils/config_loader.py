from dotenv import load_dotenv

from config.config import CONFIG, DATA_DIR, PROJECT_ROOT

load_dotenv()


def load_config() -> dict:
    """Return the application configuration defined in config.py."""
    return CONFIG