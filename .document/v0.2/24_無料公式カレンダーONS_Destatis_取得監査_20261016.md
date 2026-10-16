# ECO-019 無料取得元 第3回検証と重要指標の正規化監査（2026-10-16）

## 目的・作業範囲
ChartRecorder v0.2.0向け、公式無料カレンダーの **実HTTP応答・指標別イベントの正規化・JSON Schema検証** を進める。取得費用は0円のまま、元APIの発表日時・原タイトル・固定S/Aを保持する。今回も対象は **検証用GitHub Actionsのみ**。Windows EXE、Saxo、VERSION、main、release_0.1.0は変更しない。

## Run 1: NZD、英ONS、Eurostat、ドイツのHTTP取得
[GitHub Actions #38866257606](https://github.com/yuki746289/product_chat_record/actions/runs/38866257606) — SUCCESS。10候補中 **HTTP200が7件**、JSONはONSの2要求。いずれも元データ本文をpublicリポジトリに保存していない。

| 対象 | HTTP | 判定と制限 |
|---|---:|---|
| RBNZ OCR主要日程 | 403 | GitHub Actionsから拒否。アクセス制限を回避せず、無人取得は未合格 |
| RBNZ公表方針 | 403 | 同上。公式ページの存在はWeb側で確認できるがHTTP本体の自動取得成功ではない |
| Stats NZ発表カレンダー | 200 | HTMLは取得できたが公開日程が可視テキスト中になく、個別イベント抽出未達 |
| Stats NZ CPI指標説明 | 200 | CPI説明のみ。将来の公表日時はHTMLの可視部分から取得できず |
| 英ONS公開Release Search API・CPI | 200 | application/json、`releases[]` 配列を取得 |
| 英ONS公開Release Search API・GDP | 200 | 同上 |
| Destatis正式週間発表予定 | 200 | 2026年10月13日のCPI確報が本文に存在 |
| Destatis年次予定の誤URL | 404 | URL未確定。週間予定とは別に処理 |
| Eurostat Euro indicators | 200 | HTMLを取得。ただし2026年の個別発表予定は静的HTMLに含まれず |
| Eurostat全体カレンダー | 200 | HTMLのみ。ICSの直接取得URLは未確定 |

## Run 2: ONS JSON構造検証
[GitHub Actions #38866428910](https://github.com/yuki746289/product_chat_record/actions/runs/38866428910) — SUCCESS。

公式API `https://api.beta.ons.gov.uk/v1/search/releases` は **`releases[]`** を返し、各行の `description.title`、`description.release_date`、`uri` が利用できる。CPI候補79、GDP候補79、英国労働候補54、小売候補24件を返したが、これらは検索結果であって重要指標の件数ではない。期間・完全な元タイトルで二次フィルターが必要。結果には `time series` の別エントリがあるため、1つの政策・統計発表として重複表示しないこと。

## Run 3: 英国4系列の公式API → 固定S/A → JSON Schema
[GitHub Actions #38866589454](https://github.com/yuki746289/product_chat_record/actions/runs/38866589454) — SUCCESS。全4系列で `jsonschema.validate(..., format_checker=FormatChecker())` PASS。

| UKマスターID | S/A | ONSの正式な原タイトル例 | ソースUTC | JST |
|---|---|---|---|---|
| `GB_EMPLOYMENT` | A | UK Labour Market: October 2026 | 2026-10-20 06:00Z | 2026-10-20 15:00 |
| `GB_CPI` | S | Consumer price inflation, UK: September 2026 | 2026-10-21 06:00Z | 2026-10-21 15:00 |
| `GB_RETAIL` | A | Retail sales, Great Britain: September 2026 | 2026-10-23 06:00Z | 2026-10-23 15:00 |
| `GB_GDP` | A | GDP monthly estimate, UK: September 2026 | 2026-11-12 07:00Z | 2026-11-12 16:00 |

検証の条件:
- ONSの提供するタイムゾーン指定のある`release_date`を使用。固定時差を使わずUTC → Asia/Tokyo変換を行う。
- 各種の「time series」・派生表示を別のS/A指標として重複加算しない。該当判定はプロバイダー単位の厳密照合ルールにする。
- `forecast/previous/actual`は取得していないためnull。`first_party.verified=false`は実績値を独立検証していない意味。
- 今回のテストは公開されたRelease Search APIの特定4件の検証であり、ONSの全イベント・将来仕様変更・全系列の網羅成功ではない。

## Run 4: Destatis CPI、Eurostat、NZリリースカレンダー
[GitHub Actions #38866830724](https://github.com/yuki746289/product_chat_record/actions/runs/38866830724) — SUCCESS。

| 対象 | 結果 |
|---|---|
| Destatis公式週間予定 | HTTP200。2026年10月13日「Consumer price index (including harmonised index of consumer prices), final results」が掲載。固定`DE_CPI`/Aへ対応し、時刻不明の共通JSON Schema検証PASS |
| Eurostat（2種類の月間一覧URL） | HTTP200。ただし静的HTMLには該当指標・2026年日程を抽出できず。ICS購読の存在は公式に確認できるが**直接URL未取得** |
| Stats NZ release calendar | HTTP200。ページのHTMLに具体的な2026年予定が抽出できず。公開データの自動取得は未解決 |

DestatisのCPIは**現地の発表日**まで確認。現地発表時刻が未確定なので`date_utc=null`、`date_jst=null`、`time_precision=UNKNOWN`。JSTにおける日付が確実に同日とは断定できないため、時刻確定前の本番表示には別途慎重な扱いが必要。

## 公式利用条件の継続検討
- ONS公式開発者資料はキー不要のオープンAPIと説明: https://developer.ons.gov.uk/
- ONS著作権・データ再利用: https://www.ons.gov.uk/help/terms-conditions （通常はOGL・出典表示。第三者権利は例外）
- ONS Fair use: https://www.ons.gov.uk/help/fair-use-policy （頻繁なスクレイピング禁止。識別可能なUser-Agent/連絡先が必要）。試験時User-Agentは検証用であり、将来の運用時は適切な連絡情報付きに変更する。
- Destatis利用条件: https://www.destatis.de/EN/Service/Imprint/_node.html など正式なサイト規約で、商用/個人、出典表示と公開画像への再利用条件を採用前に再確認。
- **本番での継続自動取得および画像化を最終承認したわけではない**。最終ライセンス判定はソース別に記録する。

## カバレッジの変化（1件以上の試験がある指標グループ）
- 前回: 7 / 53（AUD CPI、CAD BoC/CPI、日銀政策、ECB政策、BOE政策、FRB FOMC）。
- 今回新たに: ONS4グループ（GB_CPI/GB_GDP/GB_RETAIL/GB_EMPLOYMENT）、Destatis1グループ（DE_CPI）。
- **累計 12 / 53、未実証41 / 53**。恒常的な無料配信・全件収集の達成率ではない。
- NZDは0 / 6のまま（公式ページが検索で見つかることと、GitHub Actionsで自動取得できることは異なる）。

## 次の作業
1. NZD公式カレンダーの機械可読な配信経路（RBNZ/Stats NZ）を調べ、403・動的描画の問題を合法的に解決する。
2. Eurostat ICS URLとDEの公表日程を本番で安定的に取得する仕組みを確認。
3. BLSの403を回避・偽装せず、正式な無料配信手段を調査。民間PMI等の有償権利が必要な項目は未網羅であることを明示。
4. provider固有の原タイトル/日時/速報・改定/重複レコードのクロスウォークを確定し、継続試験可能な形にする。
5. `.document/v0.2/99_仕様確認.md`の不合格条件を解消するまでChartRecorder本体改変と`release_0.2.0`作成には進まない。
