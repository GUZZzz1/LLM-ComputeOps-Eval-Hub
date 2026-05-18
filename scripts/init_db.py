import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.db import get_db_path, init_db


def main() -> None:
    init_db()
    print(f"Database initialized at {get_db_path()}")


if __name__ == "__main__":
    main()
