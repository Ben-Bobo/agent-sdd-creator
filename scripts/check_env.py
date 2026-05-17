"""Quick sanity check that the environment is wired correctly."""

import os
import shutil
import sys
from pathlib import Path


def main():
    checks = []
    checks.append(("Python >= 3.11", sys.version_info >= (3, 11)))
    checks.append((".venv active", sys.prefix != sys.base_prefix))
    checks.append(("mmdc on PATH", shutil.which("mmdc") is not None))
    checks.append((".env file present", Path(".env").is_file()))
    env_key = os.environ.get("ANTHROPIC_API_KEY", "")
    checks.append(("ANTHROPIC_API_KEY set", env_key and env_key != "your-key-here"))
    all_pass = all(ok for _, ok in checks)
    for label, ok in checks:
        print(f"  {'✓' if ok else '✗'}  {label}")
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
