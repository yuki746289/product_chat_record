# ChartRecorder v0.2.0 経済指標追加版 — 開発・リリース判定表
作成日: 2026-10-16 JST
作業先: develop
初回安定版: release_0.1.0（更新禁止）
次期リリース: release_0.2.0（**完成時にdevelopのSHAから生成**、生成後は一切直接編集しない）
現時点: 開発計画・無料公式ソース検証中。**v0.2.0リリースブランチ・本番EXEは未作成**。

## 目的
Windows ChartRecorderに、対象7通貨（USD/JPY/EUR/GBP/AUD/NZD/CAD）の独自S/A級重要経済指標をJST当日の一覧として1枚のPNGへ表示する機能を追加する。追加のデータ取得費用は0円。

## 変更しない範囲
- 既存SaxoのOAuth/refresh、13通貨ペア、5分生成、10スロット保持を維持。チャートの時間足・RCI・EMA・列数は初期設定（9時間足/RCI9・14・26/EMA20・30・40/2列）を保ちながら設定可変化を別途設計・検証する。
- Windowsトレイ・単一起動・インストール先選択・既存アップデート経路。
- release_0.1.0、mainの現行コード。
- .document/v0.2/11_重要指標判定マスター.yamlの53グループS/A優先度を、その場の重要度評価で変更しない。

## スコープ
1. 各公式サイトの無料取得経路をプロバイダー単位で決定。月額0円、合法的な無人取得・引用/保存/PNG化条件を確認。
2. 公表予定（時刻不明含む）をJSTへ正規化。海外の夏時間に対応。
3. データ取得の成否を個別に記録し、未取得/配信先欠落を「本日の重要指標なし」と誤表示しない。
4. 公表元の固有名称を、元名称・国・通貨・発表種別を保存しつつYAMLに安全に対応付ける。未知はREVIEW。
5. 読める値のみprevious/forecast/actualを付ける。公式公表値の確認前にactualを確定扱いしない。無償で取得できない市場予想はnull。
6. .document/v0.2/13_共通出力_schema.jsonへの適合、S/Aグループ化、日次JSONファイル生成。
7. 画像出力をchart_image/daily_events/economic_events_YYYYMMDD.pngに分離。日本語可読性と時刻/欠測/出典/取得時刻を確認。
8. Windows起動時の自動表示・日次1枚の再利用、破損/取得失敗回復。既存のタイムスタンプフォルダの削除ロジックと非干渉。
9. pytestの単体・境界・統合試験＋Windows Actionsテスト＋Windows実機での目視承認。
10. 開発時VERSIONは0.1.0を維持。リリース直前にdevelop上で0.2.0へ更新、Windowsビルドと更新スクリプトを検証、完成SHAでrelease_0.2.0を作成。その後は凍結。

## 現状の公式・無料取得手段の確認（2026-10-16）
| 公表元 | 予定データの候補 | 確認済み範囲 | HTTP実取得 | 利用条件 |
|---|---|---|---|---|
| 米BLS | https://www.bls.gov/schedule/news_release/bls.ics | 官公庁公式にICSサブスク形式を明記 | 本環境では取得成功未確認（calendar形式のビュー非対応） | 保存・画像化を精査 |
| カナダ統計局 | https://www150.statcan.gc.ca/n1/dai-quo/ssi/homepage/schedule-key_indicators-eng.json | 公式API文書にGET/無認証と記載 | 本環境では実JSON取得未確認 | Open Licenceの出典表示条件を確認済。個別データの第三者著作物除外に注意 |
| Eurostat | https://ec.europa.eu/eurostat/web/main/news/euro-indicators/release-calendar | ICS購読が公式に存在。時刻はLuxembourg | ICS実URLと自動取得未確認 | 一般再利用条件は出典表示。例外コンテンツを別途確認 |
| 豪ABS | https://www.abs.gov.au/release-calendar/future-releases-calendar | カレンダー公式HTMLで予定日時を確認 | HTTP/ICSの機械パーサ未検証 | 再利用条件を精査 |
| 中銀・その他統計局 | .document/v0.2/16_無料取得元・費用制約.md | 公式予定ページの所在を確認 | HTTPパーサ未検証 | ソース別に調査 |

参照:
- BLS: https://www.bls.gov/help/hlpiCAL.htm
- StatCan JSON: https://www.statcan.gc.ca/en/developers/schedule-key_indicators-eng-json
- StatCan Open Licence: https://www.statcan.gc.ca/en/terms-conditions/open-licence-faq
- Eurostat ICS: https://ec.europa.eu/eurostat/en/web/products-eurostat-news/w/wdn-20260105-1
- Eurostat reuse: https://ec.europa.eu/eurostat/en/about-us/communicating-disseminating-statistics

## 受入・停止条件
| ID | リリース判定の必須条件 | 現在 |
|---|---|---|
| REL-020-01 | 無料かつ利用条件を満たす本番取得元の選定 | NG：全7通貨未確認 |
| REL-020-02 | 7通貨8地域のS/A重要指標に対する取得範囲・明示的未網羅の確認 | NG |
| REL-020-03 | 固定YAMLと実API原名称の対応・未知イベントの監査 | NG |
| REL-020-04 | 正規化JSONの仕様・欠損・UTC/JST境界・夏時間テスト | 一部PASS、実データ未網羅 |
| REL-020-05 | PNG1日1枚・可読性・Windows既定ビューア・破損再生成 | NG：未実装 |
| REL-020-06 | SaxoとWindows既存全回帰、ビルド、インストール、手動実機確認 | NG：未実施 |
| REL-020-07 | 仕様確認の全項目PASS、コード規約照合 | NG：.document/v0.2/99_仕様確認.mdは不合格 |
| REL-020-08 | developのVERSION=0.2.0、commit固定、release_0.2.0の不変性 | NG：未作成 |

**すべてがPASSになるまでrelease_0.2.0を作成せず、mainへ未完成の開発版をマージしない。**

## ブランチ運用
main / develop / release_0.1.0のみ維持し、例外的な検証ブランチが必要な場合は統合後に削除する。追加ソースのドキュメント・コード変更は原則developで行う。release_*へのupdate_file、push、rebase、mergeなどは禁止（Rulesetによる技術的保護はGitHub設定で別途要実施）。

## 直近の作業順序
- 無料取得元のHTTPレスポンス実検証 → ソース固有アダプター設計 → 別名照合品質監査。
- 項目・UI・取得失敗時動作の未確定事項を解消し、仕様確認を更新。
- appルールとコーディング規約に沿って実装・テスト。成功済み処理をむやみに再実行しない。

## 2026-10-16 無料公式データ取得・JSON正規化検証の進捗
- [取得・エラーの全6件監査](../.document/v0.2/20_無料公式HTTP取得監査_20261016.md) : GitHub Actions Run #38850832684。ABS/BoC/Eurostat HTMLはHTTP200、BLS ICSとHTMLは403、カナダ統計局JSONはtimeout。
- [HTML本文から実際の予定抽出](https://github.com/yuki746289/product_chat_record/actions/runs/38851008943) : ABSのCPIとBoCの10月28日政策金利の日付・時刻をHTTPから確認。Eurostatは個別予定の取得未達。
- [2機関の共通JSONまでの実証](../.document/v0.2/21_無料公式取得JSON正規化実証_20261016.md) : GitHub Actions Run #38851280954、SUCCESS。実HTTPから取得し、JST変換、重要度マスターS級照合、jsonschemaの型・日時と参照を検証。取得範囲は2件のみ、INCOMPLETE明示。
- REL-020-04: **限定PASS**（2イベントに対する実HTTP・JST・既存JSON Schema）。全7通貨・全指標の実データ取得、日界/再試行全網羅は未完了。
- REL-020-01〜03、05〜08: **NG継続**。仕様確認は不合格のままで、リリース許可ではない。
- リリースブランチは増やさない。`release_0.1.0`は書き換えず、`release_0.2.0`は全受入条件完了後のdevelopから作成する。

## 2026-10-16 公式無料カレンダー追加試験（ECO-017）
- [監査報告](../.document/v0.2/22_無料公式カレンダー追加取得監査_20261016.md)に11公式URLのHTTP結果（9件200、RBNZ403、DE404）、カナダ統計局JSON全2,881件の解析、S級候補4件の日時精度付きJSON検証を記録。
- [Run #38856748747](https://github.com/yuki746289/product_chat_record/actions/runs/38856748747): 11 URLの応答形式確認。
- [Run #38856912117](https://github.com/yuki746289/product_chat_record/actions/runs/38856912117): StatCan JSONで今後の25日程、CPI等10件を検出。時刻未定をUNKNOWNにしてS級JSONをSchema検証。
- [Run #38857096016](https://github.com/yuki746289/product_chat_record/actions/runs/38857096016): BOJ/BoE/ECB/FOMCの4件を独自Sマスターへ照合しSchema検証。ONS CPIは今回の抽出条件では失敗。
- 7通貨中6通貨で各1件以上の限定的な公式情報→JSON変換が確認できた（うち会合日程と発表時刻を分離して検証すべき例あり）。NZDは依然未達。
- 本件は**取得元候補の調査結果**であり、7通貨53グループ全件網羅、権利確認、本体実装、PNG作成の合格ではない。REL-020-01/02/03/05/06/07/08はNGを維持。

## 2026-10-16 第2回の11ソースHTTP・実JSON検証と台帳
- [第2回HTTP監査](../.document/v0.2/22_無料公式カレンダー追加取得監査_20261016.md)：11取得元中9件がHTTP200。NZ中銀403、ドイツ指定URL404。StatCanの無認証JSON全2,881件取得成功。
- [StatCan検証 Run #38856912117](https://github.com/yuki746289/product_chat_record/actions/runs/38856912117)：10月16日～11月30日の公開予定25件を確認。公式date内の00:00:01等を発表時刻とせずUNKNOWNにしてCPI/Sの日付のみSchema検証PASS。
- [BOJ/BoE/ECB/FOMC試験 Run #38857096016](https://github.com/yuki746289/product_chat_record/actions/runs/38857096016)：5候補中4件のS級JSON照合PASS（内訳は時刻未定/会合日付のみの例を含む）。ONS CPIの自動抽出は未達。
- [53グループカバレッジ台帳](../.document/v0.2/23_重要指標53件_無料取得カバレッジ台帳_20261016.md)：**限定実証7グループ/53**、残り46グループは機械取得未検証。NZDは6グループ全て未実証。
- **全53グループの恒常無料自動取得を達成したわけではない**。REL-020-01〜08のリリース完了判定は変更しない。

## 2026-10-16 ONS/Destatis実証（ECO-019）
- [詳細報告](../.document/v0.2/24_無料公式カレンダーONS_Destatis_取得監査_20261016.md) に10候補のHTTP/JSON成否、ONS4系列のイベント日時変換、Destatis CPI日付のUNKNOWN保持を記録。
- [ONS公式API検証 #38866589454](https://github.com/yuki746289/product_chat_record/actions/runs/38866589454): GB_CPI (S)、GB_EMPLOYMENT (A)、GB_RETAIL (A)、GB_GDP (A) の4系列すべて共通JSON Schema PASS。
- [Destatis検証 #38866830724](https://github.com/yuki746289/product_chat_record/actions/runs/38866830724): DE_CPI (A) の日付のみのJSON Schema PASS。Eurostat ICSとNZDの自動日程取得は未達。
- [53グループ台帳](../.document/v0.2/23_重要指標53件_無料取得カバレッジ台帳_20261016.md): **限定実証12/53・未実証41/53**。本番での完全取得が保証されたわけではない。
- ソースごとの利用許諾、実機アプリ統合・既存チャート回帰が完了していないため、REL-020-01〜08のリリース判定は変更しない。

## 2026-10-19 FRED6指標の代替無料取得検証
- [公開カレンダーHTTP検証 #39204071618](https://github.com/yuki746289/product_chat_record/actions/runs/39204071618) — FREDの米雇用/CPI予定がGitHub ActionsからHTTP200で取得できることを確認。
- [米6系列の共通JSON実証 #39204290773](https://github.com/yuki746289/product_chat_record/actions/runs/39204290773) — 雇用統計、CPI、PPI、PCE、GDP、小売売上高の予定日時が、公開FREDカレンダー→America/Chicago→UTC/JST→独自S/A→JSON Schemaで6/6 PASS。
- [検証用FRED ID対応](../.document/v0.2/25_FRED_6指標_照合マスター_検証用.yaml)、[取得監査](../.document/v0.2/26_FRED6指標_無料公式カレンダー検証_20261019.md)。
- [53指標台帳](../.document/v0.2/23_重要指標53件_無料取得カバレッジ台帳_20261016.md)：**限定実証18/53（従来12＋二次集約6）、未実証35/53**。
- FREDは各統計の一次公表元ではなく、ソース間不一致時に一次機関を優先する。正式利用権と画像化の確認が済むまでは本番接続しない。
- NZD公式ICS、Eurostat公式ICS、米BLS一次時刻の独立照合等はNG継続。REL-020-01〜08のリリース停止条件は変更しない。
