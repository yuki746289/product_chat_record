## 開発ルール補足

  - Pine 追加ルール
    - 対象ファイル : `*.pine`
    - 参照タイミング : rules_{dev}_8_code.md, rules_{dev}_9_code_confirm.md
    - Pine を作成または修正する前は、必ず `pine/.rules/pine_checklist.md` を確認し、`:=`、分岐内タプル代入、`request.*()` 件数、`external elements` を事前チェックすること。
    - Pine を作成または修正する前は、`pine/.rules/pine_checklist_log.md` にチェック結果を毎回記録すること。
    
  - app 全般ルール
    - 対象ファイル : `*.*`
    - 参照タイミング : rules_app_8_code.md, rules_app_9_code_confirm.md
    - 参照しているファイルやurl、タグのリンクが正しいことを確認すること

  - app 追加ルール
    - 対象ファイル : `*.html`, `*.css`, `*.js`
    - 参照タイミング : rules_app_8_code.md, rules_app_9_code_confirm.md
    - idやdomの参照が正しいことを確認すること。
    - レイアウトの崩れが無いことを確認すること。
