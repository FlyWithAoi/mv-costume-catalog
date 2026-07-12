# screenshot-renamer

MV衣装カタログ用の、スクショ画像リネーム補助ツール（ローカル専用GUI）。

## 目的

画像加工CLIが読む以下のファイル名に、スクショを手作業でリネームするのが大変なので、
GUIで画像を選んで指定フォルダへ **コピー** しながら名前を揃えるためのツールです。

- `select.png`
- `front.png`
- `back.png`

元ファイルは移動・リネームしません（コピーのみ）。

## 起動方法

```powershell
cd L:\Studio\02_Projects\FlyWithAoi\mv-costume-catalog
python tools/screenshot-renamer/app.py
```

Python 標準ライブラリ（Tkinter）のみで動きます。追加インストール不要です。

## 使い方

1. `raw_screenshots ルート` を確認する（デフォルトで `_private/raw_screenshots/` が入っています。変える場合は「選択...」ボタン）
2. `collectionフォルダ名` を入力する（例: `tori_test`）
3. `衣装フォルダ名` を入力する（例: `05_new_outfit`）
4. `selectを選択...` / `frontを選択...` / `backを選択...` で画像を選ぶ
5. 「コピー実行」を押す（保存先フォルダはなければ自動作成されます）
6. 結果欄に作成されたファイルと保存先が表示される
7. 「保存先フォルダを開く」でエクスプローラーが開けます

## コピー先の構成

```
_private/raw_screenshots/
  {collection_name}/        例: tori_test
    {item_folder}/          例: 05_new_outfit
      select.png
      front.png
      back.png
```

## 注意事項

- **上書き注意**: コピー先に同名ファイルがある場合は確認ダイアログが出ます。「いいえ」を選べば何も変更されません。
- **front/backなしでもOK**: 未購入・未解放衣装などでは `select.png` だけでも保存できます。`select` が未選択の場合は警告が出ます。
- **画像変換はしません**: `.jpg` / `.jpeg` / `.webp` も選べますが、中身は変換せずそのまま `.png` という名前でコピーされます。PNG以外の中身を検出した場合は警告ダイアログが出ます。
- `_private/` 配下は `.gitignore` 対象です。コピーした画像はコミットされません。
- ドラッグ＆ドロップは**非対応**です（標準ライブラリのみで動かすため）。

## バッチ取り込みモード（manifest.json）

AI等が作成した確定済みマッピング（manifest.json）を検証し、
プレビュー → raw へ安全コピー → presets / costumes へ反映、まで量産できるモードです。

### manifest の作り方

UTF-8 の JSON ファイルとして、以下の形式で作ります。

```json
{
  "schema_version": 1,
  "idol_slug": "tenshouin-eichi",
  "collection": "tenshouin-eichi-slots-17-48",
  "inbox_dir": "_private/inbox/tenshouin-eichi",
  "start_slot": 17,
  "end_slot": 48,
  "items": [
    {
      "slot": 17,
      "costume_name": "ブルームアイドル衣装",
      "slug": "bloom-idol",
      "id": null,
      "select_file": "Screenshot_20260712-003407.png",
      "front_file": null,
      "back_file": null,
      "unlock_status": "locked",
      "requestable": false,
      "costume_group": "common",
      "tags": ["ブルーム"],
      "note_public": "アイドルランクAで解放",
      "icon_crop": null
    }
  ]
}
```

フィールドの意味:

- `collection`（省略可）: presets.json に追加する collection 名。省略時は `{idol_slug}-slots-{start:02d}-{end:02d}`。同一アイドルの追加スロットを既存と別 collection で管理できます。`collection` / `input_dir` / `output_dir` は**小文字英数字・ハイフン・アンダースコアのみ**（パス区切り・`..`・絶対パスは検証エラー）。既存 collection 名を指定した場合は、その collection の `idol_slug` / `input_dir` / `output_dir` が manifest と一致しないとエラーになります（別アイドルへの誤混入防止）。
- `inbox_dir`（省略可）: `select_file` 等の基準フォルダ。省略時は `_private/inbox/{idol_slug}`。**`_private/inbox/` 配下のみ指定可能**（サブフォルダ可。`_private/inbox/xxx` 形式でも `xxx` だけでも可）。絶対パス・ドライブレター・UNC・`..`、resolve後に inbox の外へ出るパスは検証エラーになります。
- `slot`: 衣装一覧のスロット番号。raw フォルダ名は `{NN}_{slug}` になります。
- `id`（省略可）: costumes.json の id。省略時は `{idol_slug}_{slug}-01`。
- `select_file` / `front_file` / `back_file`: inbox 内のスクショファイル名。未所持は front/back を `null` に。**inbox_dir 配下の相対パスのみ有効**（サブフォルダ可）。絶対パス・ドライブレター・UNC・`..` を含むパス、resolve後に inbox の外へ出るパスは検証エラーになります。
- `unlock_status`: `unlocked` / `card_only`（所持・front/back可）、`locked` / `not_purchased` / `card_missing`（未所持・front/back不可）。
- `requestable`: `unlocked` のときだけ `true` にできます。
- `costume_group`: `docs/costume-group-rules.md` の候補値。迷ったら `other` + tags に `"暫定分類"`。SCR は group ではなく tags に `"SCR"`。
- `icon_crop`: 所持衣装（一覧画面型）のアイコン切り抜き座標。**所持衣装では必須**です。未指定は検証エラーになり、apply・presets書き込み・WebP生成へ進めません（過去に仮cropで誤アイコンを量産した事故の再発防止）。未所持（ポップアップ型）は未指定で既存の固定 crop（x770,y340,320x300）が自動で入ります。
- `icon_mode`（省略可）: 既定 `manual_crop`。自動検出させたい場合のみ `auto_selected_card`。

### CLI での使い方

```powershell
cd L:\Studio\02_Projects\FlyWithAoi\mv-costume-catalog

# 1. 検証のみ（エラー/警告の一覧）
python tools/screenshot-renamer/batch_import.py validate manifest.json

# 2. dry-run（何も書き込まず、コピー予定・生成予定数を表示）
python tools/screenshot-renamer/batch_import.py dry-run manifest.json

# 3. rawへコピー（最終確認あり。エラーが1件でもあると実行不可）
python tools/screenshot-renamer/batch_import.py apply manifest.json

# 4. presets.json への差分プレビュー → 書き込み
python tools/screenshot-renamer/batch_import.py gen-presets manifest.json
python tools/screenshot-renamer/batch_import.py gen-presets manifest.json --write

# 5. 対象を限定してWebP生成（全再生成しない）
python tools/costume-image-processor/process_images.py --collection tenshouin-eichi-slots-17-48
#   さらに絞る: --item 17_bloom-idol / --icons-only / --body-only / --skip-existing / --debug

# 6. costumes.json への差分プレビュー → 書き込み
python tools/screenshot-renamer/batch_import.py gen-costumes manifest.json
python tools/screenshot-renamer/batch_import.py gen-costumes manifest.json --write
#   プレビューはWebP生成前でも可能。ただし --write は参照WebPが
#   すべて存在しないと拒否されます（緊急用: --allow-missing-images）

# 途中失敗した apply ログの確認
python tools/screenshot-renamer/batch_import.py check-logs
```

### GUI での使い方

```powershell
python tools/screenshot-renamer/batch_gui.py
```

（app.py の「バッチ取り込み...」ボタンからも開けます）

1. 「選択...」で manifest.json を選ぶと自動で検証されます
2. 一覧に slot / 衣装名 / slug / select・front・back のサムネイル / 状態 / group / tags / コピー先 / 警告が表示されます（エラーのある行は赤背景）
3. 「dry-run表示」で書き込みなしの適用内容を確認
4. 「rawへコピー (apply)」→ 最終確認 → コピー実行（エラーがあるとボタンが無効）
5. 「presets差分...」「costumes差分...」で差分プレビューを確認してから書き込み

### apply後の再検証（適用済み判定）

apply が完了した後に同じ manifest で validate / gen-presets / gen-costumes を実行した場合、
raw フォルダが「ファイル名・数・内容ともに manifest の apply 結果と一致し、
completed の apply ログに記録がある」ときは**衝突ではなく「適用済み」**として扱われ、
そのまま presets / WebP / costumes の工程へ進めます。

- 適用済みスロットへの**二度目の apply は拒否**されます（上書き禁止は従来どおり）
- 同名 raw の内容が manifest と一致しない場合は従来どおり衝突エラーです
- 内容は一致するが apply ログがない場合もエラーになります（出所不明のrawを黙って採用しない）

GUI もこの判定に対応しており、「manifest選択 → dry-run → rawへコピー →
presets差分・書き込み → WebP生成（この分のみ）→ costumes差分・書き込み」まで
GUI のボタン操作だけで完走できます。

### エラー時の対処

- **検証エラー**: manifest を修正して再読込（validate）。エラーが残る限り apply できません。
- **既存rawフォルダとの衝突**: すでに取り込み済みのスロットです。manifest から外すか、slug/slot を確認してください。
- **id 衝突**: costumes.json に同じ id があります。`-01` を `-02` にする等、`id` フィールドで明示してください。
- **apply が途中で失敗**: `_private/import_logs/` に `status: "failed"` / `"in_progress"` のログが残ります。`check-logs` で確認し、ログの `copied` に載っているコピー済みファイルを見て、そのフォルダを片付けてから再実行してください（inbox 側は無傷です）。
- **icon_crop 未指定のエラー（所持衣装）**: manifest に `icon_crop` を明示してから再実行してください。座標は `--debug` の確認画像で調整できます。
- **costumes 書き込み時の画像不足エラー**: `process_images.py --collection <名前>` で WebP を生成してから `gen-costumes --write` をやり直してください。

### 安全ルール

- inbox のファイルは**読み取りのみ**（削除・移動・リネームは一切しない）
- raw への書き込みは**コピーのみ**。既存ファイルは無断で上書きしない（衝突は検証エラー）
- presets.json / costumes.json は**差分プレビューを確認してから**の明示書き込みのみ（一時ファイル経由のアトミック書き込み）
- apply のログを `_private/import_logs/` に残し、途中失敗を検出可能にする
- `_private/` 配下は .gitignore 対象。個人スクショはコミットされません

## 将来改善案

- ドラッグ＆ドロップ対応（tkinterdnd2 などの導入検討）
- 衣装フォルダ名の連番自動提案（既存フォルダを見て `06_...` を提案）
- select/front/back の3枠に直接ドロップ
- presets.json への item 追加補助
