# Created: 2026-10-09 22:09 JST
"""Prune chart artifacts older than 8h using GitHub CLI API (repo Actions write)."""
from datetime import datetime, timedelta, timezone
import json
import os
import subprocess


def is_expired(created_at, now=None):
    now = now or datetime.now(timezone.utc)
    date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
    return now - date >= timedelta(hours=8)


def main():
    repo = os.environ['GH_REPO']
    api = f'repos/{repo}/actions/artifacts?per_page=100'
    # gh api --paginate outputs one JSON object per page, so parse independently.
    res = subprocess.run(['gh', 'api', '--paginate', api], capture_output=True, text=True, check=True)
    decoder = json.JSONDecoder(); raw = res.stdout; offset = 0
    while offset < len(raw):
        while offset < len(raw) and raw[offset].isspace():
            offset += 1
        if offset >= len(raw):
            break
        page, pos = decoder.raw_decode(raw, offset)
        offset = pos
        for artifact in page.get('artifacts', []):
            if artifact.get('name') == 'charts' and is_expired(artifact['created_at']):
                aid = artifact['id']
                subprocess.run(['gh', 'api', '-X', 'DELETE', f'repos/{repo}/actions/artifacts/{aid}'], check=True)
                print(f'Deleted expired chart artifact {aid}')

if __name__ == '__main__':
    main()
