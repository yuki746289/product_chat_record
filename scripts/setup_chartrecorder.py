# Created: 2026-10-14 JST
# Updated: 2026-10-14 JST (selectable desktop/c_drive/custom destination)
"""Desktop installer bundled as setup.exe; no Saxo credentials are packaged.

The compiled setup.exe contains ChartRecorder.exe and public YAML templates.
An optional system.yaml NEXT TO setup.exe overrides bundled install settings.
Existing image history is intentionally never deleted or implicitly migrated.
"""
import argparse
import json
from datetime import datetime
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

import yaml


def bundled_payload():
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "payload"
    return Path(__file__).resolve().parents[1]


def installer_directory():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def read_system(path):
    cfg = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(cfg, dict) or not isinstance(cfg.get("install"), dict):
        raise ValueError("system.yaml must contain an install mapping")
    return cfg["install"]


def desktop_directory():
    """Use Windows Explorer's configured desktop, not a guessed Desktop path.

    The registry reflects OneDrive known-folder redirection for this user.
    """
    if os.name == "nt":
        import winreg
        try:
            key = r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key) as handle:
                configured, _ = winreg.QueryValueEx(handle, "Desktop")
            expanded = Path(os.path.expandvars(str(configured))).expanduser()
            if expanded.is_absolute():
                return expanded
        except (OSError, ValueError):
            pass
    return Path.home() / "Desktop"


def _folder_name(value, field):
    if not isinstance(value, str) or not value or value in (".", ".."):
        raise ValueError(f"install.{field} must be a single folder name")
    if any(c in value for c in ("/", "\\", ":", "\0")) or value.endswith((" ", ".")):
        raise ValueError(f"install.{field} must not be a path")
    return value


def resolve_install(config, desktop=None, c_drive=None):
    location = config.get("location", "desktop")
    folder = _folder_name(config.get("folder_name", "ChartRecorder"), "folder_name")
    images = _folder_name(config.get("image_folder", "chart_image"), "image_folder")
    if location == "desktop":
        parent = Path(desktop) if desktop is not None else desktop_directory()
    elif location == "c_drive":
        # Windows may require elevated permissions to create C:\\ChartRecorder.
        parent = Path(c_drive) if c_drive is not None else Path("C:/")
    elif isinstance(location, str) and location.strip():
        parent = Path(os.path.expandvars(location)).expanduser()
        if not parent.is_absolute():
            raise ValueError("install.location must be desktop, c_drive, or an absolute parent path")
    else:
        raise ValueError("install.location must be desktop, c_drive, or an absolute parent path")
    destination = (parent / folder).resolve()
    if destination == parent.resolve() or destination.parent != parent.resolve():
        raise ValueError("Unsafe install location")
    return destination, images


def with_install_location(system_text, location):
    """Persist a GUI/CLI installation choice while preserving the YAML fields."""
    rx = re.compile(r"^([ \\t]*location[ \\t]*:[ \\t]*)[^\\r\\n#]*(?:[ \\t]*#.*)?$", re.MULTILINE)
    if len(rx.findall(system_text)) != 1:
        raise ValueError("Expected exactly one install.location in system.yaml")
    updated = rx.sub(
        lambda m: m.group(1) + json.dumps(location, ensure_ascii=False) +
        "  # desktop, c_drive, or absolute parent path",
        system_text,
    )
    cfg = yaml.safe_load(updated)
    if not isinstance(cfg, dict) or cfg.get("install", {}).get("location") != location:
        raise ValueError("Could not save the selected installation location")
    return updated


def choose_install_location(initial, config, parent_window):
    """Ask for Desktop, C drive, or a custom absolute directory."""
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox

    popup = tk.Toplevel(parent_window)
    popup.title("ChartRecorder - インストール先の選択")
    popup.resizable(False, False)
    popup.geometry("570x245")
    popup.grab_set()
    selection = {"value": None}
    options = {
        "デスクトップ (desktop)": "desktop",
        "Cドライブ直下 (c_drive)": "c_drive",
        "その他の場所を指定": "custom",
    }
    labels = {v: k for k, v in options.items()}
    mode = initial if initial in ("desktop", "c_drive") else "custom"
    folder = tk.StringVar(value=initial if mode == "custom" else "")
    current = tk.StringVar(value=labels[mode])
    preview = tk.StringVar()

    ttk.Label(popup, text="インストール先を選択してください。").pack(anchor="w", padx=18, pady=(14, 6))
    combo = ttk.Combobox(popup, textvariable=current, state="readonly", values=list(options), width=38)
    combo.pack(anchor="w", padx=18)
    line = ttk.Frame(popup)
    line.pack(fill="x", padx=18, pady=(10, 4))
    entry = ttk.Entry(line, textvariable=folder, width=51)
    entry.pack(side="left", fill="x", expand=True)

    def browse():
        value = filedialog.askdirectory(parent=popup, initialdir=folder.get() or str(Path.home()))
        if value:
            folder.set(value)
            current.set(labels["custom"])
            refresh()

    ttk.Button(line, text="参照...", command=browse).pack(side="left", padx=(8, 0))

    def selection_value():
        return folder.get().strip() if options[current.get()] == "custom" else options[current.get()]

    def refresh(event=None):
        entry.configure(state="normal" if options[current.get()] == "custom" else "disabled")
        try:
            destination, images = resolve_install({**config, "location": selection_value()})
            preview.set(f"配置先: {destination}   /   画像: {images}")
        except (ValueError, OSError) as exc:
            preview.set("配置先: " + str(exc))

    combo.bind("<<ComboboxSelected>>", refresh)
    folder.trace_add("write", lambda *_: refresh())
    ttk.Label(popup, textvariable=preview, wraplength=535).pack(
        fill="x", anchor="w", padx=18, pady=(6, 8)
    )
    ttk.Label(popup, text="Cドライブ直下ではWindowsの書き込み権限が必要な場合があります。", wraplength=535).pack(
        fill="x", anchor="w", padx=18
    )
    buttons = ttk.Frame(popup)
    buttons.pack(side="bottom", anchor="e", padx=18, pady=15)

    def accept():
        value = selection_value()
        try:
            resolve_install({**config, "location": value})
        except (ValueError, OSError) as exc:
            messagebox.showerror("配置先エラー", str(exc), parent=popup)
            return
        selection["value"] = value
        popup.destroy()

    ttk.Button(buttons, text="キャンセル", command=popup.destroy).pack(side="left", padx=(0, 8))
    ttk.Button(buttons, text="インストール", command=accept).pack(side="left")
    popup.protocol("WM_DELETE_WINDOW", popup.destroy)
    refresh()
    popup.wait_window()
    return selection["value"]


def with_local_images(settings_text, image_folder):
    """Change only the output.local_dir scalar; keep all other user settings.

    Do not re-serialize the whole YAML: comments, symbols, and formatting matter.
    """
    rx = re.compile(r"^(\s*local_dir\s*:\s*)[^\r\n#]*(?:\s*#.*)?$", re.MULTILINE)
    if len(rx.findall(settings_text)) != 1:
        raise ValueError("Expected one output.local_dir in setting.yaml")
    updated = rx.sub(lambda m: m.group(1) + repr(image_folder) +
                     "  # relative to this setting.yaml; images and logs", settings_text)
    # Parse the result before touching any target file.
    cfg = yaml.safe_load(updated)
    if not isinstance(cfg, dict) or cfg.get("output", {}).get("local_dir") != image_folder:
        raise ValueError("Could not configure chart_image output directory")
    return updated


def atomic_copy(src, dst):
    temp = dst.with_name(dst.name + ".install-tmp")
    try:
        shutil.copy2(src, temp)
        os.replace(temp, dst)
    finally:
        if temp.exists():
            temp.unlink()


def atomic_write(dst, content):
    temp = dst.with_name(dst.name + ".install-tmp")
    try:
        temp.write_text(content, encoding="utf-8", newline="\n")
        os.replace(temp, dst)
    finally:
        if temp.exists():
            temp.unlink()


def update_existing_autostart(destination):
    """Preserve user's existing startup choice; never enable it automatically."""
    if os.name != "nt":
        return
    import winreg
    key = r"Software\Microsoft\Windows\CurrentVersion\Run"
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key, 0, winreg.KEY_QUERY_VALUE | winreg.KEY_SET_VALUE) as handle:
            winreg.QueryValueEx(handle, "ChartRecorder")
            command = f'"{destination / "ChartRecorder.exe"}" --config "{destination / "setting.yaml"}"'
            winreg.SetValueEx(handle, "ChartRecorder", 0, winreg.REG_SZ, command)
    except FileNotFoundError:
        return


def perform_install(payload, system_path, desktop=None, location_override=None, c_drive=None):
    payload = Path(payload)
    exe = payload / "ChartRecorder.exe"
    template = payload / "setting.yaml"
    if not exe.is_file():
        raise FileNotFoundError(f"Missing ChartRecorder executable: {exe}")
    if not template.is_file():
        raise FileNotFoundError(f"Missing setting.yaml template: {template}")
    config = read_system(system_path)
    if location_override is not None:
        config["location"] = location_override
    dest, image_folder = resolve_install(config, desktop, c_drive)
    target_exe = dest / "ChartRecorder.exe"
    previous = dest / "setting.yaml"
    base_settings = previous.read_text(encoding="utf-8") if previous.is_file() else template.read_text(encoding="utf-8")
    updated_settings = with_local_images(base_settings, image_folder)

    try:
        dest.mkdir(parents=True, exist_ok=True)
        (dest / image_folder).mkdir(exist_ok=True)
    except PermissionError as exc:
        raise RuntimeError(
            f"Cannot write to {dest}. Choose Desktop or check C-drive permissions."
        ) from exc
    try:
        # Do not terminate or overwrite a running EXE. Windows returns WinError 5
        # and the prior binary is preserved if a copy is in use.
        atomic_copy(exe, target_exe)
    except PermissionError as exc:
        raise RuntimeError(
            "ChartRecorder is running at the installation destination. "
            "Exit it from the tray, then run setup.exe again."
        ) from exc

    if previous.is_file() and previous.read_text(encoding="utf-8") != updated_settings:
        suffix = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = dest / ("setting.yaml.before-setup-" + suffix + ".bak")
        shutil.copy2(previous, backup)
    atomic_write(previous, updated_settings)
    system_text = Path(system_path).read_text(encoding="utf-8")
    if location_override is not None:
        system_text = with_install_location(system_text, location_override)
    atomic_write(dest / "system.yaml", system_text)
    update_existing_autostart(dest)
    return dest


def main(argv=None):
    parser = argparse.ArgumentParser(description="Install ChartRecorder on the Desktop")
    parser.add_argument("--yes", action="store_true", help="do not ask for confirmation")
    parser.add_argument("--dry-run", action="store_true", help="validate payload and show destination, without writing")
    parser.add_argument("--location", default=None, metavar="desktop|c_drive|ABSOLUTE_PATH",
                        help="override system.yaml and skip GUI location selection")
    args = parser.parse_args(argv)
    payload = bundled_payload()
    external = installer_directory() / "system.yaml"
    system_path = external if external.is_file() else payload / "system.yaml"

    gui = not args.yes and not args.dry_run and os.name == "nt"
    if gui:
        import tkinter
        from tkinter import messagebox
        window = tkinter.Tk()
        window.withdraw()
    else:
        window = None

    try:
        config = read_system(system_path)
        location = args.location
        if gui and location is None:
            location = choose_install_location(config.get("location", "desktop"), config, window)
            if location is None:
                return 0
        effective = {**config, **({"location": location} if location is not None else {})}
        destination, image_folder = resolve_install(effective)
        if not (payload / "ChartRecorder.exe").is_file():
            raise FileNotFoundError("Bundled ChartRecorder.exe is missing")
        if not (payload / "setting.yaml").is_file():
            raise FileNotFoundError("Bundled setting.yaml is missing")
        if args.dry_run:
            print(f"Dry-run PASS: {destination} / {image_folder}")
            return 0
        if gui and not messagebox.askyesno(
            "ChartRecorder Setup",
            f"ChartRecorder を次の場所にインストールしますか？\n\n{destination}\n\n"
            "既存の画像フォルダは移動・削除しません。"
        ):
            return 0
        installed = perform_install(payload, system_path, location_override=location)
        print(f"Installed: {installed}")
        if gui:
            if messagebox.askyesno(
                "ChartRecorder Setup",
                f"インストールが完了しました。\n{installed}\n\nChartRecorder を起動しますか？"
            ):
                subprocess.Popen([str(installed / "ChartRecorder.exe")], cwd=str(installed))
        return 0
    except Exception as exc:
        if gui:
            messagebox.showerror("ChartRecorder Setup", str(exc))
        else:
            print(f"Setup ERROR: {exc}", file=sys.stderr)
        return 1
    finally:
        if window is not None:
            window.destroy()


if __name__ == "__main__":
    raise SystemExit(main())
