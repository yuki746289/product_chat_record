<!-- Created: 2026-10-09 22:09 JST -->
# Implementation checklist

| No | Task | State |
|---:|---|---|
| 1 | Public GitHub repository identified | Done |
| 2 | YAML configuration validation | Implemented; offline tests passed |
| 3 | 2×5 chart / nine timeframes / info panel | Implemented; PNG smoke test passed |
| 4 | EMA20/30/40 and RCI9/14/26 | Implemented; offline tests passed |
| 5 | 8H UTC-aligned resampling | Implemented; TradingView cross-check pending |
| 6 | Official MCP get_ohlcv adapter | Authenticated ChatGPT call and row schema verified; direct Python OAuth/token renewal not yet verified |
| 7 | 30-minute production scheduled capture | HOLD: permission and unattended OAuth unverified |
| 8 | 8-hour artifact cleanup | Implemented; GitHub Actions live validation pending |
| 9 | One-shot Windows BAT image retrieval | Implemented; offline tests passed, Windows CLI validation pending |
| 10 | Market vs TradingView plotted values comparison | Not started |
| 11 | Public repository secret/data leakage check | Pending |
| 12 | Windows tray: one-minute GitHub artifact polling | Implemented; Windows tray/exe verification pending |
| 13 | Local retention: within 8h OR latest 16 timestamp folders | Implemented; offline retention tests passed |
| 14 | Backfill, deduplication, and interrupted-download retry | Implemented; offline mock GitHub tests passed |
| 15 | Windows EXE build and autostart registry behavior | Implemented; Windows executable build/run verification pending |
| 16 | README Git pull/push commands for main | Done |
| 17 | Full regression suite | 18 tests passed in Linux environment |
| 18 | TradingView official MCP documentation review | Done: 2026-10-10; official URL, OAuth, tool intervals confirmed |
| 24 | USDJPY real MCP responses across 8 intervals | Done: 220 each plus 440 for 4H, row fields verified |
| 25 | UTC-anchored 8H conversion from live 4H timestamps | Done: 205 valid buckets; TradingView UI anchor alignment remains pending |
| 26 | MCP success/error and tool alias handling | Implemented; 8 targeted synthetic-contract tests passed offline |
| 23 | TradingView subscription plan eligibility | Plus plan; ChatGPT MCP login and OHLCV retrieval verified |
| 19 | TradingView unattended polling and derived-image rights | HOLD: documented permission not confirmed; request confirmation |
| 20 | Public GitHub Artifact sharing rights | HOLD: potential third-party access/redistribution; request confirmation |
| 21 | OAuth 2.1 browser authorization and renewable headless auth | HOLD: needs user login, provider OAuth grant verification |
| 22 | Production readiness and rollback plan | Documented in docs/TRADINGVIEW_MCP_AUTHORIZATION_REVIEW_20261010.md; live rollout blocked |

Do not enable 30-minute live polling before tasks 6, 10, 11, 19, 20, and 21
are verified and documented, including explicit permission for the intended
unattended processing and distribution, and a tested OAuth renewal mechanism.
