# PyInstaller spec for the portable Windows (and Linux/macOS) build.
#
# Build with:  pyinstaller packaging/agent.spec
# Output:      dist/local-agent/  (folder you zip up) and
#              dist/local-agent/local-agent.exe (the file the user double-clicks)
#
# We build a one-folder ("--onedir") bundle rather than one-file: startup
# is much faster and Playwright's bundled Chromium binaries are large, so
# unpacking them into a temp dir on every launch (as --onefile would do)
# is wasteful. The whole dist/local-agent folder is what gets zipped.
import sys
from pathlib import Path

block_cipher = None
ROOT = Path(__file__).resolve().parent.parent

a = Analysis(
    [str(ROOT / "agent" / "__main__.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        (str(ROOT / "config" / "config.example.yaml"), "config"),
        (str(ROOT / ".env.example"), "."),
    ],
    hiddenimports=[
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="local-agent",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="local-agent",
)
