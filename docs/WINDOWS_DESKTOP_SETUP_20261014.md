# Created: 2026-10-14 JST
# ChartRecorder Windows Desktop setup.exe

## Layout

Default `system.yaml` chooses the current Windows user's actual Desktop, including OneDrive redirected Desktop.

```text
Desktop/
  ChartRecorder/
    ChartRecorder.exe
    setting.yaml
    system.yaml
    chart_image/
      20261014_1600/
        cross_non_jpy/*.png
        cross_jpy/*.png
```

The installer EXE is `dist/setup.exe`. It embeds the latest `dist/ChartRecorder.exe`, public `setting.yaml` template and `system.yaml`; Saxo secrets and tokens are **never** bundled. Existing Saxo keyring credentials stay available to the same Windows user.

## Building on Windows

From the repository root in Git Bash:

```bash
cmd.exe /c 'scripts\build_setup_windows.bat'
powershell.exe -NoProfile -Command 'Start-Process -FilePath ".\dist\setup.exe"'
```

`setup.exe` asks for confirmation, installs to Desktop/ChartRecorder and optionally launches the installed EXE. The installer **does not** force-terminate the older application. Exit any running ChartRecorder from the tray first, especially if upgrading the copy at the same destination; a locked destination EXE causes an understandable error and remains unchanged.

Do **not** run `dist/ChartRecorder.exe` after installation: launch the installed desktop `ChartRecorder/ChartRecorder.exe`. Both executables share the Windows single-instance mutex, so simultaneous Saxo OAuth refresh and downloads remain prevented.

A `system.yaml` placed **beside setup.exe** overrides the embedded `system.yaml`. `install.location: desktop` uses the user's Desktop; an absolute parent directory can be configured instead. `folder_name` and `image_folder` must be plain folder names. Example:

```yaml
install:
  location: desktop
  folder_name: ChartRecorder
  image_folder: chart_image
```

Installation options are recorded in `ChartRecorder/system.yaml`. Editing that file alone does not move an installed app; adjust the file beside setup.exe and rerun it to install into a different location.

`ChartRecorder/setting.yaml` is generated from the template on the first install. On subsequent installs, existing settings (including pair selections and polling settings) are preserved, but `output.local_dir` is normalized to the selected child image folder. Any modified settings file is backed up before this change. In the installed file the image directory is relative to the installed `setting.yaml`, **not the working directory**. Therefore double-clicking the EXE works from anywhere.

The legacy `C:/TradingViewCharts` directory is **not** moved or deleted; old snapshot history is left intact. New images and `.chart_recorder.log` are written beneath the installed `chart_image`. The unchanged 10-folder retention applies only to the installed new output directory.

An existing enabled Windows logon startup registry entry is redirected to the installed EXE. If no auto-start entry exists, the installer does not create one.

## Automated validation

The optional manual-only `Setup ChartRecorder Windows` GitHub Actions workflow builds the EXE and nested setup.exe, then runs `setup.exe --dry-run --yes`. It uploads only setup.exe as a temporary build artifact. Test and build jobs use mock data and no Saxo tokens.

Headless dry-run on a local Windows shell:

```bat
dist\setup.exe --dry-run --yes
```

## Limitations

- Windows GUI installation / same-user Saxo vault reuse needs Windows **real-PC** verification; a headless runner cannot confirm task-tray behavior.
- Binary installers are not code-signed. Windows SmartScreen or antivirus may warn. Do not bypass corporate security policies.
- The install is a copy-based per-user setup, not a Windows uninstaller. To remove it, disable `Windowsログオン時に起動` from the tray, exit ChartRecorder, then remove the Desktop/ChartRecorder folder once any important images are backed up.
- Changes to `system.yaml` are applied by rerunning setup.exe; they are not a live move operation.
