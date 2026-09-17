import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def run_bot() -> None:
    dry_run = os.getenv("DRY_RUN", "true").lower() == "true"
    api_url = os.getenv("POLYMARKET_API_URL", "https://example.com")
    log_level = os.getenv("LOG_LEVEL", "INFO")

    print("Polymarket bot scaffold started")
    print(f"dry_run={dry_run}")
    print(f"api_url={api_url}")
    print(f"log_level={log_level}")
    print("This is a placeholder bot loop. Replace the logic with your own strategy.")
