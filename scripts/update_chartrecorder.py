# Created: 2026-10-14 JST
"""One-command versioned build, cooperative ChartRecorder update and restart.

Build a separate version-stamped EXE *before* asking the previous app to stop.
Never overwrite the running dist/ChartRecorder.exe or force-kill a Saxo worker.
"""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
from uuid import uuid4

from scripts.cooperative_shutdown import CooperativeShutdown
from scripts.setup_chartrecorder import perform_install, read_system, resolve_install, atomic_copy
from scripts.versioning import build_id, is_dirty


def release_folder(root, release_id):
    return Path(root) / "dist" / "releases" / release_id


def build_staged_exe(root, stage):
    """Use a separate output directory, never legacy dist/ChartRecorder.exe."""
    stage = Path(stage).resolve()
    env = os.environ.copy()
    env["CHARTRECORDER_DIST_DIR"] = str(stage)
    subprocess.run(
        ["cmd.exe", "/c", r"scripts\build_windows.bat"],
        cwd=root, env=env, check=True,
    )
    if not (stage / "ChartRecorder.exe").is_file():
        raise RuntimeError("Windows build reported success but EXE is missing")


def start_installed(exe):
    subprocess.Popen([str(exe)], cwd=str(Path(exe).parent))


def update_install(root, location=None, force_build=False, dry_run=False,
                   guard=None, builder=None, launcher=None):
    """Safely stage, stop, copy and relaunch. Dependencies can be mocked in CI.

    If the new binary cannot be built, the running app is untouched.
    If cooperative shutdown fails or times out, the running app is untouched.
    If installation fails, restore previous EXE and version marker where possible.
    """
    root = Path(root).resolve()
    release_id = build_id(root)
    system_path = root / "system.yaml"
    config = read_system(system_path)
    if location is not None:
        config["location"] = location
    destination, _ = resolve_install(config)
    target = destination / "ChartRecorder.exe"
    installed_marker = destination / "installed-version.txt"
    already_current = target.is_file() and installed_marker.is_file() and (
        installed_marker.read_text(encoding="utf-8").strip() == release_id
    )
    installed_system = destination / "system.yaml"
    desired_config = config
    config_changed = not installed_system.is_file() or (
        read_system(installed_system) != desired_config
    )
    requires_install = not already_current or config_changed or not (destination / "setting.yaml").is_file()
    if dry_run:
        print(f"Version: {release_id}")
        print(f"Installed: {destination}")
        print(f"Deploy needed: {force_build or is_dirty(root) or requires_install}")
        print(f"Rebuild needed: {force_build or is_dirty(root) or not release_folder(root, release_id).joinpath('ChartRecorder.exe').is_file()}")
        return destination
    guard = guard or CooperativeShutdown()
    builder = builder or build_staged_exe
    launcher = launcher or start_installed

    dirty = is_dirty(root)
    if requires_install or force_build or dirty:
        # Dirty tracked source code must be rebuilt, not reused under a stable SHA.
        base = release_folder(root, release_id)
        stage = base if not (dirty or force_build) else release_folder(
            root, release_id + "-build-" + uuid4().hex[:8]
        )
        stage.mkdir(parents=True, exist_ok=True)
        if not (stage / "ChartRecorder.exe").is_file():
            print(f"Building {release_id} into {stage}", flush=True)
            builder(root, stage)
        # Templates and release marker must be shipped beside the staged EXE.
        shutil.copy2(root / "setting.yaml", stage / "setting.yaml")
        shutil.copy2(system_path, stage / "system.yaml")
        (stage / "release-version.txt").write_text(release_id + "\n", encoding="utf-8")
    else:
        stage = None
        print(f"Installed version {release_id} is current; skipping rebuild.", flush=True)

    # Only after a successful build is the existing app asked to stop.
    was_running = guard.stop(timeout_seconds=300)
    backup = None
    marker_before = installed_marker.read_bytes() if installed_marker.is_file() else None
    if stage is not None and target.is_file():
        backup = stage / "ChartRecorder.previous.exe"
        shutil.copy2(target, backup)

    try:
        if stage is not None:
            perform_install(stage, system_path, location_override=location)
        if not target.is_file():
            raise RuntimeError(f"Installed ChartRecorder.exe missing: {target}")
    except Exception:
        if backup is not None and backup.is_file():
            atomic_copy(backup, target)
        if marker_before is not None:
            installed_marker.write_bytes(marker_before)
        elif installed_marker.exists():
            installed_marker.unlink()
        if was_running and target.is_file():
            print("Update failed; restarting the previous installed EXE.", file=sys.stderr)
            launcher(target)
        raise

    print(f"Starting {target}", flush=True)
    launcher(target)
    return destination


def main(argv=None):
    parser = argparse.ArgumentParser(description="Safely rebuild and restart ChartRecorder")
    parser.add_argument("--location", metavar="desktop|c_drive|ABSOLUTE_PATH",
                        help="override system.yaml install.location")
    parser.add_argument("--rebuild", action="store_true",
                        help="force a new staged EXE even with unchanged version")
    parser.add_argument("--dry-run", action="store_true",
                        help="show destination and build need, without writing or stopping")
    args = parser.parse_args(argv)
    try:
        update_install(
            Path(__file__).resolve().parents[1],
            location=args.location,
            force_build=args.rebuild,
            dry_run=args.dry_run,
        )
        return 0
    except Exception as exc:
        print(f"Update failed safely: {exc}", file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
