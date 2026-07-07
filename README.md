# MV衣装カタログ

「あんさんぶるスターズ！！Music」のMV衣装を、配信リスナーがリクエストしやすいように一覧できる静的Webページです。

暘晴あゆむのYouTube配信で、視聴者がMV衣装をリクエストする際の参考にしてもらうことを目的としています。noteやYouTube概要欄からリンクする想定です。

- ログイン不要でURLから閲覧できる
- アイドル名・ユニット名・衣装名・タグで検索できる
- 解放状態で絞り込める
- 初期表示は「リクエスト可能な衣装のみ」
- 衣装カードをクリックすると詳細（正面・背面画像、メモ、リクエスト文）が見られる

---

## ローカル確認方法

`index.html` を直接ダブルクリックして開くと、ブラウザのセキュリティ制限（CORS）で
`costumes.json` の読み込みがブロックされます。
必ず簡易サーバー経由で開いてください。

```
cd public
python -m http.server 8000
```

ブラウザで次を開きます。

```
http://localhost:8000/
```

サーバーを止めるときは、コマンドプロンプト側で `Ctrl + C` を押します。

---

## フォルダ構成

```
mv-costume-catalog/
  public/                       ← 公開対象（GitHub Pagesで配信するのはここ）
    index.html
    style.css
    app.js
    data/
      costumes.json             ← 衣装データ（手入力）
    images/
      costumes/
        hibiki-wataru/          ← 公開用の軽量画像（WebP）を置く
  _private/                     ← 元スクショ置き場。公開・コミット対象外
  README.md
  .gitignore
```

### `_private/` について

`_private/` はゲームの元スクリーンショットなど、**公開しない素材**の置き場です。

- `.gitignore` で除外済み（コミットされません）
- GitHub Pages で公開するのは `public/` フォルダのみにしてください
- `git add` の前に `git status` で `_private/` が含まれていないことを確認する習慣をつけてください

---

## データの追加方法（Phase 1）

Phase 1では手作業でデータと画像を用意します。

1. `public/data/costumes.json` の `costumes` 配列に1件追加する
2. 公開用画像（WebP）を `public/images/costumes/{idol_slug}/` に置く
   - ファイル名は JSON の `images.icon` / `images.front` / `images.back` と一致させる
   - 画像がまだ無くてもページは壊れません（「準備中」表示になります）

### 固定コードの値

`unlock_status`:

| コード | 表示 |
| --- | --- |
| `unlocked` | 解放済み |
| `card_only` | カード所持のみ |
| `card_missing` | カード未所持 |
| `not_purchased` | 未購入 |

`costume_group`:

| コード | 表示 |
| --- | --- |
| `common` | 全員共通衣装 |
| `unit` | ユニット衣装 |
| `shuffle` | シャッフル衣装 |
| `cross` | クロススカウト衣装 |
| `solo` | 個別衣装 |
| `anniversary` | 周年衣装 |
| `shop` | ショップ衣装 |
| `other` | その他 |

未購入・未解放などで着用画像が無い場合は、`images.front` / `images.back` を `null` にしてください。詳細表示では「未所持・未解放のため着用画像はありません。」と表示されます。

---

## 実装状況

- **Phase 1（このリポジトリの現状）**: 手入力JSON＋静的Webページ。検索・フィルター・詳細表示・リクエスト文コピー。
- **Phase 2以降（未実装）**: 画像の回転・トリミング・WebP変換ツール、衣装名OCR などは **まだ実装していません**。画像加工は現状すべて手作業です。
