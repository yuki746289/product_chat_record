# Created: 2026-10-14 JST
"""Local ChartRecorder release ID: semantic version plus Git commit SHA."""
import argparse
from pathlib import Path
import re
import subprocess


def read_version(root):
    value = (Path(root) / "VERSION").read_text(encoding="utf-8").splitlines()
    lines = [line.strip() for line in value if line.strip() and not line.lstrip().startswith("#")]
    if len(lines) != 1 or not re.fullmatch(r"\d+\.\d+\.\d+", lines[0]):
        raise ValueError("VERSION must contain one semantic version, e.g. 0.1.0")
    return lines[0]


def build_id(root):
    root = Path(root).resolve()
    version = read_version(root)
    commit = subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "--short=8", "HEAD"],
        text=True, encoding="utf-8",
    ).strip()
    if not re.fullmatch(r"[0-9a-f]{7,8}", commit):
        raise ValueError("Git HEAD is not a valid SHA")
    return f"v{version}-{commit}"


def is_dirty(root):
    result = subprocess.run(
        ["git", "-C", str(root), "diff", "--quiet", "HEAD", "--", "src", "scripts", "requirements-windows.txt", "VERSION"],
        check=False,
    )
    return result.returncode != 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args()
    print(build_id(args.root))


if __name__ == "__main__":
    main()
