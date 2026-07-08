# raw-folder-generator

`public/data/idols.json` に登録されている全idolを元に、
`_private/raw_screenshots/{idol_slug}/` の**親フォルダだけ**を自動生成する補助スクリプト（CLI）。

## 目的

スクショ取得の準備として、idolごとの保存先フォルダを手作業で1つずつ作るのが大変なので、
`idols.json` に登録されている slug から親フォルダだけをまとめて作成します。

衣装サブフォルダ（`01_common` など）はこのツールでは作りません（理由は後述）。

## 実行方法

リポジトリルートから実行します。

```powershell
cd L:\Studio\02_Projects\FlyWithAoi\mv-costume-catalog
python tools/raw-folder-generator/create_raw_folders.py
```

Python標準ライブラリのみで動きます。追加インストール不要です。

### `--dry-run`（作成予定だけ表示）

実際にはフォルダを作らず、何が `created` / `skip` になるかだけを確認できます。
初めて実行するときや、大量のidolが対象になる前の確認に使ってください。

```powershell
python tools/raw-folder-generator/create_raw_folders.py --dry-run
```

### `--root`（リポジトリルートを指定）

デフォルトではスクリプトの場所から自動的にリポジトリルートを判定しますが、
別の場所から実行したい場合は `--root` で明示できます。

```powershell
python tools/raw-folder-generator/create_raw_folders.py --root L:\Studio\02_Projects\FlyWithAoi\mv-costume-catalog
```

## 作成されるフォルダ構造

```
_private/raw_screenshots/
  {idol_slug}/        例: hibiki-wataru, amagi-hiiro, shino-hajime, ...
```

`idols.json` に登録されているidol1人につき、フォルダが1つ作られます。
衣装サブフォルダ（例: `01_common/`, `02_unit/`）はこの時点では**作られません**。

## 衣装サブフォルダを自動生成しない理由

衣装サブフォルダの番号は、試着室画面の左上から右へ、次の段へ進む「表示位置番号」として扱っています。
そのため、common衣装やunit衣装が必ず `01` / `02` になるとは限りません。表示順はidolごとに異なります。

例：

- 迎春飛翔が試着室の左上1番なら `01_geishun-hisho`
- 既存アイドルでは共通アイドル衣装が `02_common`、ユニット衣装が `03_trickstar` / `03_fine` などになる場合がある
- MELLOW DEAR USの4人は迎春飛翔衣装がないため、`01_common` / `02_mellow-dear-us` になる
- 先生2人は共通アイドル衣装がないため、`01_rain-bow` / `02_uta-no-ojisan` になる

このように、衣装サブフォルダの命名はスクショを実際に見ながら個別に判断する必要があるため、
このツールでは idol_slug の親フォルダだけを作り、衣装サブフォルダはスクショ取得時に手動（または
`screenshot-renamer` ツール）で作成する運用にしています。

## 安全に関する注意

- このツールは `_private/raw_screenshots/{idol_slug}/` の**親フォルダを作るだけ**です。
- 衣装サブフォルダは作りません。
- 既存フォルダがある場合は `skip` として表示するだけで、削除・上書き・中身の変更は一切行いません。
- ファイルの削除・移動は行いません。
- `public/data/idols.json` を含む `public/` 配下のファイルは一切変更しません（読み込み専用）。
- `_private/` は `.gitignore` 対象のため、生成されたフォルダ自体はコミットされません。

## 出力例

```
created : L:\...\mv-costume-catalog\_private\raw_screenshots\hidaka-hokuto
created : L:\...\mv-costume-catalog\_private\raw_screenshots\akehoshi-subaru
skip    : L:\...\mv-costume-catalog\_private\raw_screenshots\hibiki-wataru

対象idol数: 60
作成数    : 2
既存数    : 1
```
