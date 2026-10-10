<!-- Created: 2026-10-09 22:09 JST -->
# TradingView-style Currency Chart Recorder

Generate one dark-theme PNG per configured currency pair, consisting of **nine**
chart panels in two columns (1M, 5M, 15M, 1H, 4H, 8H, 1D, 1W, 1Mn) and one
information panel. EMA: 20, 30, 40. RCI: 9, 14, 26.

## Important status

- **Offline drawing with synthetic data works** via `--demo` and is intended only for layout testing.
- **Live TradingView MCP is NOT activated**: unattended OAuth refresh, response compatibility,
  TradingView's terms, and exchange data permissions must be confirmed before scheduling.
- The workflows are **manual-only** until this is resolved. Scheduled cron lines are commented out.
- Public repository: never commit tokens, cookies, account details, or private market data.

TradingView official MCP: https://www.tradingview.com/mcp/docs
TradingView use policy: https://www.tradingview.com/policies/


## Saxo FX category folders (default configuration)

The public `setting.yaml` contains **13 FX pairs**, written as one inline YAML
mapping per pair, grouped as `cross_non_jpy` (7 pairs) and `cross_jpy` (6 pairs).
`ERUJPY` was corrected to `EURJPY`. Indices, metals and cryptocurrency
instruments are not included.

In Saxo local mode, files are written to:

```text
C:/TradingViewCharts/
  YYYYMMDD_HHmm/
    cross_non_jpy/
      GBPAUD.png  AUDUSD.png  GBPUSD.png  EURGBP.png
      USDCAD.png  EURUSD.png  GBPNZD.png
    cross_jpy/
      AUDJPY.png  GBPJPY.png  USDJPY.png
      EURJPY.png  CADJPY.png  NZDJPY.png
```

Retention is evaluated at the timestamp-folder level: preserve **every folder
within 8 hours or the newest 16 timestamp folders**, then delete older batches.
Existing top-level timestamp folders with PNGs are also recognized. The legacy
GitHub Artifact downloader accepts both category-layout and flat images.

After pulling an updated `setting.yaml`, restart the Windows tray app so
that the expanded symbol list takes effect. Tokens and App Secret remain only
in Windows Credential Manager.

## Recommended: Saxo local Windows mode (SIM-first)

**No GitHub Actions or GitHub CLI is needed for chart generation in this mode.**
The Windows tray app connects to the Saxo OpenAPI, refreshes OAuth tokens while
running, checks data each 30-minute slot, renders one 9-panel PNG per configured
FX pair, and retains all folders from the last **8 hours OR the latest 16**.
Tokens and App Secret are kept in the Windows user's Credential Manager, not in Git.

The app uses the Saxo **Authorization Code** grant selected when the SIM app
was registered. Confirm the exact Redirect URL in the Saxo Developer Portal:
`http://localhost:8765/callback` is only a default, and it **must match** the
registered URL. Saxo recommends PKCE for native apps; this local confidential
client uses the already-registered Code grant and stores its secret in the
Windows credential vault. This is intended for personal use on your own PC.

### Sync your local main branch

The Saxo local mode is already merged into `main`. From the repository root:

```bash
git switch main
git pull --ff-only origin main
```

Check `git status` before switching or pulling; resolve local modifications
first rather than discarding them.

### Initial one-time authentication (Windows Command Prompt)

From your local `product_chat_record` directory:

```bat
python -m pip install -r requirements-windows.txt
python -m src.saxo_auth configure --config setting.yaml
python -m src.saxo_auth login --config setting.yaml
```

**Never paste the App Secret or OAuth tokens into a chat, setting.yaml,
GitHub commits or screenshots.** The `configure` command asks for App Key and
prompts for the App Secret without echoing it. `login` starts a loopback-only
OAuth callback listener and opens Saxo in your browser once. If Windows sleeps
or is shut down until the Refresh Token expires, click "Saxoに再ログイン" from the
tray menu (or run the `login` command again).

Update the **non-secret** settings in `setting.yaml`:

```yaml
saxo:
  enabled: true  # switch on ONLY after local browser login
  environment: sim
  redirect_uri: http://localhost:8765/callback
  price_side: bid
local_monitor:
  mode: saxo_local
  poll_seconds: 60
  chart_interval_minutes: 30
  retention_hours: 8
  min_folders: 16
```

While FX is open, run the first Saxo test locally:

```bat
python -m src.saxo_local --config setting.yaml
```

If the test succeeds, build and start the Windows tray app:

```bat
scripts\build_windows.bat
dist\ChartRecorder.exe
```

Or launch it in Git Bash with **no arguments**:

```bash
./dist/ChartRecorder.exe
```

The EXE at `dist/ChartRecorder.exe` automatically uses the Git-managed
`setting.yaml` **one directory above `dist`**. This works even if started
from another working directory or double-clicked in Explorer. An outdated
`dist/setting.yaml` file is ignored. The build no longer copies a second
settings file into `dist`. Use `--config PATH` only if deliberately running
with a nonstandard settings path.

**Windows and LIVE Saxo connectivity have not yet been confirmed.** SIM data
can be delayed or simulated. Only the read-only market-data endpoints are
used; no trading permissions or order endpoints are required.

Detailed implementation and outstanding verification:
[docs/SAXO_LOCAL_IMPLEMENTATION_20261010.md](docs/SAXO_LOCAL_IMPLEMENTATION_20261010.md).

### GitHub mode (legacy/test-only)

The existing GitHub Artifact download mode is still available by setting
`local_monitor.mode: github`, but it is **not required** for Saxo local mode.
TradingView MCP live capture and the GitHub Actions 30-minute cron remain
disabled. Existing test-only chart generation via `--demo` is unaffected.

## Quick start

```bash
python -m pip install -r requirements.txt
python -m pytest -q
python -m src.main --demo
```

Demo output: `output/YYYYMMDD_HHMM/USDJPY.png` etc. Demo content is labelled **SYNTHETIC DEMO DATA**.

Change currency pairs, TradingView `EXCHANGE:SYMBOL` identifiers, local download directory, and right-side chart padding (`chart.right_padding_bars`, default `12`) in `setting.yaml`.

## When the market is closed

Live mode checks the timestamp of the most recent **1M** candle before fetching
other intervals. When it is older than `market.max_1m_age_minutes` (default
**10 minutes**) or implausibly future-dated, that currency pair is **skipped**.
If no currency pair has recent data, the workflow uploads **no Artifact**.
Other pairs may still produce images. Demo mode deliberately bypasses this check.

This is a **data freshness** check, not an exact holiday calendar. There is a
short grace period after market close; delayed vendor feeds may also result in
skips, so verify timestamps and adjust the threshold with actual MCP data.
Network errors remain errors rather than being mislabeled as holidays.
Windows downloads select the latest existing nonexpired artifact rather than
the latest successful run, preventing closed-market runs from breaking downloads.

## GitHub Actions

- `Generate Charts` → Run workflow → `demo=true` produces sample PNGs as one artifact called `charts`.
- Artifacts have 1-day GitHub minimum built-in retention; `Cleanup Charts Artifacts` manually removes chart artifacts older than **8 hours**. Enable cron after validating automated operations.
- After authorization, set `provider.enabled: true`, establish a secure renewable OAuth access token flow, and provide `TRADINGVIEW_MCP_ACCESS_TOKEN` as a **GitHub Actions secret**. An access token alone is not an unattended refresh strategy.
- GitHub-hosted runners may start later than the scheduled time; exact 30-minute capture is not guaranteed.

## Legacy: GitHub Artifact download mode (1-minute polling)

**Legacy GitHub mode only:** TradingView MCP unattended access has not yet been
validated or enabled. Without successful chart-generation runs on GitHub, the
Windows app will have no live images to download.

Windows requirements: install [Python](https://www.python.org/),
[GitHub CLI](https://cli.github.com/) (`gh`), and sign in once with
`gh auth login`. The executable still needs `gh.exe` available in the
Windows user's PATH; log in as the same Windows user who will run the app.

Build a Windows `.exe` **on a Windows PC** (not Linux):

```bat
scripts\build_windows.bat
```

This builds `dist\ChartRecorder.exe`, which automatically uses the
repository-root `setting.yaml`. It does not create a separate `dist\setting.yaml`.
If a copy from an older build exists in `dist`, it will **not** be read.
Double-click the EXE or run `./dist/ChartRecorder.exe` without arguments.
Restart the app after changing `local_monitor.poll_seconds` or `output.local_dir`.

Launch the EXE once; it stays in the Windows system tray,
checking GitHub every **60 seconds**. From its right-click menu you can poll
now, pause, open the output directory, enable start-at-login (for built EXE
only), or exit. Start-at-login uses the **current user's** Windows registry,
without administrator privileges. Pausing disables polling until resumed.
The log is stored in `<output.local_dir>\.chart_recorder.log` (rotating).

For development without packaging:

```bat
python -m pip install -r requirements-windows.txt
python -m src.tray_app --config setting.yaml
```

### Image retention and missed downloads

Settings in `setting.yaml`:

```yaml
local_monitor:
  poll_seconds: 60
  retention_hours: 8
  min_folders: 16
```

After every poll, preserve **all timestamp folders not older than eight
hours**, and **at least the newest 16 nonempty timestamp folders**, even
across weekends/market holidays. Delete only folders matching
`YYYYMMDD_HHmm` that contain PNGs and violate both retention criteria.
Unknown folder names are never deleted. Images remain at
`<output.local_dir>\yyyyMMdd_HHmm\<currency_pair>.png`.
A folder can have fewer pairs when TradingView returns fresh data for only
some symbols. A `.downloaded_artifacts.json` file prevents repeat downloads.

The app backfills all **available unprocessed** GitHub artifacts in oldest-
first order (up to the latest 16 plus any within the eight-hour window). Images
already expired or deleted from GitHub cannot be recovered. An interruption
keeps the last successful images and retries missing downloads. No images are
created locally during a market closure when no new GitHub artifacts exist.
The 8-hour retention applies to local files; GitHub currently keeps its
Artifacts for one day unless cleanup is run (the automated cleanup cron is
currently disabled).

### Manual legacy download (Python only)

The unused `scripts/download_charts.bat` wrapper has been removed. If the
legacy GitHub Artifact mode is ever needed for debugging, its one-shot Python
command remains:

```bat
python -m src.local_download --config setting.yaml
```

The default `saxo_local` mode does not need this command or GitHub CLI.

## Updating setting.yaml on main

The working branch for normal operation is **main**. After PR #1 is merged,
use `main` for downloads and your local configuration updates.

One-time clone (Windows Command Prompt or PowerShell):

```bat
git clone https://github.com/yuki746289/product_chat_record.git
cd product_chat_record
git switch main
```

If you previously cloned the feature branch, switch to `main` first:

```bat
git fetch origin
git switch main
```

**Before editing** `setting.yaml`, fetch the latest `main`:

```bat
git pull --ff-only origin main
```

After editing, commit and push **only the settings file**:

```bat
git status
git add setting.yaml
git commit -m "Update chart settings"
git push origin main
```

The repository's `setting.yaml` is public: **never store OAuth tokens,
passwords, or other secrets** in it. Keep credentials in GitHub Secrets or
protected local storage. If `git pull --ff-only` fails, resolve your local
changes before retrying; avoid force pushes.

## Fidelity limitations

- The 8H frame is built from pairs of 4H candles aligned to **UTC 00:00**; verify this anchor against your TradingView session before relying on it.
- RCI is Spearman rank correlation ×100; ties receive average ranks. An exact TradingView Pine-script RCI implementation may differ in tie policy.
- Monthly (`1Mn`) fetches `M` via official MCP. Tool docs list `1m`, `5m`, `15m`, `1h`, `4h`, `1D`, `1W`, `M`; other intervals and symbol mappings must be verified.
- Live output uses each incoming latest bar and can include an incomplete current candle.
- This application does not execute trades or perform automated decisions.
