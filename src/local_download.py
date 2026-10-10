# Created: 2026-10-10 10:35 JST
"""One-shot local download command used by the existing BAT fallback."""
import argparse
from .local_monitor import poll_once


def download(settings):
    paths = poll_once(settings)
    if not paths:
        print("No new chart artifact; existing images retained")
        return None
    for path in paths:
        print(f"Downloaded chart images to {path}")
    return paths[-1]


def cli():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="setting.yaml")
    arguments = parser.parse_args()
    download(arguments.config)


if __name__ == "__main__":
    cli()

# Compatibility helper used by the original unit tests. The new monitor's
# _find_artifact_batch intentionally allows a partial set of configured pairs.
def find_batch_folder(directory, known_pairs):
    from pathlib import Path
    import re
    folders = [p for p in Path(directory).rglob('*') if p.is_dir() and re.fullmatch(r'\d{8}_\d{4}', p.name)]
    folders = [p for p in folders if all((p / f'{pair}.png').is_file() for pair in known_pairs)]
    if len(folders) != 1:
        raise ValueError(f'Expected one valid timestamp folder in artifact, got {len(folders)}')
    return folders[0]
