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

<!-- Created: 2026-10-10 JST -->
## TradingView MCP: authorization and production readiness

The official TradingView MCP offers OAuth 2.1 and read-only `get_ohlcv`, but
**the intended 30-minute unattended GitHub Actions polling, image transformation,
and Public Artifact sharing have not been confirmed as authorized uses**.
See [`docs/TRADINGVIEW_MCP_AUTHORIZATION_REVIEW_20261010.md`](docs/TRADINGVIEW_MCP_AUTHORIZATION_REVIEW_20261010.md)
for the official references, support questions, and controlled rollout checklist.

**Do not** enable `provider.enabled: true` or the production cron schedule until
TradingView expressly confirms the intended unattended use and the OAuth renewal
mechanism is tested. Paid TradingView plan access alone is not permission for
automated extraction. The account owner must authorize OAuth interactively; no
credentials should be posted to GitHub, `setting.yaml`, or this chat.

Interactive authentication supported by TradingView's official documentation
(not a GitHub Actions login):

1. In an eligible ChatGPT client, open Settings → Plugins → Add → MCPs → Add.
2. Enter `https://mcp.tradingview.com/mcp` with Streamable HTTP.
3. Authenticate with a paid TradingView account and approve the tool access.

This verifies interactive access **only**. OAuth login in ChatGPT is not shared
with GitHub Actions, which requires a separately authorized unattended flow.

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

## Local Windows app (1-minute GitHub polling)

**Current limitation:** TradingView MCP unattended access has not yet been
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

This creates `dist\ChartRecorder.exe` and, if absent, `dist\setting.yaml`.
Edit the copy of `dist\setting.yaml` for that executable (in particular,
`output.local_dir`). The EXE reads this external file, not an embedded copy.
To use the **repository's** editable `setting.yaml` directly (so Git
pull/push updates and the app use the same file), run from the repository root:

```bat
dist\ChartRecorder.exe --config "%CD%\setting.yaml"
```

Alternatively, double-click `dist\ChartRecorder.exe` to use the adjacent
`dist\setting.yaml` (a **separate copy** that does not change with Git pulls).
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

### Manual BAT download (fallback)

```bat
scripts\download_charts.bat
```

This checks once and exits. It uses the **same** download history and cleanup
rules as the tray app; do not schedule both concurrently. Run the app instead
for continuous 1-minute monitoring.

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
