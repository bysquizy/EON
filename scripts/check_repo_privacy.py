"""Find obvious secrets and personal paths; manual review remains essential."""
from pathlib import Path
import re
import subprocess
import sys

PATTERNS = {
    "email address": re.compile(r"\b[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}\b", re.I),
    "user profile path": re.compile(r"[A-Z]:[\\/]+Users[\\/]+(?!Public\b|Default\b)[^\\/\s`\"']+", re.I),
    "Unix home path": re.compile(r"/(?:home|Users)/(?!shared(?:/|$))[^/\s`\"']+", re.I),
    "secret": re.compile(r"(?:ghp_|gho_|github_pat_|sk-)[A-Za-z0-9_\-]{12,}"),
    "private key": re.compile(r"-+BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-+"),
}
CHECK_EXT = {'.py', '.md', '.html', '.css', '.js', '.cjs', '.yml', '.yaml', '.json', '.txt', '.bat'}

def main() -> int:
    try:
        names = [Path(p.decode('utf-8')) for p in subprocess.check_output(['git', 'ls-files', '-z']).split(b'\0') if p]
    except (OSError, subprocess.CalledProcessError):
        print('Run inside a Git repository.')
        return 2
    findings = []
    for file in names:
        if file.suffix.lower() not in CHECK_EXT and file.name not in ('VERSION', '.gitignore'):
            continue
        try:
            lines = file.read_text(encoding='utf-8').splitlines()
        except (OSError, UnicodeError):
            continue
        for index, line in enumerate(lines, 1):
            for title, pattern in PATTERNS.items():
                if pattern.search(line):
                    findings.append(f'{file}:{index}: possible {title}')
    if findings:
        print('\n'.join(findings))
        return 1
    print('No obvious personal identifiers found. Manual review still required.')
    return 0

if __name__ == '__main__':
    sys.exit(main())
