import os
import sys
from pathlib import Path

# When running from a PyInstaller-frozen portable build, point Playwright
# at the Chromium copy bundled alongside the executable instead of the
# per-user cache directory it would otherwise try to use.
if getattr(sys, "frozen", False):
    _bundle_dir = Path(sys.executable).resolve().parent
    _browsers_dir = _bundle_dir / "playwright-browsers"
    if _browsers_dir.exists():
        os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(_browsers_dir))

from agent.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
