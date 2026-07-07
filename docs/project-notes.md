# MV衣装カタログ 運用・設計メモ

このドキュメントは、実装そのものではなく「今どこまでできていて、次に何をどう進めるか」を記録しておくためのメモです。

最終更新の基準コミット: `9b4909c feat: add MV costume catalog MVP`

---

## 1. プロジェクト概要

- VTuber配信（あんさんぶるスターズ！！Music）用の、MV衣装カタログWebアプリ
- noteやYouTube概要欄からリンクする想定の、ログイン不要な公開ページ
- 目的は、リスナーが配信主の所持MV衣装を検索・閲覧し、「この衣装をリクエストしたい」と伝えやすくすること

---

## 2. 現在できていること

### Phase 1: 静的WebページMVP

- `public/index.html` / `style.css` / `app.js`（ビルドツールなし、素のHTML/CSS/JS）
- `public/data/costumes.json` を読み込んでカード一覧表示
- 検索（アイドル名・ユニット名・衣装名・タグ、大文字小文字区別なし）
- 解放状態フィルター
- 「リクエスト可能のみ」フィルター（初期表示ON）
- カードクリックで詳細モーダル表示（正面・背面画像、タグ、公開メモ）
- リクエスト文コピー（`navigator.clipboard.writeText()`、失敗時は手動選択にフォールバック）
- front/backが無い衣装でもページが壊れない設計（画像404は「準備中」表示に自動フォールバック）

### Phase 2: 画像加工CLI

- `tools/costume-image-processor/process_images.py`（Python + Pillow）
- 元スクショ（横向き）を回転・トリミング・リサイズしてWebP化
- 選択中カードの黄緑枠を自動検出する `auto_selected_card` モードと、手動座標指定の `manual_crop` モード
- `--debug` オプションで、切り抜き範囲を枠（青=探索範囲／赤=自動検出／オレンジ=手動crop）で確認できる
- 座標・閾値はすべて `presets.json` に外出し（コード変更不要で調整可能）

### テストデータ

- 日々樹 渉のテスト衣装5件（`共通アイドル衣装` `Caelum` `黒系衣装（仮）` `ヘッドパーツあり衣装（仮）` `スタライ10thライブTシャツ`）
- 画像13枚（アイコン5＋front/back各4着分）
- 姫宮 桃李・朔間 零の衣装（C-3）に加え、紫之 創の衣装4件を追加（`共通アイドル衣装` `Ra*bits衣装` `迎春飛翔` ＋ 未解放の `共通アイドル衣装（SCR）`）
- ユニット `Ra*bits` を追加（メンバー4人を `idols.json` にフル登録）。`Ra*bits` / `RaBits` / `rabits` / `ラビッツ` はいずれも検索正規化で同一扱いになることを確認済み
- 解放状態コード `locked`（未解放。ランク条件などで未入手）を追加（`app.js` のラベル表と `index.html` のフィルターに1行ずつ）

---

## 3. 非公開にするもの（絶対厳守）

以下は**絶対に公開・コミットしない**。`.gitignore` で除外済みだが、コミット前は毎回目視確認する。

- `_private/`（元スクショ一式）
- 元スクショ（`select.png` / `front.png` / `back.png` など）
- `tools/costume-image-processor/debug/`（`--debug` の確認画像）
- debug画像（元スクショ全体に枠を描いただけなので、実質的に非公開素材と同じ）
- 管理用メモ・未公開メモ（`costumes.json` の `note_private` 的なフィールドを将来追加する場合は特に注意。現状は公開JSONに管理用メモ用のフィールドは存在しない）

> `_private/` や `debug/` はゲームの著作物のスクリーンショットを含むため、公開リポジトリに絶対に含めないこと。

---

## 4. 衣装追加の運用手順

新しい衣装を1着追加するときの標準フロー。

**複数キャラ対応（C-3以降）**: 元スクショは `_private/raw_screenshots/{キャラフォルダ}/{衣装フォルダ}/` の2段構成。
キャラを増やすときは、キャラフォルダを作り、`presets.json` の `collections` にエントリを追加し、
`idols.json`（必要なら `units.json` も）にマスタを追加する。
自動検出は選択中カードが `search_area` の外にあると別カードに誤爆するため、
**--debug の赤枠が選択中カードを囲んでいるか必ず目視確認**する（詳細はツールREADME参照）。

1. `_private/raw_screenshots/{キャラフォルダ}/` の下に、衣装用のフォルダを作る（例: `06_xxx`）
2. フォルダに `select.png` / `front.png` / `back.png` を入れる
   - 未購入・未解放などで着用画像が無い場合は `front.png` / `back.png` を省略してよい（`process_images.py` は欠損してもエラーにならずスキップする）
3. `tools/costume-image-processor/presets.json` の `items` に、その衣装のエントリを追加する
   - `id`（`public/data/costumes.json` の想定ファイル名と揃える）
   - `icon_mode`（通常一覧画面なら `auto_selected_card`、詳細ポップアップなど自動検出できない画面なら `manual_crop`）
   - `icon_crop`（フォールバック用、または manual_crop の実座標）
   - `has_body_images`
4. `python tools/costume-image-processor/process_images.py --debug` を実行し、`tools/costume-image-processor/debug/` の画像で切り抜き範囲を確認する
   - 青枠 = 自動検出の探索範囲
   - 赤枠 = 自動検出できた範囲
   - オレンジ枠 = 手動座標（フォールバック or manual_crop）
   - ズレていたら `presets.json` を調整して再実行
5. 問題なければ `python tools/costume-image-processor/process_images.py`（`--debug` なし）を実行し、本番用WebPを生成する
6. `public/data/costumes.json` の `costumes` 配列に、その衣装のレコードを追加する
   - `images.icon` / `images.front` / `images.back` のファイル名を、実際に生成されたWebPファイル名と一致させる
7. ローカルサーバーで表示確認する
   ```
   cd public
   python -m http.server 8000
   ```
   `http://localhost:8000/` を開いて、カード表示・検索・詳細モーダルが正しく動くか確認する
8. コミット前に `git status --short --untracked-files=all` を実行し、`_private` や `debug` がリストに出てこないことを確認する
9. 問題なければコミットする

---

## 5. データ設計メモ

### 現在の `costumes.json` の役割

- 1レコード＝「アイドル1人の衣装1着」
- Webページは `costumes.json` / `idols.json` / `units.json` の3ファイルを `Promise.all` で読み込む
- アイドル名・ユニット名は **`idol_slug` を正** とし、表示名は `idols.json` / `units.json` から lookup して補完する（C-1で移行済み。旧 `idol` / `unit` フィールドは削除）
  - `idols.json`: アイドルマスタ（`slug` / `name` / `name_kana` / `name_romaji` / `aliases` / `sort_order`）
  - `units.json`: ユニットマスタ（`slug` / `name` / `aliases` / `unit_type` / `member_slugs` / `sort_order`）
  - 「アイドル→所属ユニット」は `units.json` の `member_slugs` を正とし、読み込み時に逆引きマップ（`unitsByMemberSlug`）を構築する
  - `idol_slug` が `idols.json` に無い場合は `console.warn` を出し、表示は「不明なアイドル」にフォールバックする
- `unlock_status` / `costume_group` は固定コードで持ち、日本語表示への変換は `app.js` 側の変換テーブルで行っている

### 検索の仕様（C-1）

- 検索対象: 衣装名・タグ・公開メモ・アイドル名/読み/ローマ字/別名・所属ユニット名/別名
- 入力とデータの両方を同じ正規化関数（`normalizeForSearch`）に通す: `NFKC` 正規化＋小文字化＋空白・記号除去
  - これにより `日々樹 渉`＝`日々樹渉`、`Ra*bits`＝`rabits`、`Special for Princess!`＝`specialforprincess` が別名なしで一致する
- 各衣装に正規化済みの検索文字列 `_search` を読み込み時に1回だけ事前構築する（毎回 units→members を辿り直さない）
- **ユニット名検索は所属アイドル経由**: `fine` / `フィーネ` で検索すると fine 所属アイドルの衣装（個別衣装・クロス衣装含む）がすべてヒットする。「衣装自体が fine 衣装か」ではなく「着ているアイドルが fine 所属か」で判定する
- 将来「この衣装がどのユニット衣装か」を厳密に管理したくなったら、`costume_unit_slug` のような別フィールドを追加する方針（C-1では未追加）

### 今後、データが増える前に検討したいこと

衣装数・アイドル数が増えると、今の「衣装レコードの中にアイドル名・ユニット名を文字列でベタ持ち」する方式は表記ゆれや変更漏れの温床になる。以下を追加検討する。

- **`idols.json` の新設**: アイドルごとのマスタデータ（本名、読み、所属ユニット、別名など）を切り出す
- **`units.json` の新設**: ユニットごとのマスタデータ（正式名称、表示名、別名リストなど）を切り出す
- **アイドルの所属ユニット**: 1アイドルが複数ユニットに所属するケース（クロスユニット、シャッフルユニットなど）にどう対応するか設計する
- **ユニット名の別名・表記ゆれ対応**: `Ra*bits` のような記号入り名称、通称・略称への対応（詳細は6章）
- **アイドル名の別名・表記ゆれ対応**: 漢字表記・カタカナ表記・愛称などの揺れに対応する仕組み
- **ユニットプルダウン**: 検索ボックスとは別に、ユニットで絞り込むUIを追加するかどうか
- **アイドル複数選択**: 複数アイドルを同時に選んで絞り込むUIを追加するかどうか

これらは今すぐ実装する必要はないが、データ件数が増えてから設計変更すると手戻りが大きいため、次にデータを大きく増やす前に一度設計を見直すタイミングを作る。

---

## 6. ユニット検索の今後仕様（方針メモ）

検索ボックスに **ユニット名を入力したら、そのユニット所属アイドルの衣装がヒットする**ようにしたい。

### 基本方針

- 例: 検索欄に `fine` と入力 → fine所属アイドル（日々樹 渉、姫宮 桃李、天祥院 英智、伏見 弓弦）の衣装がすべてヒットする
- 判定基準は「**その衣装自体がfine衣装かどうか**」ではなく、「**その衣装を着ているアイドルがfine所属かどうか**」
  - 衣装グループ（`costume_group`: unit / shuffle / cross など）による厳密な判定は後回しでよい
  - まずは「所属アイドルベースの検索ヒット」を優先する
- `Ra*bits`、`Special for Princess!`、`MELLOW DEAR US` のように、記号入り・長い・入力しづらいユニット名は、**aliases（別名リスト）でカバーする**
  - 例: `Ra*bits` → `rabbits`, `らびっつ` などのエイリアスを持たせて検索にヒットさせる
  - 実装時は `units.json` にユニットごとの `aliases: []` を持たせる案が有力

この仕様はまだ実装していない。実装するタイミングでは、5章の `units.json` / `idols.json` の設計とセットで進める。

---

## 7. UI改善メモ（今すぐではないが、やりたいこと）

優先度・時期は未定。思いついたものをここに書き留めておく。

- ~~ユニットプルダウン~~（C-2で実装済み。`units.json` から選択肢を自動生成し、所属アイドル基準で絞り込む。既存フィルターとAND）
- アイドル複数選択（複数アイドルを同時に選んで絞り込むUI）
- タグフィルター（現状タグはデータに持っているが、フィルターUIとしては未実装）
- 暘晴あゆむらしいテーマカラーへの変更
- ロゴ追加
- GitHub Pages公開（本番公開）
- レスポンシブ微調整（スマホでの見え方の細かい調整）

---

## 8. Git運用メモ

### コミット前チェック

```
git status --short --untracked-files=all
```

- 出力に `_private` や `debug` が**含まれていないこと**を毎回目視で確認する
- 不安な場合は、個別ファイルが無視対象になっているか次のコマンドで確認できる
  ```
  git check-ignore -v _private/raw_screenshots/xxx/select.png
  git check-ignore -v tools/costume-image-processor/debug/xxx_select_debug.png
  ```
  パスとマッチした `.gitignore` の行が表示されれば、正しく除外されている

### push前チェック

- ローカルコミット内容を確認してからpushする（`git log` や `git show` で直前のコミットを見直す）
- pushは取り消しにくい操作なので、`_private` や `debug` が過去に誤って追跡対象になっていないか、履歴も含めて疑わしい場合は確認してからpushする

### GitHub Pages公開時の注意

- GitHub Pagesの公開設定では、公開対象のディレクトリ（ルート or `docs/` など）を必ず確認する
- 現状の構成では、**公開してよいのは `public/` の中身だけ**
- リポジトリのルートをそのまま公開設定にすると、`_private/` や `tools/` が公開ディレクトリの外にあっても、リポジトリ自体が公開されていれば誰でも見える点に注意（GitHubリポジトリを非公開にするか、`public/` だけを配信する設定にするか、公開前に方針を決める）
