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

## 将来改善案

- ドラッグ＆ドロップ対応（tkinterdnd2 などの導入検討）
- 衣装フォルダ名の連番自動提案（既存フォルダを見て `06_...` を提案）
- select/front/back の3枠に直接ドロップ
- presets.json への item 追加補助
