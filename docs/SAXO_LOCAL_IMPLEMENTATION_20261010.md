<!-- Created: 2026-10-10 JST -->
# Saxo Windows local mode — specification, verification and remaining steps

## Architecture

- GitHub repository is **code and public configuration only**; Saxo quotes and all OAuth tokens remain on the Windows PC.
- `src/saxo_auth.py`: registered **Authorization Code** flow, local callback (`http://localhost:8765/callback` by default), OAuth state verification, access-token renewal and refresh-token rotation; Windows Credential Manager via `keyring` stores App Key, App Secret, access/refresh tokens.
- `src/saxo_provider.py`: Saxo REST API instrument search (`ref/v1/instruments`) for exactly matching `FxSpot` pair; chart data via `chart/v3/charts` with **Bid** as default. No order/trade endpoints.
- `src/saxo_local.py`: tray calls it every 60 seconds. Tokens are refreshed as required even between chart generations. One image batch per 30-minute UTC-aligned slot; no image if 1-minute candle is stale. 9 direct Saxo horizons: 1/5/15/60/240/480/1440/10080/43200 minutes.
- `src/chart.py`: original 2-column 9-chart layout, EMA20/30/40, RCI9/14/26, 12-bar right padding, with Saxo data source text.
- `src/local_monitor.py`: existing image retention logic reused — retain **all folders <=8 hours old OR newest 16**.
- `src/tray_app.py`: existing `github` download mode retained; new `saxo_local` mode, one-minute tick, optional browser re-login from tray, Windows autostart and single-instance mutex.

## Configuration and controls

Set in `setting.yaml` after completing **local** OAuth:

```yaml
saxo:
  enabled: true
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

**Never** save App Key/App Secret, OAuth codes, access/refresh tokens or market-data dumps inside the Public GitHub repository. The app refuses Saxo API calls until `saxo.enabled: true`.

## Before first use on Windows

1. Confirm `redirect_uri` exactly matches the registered Saxo SIM Code-grant app.
2. Run `python -m pip install -r requirements-windows.txt`.
3. Run `python -m src.saxo_auth configure --config setting.yaml` to save App Key and App Secret to Windows Credential Manager (hidden secret prompt).
4. Run `python -m src.saxo_auth login --config setting.yaml` for browser authorization; the app validates OAuth state and stores rotating tokens in the credential vault.
5. Set `saxo.enabled: true` and run `python -m src.saxo_local --config setting.yaml` while FX market is open. SIM data/feed accuracy and delay require live checks.
6. Build EXE using `scripts\build_windows.bat` and launch from repository root using `dist\ChartRecorder.exe --config "%CD%\setting.yaml"`.
7. If PC is off/asleep longer than the refresh-token expiry, manually sign in again. An invalid/revoked previously pasted 24-hour token is *not* reused.

## Testing and gaps

- Mock Saxo payloads, OHLC Bid/Ask handling, FxSpot UIC lookup, token rotation and expiry, 30-minute scheduling, weekend no-data skip, PNG rendering: tested on Linux without account secrets.
- Not yet tested: Saxo SIM **real** OAuth browser callback, live SIM instruments/UIC, actual Saxo quote field sets, 8H/month bar boundary versus SaxoTrader, Windows Credential Manager, real Windows tray/EXE build.
- Do not enable LIVE mode before validating broker data rights and explicit account access. SIM environment is the only default.
- The registered Code-grant client secret remains on the same Windows user credential vault. For true native apps Saxo recommends PKCE. This project deliberately matches the user's existing Code-grant app for local-only use; if a native PKCE app is registered later, migrate the OAuth flow instead of reusing this confidential-client mechanism.

## Official documentation

- https://www.developer.saxo/openapi/learn/oauth-authorization-code-grant
- https://www.developer.saxo/openapi/learn/security
- https://www.developer.saxo/openapi/referencedocs/chart/v3/charts/get__chart
- https://www.developer.saxo/openapi/referencedocs/ref/v1/instruments/get__ref
