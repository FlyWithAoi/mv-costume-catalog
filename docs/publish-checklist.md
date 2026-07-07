# MV衣装カタログ 公開前チェックリスト

GitHub Pages などで公開する前、および衣装を追加したあとに、事故（元スクショや debug 画像の混入など）を防ぐための確認リストです。

このドキュメントは**確認用のチェックリスト**であり、実装手順そのものは `docs/project-notes.md` を参照してください。

対象コミット基準: `11c0873 feat: add hajime costumes and rabits unit`

> このリポジトリはあんさんぶるスターズ！！Music のスクリーンショットを素材として扱います。元スクショ・debug 画像はゲームの著作物を含むため、**公開リポジトリに絶対に含めない**でください。

---

## 1. 公開前チェック（コミット・push・公開の前に毎回）

作業ディレクトリはリポジトリのルート（`L:\Studio\02_Projects\FlyWithAoi\mv-costume-catalog`）を想定しています。

- [ ] `git status --short --untracked-files=all` を実行して、追跡・未追跡ファイルを一覧する
- [ ] 出力に `_private/` が**出ていない**こと
- [ ] 出力に `tools/costume-image-processor/debug/` が**出ていない**こと
- [ ] 出力に `.claude/` などの作業用一時ファイルが**出ていない**こと
- [ ] コミット対象が **`public/` 配下を中心**とした公開対象になっていること
- [ ] 元スクショ（`select.png` / `front.png` / `back.png` など）が公開対象に**入っていない**こと
- [ ] debug 画像（`*_debug.png`）が公開対象に**入っていない**こと

### 確認コマンド例（PowerShell）

```powershell
git status --short --untracked-files=all
git status --short --untracked-files=all | Select-String "_private|debug|.claude"
```

2行目のコマンドで**何も表示されなければ OK**です。`_private` / `debug` / `.claude` を含む行が出た場合は、`.gitignore` を確認し、原因を取り除くまでコミット・push しないでください。

> メモ: 現状 `.gitignore` は `_private/` と `tools/costume-image-processor/debug/` を除外済みです。`.claude/` はこのリポジトリの `.gitignore` には入っていないため、目視確認を特に忘れないでください（将来 `.gitignore` に `.claude/` を追加するのは別タスク候補です。9章参照）。

---

## 2. ローカル表示確認

公開前に、ローカルサーバーで実際の表示を確認します。

```powershell
cd L:\Studio\02_Projects\FlyWithAoi\mv-costume-catalog\public
python -m http.server 8000
```

確認 URL:

```text
http://localhost:8000/
```

ブラウザで開いて、以下を確認します（確認後は、サーバーを起動したターミナルで `Ctrl + C` で停止）。

- [ ] ページが開く（真っ白・読み込みエラーにならない）
- [ ] 初期表示が「リクエスト可能衣装のみ」になっている
- [ ] 「リクエスト可能のみ」を OFF にすると全件表示される
- [ ] ユニットプルダウンが表示される
- [ ] fine / UNDEAD / Ra*bits がプルダウン・一覧に表示される
- [ ] 検索が動く（下記3章の検索語で確認）
- [ ] 解放状態フィルターが動く
- [ ] カードをクリックすると詳細モーダルが開く
- [ ] リクエスト文のコピー機能が動く
- [ ] 画像表示が崩れない
- [ ] front/back が無い未解放・未購入衣装も、自然に（「準備中」フォールバックなどで）表示される
- [ ] ブラウザのコンソール（F12 → Console）にエラーが出ていない

---

## 3. 検索確認

検索ボックスに以下を入力して、期待どおりヒットするか確認します。ユニット名検索は「所属アイドル経由」でヒットする仕様です（`docs/project-notes.md` 5〜6章参照）。

ユニット名・別名:

- [ ] `fine`
- [ ] `フィーネ`
- [ ] `UNDEAD`
- [ ] `アンデッド`
- [ ] `Ra*bits`
- [ ] `RaBits`
- [ ] `rabits`
- [ ] `ラビッツ`

アイドル名（漢字）:

- [ ] `渉`（日々樹 渉）
- [ ] `桃李`（姫宮 桃李）
- [ ] `零`（朔間 零）
- [ ] `創`（紫之 創）

アイドル名（ローマ字 / slug 系）:

- [ ] `wataru`
- [ ] `tori`
- [ ] `rei`
- [ ] `hajime`

いずれも、大文字小文字・記号・空白の違いが正規化で吸収され、同じ結果になることを確認します。

---

## 4. 衣装追加時チェック

新しい衣装を追加したあとの確認フロー（詳しい実装手順は `docs/project-notes.md` 4章）。

1. [ ] screenshot-renamer で `_private/raw_screenshots/{collection}/{item}/` に `select.png` / `front.png` / `back.png` を配置した
2. [ ] `tools/costume-image-processor/presets.json` に collection / item を追加した
3. [ ] `python tools/costume-image-processor/process_images.py --debug` を実行した
4. [ ] `tools/costume-image-processor/debug/` の debug 画像で、アイコン切り抜き位置を目視確認した（赤枠が選択中カードを囲んでいるか）
5. [ ] 誤検出があれば `manual_crop` に切り替えて再確認した
6. [ ] `python tools/costume-image-processor/process_images.py`（`--debug` なし）で本番用 WebP を生成した
7. [ ] `public/images/costumes/{idol_slug}/` に WebP 画像が出力されたことを確認した
8. [ ] `public/data/costumes.json` にレコードを追加した
9. [ ] 必要なら `public/data/idols.json` / `units.json` を追加・更新した
10. [ ] ローカルサーバーで表示確認した（2章）
11. [ ] `git status` で `_private` / debug の混入が無いことを確認した（1章）
12. [ ] コミットした

---

## 5. データ整合性チェック

`public/data/` の3ファイル（`costumes.json` / `idols.json` / `units.json`）の整合を確認します。

- [ ] `costumes.json` の各レコードの `idol_slug` が、`idols.json` に存在する
- [ ] `units.json` の各ユニットの `member_slugs` が、すべて `idols.json` に存在する
- [ ] `images.icon` / `images.front` / `images.back` に書いたファイルが、`public/images/costumes/` に実在する
- [ ] front/back が無い衣装は、`images.front` / `images.back` を `null` にしている（空文字や存在しないファイル名を書かない）
- [ ] `requestable: true` の衣装は、基本的に front/back がある
- [ ] 未購入・未解放・カード未所持などの衣装は `requestable: false` になっている
- [ ] `unlock_status` の値を、必要以上に増やしていない（既存コードを揃える）

現在の主な `unlock_status`:

- `unlocked`（解放済み）
- `locked`（未解放。ランク条件などで未入手）
- `not_purchased`（未購入）
- `card_only`（カードのみ）
- `card_missing`（カード未所持）

> 新しい `unlock_status` を追加する場合は、`app.js` のラベル変換テーブルと `index.html` のフィルターにも1行ずつ追加が必要です。安易に増やさず、既存コードで表せないか先に検討してください。

---

## 6. 非公開ファイル・公開ファイルの境界

### 非公開（コミット・公開しない）

- `_private/`
- 元スクショ（`select.png` / `front.png` / `back.png` など）
- `tools/costume-image-processor/debug/`
- debug 画像（`*_debug.png`）
- `.claude/` などの作業用一時ファイル

### 公開・コミット対象

- `public/data/*.json`
- `public/images/costumes/**/*.webp`
- `public/index.html`
- `public/app.js`
- `public/style.css`
- `tools/` 配下のツール本体（`process_images.py` / `presets.json` / screenshot-renamer など）
- `docs/` 配下の運用メモ・チェックリスト

> 例外: `tools/` はツール本体を公開する一方で、**`tools/costume-image-processor/debug/` だけは公開しない**。debug 画像は元スクショ全体に枠を描いただけで、実質的に非公開素材と同じだからです。

---

## 7. 命名ルール

- collection 名の例: `wataru_test`, `tori_test`, `rei_test`, `hajime_test`
- 出力先ディレクトリ: `public/images/costumes/{idol_slug}/`
- 画像ファイル名: `{idol_slug}_{costume-slug}_icon.webp` / `..._front.webp` / `..._back.webp`
  - 例: `hibiki-wataru_common-01_icon.webp`
- raw 衣装フォルダの番号は、**キャラ内の試着室並び・作業順**（キャラごとにローカルな番号）
- 全キャラ共通の通し番号としては扱わない
- `01_common` は共通衣装として固定するのを推奨
- 未入手ぶんも含め、試着室の右上から順番に番号を振ると、後で管理しやすい

---

## 8. 公開ページ向けの説明文案（note / YouTube 概要欄用）

そのまま貼れる短い案です。用途に合わせて選んでください。

案A（標準）:

```text
配信中にリクエストできるMV衣装一覧はこちら。
検索欄やユニット絞り込みから、見たい衣装を探せます。
「リクエスト可能」の衣装を中心に選んでね。
```

案B（やわらかめ）:

```text
配信で「この衣装が見たい！」を伝えやすくするために、
持ってるMV衣装のカタログを作りました🌸
名前やユニットで検索できるので、気になる衣装を探して、
「リクエスト可能」の中から気軽にリクエストしてね。
```

---

## 9. 将来やることメモ（今はやらないが候補）

- NEW / 最近リクエスト可になった衣装フィルター
- `requestable_since`（リクエスト可能になった日）フィールド
- `catalog_added_at`（カタログ追加日）フィールド
- アイドル複数選択フィルター
- タグフィルター UI
- 見た目カスタム（テーマカラー・ロゴなど）
- GitHub Pages 公開（本番公開）
- screenshot-renamer のドラッグ＆ドロップ対応
- `presets.json` への item 追加補助ツール
- JSON 整合性チェックツール（5章の内容を自動化）
- `.gitignore` に `.claude/` を追加する
