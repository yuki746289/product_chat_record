<!-- Created: 2026-10-09 22:09 JST -->
# Implementation checklist

| No | Task | State |
|---:|---|---|
| 1 | Public GitHub repository identified | Done |
| 2 | YAML configuration validation | Implemented; offline tests passed |
| 3 | 2×5 chart / nine timeframes / info panel | Implemented; PNG smoke test passed |
| 4 | EMA20/30/40 and RCI9/14/26 | Implemented; offline tests passed |
| 5 | 8H UTC-aligned resampling | Implemented; TradingView cross-check pending |
| 6 | Official MCP get_ohlcv adapter | Implemented; live authentication/response unverified |
| 7 | 30-minute production scheduled capture | HOLD: permission and unattended OAuth unverified |
| 8 | 8-hour artifact cleanup | Implemented; GitHub Actions live validation pending |
| 9 | One-shot Windows BAT image retrieval | Implemented; offline tests passed, Windows CLI validation pending |
| 10 | Market vs TradingView plotted values comparison | Not started |
| 11 | Public repository secret/data leakage check | Pending |
| 12 | Windows tray: one-minute GitHub artifact polling | Implemented; Windows tray/exe verification pending |
| 13 | Local retention: within 8h OR latest 16 timestamp folders | Implemented; offline retention tests passed |
| 14 | Backfill, deduplication, and interrupted-download retry | Implemented; offline mock GitHub tests passed |
| 15 | Windows EXE build and autostart registry behavior | Implemented; Windows executable build/run verification pending |
| 16 | README Git pull/push commands for feature branch | Done |
| 17 | Full regression suite | 18 tests passed in Linux environment |

Do not enable a 30-minute live workflow before tasks 6, 10, 11 have passed, and
market data provider terms explicitly authorize this intended use.
