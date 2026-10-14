# Created: 2026-10-14 JST
# ChartRecorder Windows Desktop setup.exe

## Layout

Default `system.yaml` chooses the current Windows user's actual Desktop, including OneDrive redirected Desktop. The installer has a GUI location dropdown with **desktop**, **c_drive**, and **custom directory** choices.

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

## Selecting an installation directory

`setup.exe` (double-click, or launch without `--yes`) prompts you to select:

| GUI choice | `system.yaml install.location` | Output directory |
| --- | --- | --- |
| Desktop | `desktop` (default) | Windows Desktop/ChartRecorder |
| C drive root | `c_drive` | `C:/ChartRecorder` |
| Custom path / browse | Absolute parent path such as `D:/Applications` | `D:/Applications/ChartRecorder` |

The selected directory and the `chart_image` child are shown before installation. It never moves existing image folders. The installer records the selected choice in the **installed** `system.yaml`; `setup.exe` on its own next run still uses its bundled settings, or a user-provided `system.yaml` beside the installer.

You can bypass the GUI via the Windows shell (`--yes` is for non-interactive installation):

```bash
./dist/setup.exe --dry-run --yes --location desktop
./dist/setup.exe --dry-run --yes --location c_drive
./dist/setup.exe --location desktop --yes
./dist/setup.exe --location c_drive --yes
./dist/setup.exe --location "D:/Applications" --yes
```

`c_drive` is `C:/ChartRecorder`, not `C:/Users/<user>/ChartRecorder`. Windows may restrict creating directories directly under `C:/`: if access is denied, use Desktop or a writable custom directory. No implicit privilege elevation occurs.

## Building on Windows

From the repository root in Git Bash:

```bash
cmd.exe /c 'scripts\build_setup_windows.bat'
powershell.exe -NoProfile -Command 'Start-Process -FilePath ".\dist\setup.exe"'
```

`setup.exe` lets you choose Desktop, C drive or a custom location, then asks for confirmation and optionally launches the installed EXE. The installer **does not** force-terminate the older application. Exit any running ChartRecorder from the tray first, especially if upgrading the copy at the same destination; a locked destination EXE causes an understandable error and remains unchanged.

Do **not** run `dist/ChartRecorder.exe` after installation: launch the installed desktop `ChartRecorder/ChartRecorder.exe`. Both executables share the Windows single-instance mutex, so simultaneous Saxo OAuth refresh and downloads remain prevented.

A `system.yaml` placed **beside setup.exe** overrides the embedded `system.yaml`. `install.location: desktop` uses the user's Desktop, `c_drive` uses `C:/`; an absolute parent directory can also be configured. `folder_name` and `image_folder` must be plain folder names. Example:

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
