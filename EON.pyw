"""EON v0.8.0 — Direct GUI launcher (no console window)."""
import sys
from eon import __version__  # noqa: F401
import eon as _eon_main

if __name__ == "__main__":
    if len(sys.argv) == 1:
        sys.argv.append("--tray")
    raise SystemExit(_eon_main.main())
