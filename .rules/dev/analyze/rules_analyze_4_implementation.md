# 分析 手順4: Actions・分析処理作成

## 目的

承認済みの全体ワークフローに従い、Actions、分析コード、manifest、checkpoint、統合処理および通知処理を作成します。

## 出力

- `.github/workflows/`配下のworkflow
- 分析コード、テスト、設定例および実行説明
- `{analysis}_v{n}.{m}_4_implementation.md`

## 実装規則

- 承認済みjobを省略、統合、追加または方式変更してはいけません。
- workflowと分析コードはGit管理し、実行対象をコミットSHAへ固定して下さい。
- 依存関係、コンテナ、Actionおよび外部コードは可能な限り不変の版へ固定して下さい。
- 全jobへtimeout、最小権限、失敗時処理および安全なログ設定を行って下さい。
- shard manifest、checkpoint、結果統合、欠落・重複検証および再実行機能を実装して下さい。
- 通知失敗と分析失敗を分離して下さい。
- コードで解析困難な場合も独自にChatGPTへ切り替えず、承認済みworkflowに従って下さい。

## public/private分離

- private完結が必要な場合はprivate Actionsを使用して下さい。
- private管理・public実行では、public側を汎用workflowと安全な状態だけに限定します。
- privateリポジトリへの認証は、対象、権限および有効期間を最小化し、原則として読み取り専用にして下さい。
- privateコードは実行時だけ取得し、publicのログ、artifact、cacheまたは通知へ残してはいけません。
- publicへ出力するファイルは許可リスト方式で選び、出力前に一覧と内容を検査して下さい。
- privateリポジトリ名、ファイル名、分析条件、入力、結果、コマンド、stack traceおよびcommit messageをpublicへ出してはいけません。
- publicからprivate情報を推測できる可能性を排除できない場合は、作業を停止してprivate完結へ変更する承認を得て下さい。

## メール通知

- SMTP、メールAPI、組織内APIまたは検証済みの通知用Actionを使用できます。
- 宛先と認証情報はSecrets等で管理し、コード、ログおよびコマンドラインへ表示してはいけません。
- 外部Actionは提供元と権限を確認し、不変の参照へ固定して下さい。
- forkや未信頼の変更から通知用Secretsを利用させてはいけません。
- private分析のメール本文には、公開可否表で許可された情報だけを含めて下さい。

## ChatGPT分析のGit管理

- ChatGPTの会話だけを正本にしてはいけません。
- 入力、入力ハッシュ、確定プロンプト、条件、判断基準、中間結果、最終結果、除外、根拠、未確認事項および再開位置をGit側で管理して下さい。
- private分析のChatGPT関連成果物はprivateリポジトリだけへ保存して下さい。
