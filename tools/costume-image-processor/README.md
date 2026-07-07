# 画像加工スクリプト（Phase 2）

MV衣装カタログの元スクショから、公開用の軽量WebP画像を生成するローカル用CLIツールです。

- 入力: `_private/raw_screenshots/{キャラフォルダ}/`（`.gitignore` で除外済み・非公開）
- 出力: `public/images/costumes/{idol_slug}/`

複数キャラに対応しています。キャラフォルダと衣装一覧は `presets.json` の `collections` に定義します
（例: `wataru_test` → `hibiki-wataru`、`tori_test` → `himemiya-tori`、`rei_test` → `sakuma-rei`）。

GUI・OCR・JSON追記機能はまだありません（Phase 2はこの画像加工のみ）。

---

## 必要なもの

- Python 3.8 以上
- Pillow（画像処理ライブラリ）

### インストール

```
pip install pillow
```

---

## 使い方

プロジェクトルートに移動してから実行します。

```
cd L:\Studio\02_Projects\FlyWithAoi\mv-costume-catalog
python tools/costume-image-processor/process_images.py
```

実行すると、処理したファイルとスキップした項目が一覧表示されます。
出力先フォルダが無ければ自動で作成し、既存ファイルは上書きします。

### おすすめの流れ（まず --debug で赤枠を確認）

アイコンの切り抜き位置は衣装ごとに違うので、いきなり本番実行するとズレます。
次の順番がおすすめです。

1. `--debug` を付けて実行し、赤枠つきの確認画像を出す
2. `tools/costume-image-processor/debug/` の画像を開き、赤枠が切り抜きたい範囲と合っているか見る
3. ズレていたら `presets.json` の座標を調整する
4. もう一度 `--debug` で確認する
5. 赤枠がOKになったら、`--debug` なしで本番実行してWebPを生成する

```
python tools/costume-image-processor/process_images.py --debug
```

---

## 処理内容

### front.png / back.png（着用画像）

1. 90度回転して縦向きに直す（ゲームは横向きで保存するため）
2. `presets.json` の `body.crop` で余白をトリミング（全衣装共通）
3. 長辺 1000px 程度にリサイズ
4. WebP（品質80）で保存

人物を完璧に切り抜く必要はありません。色味と形が分かる参考画像であれば十分です。
手先・足先が多少切れても問題ありません。

### select.png（衣装一覧画面）→ アイコン

select.png からミニアイコンを切り抜きます。切り抜き方法は、各衣装の `icon_mode` で選びます。

| icon_mode | 用途 | 動き |
| --- | --- | --- |
| `auto_selected_card` | 通常の衣装一覧画面 | 選択中カードの**黄緑枠を自動検出**して切り抜く。**失敗したら `icon_crop` にフォールバック** |
| `manual_crop` | locked詳細ポップアップなど、自動検出できない画面 | `icon_crop` の座標をそのまま使う |

- **通常の一覧画面は `auto_selected_card` を推奨**します。選択中カードに付く黄緑の枠を検出するので、
  毎回手動で座標を合わせなくて済みます。
- **locked詳細ポップアップ（05_locked）などは `manual_crop`** を使い、`icon_crop` を手動で合わせます。
- 自動検出が失敗した場合は、その衣装の `items.<フォルダ名>.icon_crop` の座標に自動でフォールバックします。
  （フォールバック用に `icon_crop` は常に設定しておいてください）

#### 自動検出の注意点

この画面は**全サムネイルに黄緑の「MV」バッジ**が付いています。単純な黄緑検出だと、選択枠だけでなく
それらのバッジまで拾って検出枠が大きくなりがちです。対策として `auto_selected_card.search_area`
（探索範囲）を、**選択中カードのおおよその位置だけに絞る**のが有効です。
`--debug` の青枠（探索範囲）・赤枠（検出結果）を見ながら `search_area` と `green_threshold` を調整してください。

---

## 座標の調整方法（重要）

`presets.json` の座標は**すべて仮の初期値**です。実際のスクショに合わせて調整してください。
コードを触る必要はありません。`presets.json` の数字を書き換えて再実行するだけです。

```json
{
  "output": {
    "long_edge_body": 1000,   // front/back の長辺サイズ
    "icon_size": 200,         // アイコンの最大サイズ
    "webp_quality": 80        // WebPの品質（0-100）
  },
  "body": {
    "rotate_degrees": -90,    // 回転が逆向きなら 90 か 270 にする（全衣装共通）
    "crop": { "x": 0, "y": 580, "width": 1000, "height": 1250 }
  },
  "auto_selected_card": {
    "search_area": { "x": 700, "y": 260, "width": 320, "height": 320 }, // 探索範囲（青枠）
    "green_threshold": { "min_g": 200, "max_r": 255, "max_b": 130 },     // 黄緑の判定
    "padding": 20,          // 検出枠の外側に足す余白
    "min_box_width": 60,    // これより小さい検出はノイズ扱いでフォールバック
    "min_box_height": 60
  },
  "collections": {
    "wataru_test": {                        // _private/raw_screenshots/ 内のフォルダ名
      "idol_slug": "hibiki-wataru",
      "output_dir": "hibiki-wataru",        // public/images/costumes/ 内の出力先
      "items": {
        "01_common": {
          "id": "hibiki-wataru_common-01",
          "icon_mode": "auto_selected_card",                             // 通常一覧は自動検出
          "icon_crop": { "x": 0, "y": 0, "width": 200, "height": 200 },  // 失敗時のフォールバック
          "has_body_images": true
        },
        "05_locked": {
          "id": "hibiki-wataru_starlight-10th-01",
          "icon_mode": "manual_crop",                                    // ポップアップは手動
          "icon_crop": { "x": 770, "y": 340, "width": 320, "height": 300 },
          "has_body_images": false
        }
        // ... 他の衣装も同様
      }
    },
    "tori_test": {
      "idol_slug": "himemiya-tori",
      "output_dir": "himemiya-tori",
      "items": { /* 同様 */ }
    }
    // キャラを増やすときは collections にフォルダごと追記する（コード変更不要）
  }
}
```

### body.crop の決め方（参考）

`body.crop` は全衣装共通の設定です。衣装によって帽子やヘルメットの高さが違うため、
**一番背の高いヘッドパーツに合わせて上方向の余裕を決める**必要があります。

テスト5件では、回転後（縦向き）の画像上でおおよそ次の位置に人物が写っていました。

| 衣装 | 頭頂部 y座標 | 足元下端 y座標 |
| --- | --- | --- |
| 共通衣装 | 約850 | 約1780 |
| Caelum（ヘルメット） | 約620 | 約1780 |
| 黒系衣装 | 約830 | 約1780 |
| ヘッドパーツあり（帽子） | 約760 | 約1780 |

一番高いヘルメット（約620）を基準に、上に少し余裕を足して `crop.y = 580` にしています。
新しい衣装を追加してヘルメット等でこれより高い位置まで達する場合は、
`--debug` の赤枠で頭が切れていないか確認し、`crop.y` をさらに小さくしてください。

- `x`, `y` は左上を原点としたピクセル座標
- `items.<フォルダ名>.icon_crop` は **select.png（元画像）**に対する座標
- `auto_selected_card.search_area` も select.png に対する座標
- `body.crop` は **回転後（縦向き）**の画像に対する座標
- 回転方向が逆だった場合は `body.rotate_degrees` を `-90` または `270` に変更

### 調整の目安

1. `--debug` で枠つき確認画像を出す
2. 自動検出（auto）の赤枠がズレる・出ない → `auto_selected_card.search_area` を選択カード付近に絞る、
   または `green_threshold` を調整
3. 手動（manual）やフォールバックのオレンジ枠がズレる → その衣装の `items.<フォルダ名>.icon_crop` を調整
4. front/back の向きが違えば `body.rotate_degrees` を変更
5. front/back の余白が多すぎ／人物が切れすぎていたら `body.crop` を調整
6. 再度 `--debug` で確認 → OKなら本番実行（既存ファイルは上書きされます）

---

## --debug モード（座標調整用）

```
python tools/costume-image-processor/process_images.py --debug
```

元画像に、現在の切り抜き範囲・探索範囲を枠で描いた確認画像を出力します。

**枠の色:**

- **青枠** … `auto_selected_card.search_area`（自動検出の探索範囲）
- **赤枠** … 自動検出できた選択カード範囲（auto detected）
- **オレンジ枠** … `icon_crop` を使った範囲（フォールバック or 手動 manual_crop）

出力先: `tools/costume-image-processor/debug/`
（ファイル名は「コレクション名_フォルダ名」プレフィックスで、キャラ間で衝突しません）

- `wataru_test_01_common_select_debug.png` … select.png に青枠＋赤/オレンジ枠
- `wataru_test_01_common_front_debug.png` … 回転後の front に body.crop の赤枠
- `wataru_test_01_common_back_debug.png` … 回転後の back に body.crop の赤枠

コンソールにも各フォルダの結果（`auto detected` / `fallback manual crop` / `manual crop`）が表示されます。
赤枠が出ない・ズレる場合は `presets.json` を調整してください。
`--debug` のときは公開用WebP（`public/` 配下）は生成しません（確認画像のみ）。

> `debug/` の画像は元スクショ全体に赤枠を描いたものなので、**非公開扱い**です。
> `.gitignore` で除外済み（コミット・公開されません）。

---

## 対応している衣装

衣装一覧は `presets.json` の `collections.<コレクション名>.items` に定義しています。
現在は `wataru_test`（日々樹 渉・5件）、`tori_test`（姫宮 桃李・5件）、`rei_test`（朔間 零・2件）の3コレクションです。

衣装を増やす場合は該当コレクションの `items` に、キャラを増やす場合は `collections` に
新しいコレクションを追記してください（コード変更は不要）。

### 選択中カードが探索範囲の外にある場合

`auto_selected_card` の探索範囲（`search_area`）は全キャラ共通のため、スクショによっては
選択中カードが範囲外にあり、**別のカードを誤検出**することがあります（黄緑のMVバッジを拾うため、
検出自体は「成功」扱いになるのが罠です）。`--debug` で赤枠が選択中カードを囲んでいるか必ず目視確認し、
ズレている場合はその衣装だけ `icon_mode: "manual_crop"` にして `icon_crop` を選択中カードの位置に合わせてください。

---

## 注意

- 入力ファイルが無い場合はエラーで止まらず、警告を出してスキップします
- `05_locked` は front/back が無い前提なので、icon のみ生成されます
- 出力される WebP には元スクショのメタデータは引き継がれません
- 生成した画像は `public/` 配下なので、これは**公開対象**です（元スクショの `_private/` とは別）
