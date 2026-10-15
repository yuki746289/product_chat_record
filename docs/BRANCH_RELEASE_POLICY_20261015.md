# ChartRecorder ブランチ・リリース運用ルール

作成日: 2026-10-15 JST
対象: `yuki746289/product_chat_record`
現在のリリースソース基準: `main` SHA `4c65d32bb8d4fa1ba6bcf69451bffd390f0ec858`, `VERSION=0.1.0`
初回リリースブランチ: `release_0.1.0`

## 基本的に維持するブランチ

| ブランチ | 役割 | 更新可否 |
|---|---|---|
| `main` | 安定版ソース・リリース済み変更の統合先 | 検証済みリリースのみ取り込む |
| `develop` | 新規機能、仕様書、検証、バグ修正を継続的に統合する | 変更可能 |
| `release_{n}.{m}.{l}` | 完了時点の固定リリーススナップショット | **作成後の直接編集、commit、push、force-push、リベース、マージを禁止** |

- 原則としてfeature/fix/docs/researchなどの常設作業ブランチを増やさない。短期的な作業ブランチが必要な場合は、`develop`から作ってPRで取り込み、統合後は削除する。
- 既存の未統合コミットがあるブランチは、内容を失わず、保全策（archiveタグ/別保管場所）を確認してから整理する。
- すべてのリリースブランチは`release_0.1.0`など`release_{n}.{m}.{l}`形式とし、`VERSION`との整合性を検査する。
- 初回`release_0.1.0`は**2026-10-15にmainの上記SHAから作成**した。既存のWindows EXEの実物ビルドIDと一致することは、ユーザPCの`installed-version.txt`等で別途照合が必要。

## リリース作成フロー

1. 日常開発: `develop`で新機能と修正を実施する。
2. 仕様・実装テストとWindows実機の受入を済ませ、リリース対象のコミットを確定する。
3. `develop`の対象SHAから新しい`release_{n}.{m}.{l}`ブランチを**同じSHAを指す参照**として作成する（ファイルの再コピー・個別転記は禁止）。
4. 作成時に`release`、`develop`、`VERSION`の整合性と差分を検証する。
5. **リリースブランチに対する直接変更を一切行わない**。緊急修正も`develop`で行い、修正後に別バージョン（例`release_0.1.1`）を作る。
6. `main`にはテスト済みリリースを取り込む。未完成の仕様や取得API実験だけで`main`/リリースを更新しない。

## リリースの編集禁止をGitHub上で技術的に担保する

- GitHubのRepository Settings > Rules > Rulesets で`release_*`を対象とするactiveなbranch rulesetを作り、**Restrict updates**と**Restrict deletions**を有効化し、バイパスを原則認めない。あるいはBranch protection rulesで`release_*`をロックする。
- **Restrict creationsは選ばない**（新しいリリースブランチの生成まで妨げるため）。
- ルール未設定の場合、文書上の禁止だけではGitHubのpushを技術的に拒否できない。
- 適用後、ダミーの更新はリリースブランチで実行せず、Rulesetsの対象評価とGitHub画面で設定を確認する。

## ソースと実行EXEの区別

このリポジトリのcommit SHAは`ChartRecorder.exe`のビルドソースの同一性を示す。起動中のEXEがこのSHAからビルドされたと断定するには、インストールディレクトリの`installed-version.txt`等と対照する必要がある。Saxoのトークン等はリポジトリへ記録しない。

## 現時点の経済指標機能

追加取得費用0円、公式無料情報の複数統合、共通JSONとYAMLのS/A判定仕様は`develop`内の`.document/v0.2/`を正本とする。`release_0.1.0`へ含めない。
