<!-- Created: 2026-10-10 JST -->
# TradingView MCP: 認証・無人実行・利用許諾の検証（2026-10-10）

## 結論 / 現在の状態

**HOLD：GitHub Actionsからの実データ定期取得は有効化しない。**

- TradingView公式MCP（ベータ版）は `https://mcp.tradingview.com/mcp`、OAuth 2.1 認証、Essential以上（トライアル対象外）で提供されている。
- `get_ohlcv` はOHLCVを取得できる。選択可能な間隔は `1m, 5m, 15m, 30m, 1h, 4h, 1D, 1W, M`。8時間足は直接提供されず、既存の4時間足合成処理が必要。
- **公式MCPの対話型利用と、GitHub Actionsによる30分ごとの無人取得は別の許諾問題。** 公式資料から後者の許可を確認できなかった。
- TradingView公式の利用規約・サポート文書は、自動的なデータ収集や表示目的外の加工利用について制約を明示している。
- PublicリポジトリのArtifactsに加工したチャート画像を保存・第三者が取得可能にする行為についても、許可範囲を確認する必要がある。
- **契約プラン: TradingView Plus（ユーザー申告、2026-10-10）**。公式MCPのEssential以上というプラン条件を満たす見込み（無料トライアルでないことが条件）。OAuthログイン、refresh_tokenの発行可否、無人更新の継続性は未検証。アカウント情報・トークン等はGitHubやチャットへ貼らないこと。

## 公式ソース

1. 公式MCP・ツール仕様: https://www.tradingview.com/mcp/docs
2. 公式導入アナウンス: https://www.tradingview.com/blog/en/tradingview-mcp-server-public-beta-60864/
3. 利用規約: https://www.tradingview.com/policies/
4. 自動収集に関する公式サポート: https://www.tradingview.com/support/solutions/43000674726-why-is-my-account-banned-due-to-suspicious-activity/
5. Python MCP SDKのOAuthクライアント参考: https://github.com/modelcontextprotocol/python-sdk/tree/main/docs/client

## アプリケーションで想定するAPI呼び出し

- 設定済み通貨ペアごとに、1M、5M、15M、1H、4H、1D、1W、1Mnの **8種類の取得**。8Hは4Hから合成。
- 1Mは鮮度確認にも使用し、同一実行中に二重取得しない。
- 3通貨ペアの場合、通常1回の生成で約24リクエスト、30分ごとの実行で市場オープン中約48回/日（1日最大約1,152リクエスト）。休日は1M鮮度チェックのみになる可能性がある。これは計画上の単純計算であり、再試行・認証・MCP内部呼び出し・利用上限などは含まれない。
- MCP公式の約100リクエスト/分という説明だけでは、1日あたりの契約上限を保証しない。

## TradingViewへ確認する事項（必須）

1. 公式MCPの `get_ohlcv` を外部のGitHub Actionsで**無人・30分間隔**に繰り返すことを認めるか（対象: 設定した複数のFX通貨ペア、8種類の時間足、1回あたり最大数千本）。
2. 取得したOHLCVを使ってPythonでEMA20/30/40、RCI9/14/26、ローソク足チャートのPNGを生成する**加工利用**を認めるか。
3. Public GitHub Actions ArtifactsへのPNGの一時保存（第三者がアクセスし得る）と、本人PCでの短期保存・表示を認めるか。Publicへの掲載が認められない場合は非公開配布手段へ変更可能か。
4. OAuth 2.1のクライアント登録、refresh token発行・期限・ローテーション、GitHubのヘッドレス環境での継続利用を認めるか。client_credentials等の正式な無人認証手段の提供有無。
5. 同時取得/日次リクエストの上限、利用プラン、データ提供元ごとの権限・再配布制限。

**明確な許可が得られるまで、本番の `provider.enabled` と30分cronは無効のままにする。**

## 問い合わせに使える英語文面

Subject: Permission and authentication for unattended TradingView MCP usage

Hello TradingView Support,

I have a paid TradingView Plus subscription and would like to use the official TradingView MCP server's `get_ohlcv` tool in a personal chart-recording project. A GitHub Actions workflow would run every 30 minutes, request OHLCV bars for several FX pairs across eight intervals (1m, 5m, 15m, 1h, 4h, 1D, 1W, M), compute EMA and RCI indicators in Python, and generate human-readable PNG charts. The charts would be temporarily stored as artifacts on a public GitHub repository and downloaded to my own Windows PC. No automated orders would be placed.

Could you confirm whether this unattended polling, data transformation, and public artifact storage are permitted under the TradingView MCP beta and market data license? If any part is not allowed, would it be permitted with private artifacts or a different agreement? Also, does the official MCP OAuth 2.1 flow support renewable, headless GitHub Actions authentication, and what limits apply?

Thank you.

## 許可が得られた後の実施手順（現在は未実行）

1. TradingViewアカウントがEssential以上・トライアルでないことをユーザーが確認する。
2. ユーザー自身がブラウザまたはCodex/ChatGPTの公式MCP認証画面からログインし、`list_tools` と手動での1件の `get_ohlcv` を検証する。パスワード・トークンをリポジトリへ公開しない。
3. 実際の認証サーバーが提供するOAuthクライアント登録方式とrefresh tokenの寿命・更新方法を検証し、保存先をGitHub Secretsなどの保護された場所に設計する。ChatGPTプラグインのログイン状態はGitHub Actionsに自動継承されない。
4. MCPの実レスポンスに対して `parse_mcp_response` の互換性、OHLCV本数、シンボル、鮮度、日付境界（とくに8H/週足/月足）を検証する。
5. `provider.enabled` を明示的に許可した実行環境だけで有効にし、手動テスト→単一通貨ペア→複数通貨ペアの順に段階展開する。公開配布が未許可ならPublic Artifactは使わない。
6. 承認済みの利用条件と上限に合わせて30分cronを有効化し、429/401/403/5xx、更新停止、欠損、権限切れ、画像数、GitHub課金を監視する。

## 既存実装の監査結果

- `setting.yaml`: `provider.enabled: false`（安全側の初期設定）。
- `.github/workflows/generate_charts.yml`: `schedule`コメントアウト。手動デモ実行が可能。
- `src/providers.py`: `TRADINGVIEW_MCP_ACCESS_TOKEN` 環境変数を要求するMCPクライアントを実装済み。ただしOAuthの取得・期限切れ時の更新は未実装。
- `requirements.txt`: MCP Python SDK v1を指定。上流SDK v2のAPIは変更されているため、導入時は使用バージョンを固定して同一バージョンで試験する。
- TradingViewアプリやブラウザの常時起動は予定構成上不要。ただし初回対話認証はユーザー操作が必要。

## 代替策

許可が得られない場合は、**自動取得とチャート生成を契約上許可する市場データAPI**へデータ提供元を変更する。既存の `src/chart.py`、EMA/RCI、Windows画像取得などは維持し、`src/providers.py` の実装を切り替える。代替APIも対象のFXペア・全期間足と利用・配信許諾を確認する。