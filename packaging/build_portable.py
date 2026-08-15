"""Build a portable, single-folder distribution of the agent.

Usage:
    python packaging/build_portable.py

This runs PyInstaller against ``packaging/agent.spec`` and then copies the
double-click launcher + example config into ``dist/local-agent``, and
finally zips the whole folder up as ``dist/local-agent-portable-<os>.zip``.

Notes:
- PyInstaller builds an executable for the OS/architecture it is *run on*
  -- it cannot cross-compile a Windows .exe from Linux/macOS. To produce
  the Windows portable zip, run this script on Windows (or let the
  ``build-portable.yml`` GitHub Actions workflow do it on a
  ``windows-latest`` runner and download the resulting artifact/release).
- Playwright's Chromium browser is downloaded separately (not bundled by
  PyInstaller) because it's a large, platform-specific binary blob. The
  build step below runs ``playwright install chromium`` into the dist
  folder so the portable package is fully self-contained.
"""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = ROOT / "dist" / "local-agent"


def run(cmd: list[str], **kwargs) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, check=True, **kwargs)


def main() -> int:
    run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", str(ROOT / "packaging" / "agent.spec")])

    shutil.copy2(ROOT / "packaging" / "Start-Agent.bat", DIST_DIR / "Start-Agent.bat")
    shutil.copy2(ROOT / "README.md", DIST_DIR / "README.md")

    # Bundle a real Chromium next to the executable so the browser skill
    # works out of the box without a separate `playwright install` step.
    browsers_dir = DIST_DIR / "playwright-browsers"
    browsers_dir.mkdir(exist_ok=True)
    env = {"PLAYWRIGHT_BROWSERS_PATH": str(browsers_dir)}

    run([sys.executable, "-m", "playwright", "install", "chromium"], env={**os.environ, **env})

    system = platform.system().lower()
    zip_path = ROOT / "dist" / f"local-agent-portable-{system}.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in DIST_DIR.rglob("*"):
            zf.write(file, file.relative_to(DIST_DIR.parent))

    print(f"\nPortable build ready: {zip_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
