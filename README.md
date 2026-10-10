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

## Local Windows retrieval

Install Python, GitHub CLI (`gh`), authenticate using `gh auth login`, install Python dependencies, then run:

```bat
scripts\download_charts.bat
```

The BAT wrapper calls `src.local_download`, which gets the latest successful run's `charts` artifact and copies all configured pairs to `local_dir/YYYYMMDD_HHmm/{pair}.png`, preserving past folders and ignoring duplicate run IDs. Schedule this BAT through Windows Task Scheduler every 30 minutes (while the PC is online). An expired artifact cannot be recovered.

## Fidelity limitations

- The 8H frame is built from pairs of 4H candles aligned to **UTC 00:00**; verify this anchor against your TradingView session before relying on it.
- RCI is Spearman rank correlation ×100; ties receive average ranks. An exact TradingView Pine-script RCI implementation may differ in tie policy.
- Monthly (`1Mn`) fetches `M` via official MCP. Tool docs list `1m`, `5m`, `15m`, `1h`, `4h`, `1D`, `1W`, `M`; other intervals and symbol mappings must be verified.
- Live output uses each incoming latest bar and can include an incomplete current candle.
- This application does not execute trades or perform automated decisions.
