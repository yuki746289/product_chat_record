# ChartRecorder v0.2.0 経済指標追加版 — 開発・リリース判定表
作成日: 2026-10-16 JST
作業先: develop
初回安定版: release_0.1.0（更新禁止）
次期リリース: release_0.2.0（**完成時にdevelopのSHAから生成**、生成後は一切直接編集しない）
現時点: 開発計画・無料公式ソース検証中。**v0.2.0リリースブランチ・本番EXEは未作成**。

## 目的
Windows ChartRecorderに、対象7通貨（USD/JPY/EUR/GBP/AUD/NZD/CAD）の独自S/A級重要経済指標をJST当日の一覧として1枚のPNGへ表示する機能を追加する。追加のデータ取得費用は0円。

## 変更しない範囲
- 既存SaxoのOAuth/refresh、13通貨ペア、1M/5M/15M/1H/4H/8H/1D/1W/1Mn、RCI9/14/26、EMA20/30/40、5分生成、10スロット保持。
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
