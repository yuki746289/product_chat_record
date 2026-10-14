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

The installer EXE is `dist/setup.exe`. It embeds the latest versioned `ChartRecorder.exe`, public `setting.yaml` template and `system.yaml`; Saxo secrets and tokens are **never** bundled. Existing Saxo keyring credentials stay available to the same Windows user.

## Installing on another Windows PC with only setup.exe

The destination PC needs **only setup.exe**, a network connection and access to
the relevant Saxo OpenAPI app. It does not need a Python installation, Git,
GitHub CLI, or the source repository.

1. Copy the Windows-built `dist/setup.exe` to the other PC (for example using USB).
2. Double-click it, select `desktop`, `c_drive` or a writable custom folder,
   and confirm installation. Choose to launch ChartRecorder when prompted.
3. On a **fresh** Windows user account, the packaged ChartRecorder opens a
   `Saxo初期設定` dialog automatically because no Saxo OpenAPI App Key/Secret
   is stored. Enter the **App Key and App Secret**, not the Saxo account password.
4. Choose `保存してブラウザでログイン`. The credentials are saved to the
   current user's **Windows Credential Manager** only. The existing Saxo
   Authorization Code login opens in the **default web browser**, allowing
   the user's browser/password-manager autofill for their Saxo account.
5. Once browser authorization returns through the configured loopback redirect,
   the existing five-minute chart capture starts automatically. Chart output is
   saved to the installed `chart_image`.

If the initial dialog is canceled, ChartRecorder remains running without
capturing images; choose `Saxoに再ログイン` from the tray menu to retry.
For subsequent token expiry, the existing browser re-login continues without
requesting the App Key/Secret again, unless those credentials have been removed.

**Security:** setup.exe does not contain App Key, App Secret, Saxo account
password or OAuth tokens. The App Secret input is masked, and credentials are
never copied to YAML, GitHub, chart images or log files. Use the same Saxo SIM
or LIVE environment and a registered redirect URI matching `setting.yaml`.
A different Windows PC will not inherit the old PC's vault; re-enter the app
credentials and sign in once per Windows user.

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

## Versioned safe rebuild and restart (2026-10-14)

**Recommended command (Git Bash in repository root):**

```bash
cd /c/Users/yuki_/OneDrive/Documents/github/product_chat_record
git switch main
git pull --ff-only origin main
cmd.exe /c 'scripts\\update_chartrecorder.bat --location c_drive'
```

Use `--location desktop` for Desktop/ChartRecorder, or an absolute parent path such as `--location "D:/Apps"`. The default location comes from `system.yaml`. If the EXE and `installed-version.txt` already match the current release, the updater **skips the rebuild**, but still safely restarts the app. To explicitly recompile, pass `--rebuild`; use `--dry-run` to inspect the target without stopping it.

The release ID is `VERSION` (semantic version, currently 0.1.0) plus the eight-character Git commit SHA, e.g. `v0.1.0-abcdefgh`. New builds go to `dist/releases/<release-id>/ChartRecorder.exe` and **never overwrite** the running `dist/ChartRecorder.exe`. The updater copies the versioned binary into the selected installation folder only after a cooperative stop. No Saxo tokens or secrets are ever included in release artifacts or in `installed-version.txt`.

Update order: **build to a separate versioned folder → request shutdown using the existing named Windows event → wait until the mutex disappears (including any in-flight market-data capture or Saxo login) → install atomically → launch**. This is deliberately safer than stopping the app first, because compilation failures do not interrupt chart capture.

On a legacy executable lacking the cooperative event, or if processing fails to stop within five minutes, the updater **refuses to force-kill**. Exit the old app from the tray manually, then rerun the command. It never starts concurrent Saxo workers. If installation fails after shutdown, it attempts to restore and launch the previous installed executable.

`scripts/build_setup_windows.bat` also stages the app binary by version before building `dist/setup.exe`. The installer now cooperatively stops an existing modern instance, installs the new app, and restarts it. The old data directory is never migrated or deleted.

## Limitations

- Windows GUI installation / same-user Saxo vault reuse needs Windows **real-PC** verification; a headless runner cannot confirm task-tray behavior.
- Binary installers are not code-signed. Windows SmartScreen or antivirus may warn. Do not bypass corporate security policies.
- The install is a copy-based per-user setup, not a Windows uninstaller. To remove it, disable `Windowsログオン時に起動` from the tray, exit ChartRecorder, then remove the Desktop/ChartRecorder folder once any important images are backed up.
- Changes to `system.yaml` are applied by rerunning setup.exe; they are not a live move operation.
