# ChartRecorder 引継ぎ（2026-10-14）— 二重起動ダイアログ実装・main反映済み／Windows実機確認待ち

作成日：2026-10-14 JST
対象リポジトリ：`yuki746289/product_chat_record`（**public**）
正本ブランチ：`main`
最終確認時のmain HEAD：`670eefa36029fc5809d05e69be5a47b39adb3bf2`
引継ぎ時の状態：**PR #9 マージ済み、Windows Actions 61/61 PASS、EXEビルドPASS。ユーザーPCへの新EXE適用・UI実機確認は未完了。**

## 1. このスレッドの直近の依頼と最終結論

ユーザーはWindows常駐のChartRecorderについて、タスクトレイにアイコンが見えず、次に起動すると次の例外が出る問題を相談している。

```text
RuntimeError: ChartRecorder is already running for this Windows session
```

その後の要望は、**二重起動をエラーとして表示せず、確認ダイアログを表示して既存アプリをそのまま使うか、既存を終了して新しいアプリを起動するか選択できるようにする**というもの。

2026-10-14に**確認ダイアログと協調的再起動の実装をPR #9でmainへマージ済み**。Windows側の新しいEXEはユーザーがpullして再ビルドする必要がある。

- PR #9：[二重起動時の確認ダイアログ・安全な再起動](https://github.com/yuki746289/product_chat_record/pull/9) — **merged**
- マージコミット：`670eefa36029fc5809d05e69be5a47b39adb3bf2`
- 検証Run：[Windows Actions 38513069001](https://github.com/yuki746289/product_chat_record/actions/runs/38513069001) — **success**
- Windowsテスト：**61 passed in 14.61s**
- PyInstaller Windows EXE：ビルドPASS（`ChartRecorder.exe` 約63,855,962 bytes、Windows Actions上）
- 先行Run [38512854600](https://github.com/yuki746289/product_chat_record/actions/runs/38512854600) は **1 failed / 60 passed**。失敗は従来のテストスタブに `instance_guard` 属性が存在しないため（実機不具合ではない）。`getattr(..., None)` に修正した後、上記最新Runで **61/61 PASS**。先行失敗を最終状態と混同しない。
- 使い捨てpushトリガーは削除済み。`.github/workflows/tray_windows_check_20261014.yml` は`workflow_dispatch`のみ（**手動専用**）。GitHub Actionsの定期実行は有効にしていない。

## 2. 最新機能：二重起動時の確認ダイアログ（PR #9）

変更・追加ファイル：
- `src/windows_single_instance.py`：新規。Windowsの名前付きミューテックスと名前付きイベントによる二重起動処理
- `src/tray_app.py`：ミューテックス直接判定→`WindowsSingleInstance` に置換、古いアプリからの終了要求を受け付けるスレッドを追加
- `tests/test_windows_single_instance_20261014.py`：追加。初回起動・キャンセル・協調停止・旧版フォールバック・タイムアウト等を検証
- `README.md`：利用案内更新

UX仕様：
1. 先行アプリがない：従来どおり起動し、タスクトレイアイコンを表示。
2. 先行アプリがある：Windows標準の「ChartRecorderは既に起動しています。既存のChartRecorderを終了して、新しく起動しますか？」の**はい／いいえ**ダイアログを表示。
3. **いいえ**：後から起動しようとした側は例外・トレースバックを出さず、正常に終了。既存アプリは継続。
4. **はい**：協調停止用の名前付きイベントで既存アプリへ停止要求。先行プロセスのミューテックスの消滅を待ってから、新側を起動する（最大約20秒）。
5. **先行アプリが旧バージョン**：新しい停止イベントに未対応のため**強制終了せず**、手動終了するようメッセージ表示。安全のため新側は起動しない。
6. 停止要求が失敗／20秒以内に終了しない：メッセージ表示し、新側を起動しない。
7. **Saxo OAuth refresh tokenの同時更新・二重画像取得を防ぐ単一起動制約は維持する**。

内部識別子：
- 名前付きmutex：`Local\ChartRecorderSaxoTray`（旧版とも共通）
- 名前付き停止イベント：`Local\ChartRecorderSaxoTrayStopV1`
- 先行アプリが旧版の場合、このイベントはないため初回切替は手動終了が必要。

**重要：** Windows Actionsは、Windows上でWin32 backendのimport、テスト用モックによる動作、PyInstallerビルドを確認しただけ。ユーザーPCでダイアログが実際に表示されること、クリックで先行プロセスが停止して再起動すること、Windows通知領域との統合は**未検証**。確認前に実機PASSと断言しない。

## 3. その前のタスクトレイ非表示問題（PR #8）

原因：`pystray.Icon.run(setup=...)` に独自setup callbackを渡すと、既定の `icon.visible=True` が実行されない。以前のコードはバックグラウンドのpollingだけ開始してアイコンを表示しない状態になっていた。

- PR #8：[トレイアイコン表示修正](https://github.com/yuki746289/product_chat_record/pull/8) — **merged**
- マージSHA：`13df262bc0137dc5823e3ff3b5206d1745e425fb`
- Windows Actions：[38502740666](https://github.com/yuki746289/product_chat_record/actions/runs/38502740666) — **54 passed、Windows EXE build PASS**
- `src/tray_app.py` の `_on_tray_ready` が、**ワーカースレッド開始前に `icon.visible = True` を設定**し、失敗時には停止・ログ記録する。
- 正常起動時のログメッセージ：
  `Tray icon initialized and visible; mode=saxo_local`

ユーザーが見た`ChartRecorder is already running`は、アイコンを表示できなかった**先行常駐プロセス**や、別途起動していた `python -m src.tray_app` が保持したmutexによる可能性がある。Windowsで以前PID `32112` の `ChartRecorder` が動作していることを確認し、`Stop-Process -Force` で終了できた記録あり。旧プロセスが残れば後から起動するEXEは起動前に拒否される。

## 4. 5分間隔・最大10フォルダ（PR #7、実装済み）

- PR #7：[5分ごとのSaxo画像取得＋最大10日時フォルダ保持](https://github.com/yuki746289/product_chat_record/pull/7) — **merged**
- Windowsではない合成検証：[Actions 38498278232](https://github.com/yuki746289/product_chat_record/actions/runs/38498278232) — **50テストPASS＋合成13PNG生成**
- `setting.yaml`では各セクション内で「:」を縦に揃え、設定ごとに説明コメントを付与した。設定正本：

```yaml
local_monitor:
  mode                   : saxo_local  # Windows常駐の取得方式（Saxo）
  poll_seconds           : 60          # 状態確認間隔（秒）
  chart_interval_minutes : 5           # PNGを新規生成する間隔（分）
  max_folders            : 10          # 最新日時フォルダを最大10個保持
```

- 旧`retention_hours`・`min_folders`は廃止。`local_monitor`の旧キーが残っていれば明示エラーになる。`output.retention_hours`も削除済み。
- 画像出力：`C:\TradingViewCharts\YYYYMMDD_HHmm\cross_non_jpy\<pair>.png` または `cross_jpy`。カテゴリ・通貨ペア13（クロス円以外7、クロス円6）を保持。
- 画像は9時間足、EMA20/30/40、RCI9/14/26、2列。Saxo SIMのFxSpot OHLC（Bid既定）。
- 5分ごとに同期的・順次取得。**13ペア×9時間足の実取得／描画が毎回5分以内に収まるかはWindows/Saxo SIM実機で未検証**。長引けばスロットが飛ぶ場合がある。
- 最新10日時フォルダを超えたときに11個目以降を削除。古い画像を残したい場合は別場所にバックアップしてから初回新版を起動。
- 認証期限切れでも常駐アプリは起動できるが、画像は生成不可。トレイから再ログインし、成功後に自動でキャプチャを再開する。

## 5. Saxo OAuthとEXEの運用

- SAXO OAuth：Windows資格情報マネージャー（`keyring`）にApp Key、App Secret、Access/Refresh Tokenを保存。**GitHubに秘密情報をcommitしない**。
- ローカル設定ファイル：リポジトリルートの `setting.yaml`。EXEに埋め込まない。`dist\ChartRecorder.exe`はデフォルトで一つ上の`setting.yaml`を読む。
- ビルド：`scripts\build_windows.bat`。Python 3.12、PyInstaller `--onefile --windowed`。Windows版のEXEをローカルWindowsで再ビルドする。
- 使用ユーザーPC：`C:\Users\yuki_\OneDrive\Documents\github\product_chat_record`
- 画像／ログ：`C:\TradingViewCharts`、`C:\TradingViewCharts\.chart_recorder.log`
- Git Bashで /F 等を `taskkill.exe` に渡すとMSYSパス変換問題が発生するため、PowerShellを経由してプロセスを確認・終了できる。
- 従来発生したエラー：
  - `PermissionError: [WinError 5] ... dist\ChartRecorder.exe`：旧EXEが起動中で上書きできない可能性が高い。
  - `Saxo refresh token expired; browser login required`：**画像取得**には再ログインが必要だが、**アプリ起動／トレイ表示**には再ログイン不要。
  - `ValueError: retention_hours must be 8`：旧コードと新しいYAMLの不整合。最新版では旧チェックを削除済み。

## 6. 次スレッドで優先する作業（実機確認）

**ユーザーとの確認往復を減らす方針。GitHubの成功済みRunを再実行しない。** 最初に最新`main`、このMD、PR #9、Windows Actions #38513069001を読み、テスト結果を再確認。

ユーザーPCでの最初の適用手順：

```bash
cd /c/Users/yuki_/OneDrive/Documents/github/product_chat_record
git status
git switch main
git pull --ff-only origin main
```

**新旧切替の最初の1回のみ**：現在動作中の旧EXEは協調停止イベントに非対応。タスクトレイから終了できなければ、次のコマンドで**ChartRecorder.exeだけ**終了。Python版が別に常駐している可能性もあるため、その場合はプロセスを区別して終了する。無関係なPythonプロセスを一括終了しない。

```bash
powershell.exe -NoProfile -Command "Get-Process ChartRecorder -ErrorAction SilentlyContinue | Stop-Process -Force"
cmd.exe /c 'scripts\build_windows.bat'
./dist/ChartRecorder.exe
```

1. 通知領域（`^`の隠しアイコン含む）にChartRecorderアイコンが表示されるか。
2. 認証期限切れの状態でもアイコン表示・「Saxoに再ログイン【必要】」メニューが有効か（**ログインそのものは不要**）。
3. 同じEXEをもう一度起動したときWindowsの**「はい／いいえ」ダイアログ**が表示されるか。
4. **いいえ**：既存アプリ継続／トレースバックなし。
5. **はい**：既存の新版アプリが停止し、新版が起動するか（トレイアイコン、PID、ログで確認）。
6. `tail -n 50 /c/TradingViewCharts/.chart_recorder.log` でアイコン起動ログと再起動要求ログを確認。
7. Saxo再ログイン後の5分間隔撮影・最大10フォルダは別の稼働確認として扱い、**アイコンの再起動問題と混同しない**。
8. もし不具合が再発した場合は、実際のWindowsのプロセス・ログ・表示状態を根拠に絞り込む。根拠なく何度も再ビルド・再ログインさせない。必要ならpublic Windows Actionsを明示的に許された範囲で再使用。

## 7. 変更制約

- Saxoの実OAuth秘密情報・認証コード・トークンをGitHubやログへ公開しない。
- 13ペア、9時間足、EMA/RCI、5分キャプチャ、最新10フォルダ保持はユーザー承認済みの固定仕様。理由なく変更しない。
- Windowsミューテックスによる単一インスタンス保護は維持し、Saxoリフレッシュトークンを同時更新する複数プロセスを作らない。
- Actionsは**public**の `product_chat_record`で実行可能だが、Saxo LIVEデータや資格情報を利用しない。ワークフローの定期起動は無効のまま。
- 実行済み：PR #7/#8/#9のmainマージ、Windows mockテスト61/61 PASS、EXEビルドPASS。
- 未実行／未証明：ユーザーWindowsでの確認ダイアログ実表示・切替、トレイアイコン、Saxo実機で5分周期の連続動作。今後、未検証をPASSと宣言しない。

### 最終状態

`PR9_MERGED_MAIN_670eefa; WIN_ACTION_38513069001_SUCCESS_61_OF_61; WINDOWS_EXE_BUILD_PASS; CI_MANUAL_ONLY; LOCAL_WINDOWS_TRAY_AND_RESTART_UI_NOT_YET_VERIFIED; SAXO_LOGIN_NOT_REQUIRED_FOR_TRAY_UI`.
