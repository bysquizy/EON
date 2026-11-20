"""Flag obvious personal identifiers in tracked repository content.

This is a preventive lint, not a guarantee that all personal information is absent.
"""
from pathlib import Path
import re
import subprocess
import sys

CHECK_EXTENSIONS = {".md", ".py", ".yml", ".yaml", ".json", ".toml", ".bat", ".txt"}
CHECK_NAMES = {"VERSION", ".gitignore"}

PATTERNS = {
    "email address": re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I),
    "Windows user profile path": re.compile(r"[A-Z]:[\\/]+Users[\\/]+(?!Public\b|Default\b)[^\\/\s`\"']+", re.I),
    "Unix home directory": re.compile(r"/(?:home|Users)/(?!shared(?:/|$))[^/\s`\"']+", re.I),
    "possible secret token": re.compile(r"(?:ghp_|gho_|github_pat_|sk-)[A-Za-z0-9_\-]{12,}"),
    "private key block": re.compile(r"-{5}BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-{5}"),
}

def main() -> int:
    tracked = subprocess.check_output(["git", "ls-files", "-z"]).split(b"\0")
    findings = []
    for raw in tracked:
        if not raw:
            continue
        path = Path(raw.decode("utf-8"))
        if path.suffix.lower() not in CHECK_EXTENSIONS and path.name not in CHECK_NAMES:
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (UnicodeDecodeError, OSError):
            continue
        for line_number, line in enumerate(lines, 1):
            for label, pattern in PATTERNS.items():
                if pattern.search(line):
                    findings.append(f"{path}:{line_number}: possible {label}")
    if findings:
        print("Potential privacy issues detected. Review before publishing:")
        print("\n".join(findings))
        return 1
    print("No obvious personal identifiers detected in tracked text files.")
    print("Manual review is still required for context-specific personal details.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
