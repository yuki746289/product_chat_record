# Created: 2026-10-10 10:35 JST
"""GitHub artifact downloader and count-limited local retention for Windows.

Runs one polling pass; UI and Python CLI can call poll_once(). No background jobs
are created by this module. All times are timezone-aware.
"""
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from zoneinfo import ZoneInfo

from .config import load_settings

PNG_HEADER = b"\x89PNG\r\n\x1a\n"


def _gh(*args):
    result = subprocess.run(["gh", *args], capture_output=True, text=True,
                            encoding="utf-8", check=False, timeout=75)
    if result.returncode:
        raise RuntimeError("GitHub CLI failed: " + (result.stderr.strip() or result.stdout.strip()))
    return result.stdout.strip()


def get_monitor_options(cfg):
    opts = cfg.get("local_monitor", {})
    if not isinstance(opts, dict):
        raise ValueError("local_monitor must be a mapping")
    poll = opts.get("poll_seconds", 60)
    maximum = opts.get("max_folders", 10)
    if "retention_hours" in opts or "min_folders" in opts:
        raise ValueError("Deprecated local_monitor retention_hours/min_folders; use max_folders")
    for name, value, low, high in (("poll_seconds", poll, 30, 3600),
                                   ("max_folders", maximum, 1, 1000)):
        if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
            raise ValueError(f"local_monitor.{name} must be an integer from {low} to {high}")
    return poll, maximum


def parse_chart_stamp(name, time_zone, folder_format="%Y%m%d_%H%M"):
    try:
        local = datetime.strptime(name, folder_format).replace(tzinfo=ZoneInfo(time_zone))
        # Reject normalized/missing wall-clock values (including DST gaps).
        if local.astimezone(timezone.utc).astimezone(ZoneInfo(time_zone)).strftime(folder_format) != name:
            return None
        return local
    except ValueError:
        return None


def clean_local_images(local_dir, now, max_folders=10, time_zone="Asia/Tokyo", folder_format="%Y%m%d_%H%M"):
    """Retain at most the newest N timestamp folders containing PNGs.

    A snapshot folder has YYYYMMDD_HHmm and at least one direct/category PNG.
    Unknown names, empty folders, and symlinks are not deleted.
    """
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    directory = Path(local_dir)
    if not directory.is_dir():
        return []
    candidates = []
    for entry in directory.iterdir():
        if not entry.is_dir() or entry.is_symlink():
            continue
        local_dt = parse_chart_stamp(entry.name, time_zone, folder_format)
        # Both timestamp/*.png and timestamp/category/*.png count as snapshots.
        direct = any(entry.glob("*.png"))
        categorized = any(
            child.is_dir() and not child.is_symlink() and any(child.glob("*.png"))
            for child in entry.iterdir()
        )
        if local_dt is not None and (direct or categorized):
            candidates.append((local_dt.astimezone(timezone.utc), entry))
    candidates.sort(key=lambda item: (item[0], item[1].name), reverse=True)
    if isinstance(max_folders, bool) or not isinstance(max_folders, int) or max_folders < 1:
        raise ValueError("max_folders must be a positive integer")
    deleted = []
    for index, (stamp, directory_path) in enumerate(candidates):
        if index >= max_folders:
            shutil.rmtree(directory_path)
            deleted.append(directory_path)
    return deleted


def get_recent_artifacts(repo, name):
    """Collect available matching artifact metadata, paginating recent first."""
    found = []
    for page in range(1, 11):
        payload = json.loads(_gh("api", f"repos/{repo}/actions/artifacts?per_page=100&page={page}"))
        batch = payload.get("artifacts", [])
        if not isinstance(batch, list):
            raise ValueError("Unexpected GitHub API artifact response")
        for entry in batch:
            if entry.get("name") == name and not entry.get("expired", False):
                run = entry.get("workflow_run") or {}
                if run.get("id") is not None and entry.get("id") is not None:
                    found.append(entry)
        if len(batch) < 100:
            break
    return sorted(found, key=lambda a: (a.get("created_at", ""), int(a["id"])))


def _state_file(root):
    return Path(root) / ".downloaded_artifacts.json"


def _read_state(root):
    file = _state_file(root)
    if not file.exists():
        return set()
    value = json.loads(file.read_text(encoding="utf-8"))
    if not isinstance(value, list) or any(not isinstance(v, int) for v in value):
        raise ValueError("Local artifact state is malformed")
    return set(value)


def _save_state(root, ids):
    path = _state_file(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(sorted(ids), indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def _find_artifact_batch(temp_dir, configured_pairs, time_zone="Asia/Tokyo", folder_format="%Y%m%d_%H%M"):
    choices = []
    base = Path(temp_dir)
    for candidate in [base, *base.rglob("*")]:
        if not candidate.is_dir() or candidate.is_symlink():
            continue
        if parse_chart_stamp(candidate.name, time_zone, folder_format) is None:
            continue
        # Accept both the historical flat artifact and nested category output.
        roots = [candidate, *(child for child in candidate.iterdir()
                              if child.is_dir() and not child.is_symlink())]
        files = []
        for pair in configured_pairs:
            matching = [folder / f"{pair}.png" for folder in roots
                        if (folder / f"{pair}.png").is_file()]
            if len(matching) > 1:
                raise ValueError(f"Ambiguous artifact images for {pair}")
            files.extend(matching)
        if files:
            choices.append((candidate, files))
    if len(choices) != 1:
        raise ValueError(f"Expected one timestamp image folder, found {len(choices)}")
    directory, images = choices[0]
    for png in images:
        if png.stat().st_size < 8 or png.open("rb").read(8) != PNG_HEADER:
            raise ValueError(f"Invalid PNG in downloaded artifact: {png.name}")
    return directory, images


def poll_once(config_path, now=None):
    """Get all unprocessed artifacts, then prune local snapshots; returns paths.

    New artifacts are downloaded oldest-first. An error leaves the ID unrecorded
    so the next poll retries it. No duplicate folder is made for the same ID.
    """
    cfg = load_settings(config_path)
    _, maximum = get_monitor_options(cfg)
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    root = Path(cfg["output"]["local_dir"])
    root.mkdir(parents=True, exist_ok=True)
    processed = _read_state(root)
    repo = cfg["repository"]
    artifact_name = cfg["output"]["artifact_name"]
    pairs = [item["pair"] for item in cfg["symbols"]]
    downloaded = []
    try:
        available = get_recent_artifacts(repo, artifact_name)
        # Backfill only the latest N artifacts, matching local folder cap.
        selected = available[-maximum:]
        processed.intersection_update({int(a["id"]) for a in available})
        for artifact in selected:
            artifact_id = int(artifact["id"])
            if artifact_id in processed:
                continue
            run_id = str(artifact["workflow_run"]["id"])
            with tempfile.TemporaryDirectory() as temp:
                _gh("run", "download", run_id, "-R", repo, "-n", artifact_name,
                    "-D", temp)
                batch, files = _find_artifact_batch(temp, pairs, cfg["output"]["timezone"], cfg["output"]["folder_format"])
                if parse_chart_stamp(batch.name, cfg["output"]["timezone"], cfg["output"]["folder_format"]) is None:
                    raise ValueError(f"Invalid timestamp folder: {batch.name}")
                target = root / batch.name
                target.mkdir(parents=True, exist_ok=True)
                for file in files:
                    destination = target / file.relative_to(batch)
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    intermediate = destination.with_name(destination.name + ".part")
                    shutil.copyfile(file, intermediate)
                    intermediate.replace(destination)
                downloaded.append(target)
                processed.add(artifact_id)
                _save_state(root, processed)
    finally:
        # Cleanup runs even with no new images or if GitHub is temporarily down.
        clean_local_images(root, now, maximum, cfg["output"]["timezone"], cfg["output"]["folder_format"])
    return downloaded
