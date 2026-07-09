# raw_screenshots 本番移行計画

`_private/raw_screenshots/` の `*_test` フォルダ（`wataru_test` / `tori_test` / `rei_test` / `hajime_test`）を、本番用の `idol_slug` フォルダ名へ移行するための計画メモです。

このドキュメントは**計画**であり、この文書自体の追加によってファイル移動・コピー・削除・JSON編集は行っていません。実際の移行作業は、この計画をもとに別ステップで進めます。

対象コミット基準: `3bf063f docs: add costume group rules`

---

## 1. 背景・目的

- 衣装データの入力元は `_private/raw_screenshots/{collection}/{item}/` に `select.png` / `front.png` / `back.png` を置く形。
- 現状の `collection` フォルダ名がテスト時の仮名（`wataru_test` など）のままになっている。
- 本番運用に入る前に、`collection` フォルダ名と `presets.json` の `collections` キーを本番の `idol_slug` に揃えておきたい。

---

## 2. 最重要ポイント：公開側は変更不要

データの流れ:

```
_private/raw_screenshots/{collection}/{item}/{select,front,back}.png   ← 「_test」が付いているのはここだけ
        ↓ process_images.py（presets.json の指示に従う）
public/images/costumes/{output_dir}/{id}_icon.webp など               ← すでに本番命名（hibiki-wataru 等）
        ↓ 参照
public/data/costumes.json                                              ← webpファイル名と id を参照
```

`presets.json` の `items` は、すでに `id`（例: `hibiki-wataru_common-01`）と `output_dir`（例: `hibiki-wataru`）を本番命名で持っている。`_test` が残っているのは、

- raw の `collection` フォルダ名（`_private/raw_screenshots/wataru_test/` など）
- `presets.json` の `collections` キー（`"wataru_test": { ... }`）

の2箇所だけ。

**したがって今回の移行は「raw フォルダ名」と「presets.json の collection / item キー」だけを整理すればよく、`public/images/` の webp ファイルや `public/data/costumes.json` は一切変更不要。** `id` を変えない限り、再生成しても出力ファイル名は変わらない。

---

## 3. collection名の移行方針

| 旧（raw フォルダ名 / presets collection キー） | 新（本番 idol_slug） |
|---|---|
| `wataru_test` | `hibiki-wataru` |
| `tori_test` | `himemiya-tori` |
| `rei_test` | `sakuma-rei` |
| `hajime_test` | `shino-hajime` |

`output_dir`（`public/images/costumes/` 配下の出力先）がすでに同じ名前なので、raw 側と出力側のフォルダ名が揃い、対応関係が読みやすくなる。

---

## 4. 変更する対象・しない対象

| 対象 | 変更 | 理由 |
|---|:---:|---|
| raw の collection フォルダ名 | 変更する | `wataru_test` → `hibiki-wataru` など |
| raw の衣装サブフォルダ名 | 変更する（必要な範囲で） | 日本語表記ゆれ・番号整理のため（6章） |
| `presets.json` の `collections` キー | 変更する（raw フォルダ名と同期） | raw フォルダ名とキーが一致していないと処理対象を見失う |
| `presets.json` の `items` キー | 変更する（raw サブフォルダ改名時のみ） | raw サブフォルダ名と一致させる必要がある |
| `presets.json` の `id` / `output_dir` / `icon_crop` など | **変更しない** | 出力 webp のファイル名を変えないため |
| `public/images/costumes/**/*.webp` | **変更しない** | すでに本番命名。`id` が不変なので再生成しても同名になる |
| `public/data/costumes.json` | **変更しない** | webp ファイル名と `id` を参照するのみで、raw フォルダ名には依存しない |

補足: フォルダ番号（`NN_`）と `id` 末尾の連番（例: `common-01` の `-01`）は別物。前者は試着室内の位置、後者はその衣装スラッグの通し番号。今回 `id` 自体は変更しないため、`-01` はそのまま。

---

## 5. フォルダ命名ルール

- **日本語フォルダ名は使わない**。半角英数字・ハイフン・アンダーバーのみを使用する。
  - 例: `geisyunHisho` → `geishun-hisho`
- **日本語の衣装名は `costumes.json` の `costume_name` に残す**。フォルダ名を日本語から英語スラッグに変えても、表示上の日本語名（例: 「迎春飛翔」「共通アイドル衣装（SCR）」）はそのまま `costume_name` に維持される。フォルダ名の変更は表示内容に影響しない。
- サブフォルダ名は、可能な範囲で `id` の衣装スラッグ部分（`hibiki-wataru_black-01` の `black` 部分など）に合わせ、フォルダ名から webp の対応が読み取りやすいようにする。

---

## 6. フォルダ番号の付け方

- **番号は試着室画面での表示位置に対応する値であり、衣装カテゴリ（common / unit / event など）とは独立している。** `01` が必ず共通アイドル衣装、`02` が必ずユニット衣装になるわけではない。試着室内でその衣装がどこに表示されているか（左上から右へ、次の段へ進む順）だけで番号が決まる。
- 基本方針: **試着室画面の左上から右へ、右端まで行ったら次の段へ進む順番**で番号を振る。
- ただし、**既存の番号がすでに試着室内の位置を反映している場合は、その番号をそのまま使い、欠番を許容する**。
  - 例: `rei_test` は現状 `02_caelum` と `11_commonSCR` のように番号が飛んでいる。これは「試着室内の位置＝番号」という運用を反映している可能性が高く、無理に `01/02` へ詰め直す必要はない。
  - 詰め直すかどうかは、実際に試着室画面を見て位置を確認したうえで判断する（このドキュメント内では未確定）。
- フォルダ番号はあくまで**キャラ内でのローカルな番号**であり、全キャラ共通の通し番号としては扱わない（`docs/publish-checklist.md` 7章と同じ方針）。

### 衣装カテゴリが同じでも、キャラによって番号が変わる例

番号は表示位置だけで決まるため、同じ「共通アイドル衣装」でもキャラによって `01` だったり `02` だったりする。

```text
既存アイドルの例:
01_geishun-hisho
02_common
03_trickstar

MELLOW DEAR USの例:
01_common
02_mellow-dear-us

先生の例:
01_rain-bow
02_uta-no-ojisan
```

- 迎春飛翔（正月限定衣装）が試着室の左上1番に表示されるキャラは `01_geishun-hisho` となり、共通アイドル衣装はその分ずれて `02_common` になる（既存アイドルの一部で確認済み。7章参照）。
- MELLOW DEAR US の4人は迎春飛翔衣装を持っていないため、`01_common` から始まり、ユニット衣装（MELLOW DEAR US）が `02_mellow-dear-us` になる。
- 先生2人（Jin & Akiomi）は共通アイドル衣装を持っていないため、`01` から先生固有の衣装（例: `01_rain-bow`）になり、`02_uta-no-ojisan` のように続く。

### サブフォルダの作成タイミング

- 全idolの親フォルダ（`_private/raw_screenshots/{idol_slug}/`）は raw-folder-generator であらかじめ作成済みとする。
- 衣装サブフォルダ（`NN_costume-slug/`）は自動生成しない。実際にスクショを取得したタイミングで、試着室の表示位置を確認しながら個別に作成する（先に番号だけ決め打ちしない）。

---

## 7. 移行表

`✅` = 画像あり、`空` = 空フォルダ。

> ⚠️ **本章の「新フォルダ」列の番号はすべて仮番号です。** 6章の方針どおり、番号は「試着室画面での表示位置」に対応するべきであり、衣装カテゴリ（common/unitなど）とは無関係です。実際の移行時には、必ず試着室画面を確認してから番号を確定してください。現時点で試着室の表示位置が判明しているのは shino-hajime の一部のみです（下記参照）。それ以外（hibiki-wataru / himemiya-tori / sakuma-rei）の番号は、旧フォルダ番号をそのまま踏襲した**未確認の仮番号**であり、衣装カテゴリと番号の対応関係を示すものではありません。

### hibiki-wataru（← wataru_test）

番号は旧フォルダをそのまま踏襲した仮番号。試着室位置は未確認。

| 旧フォルダ | costume_name（不変） | id（不変） | 新フォルダ（提案・番号は仮） |
|---|---|---|---|
| `01_common` ✅ | 共通アイドル衣装 | `hibiki-wataru_common-01` | `01_common`（仮） |
| `02_caelum` ✅ | Caelum | `hibiki-wataru_caelum-01` | `02_caelum`（仮） |
| `03_black` ✅ | 黒系衣装（仮） | `hibiki-wataru_black-01` | `03_black`（仮） |
| `04_headparts` ✅ | ヘッドパーツあり衣装（仮） | `hibiki-wataru_headparts-01` | `04_headparts`（仮） |
| `05_locked` ✅ | スタライ10thライブTシャツ | `hibiki-wataru_starlight-10th-01` | `05_starlight-10th`（仮） |

### himemiya-tori（← tori_test）

番号は旧フォルダをそのまま踏襲した仮番号。試着室位置は未確認。

| 旧フォルダ | costume_name（不変） | id（不変） | 新フォルダ（提案・番号は仮） |
|---|---|---|---|
| `01_common` ✅ | 共通アイドル衣装 | `himemiya-tori_common-01` | `01_common`（仮） |
| `02_caelum` 空 | （準備中・costumes.json未登録） | `himemiya-tori_caelum-01` | `02_caelum`（空のまま保留、番号は仮） |
| `03_black` ✅ | Musica | `himemiya-tori_musica-01` | `03_musica`（仮） |
| `04_headparts` ✅ | エゴイスト | `himemiya-tori_egoist-01` | `04_egoist`（仮） |
| `05_locked` ✅ | ニューイヤーライズ（白銀） | `himemiya-tori_newyear-rise-01` | `05_newyear-rise`（仮） |

### sakuma-rei（← rei_test）

番号は旧フォルダをそのまま踏襲した仮番号。試着室位置は未確認。

| 旧フォルダ | costume_name（不変） | id（不変） | 新フォルダ（提案・番号は仮） |
|---|---|---|---|
| `02_caelum` ✅ | Caelum | `sakuma-rei_caelum-01` | `02_caelum`（仮。試着室位置要確認） |
| `11_commonSCR` ✅ | 共通アイドル衣装（SCR） | `sakuma-rei_common-scr-01` | `11_common-scr`（仮。試着室位置要確認） |

> rei は捕捉2件のみで番号が飛んでいる。位置ベースの番号なら現番号を維持（欠番はそのまま）、単なる作業順であれば `01/02` に詰めることも可能。試着室を確認してから決める。

### shino-hajime（← hajime_test）

現時点で判明している範囲の試着室表示位置を反映済み。迎春飛翔が試着室左上1番のため、共通アイドル衣装・Ra*bits衣装の番号がそれぞれ1つずつ後ろにずれる。`05_locked`（共通アイドル衣装SCR）のみ、実際の試着室位置が未確認のため番号は決めていない。

| 旧フォルダ | costume_name（不変） | id（不変） | 新フォルダ（提案） |
|---|---|---|---|
| `03_geisyunHisho` ✅ | 迎春飛翔 | `shino-hajime_geishun-hisho-01` | `01_geishun-hisho`（試着室左上1番） |
| `01_common` ✅ | 共通アイドル衣装 | `shino-hajime_common-01` | `02_common` |
| `02_unit` ✅ | Ra*bits衣装 | `shino-hajime_rabits-01` | `03_rabits` |
| `05_locked` ✅ | 共通アイドル衣装（SCR） | `shino-hajime_common-scr-01` | 番号要確認（試着室位置が未確認のため未確定） |
| `04_headparts` 空 | （孤立フォルダ・presets/costumes.json未登録） | — | 移行しない（要確認のうえ削除候補） |

### 移行対象外（今回の計画に含めない）

| フォルダ | 内容 | 扱い |
|---|---|---|
| `99_tmp` | 未整理スクショ12枚 | どのキャラにも未紐付け。別途仕分けが必要 |
| `back2.png` / `back3.png` / `front2.png` / `select2.png` / `select3.png` など | 予備・重複ショット | processor は正規名（`select.png`/`front.png`/`back.png`）のみ使用。害はないが未使用ファイルとして残る |

---

## 8. 安全なコピー手順（実行はまだしない）

`_private/` は `.gitignore` 対象のため、Git 履歴による復元が効かない。そのため「削除せずコピー」と「事前バックアップ」を徹底する。

1. **バックアップ**: `_private/raw_screenshots/` 全体を `_private/raw_screenshots_backup_YYYYMMDD/` へ丸ごとコピーする。
2. **新フォルダへコピー**: 各 `*_test` の中身を新しい collection 名フォルダへ**コピー**する（move ではなく copy）。旧 `*_test` フォルダはこの時点では削除しない。コピーと同時に、サブフォルダ名を移行表の新名にリネームする。
3. **`presets.json` 更新**: `collections` キーと `items` キーだけを新しい名前に合わせて変更する（`id` / `output_dir` / `icon_crop` は変更しない）。この編集は別途ユーザーの承認を得たうえで行う。
4. **debug検証**: `python tools/costume-image-processor/process_images.py --debug` を実行し、`tools/costume-image-processor/debug/` の枠（赤枠・オレンジ枠）が従来どおり衣装アイコンを囲んでいるか目視確認する。
5. **本番生成**: `--debug` なしで実行し、出力 webp のファイル名・内容が従来と変わっていないことを確認する（`id` が不変なので、実質「差分が無いこと」を確認する作業になる）。
6. **表示確認**: ローカルサーバーで表示を確認する（`docs/publish-checklist.md` 2章の手順）。
   ```powershell
   cd public
   python -m http.server 8000
   ```
7. **旧フォルダ削除は別ステップとする**。上記1〜6がすべて問題ないことを確認したうえで、**明示的な承認を得てから**、`*_test` フォルダとバックアップフォルダの要否を判断して削除する。このドキュメントの範囲では削除しない。

---

## 9. 未確定事項（着手前に決めること）

- `sakuma-rei` の新フォルダ番号を、現状の位置ベース（`02` / `11` のまま）にするか、作業順に詰める（`01` / `02`）かの最終判断。
- `himemiya-tori/02_caelum`（空フォルダ、`presets.json` に定義済みだが `costumes.json` 未登録）をどう扱うか。画像が用意でき次第、そのまま移行して使う想定。
- `shino-hajime/04_headparts`（空フォルダ、`presets.json` / `costumes.json` ともに未登録の孤立フォルダ）を移行するか、削除候補として保留するか。
- `shino-hajime/05_locked`（共通アイドル衣装SCR）の新フォルダ番号。試着室位置が未確認のため、実際の試着室画面を確認してから番号を確定する。
- `hibiki-wataru` / `himemiya-tori` の新フォルダ番号（7章で「仮」としているすべての行）。試着室画面での実際の表示位置は未確認のため、移行時に確認してから確定する。
