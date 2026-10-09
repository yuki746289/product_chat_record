# Created: 2026-10-09 22:09 JST
"""Windows batch companion: download latest successful GitHub Actions artifact."""
import argparse
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from .config import load_settings


def _gh(*args):
    proc = subprocess.run(['gh', *args], capture_output=True, text=True, encoding='utf-8', check=False)
    if proc.returncode:
        raise RuntimeError('gh command failed: ' + proc.stderr.strip())
    return proc.stdout.strip()


def find_batch_folder(directory, known_pairs):
    folders = [p for p in Path(directory).rglob('*') if p.is_dir() and re.fullmatch(r'\d{8}_\d{4}', p.name)]
    folders = [p for p in folders if all((p / f'{pair}.png').is_file() for pair in known_pairs)]
    if len(folders) != 1:
        raise ValueError(f'Expected one valid timestamp folder in artifact, got {len(folders)}')
    return folders[0]


def download(settings):
    cfg = load_settings(settings)
    repo = cfg['repository']
    local_root = Path(cfg['output']['local_dir'])
    last_file = local_root / '.last_successful_run'
    run_id = _gh('run', 'list', '-R', repo, '--workflow', 'generate_charts.yml',
                 '--status', 'success', '--limit', '1', '--json', 'databaseId', '--jq', '.[0].databaseId')
    if not run_id or not run_id.isdigit():
        print('No successful workflow run found')
        return None
    if last_file.is_file() and last_file.read_text(encoding='utf-8').strip() == run_id:
        print('No new images')
        return None
    with tempfile.TemporaryDirectory() as tmp:
        _gh('run', 'download', run_id, '-R', repo, '-n', cfg['output']['artifact_name'], '-D', tmp)
        pair_names = [x['pair'] for x in cfg['symbols']]
        batch = find_batch_folder(tmp, pair_names)
        dest = local_root / batch.name
        dest.mkdir(parents=True, exist_ok=True)
        for pair in pair_names:
            shutil.copy2(batch / f'{pair}.png', dest / f'{pair}.png')
        # Persist successful run only after every PNG has been copied.
        last_file.write_text(run_id + '\n', encoding='utf-8')
    print(f'Downloaded {len(pair_names)} PNGs to {dest}')
    return dest


def cli():
    p = argparse.ArgumentParser()
    p.add_argument('--config', default='setting.yaml')
    args = p.parse_args()
    download(args.config)

if __name__ == '__main__':
    cli()
