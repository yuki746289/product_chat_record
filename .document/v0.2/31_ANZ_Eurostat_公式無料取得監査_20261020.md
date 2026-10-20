# ECO-023/024 無料公表日程の取得監査：ANZ企業景況感・Eurostat指標（2026-10-20）

## 範囲
- ChartRecorder v0.2.0向け、無料の発表予定を収集・正規化できるかの独立検証。既存の固定S/Aマスターに新しい評価・基準を加えていない。
- 作業ブランチ：`develop`。Run終了後、一時検証ブランチは削除。`main`と`release_0.1.0`への変更なし。
- 実装状況：今回実行したPythonは**一時的GitHub Actionsの検証コード**。Windows ChartRecorder本体へのデータ取得・画像生成・日次スケジューリングは未実装。
- マッピング正本（調査用）：[30_ANZ_Eurostat_指標対応_検証用.yaml](30_ANZ_Eurostat_指標対応_検証用.yaml)。

## ECO-023 ANZ Business Outlook の一次発表日程
- ANZ公式サイト（https://www.anz.co.nz/about-us/economic-markets-research/）の「Data timetable」から、2026年の調査発表予定PDFの公開URLを確認。
- URL: https://www.anz.co.nz/content/dam/anzconz/documents/economics-and-market-research/ANZ-NZ-Release-Schedule.pdf
- [GitHub Actions #39369561725](https://github.com/yuki746289/product_chat_record/actions/runs/39369561725) **SUCCESS**。公表機関（ANZ自身）のPDFをHTTP200で取得し、発表日・時間の原文を確認、既存`NZ_BUSINESS`（A級）と共通JSON Schemaへ変換PASS。
- PDFは**2025-12-15時点の予定**であり「subject to change」と明記。2026-10-29は確定保証ではない。変更や取消の検出が必要。
- 発表予定：2026年10月29日13:00 NZDT（UTC+13）＝10月29日09:00 JST。11月30日・12月18日の予定も掲載されるが、本Schema検証は10月29日の1件のみ。
- ANZ提供の公開PDFに機械的なイベントUIDはないため、`source_record_id`はローカル導出IDとして区別。`forecast`、`actual`、`previous`はすべてnull。
- 同サイトのライセンス/二次利用/アプリ内表示条件は未確定。`license_status=PENDING`とする。

## ECO-024 Eurostat JSON 経済指標発表予定
- Eurostat一般公開カレンダー（https://ec.europa.eu/eurostat/news/release-calendar）のHTML内で、公式フロントエンドが利用する`/eurostat/o/calendars/eventsJson`と、`theme`・`category`・`keywords`・`isEuroindicator`等のパラメータを確認。
- [HTMLパラメータ調査 #39369081914](https://github.com/yuki746289/product_chat_record/actions/runs/39369081914) **SUCCESS**。
- 最初のパラメータ不足の試験（[Run #39369229154](https://github.com/yuki746289/product_chat_record/actions/runs/39369229154)）ではHTTP200でもレスポンス本文が空だった。**HTTP200のみでデータ取得成功とみなさない。**
- カレンダー画面のパラメータと日時範囲を正しく設定し、`X-Requested-With: XMLHttpRequest`を伴う公開リクエストにすると、[Run #39369682243](https://github.com/yuki746289/product_chat_record/actions/runs/39369682243) でHTTP200、全日程105イベント、Euro indicators絞込25イベントのJSON配列を取得。
- [重要度とSchema検証 #39369891456](https://github.com/yuki746289/product_chat_record/actions/runs/39369891456) **SUCCESS**。既存`EU_HICP`の2発表例、`EU_GDP`の1発表例、計**3イベント/2グループ**を正規化、固定S/A・共通JSON Schema検証PASS。

| 元名称 | 発表予定日 | 元recordid | 固定ID | S/A | 時刻 |
|---|---|---:|---|---|---|
| Flash estimate inflation euro area | 2026-10-02 | 22494168 | `EU_HICP` | S | UNKNOWN |
| Inflation (HICP) | 2026-10-16 | 22494298 | `EU_HICP` | S | UNKNOWN |
| Preliminary flash estimate GDP - EU and euro area | 2026-10-30 | 22494395 | `EU_GDP` | A | UNKNOWN |

**重要な時刻精度条件**
- APIは`start`に`2026-10-02T11:00Z`などの値を返すが、検証した3イベントは`allDay=true`だった。
- そのため、その数値を「実際の経済指標発表時刻」と断定しない。`date_utc=null`、`date_jst=null`、`time_precision=UNKNOWN`、`release_status=TIME_UNKNOWN`で正規化し、予定日だけを参考にする。
- `recordid`は元サービスの識別子として保持。将来も常に不変であることは未検証。EU HICP速報値・確報値は同じ指標グループだが異なる日程・発表と扱い、同時刻の重複統合対象にしない。
- 公式Eurostatのカレンダー表示用JSONは、**汎用の公開APIとしての利用保証や長期利用許諾の調査が必要**。画面内の公開エンドポイントを確認しただけで正式採用を宣言しない。
- Eurostat ICS購読自体は公式が案内しているが、**ICSの直URLと本体取得は引き続き未実証**。現時点の成功はJSON方式のみ。
- Eurostatから実績・前回値・市場予想は取得していない。すべてnullで扱う。

## RBNZの政策金利
- 公開サイト/検索で2026年10月28日14:00 NZDTのOCR公表予定を確認できるが、[Run #39368889133](https://github.com/yuki746289/product_chat_record/actions/runs/39368889133)でRBNZの予定・OCRの2ページともHTTP403。
- 今回はRBNZの自動取得もSchema検証もPASSしていない。**`NZ_RBNZ_RATE`は未検証のまま**。アクセス制限の迂回を行わない。

## 53指標カバレッジへの計上
- 前回：22/53（NZD4/6、EUR2/8）。
- 新たなグループ：`NZ_BUSINESS`、`EU_HICP`、`EU_GDP`の3件。
- **現在：限定実証25/53、未実証28/53。NZD5/6、EUR4/8。**
- あくまで各グループの一例で、1日単位の網羅性・正確な時刻の完全性・本番での自動取得/保存/画像化権限を意味しない。
- 使用する発表元の優先順位は一次発表元＞許諾済み二次カレンダーとする。ただし日時が不明なら架空の時間を付けない。

## 次工程
1. RBNZ公式の合法的な機械可読な予定フィードを再検討。無理な回避や架空のURLは禁止。
2. EurostatのICSを公式UIから取得可能か確認し、JSONの`allDay`イベントをどう表示するかの仕様を確定。
3. 民間調査の利用規約と再配布・画像化条件、無料取得元の継続性・取得頻度をソース別に監査。
4. 残り28グループと未確認の具体的な時刻を監査し、仕様確認`99_仕様確認.md`の未決事項を解消。
5. リリース判定が合格するまでWindows ChartRecorderのソースへ経済指標機能を統合しない。`release_0.1.0`は変更せず、`release_0.2.0`は完成時に`develop`から作る。
