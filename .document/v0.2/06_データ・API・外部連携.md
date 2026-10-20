# データ・API・外部連携

## ECO-002 通貨別独自重要指標マスター（初期採用候補）
ユーザーと会話で承認されたS/A分類を初期マスターとして登録する。**実績ボラティリティから算出した定量ランキングではない**。

| 通貨 | S級（最重要） | A級（重要） |
|---|---|---|
| USD | FOMC政策金利・声明・FRB議長会見、雇用統計、CPI、PCE | 小売売上高、ISM製造業/サービス業、ADP雇用、GDP、JOLTS、PPI |
| JPY | 日銀金融政策決定会合、日銀総裁会見、全国CPI | 日銀短観、毎月勤労統計、GDP、東京都区部CPI |
| EUR | ECB政策金利・総裁会見、ユーロ圏HICP | ドイツCPI、ドイツPMI、ユーロ圏PMI、GDP、ZEW |
| GBP | BOE政策金利、BOE総裁発言、CPI | 雇用統計、GDP、小売売上高、PMI |
| AUD | RBA政策金利、豪雇用統計、豪CPI | 小売売上高、GDP、PMI、RBA総裁発言 |
| NZD | RBNZ政策金利、CPI、雇用統計 | GDP、小売売上高、企業景況感 |
| CAD | BOC政策金利、CPI、雇用統計 | GDP、小売売上高、BOC総裁発言 |

- 豪CPIは現在の発表体系（月次の主要指標等）に対応する。旧式の「四半期CPIのみ」固定は避ける。
- 発言イベントはFRB/日銀/ECB/BOE/RBA/RBNZ/BOCの**議長・総裁級**を対象とし、一般委員・担当者の演説は原則除外する。
- PMIやGDP等は速報/確報・各構成要素があるため、マスターでは「発表名の別名」と「対象となる派生系列」を明示する。具体的な正規化マッピングは実際のAPIイベント名を収集してから後続設計で確定する。
- `B`級は初版では保存・表示の対象外。未分類イベントを安易にB級や0件に分類しない。
- 前回・予想・結果は可能なものを付記する。欠損項目は任意。
- 同一日に対象7通貨の複数発表があっても、画像は**全通貨合算で1枚**。

## ECO-007 データ取得元・API
- 接続済みTradingView経済カレンダーの読み取り機能で7通貨分の `date/currency/title/importance/forecast/previous/actual` 等を取得できることはチャット上で試験確認済み。
- **ただしチャットのTradingView接続は、ChartRecorder Windows EXEからの継続的・無人APIアクセスを保証しない。** 公式APIの提供形態、サービス規約、再配布/画像化権限、認証、レート制限、費用を確定してから実装する。
- 他の適法な経済カレンダーAPIを用いる案も可。提供元が未決のまま非公式スクレイピングを既定にしない。
- Saxo FXの価格データと経済カレンダーデータを混同しない。カレンダーだけのエラーでSaxo OAuthを再認証させない。
- 推奨取得範囲: 当日JSTの00:00〜24:00を包含するUTC日付範囲を要求し、取り込み後JSTで厳密に絞り込む。
- 発表日時が空欄または未確定の場合の表示は未決（勝手な時計時刻を捏造しない）。

## データ項目（論理モデル）
| キー | 内容 |
|---|---|
| `source_event_id` | 配信元イベント識別子（ある場合） |
| `source` | 提供元・版 |
| `datetime_utc` | UTC発表日時 |
| `datetime_jst` | 表示用JST日時 |
| `currency` | 対象通貨 |
| `title_raw` | 元のイベント名 |
| `event_key` | 正規化済イベントコード |
| `group_key` | 同系統集約の識別子 |
| `priority` | S / A |
| `previous`, `forecast`, `actual` | 提供される場合の数値/文字列 |
| `unit`, `period` | 単位・対象月/四半期 |
| `fetched_at` | 取得時刻（鮮度表示） |

DB・テーブルは初版で必須としない。マスターのファイル形式(JSON/YAML等)、具体的なAPI URI・認証・値の単位は後続設計で確定。秘密情報はGitHubに保存しない。

## ECO-011 判定ロジックの固定（2026-10-15）
- `11_重要指標判定マスター.yaml`に独自S/Aを宣言し、配信元のimportanceは参考値としてのみ保存する。
- 照合順序は **通貨→対象国（EUとDEを区別）→イベント名のNFKC/小文字/余白正規化→`aliases_exact`との完全一致→S/A**。同一時刻・同一IDの構成指標は1見出しに集約し、個々の数値は失わない。
- 未登録名は推測でS/Aと判定せず**REVIEW**に記録する。登録済みaliasの競合はエラーとする。
- 総裁/議長発言は認識可能な別名で明示的に許可した場合のみ自動選別する。人事や提供元名変更時はYAMLの版を上げて対応する。
- 公式一次情報は主として実績値の正本に使用し、事前予想・カレンダー予定時刻は利用権を確認した提供元を使う。**公式データだけですべての市場予想が得られるとは仮定しない**。
- YAMLの英語別名は初期候補。**すべてのデータ提供元・イベント名について照合試験を実施済みではない**。対象外と判定される未知名を記録し、実装前にマッピングを検証する。

## ECO-012 取得・正規化・出力契約（追加）
- [12_経済指標取得・正規化・出力契約.md](12_経済指標取得・正規化・出力契約.md) に取得条件とデータ変換を定義。
- 全行`events[]`、S/A集約`display_groups[]`、未登録`review_record_ids[]`を同じJSONで管理し、[13_共通出力_schema.json](13_共通出力_schema.json)に従う。
- 一次情報実績の検証とカレンダー日程/市場予想の提供元を分離し、TradingViewの対話型接続をEXEの無人取得に転用しない。
- 正式API契約・保存権・認証・APIレート制限は**未決事項**。既存のS/A YAMLは変更しない。

## ECO-013 費用0円の取得元制約（2026-10-15）
- **追加の経済指標データ取得費用は0円/月**。有料購読、無料体験のみ、一定期間後の課金は採用禁止。
- 予定カレンダーは、利用許諾が確認できた各国の統計局・中央銀行の無料日程表/公式APIを個別に統合する方式とする（[16_無料取得元・費用制約.md](16_無料取得元・費用制約.md)）。
- Trading Economics等の有料APIは採用候補から除外する。TradingView MCPは対話による仕様試験に限定し、無人API代替としては使わない。
- 一次情報だけで不足する市場予想（forecast）は`null`。全7通貨の完全カバレッジが実証されるまでは、部分取得/網羅性未確認を明示する。
- サービス規約、継続的な自動取得、ローカル保存・画像化に関する利用条件の確認はソースごとに必要。URLの公開は利用許諾を意味しない。

## ECO-014 無料公式カレンダーの照合事例
- 2026-10-28のAUD CPI・RBNZ OCR・BoC政策金利を各機関の公式予定から確認した。
- 公式原題と重要度YAMLの対応は `17_公式取得元クロスウォーク_検証用.yaml`。これは3件の試験入力専用で、一般的な本番照合として使用しない。
- 共通JSON化した3件は `18_公式日程_正規化例_20261028.json`。8地域中3地域の部分取得につき `fetch_status=PARTIAL`、`coverage_status=INCOMPLETE`、`license_status=PENDING`。
- 各国日程とタイムゾーンの確認事項は `19_無料公式カレンダー実地検証_20261015.md`。
- 一次情報の予定確認と、HTTP自動収集の許諾・網羅性・実績値自動照合は別工程とする。

## ECO-019 ONS公開Release Search API・Destatisの限定的な実証
- ONS公式API `https://api.beta.ons.gov.uk/v1/search/releases`の応答は`releases[]`配列であり、原タイトル`description.title`とUTC指定を含む`description.release_date`、`uri`を確認。未来のCPI/雇用/GDP/小売を提供元固有のタイトルで照合し、S/AとSchema検証PASS（各1件）。
- 「time series」等の派生リリースは統計指標の二重カウントを起こし得るため、元タイトルとURIに基づく重複排除を後続設計で検証する。検索結果の件数は発表イベントの件数ではない。
- Destatis公式週間予定のCPI確報は、元イベントの日付を確認できたが正確な発表時刻は未検証。共通JSONはUNKNOWNを維持する。
- `24_無料公式カレンダーONS_Destatis_取得監査_20261016.md`参照。無料であることと、持続的な自動収集/出典表示/画像化の適用条件の最終判定は分けて管理する。

## ECO-020 FRED補助カレンダーの取り扱い（2026-10-19）
- FRED/セントルイス連銀のWeb公開日程は、米BLS/BEA/Censusの一次公表元ではない。公的二次取得先として利用候補に加え、一次確認ができていない日は`source_tier=SECONDARY`相当の品質注記を付ける。
- 米6系列について`25_FRED_6指標_照合マスター_検証用.yaml`でrelease_id、元名称、確認済み日程を固定。元重要度マスター11は変えない。
- 検証Run #39204290773 は6件HTTP200・日付時刻原文隣接確認・America/Chicagoの夏時間変換・JsonSchema検証PASS。実績・予想値、正式API鍵、保存・画像化権、一次公表元との日時一致は未確認。
- FREDの利用条件は第三者データの権利・クレジット表記・用途を区別する。条件が満たせない場合は本番の補助取得元にも採用しない。
- 公式Web掲載時刻の精度と、本来の発表機関による正式公表時刻の検証状態を混同しない。

## ECO-021 米国の一次公表予定・BEA ICS対応（2026-10-19）
- FREDの米6系列はBLS/BEA/Census Bureauが掲載する一次予定日時との整合性を監査する。FREDは**二次取得先**であり一次公表機関ではない。
- BEA公式ICS `https://www.bea.gov/news/schedule/ics/online-calendar-subscription.ics` はHTTP200でVEVENT 166件を取得、2026-10-29のGDP/PCE2件はUIDとUTC時刻を持つ。固定S/A（US_GDP=A、US_PCE=S）と共通JSON Schemaへ変換PASS（Run #39227699077）。
- BLS3系列の予定日時はWebで一次日程と照合済み、ただしGitHub ActionsからのBLS HTTP403は継続。Censusの小売日時もWeb上では一致するが、本試験のHTMLから日時を抽出できていない。
- 米国各源の実績/市場予想値・許諾条件の確認は未完了。欠測値はnull、取得不完全時はINCOMPLETEを維持。詳細は`27_米国6指標_一次情報日時照合_20261019.md`。

## ECO-022 Stats NZ公式iCalendarのデータ取得（2026-10-19）
- 発表元: Stats NZ。公開ICS実URL: `https://www.stats.govt.nz/release-calendar/calendar-export/`。当該サイトの一般公開JavaScriptに記述された公式リンクであり、非公開APIや推測URLではない。
- GitHub Actions Run #39250285686 でHTTP200/`text/calendar`を取得、VEVENT 140件を解析。Run #39250626014 ではNZ CPI（S）、雇用統計（S）、小売（A）、GDP（A）の4系列を元ICS UID/DTSTARTからJSTへ変換し、共通JSON Schema PASS。
- 既存YAMLの判定値を変更せず、原題（Summary）に対する4件限定クロスウォーク`28_StatsNZ_4指標_公式ICS照合.yaml`を追加した。Stats NZの`Employment indicators`と`Labour market statistics`は名称も定義も異なるため、全て同じ経済指標と推測して自動統合しない。
- 取得時刻は`DTSTART`のタイムゾーンを使い`Asia/Tokyo`へ変換。2026年10月～12月の対象4件はいずれもJST 06:45。
- Stats NZは一般的に自作コンテンツをCC BY 4.0で提供（https://www.stats.govt.nz/about-us/copyright/）。出典表示を必須とし、例外の第三者著作物・運用アクセス条件は後続で確認。`license_status=PENDING`を維持。
- 対象8地域のうちNZだけを検査した部分例なので`coverage_status=INCOMPLETE`。`forecast`/`actual`/`previous`は取得していないため`null`。運用アプリは未実装。

## ECO-023/024 ANZ・Eurostatの公式予定（2026-10-20）
- ANZ公式の2026発表予定PDFを無認証HTTPで取得し、NZ_BUSINESS/Aに照合・Schema PASS。PDFは2025年12月15日時点の「subject to change」付き日程で、10月29日13:00 NZDT＝09:00 JST。正本IDはPDFに存在しないため発表元UIDを捏造しない。
- Eurostat公式カレンダーHTMLに記述された`/eurostat/o/calendars/eventsJson`へ、実際のFullCalendarパラメータでアクセス。全体105件・Euro indicators25件の公式表示用JSONを取得。EU_HICP（2発表）、EU_GDP（1発表）を固定S/AとSchemaで検証。
- Eurostat JSONは`start`日時があるが検証対象の`allDay=true`を尊重し、`time_precision=UNKNOWN`、`date_utc/date_jst=null`とする。値から勝手に発表時刻を決めない。
- 試験クロスウォークは`30_ANZ_Eurostat_指標対応_検証用.yaml`。実証経緯は`31_ANZ_Eurostat_公式無料取得監査_20261020.md`。
- どちらも利用条件/自動収集・保存・PNG化・出典表示について最終確認未了。`license_status=PENDING`、`coverage_status=INCOMPLETE`。正規化データに市場予想値・結果値を補完しない。
