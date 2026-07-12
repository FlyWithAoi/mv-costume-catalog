"""
MV衣装カタログ Phase 2: 画像加工CLIスクリプト

元スクショ（_private/raw_screenshots/{キャラフォルダ}/）から、
公開用のWebP画像（public/images/costumes/{idol_slug}/）を生成する。
キャラフォルダと衣装一覧は presets.json の collections に定義する（複数キャラ対応）。

処理内容:
  - front.png / back.png: 90度回転で縦向きに直す → プリセットでトリミング
    → 長辺リサイズ → WebP保存（body設定は全衣装共通）
  - select.png: アイコン切り抜き。icon_mode により方法が変わる。
      * auto_selected_card : 選択中カードの黄緑枠を自動検出して切り抜く。
                             失敗したら icon_crop にフォールバック。
      * manual_crop        : icon_crop の座標をそのまま使う（locked詳細ポップアップ等）。

座標・サイズ・閾値・衣装一覧はすべて presets.json に外出ししてあり、
コードを触らず調整できる。追加の重い依存（OpenCV等）は使わず Pillow のみ。

使い方:
    cd L:\\Studio\\02_Projects\\FlyWithAoi\\mv-costume-catalog
    python tools/costume-image-processor/process_images.py

    # 座標・検出範囲を枠で描いた確認画像を出力する
    python tools/costume-image-processor/process_images.py --debug

必要ライブラリ: Pillow ( pip install pillow )
"""

import argparse
import json
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw
except ImportError:
    print("[エラー] Pillow がインストールされていません。")
    print("        次のコマンドでインストールしてください: pip install pillow")
    sys.exit(1)


# --- パス設定（このスクリプトの位置からプロジェクトルートを特定） ---
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]  # tools/costume-image-processor -> tools -> ルート

INPUT_ROOT_BASE = PROJECT_ROOT / "_private" / "raw_screenshots"
OUTPUT_DIR_BASE = PROJECT_ROOT / "public" / "images" / "costumes"
PRESETS_PATH = SCRIPT_DIR / "presets.json"
DEBUG_DIR = SCRIPT_DIR / "debug"

# --debug の枠の色
COLOR_SEARCH = (0, 120, 255)    # 青: 探索範囲
COLOR_AUTO = (255, 0, 0)        # 赤: 自動検出できた選択カード範囲
COLOR_MANUAL = (255, 150, 0)    # オレンジ: icon_crop（フォールバック or 手動）
COLOR_BODY = (255, 0, 0)        # 赤: body crop


def load_presets():
    with open(PRESETS_PATH, encoding="utf-8") as f:
        return json.load(f)


def is_under(child, base):
    """child(resolve後) が base 配下にあるか。パス脱出の二重防御に使う。"""
    try:
        Path(child).resolve().relative_to(Path(base).resolve())
        return True
    except ValueError:
        return False


def clamp_crop_box(box, img_w, img_h):
    """crop座標(x,y,width,height)を画像の範囲内に収めて (left,top,right,bottom) を返す。"""
    x, y, w, h = box["x"], box["y"], box["width"], box["height"]
    left = max(0, min(x, img_w))
    top = max(0, min(y, img_h))
    right = max(left, min(x + w, img_w))
    bottom = max(top, min(y + h, img_h))
    return (left, top, right, bottom)


def resize_long_edge(img, long_edge_px):
    """長辺が long_edge_px になるように縦横比を保ってリサイズ（拡大はしない）。"""
    w, h = img.size
    longest = max(w, h)
    if longest <= long_edge_px:
        return img
    scale = long_edge_px / longest
    new_size = (round(w * scale), round(h * scale))
    return img.resize(new_size, Image.LANCZOS)


def save_webp(img, out_path, quality):
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "WEBP", quality=quality)


# ---------------------------------------------------------------------------
# 選択中カードの自動検出（Pillowのみ）
# ---------------------------------------------------------------------------
def detect_selected_card(select_img, auto_cfg):
    """
    select.png から選択中カードの黄緑枠を検出し、切り抜き用の box(x,y,width,height) を返す。
    検出できなければ None。

    方針:
      - search_area 内のピクセルだけを走査（タイトルバー等の緑を誤検出しないため）
      - green_threshold を満たす黄緑ピクセルの外接矩形を求める
      - padding を足し、正方形に近づけて返す
    """
    im = select_img.convert("RGB")
    W, H = im.size
    sx0, sy0, sx1, sy1 = clamp_crop_box(auto_cfg["search_area"], W, H)

    th = auto_cfg["green_threshold"]
    min_g, max_r, max_b = th["min_g"], th["max_r"], th["max_b"]

    px = im.load()
    min_x = min_y = max_x = max_y = None
    step = 2  # 2pxおきに走査（黄緑枠は太いので十分。速度優先）

    for y in range(sy0, sy1, step):
        for x in range(sx0, sx1, step):
            r, g, b = px[x, y]
            if g >= min_g and r <= max_r and b <= max_b:
                if min_x is None or x < min_x:
                    min_x = x
                if max_x is None or x > max_x:
                    max_x = x
                if min_y is None or y < min_y:
                    min_y = y
                if max_y is None or y > max_y:
                    max_y = y

    if min_x is None:
        return None  # 黄緑ピクセルなし

    w = max_x - min_x
    h = max_y - min_y
    if w < auto_cfg.get("min_box_width", 0) or h < auto_cfg.get("min_box_height", 0):
        return None  # 小さすぎ（ノイズとみなす）

    pad = auto_cfg.get("padding", 0)
    bx = min_x - pad
    by = min_y - pad
    bw = w + 2 * pad
    bh = h + 2 * pad

    # 正方形に近づける（中心を保って長辺に合わせる）
    side = max(bw, bh)
    cx = bx + bw / 2
    cy = by + bh / 2
    return {
        "x": round(cx - side / 2),
        "y": round(cy - side / 2),
        "width": side,
        "height": side,
    }


def resolve_icon_box(select_img, entry, presets):
    """
    icon_mode に従って、実際に使う切り抜き box と、その方法を返す。
    戻り値: (box, method)  method は "auto" / "fallback" / "manual"
    """
    mode = entry.get("icon_mode", "manual_crop")
    if mode == "auto_selected_card":
        auto_cfg = presets.get("auto_selected_card")
        box = None
        if auto_cfg:
            try:
                box = detect_selected_card(select_img, auto_cfg)
            except Exception:
                box = None
        if box is not None:
            return box, "auto"
        return entry["icon_crop"], "fallback"
    # manual_crop
    return entry["icon_crop"], "manual"


# ---------------------------------------------------------------------------
# 本番処理
# ---------------------------------------------------------------------------
def process_icon(select_src, out_path, entry, presets):
    """select.png からアイコンを切り抜いてWebP保存。戻り値は使った method。"""
    out_cfg = presets["output"]
    with Image.open(select_src) as im:
        im = im.convert("RGB")
        box, method = resolve_icon_box(im, entry, presets)
        left, top, right, bottom = clamp_crop_box(box, im.width, im.height)
        icon = im.crop((left, top, right, bottom))
        icon = resize_long_edge(icon, out_cfg["icon_size"])
        save_webp(icon, out_path, out_cfg["webp_quality"])
    return method


def process_body(src_path, out_path, presets):
    """front/back を回転→トリミング→リサイズしてWebP保存。"""
    out_cfg = presets["output"]
    body_cfg = presets["body"]
    with Image.open(src_path) as im:
        im = im.convert("RGB")
        rotated = im.rotate(body_cfg["rotate_degrees"], expand=True)
        box = clamp_crop_box(body_cfg["crop"], rotated.width, rotated.height)
        cropped = rotated.crop(box)
        cropped = resize_long_edge(cropped, out_cfg["long_edge_body"])
        save_webp(cropped, out_path, out_cfg["webp_quality"])


# ---------------------------------------------------------------------------
# デバッグ描画
# ---------------------------------------------------------------------------
def draw_boxes(base_img, boxes, out_path):
    """base_img に (box, color) を順に描いてPNG保存。boxes は [(box, color), ...]。"""
    dbg = base_img.convert("RGB").copy()
    draw = ImageDraw.Draw(dbg)
    line_w = max(3, round(max(dbg.size) / 300))
    for box, color in boxes:
        left, top, right, bottom = clamp_crop_box(box, dbg.width, dbg.height)
        draw.rectangle([left, top, right - 1, bottom - 1], outline=color, width=line_w)
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    dbg.save(out_path, "PNG")


def debug_icon(select_src, prefix, entry, presets):
    """select.png に探索範囲(青)・自動検出(赤)・icon_crop(オレンジ)を描く。戻り値は method。"""
    with Image.open(select_src) as im:
        im = im.convert("RGB")
        box, method = resolve_icon_box(im, entry, presets)
        boxes = []
        # auto モードなら探索範囲を青で表示
        if entry.get("icon_mode") == "auto_selected_card":
            auto_cfg = presets.get("auto_selected_card")
            if auto_cfg:
                boxes.append((auto_cfg["search_area"], COLOR_SEARCH))
        # 実際に使う box を色分け
        if method == "auto":
            boxes.append((box, COLOR_AUTO))        # 赤: 自動検出
        else:
            boxes.append((box, COLOR_MANUAL))      # オレンジ: フォールバック or 手動
        out = DEBUG_DIR / f"{prefix}_select_debug.png"
        draw_boxes(im, boxes, out)
        return out.name, method


def debug_body(src_path, prefix, kind, presets):
    """front/back を回転した画像に body.crop の赤枠を描く。"""
    body_cfg = presets["body"]
    with Image.open(src_path) as im:
        rotated = im.convert("RGB").rotate(body_cfg["rotate_degrees"], expand=True)
        out = DEBUG_DIR / f"{prefix}_{kind}_debug.png"
        draw_boxes(rotated, [(body_cfg["crop"], COLOR_BODY)], out)
        return out.name


# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="MV衣装カタログ 画像加工スクリプト")
    parser.add_argument(
        "--debug",
        action="store_true",
        help="切り抜き範囲・探索範囲を枠で描いた確認画像を debug/ に出力する",
    )
    parser.add_argument(
        "--collection",
        action="append",
        default=None,
        metavar="NAME",
        help="処理対象の collection を限定する（複数指定可）",
    )
    parser.add_argument(
        "--item",
        action="append",
        default=None,
        metavar="FOLDER",
        help="処理対象の衣装フォルダ名を限定する（複数指定可、例: 17_bloom-idol）",
    )
    parser.add_argument(
        "--icons-only",
        action="store_true",
        help="アイコン（select.png由来）だけ生成し、front/backは再生成しない",
    )
    parser.add_argument(
        "--body-only",
        action="store_true",
        help="front/back だけ生成し、アイコンは再生成しない",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="出力先WebPが既にあるものはスキップする",
    )
    args = parser.parse_args()

    if args.icons_only and args.body_only:
        print("[エラー] --icons-only と --body-only は同時に指定できません。")
        sys.exit(1)

    print("=" * 60)
    print("MV衣装カタログ Phase 2: 画像加工スクリプト" + ("  [DEBUGモード]" if args.debug else ""))
    print("=" * 60)
    print(f"入力元 : {INPUT_ROOT_BASE}/(collections)")
    print(f"出力先 : {DEBUG_DIR}  (確認画像)" if args.debug else f"出力先 : {OUTPUT_DIR_BASE}/(idol_slug)")
    if args.debug:
        print("枠の色 : 青=探索範囲 / 赤=自動検出 / オレンジ=icon_crop(フォールバック or 手動)")
    print()

    if not PRESETS_PATH.exists():
        print(f"[エラー] presets.json が見つかりません: {PRESETS_PATH}")
        sys.exit(1)
    presets = load_presets()
    collections = presets.get("collections", {})
    if not collections:
        print("[エラー] presets.json の collections が空です。")
        sys.exit(1)

    if args.collection:
        unknown = [c for c in args.collection if c not in collections]
        if unknown:
            print(f"[エラー] presets.json にない collection が指定されました: {unknown}")
            print(f"         利用可能: {sorted(collections)}")
            sys.exit(1)
        collections = {k: v for k, v in collections.items() if k in args.collection}

    generated = []   # 生成できたファイル
    skipped = []     # スキップ（理由つき）
    icon_results = []  # (collection/folder, method) アイコンの検出結果

    for coll_name, coll in collections.items():
        input_root = INPUT_ROOT_BASE / coll.get("input_dir", coll_name)
        output_dir = OUTPUT_DIR_BASE / coll.get("output_dir", coll.get("idol_slug", coll_name))
        # 二重防御: presets.json の値が不正でも、規定のルート外は読み書きしない
        if not is_under(input_root, INPUT_ROOT_BASE):
            print(f"[エラー] {coll_name}: input_dir が {INPUT_ROOT_BASE} の外を指しています: {input_root}")
            sys.exit(1)
        if not is_under(output_dir, OUTPUT_DIR_BASE):
            print(f"[エラー] {coll_name}: output_dir が {OUTPUT_DIR_BASE} の外を指しています: {output_dir}")
            sys.exit(1)
        items = coll.get("items", {})

        print(f"===== コレクション: {coll_name} -> {output_dir.name}/ =====")
        if not input_root.exists():
            msg = f"{coll_name}: 入力フォルダなし ({input_root}) → コレクションごとスキップ"
            print(f"  [警告] {msg}")
            skipped.append(msg)
            print()
            continue
        if not items:
            print(f"  (items が空。presets.json に衣装を追加してください)")
            print()
            continue
        print()

        if args.item:
            items = {k: v for k, v in items.items() if k in args.item}
            if not items:
                print(f"  (--item に一致する衣装がありません)")
                print()
                continue

        for folder_name, entry in items.items():
            folder = input_root / folder_name
            if not is_under(folder, input_root):
                print(f"[エラー] {coll_name}/{folder_name}: 衣装フォルダ名が入力ルートの外を指しています")
                sys.exit(1)
            cid = entry["id"]
            label = f"{coll_name}/{folder_name}"
            print(f"--- {label} ({cid}) ---")

            if not folder.exists():
                msg = f"{label}: フォルダなし → スキップ"
                print(f"  [警告] {msg}")
                skipped.append(msg)
                print()
                continue

            # 1. アイコン（select.png）
            select_src = folder / "select.png"
            if args.body_only:
                print("  (--body-only のためアイコンをスキップ)")
            elif (args.skip_existing and not args.debug
                    and (output_dir / f"{cid}_icon.webp").exists()):
                print(f"  (icon は既存のためスキップ: {cid}_icon.webp)")
            elif select_src.exists():
                try:
                    if args.debug:
                        prefix = f"{coll_name}_{folder_name}"
                        name, method = debug_icon(select_src, prefix, entry, presets)
                        print(f"  [OK] debug icon  -> {name}   [{_method_label(method)}]")
                        generated.append(name)
                    else:
                        icon_out = output_dir / f"{cid}_icon.webp"
                        method = process_icon(select_src, icon_out, entry, presets)
                        print(f"  [OK] icon  -> {icon_out.name}   [{_method_label(method)}]")
                        generated.append(icon_out.name)
                    icon_results.append((label, method))
                except Exception as e:
                    msg = f"{label}/select.png: 処理失敗 ({e})"
                    print(f"  [警告] {msg}")
                    skipped.append(msg)
            else:
                msg = f"{label}/select.png: なし → アイコンをスキップ"
                print(f"  [警告] {msg}")
                skipped.append(msg)

            # 2. front / back
            if args.icons_only:
                print("  (--icons-only のため front/back をスキップ)")
            elif entry.get("has_body_images"):
                for kind in ("front", "back"):
                    body_src = folder / f"{kind}.png"
                    if (args.skip_existing and not args.debug
                            and (output_dir / f"{cid}_{kind}.webp").exists()):
                        print(f"  ({kind} は既存のためスキップ: {cid}_{kind}.webp)")
                        continue
                    if body_src.exists():
                        try:
                            if args.debug:
                                prefix = f"{coll_name}_{folder_name}"
                                name = debug_body(body_src, prefix, kind, presets)
                                print(f"  [OK] debug {kind:5s} -> {name}")
                                generated.append(name)
                            else:
                                body_out = output_dir / f"{cid}_{kind}.webp"
                                process_body(body_src, body_out, presets)
                                print(f"  [OK] {kind:5s} -> {body_out.name}")
                                generated.append(body_out.name)
                        except Exception as e:
                            msg = f"{label}/{kind}.png: 処理失敗 ({e})"
                            print(f"  [警告] {msg}")
                            skipped.append(msg)
                    else:
                        msg = f"{label}/{kind}.png: なし → スキップ"
                        print(f"  [警告] {msg}")
                        skipped.append(msg)
            else:
                print("  (この衣装は front/back なし設定)")

            print()

    # --- サマリ ---
    print("=" * 60)
    label = "確認画像" if args.debug else "画像"
    print(f"生成した{label}: {len(generated)}件 / スキップ: {len(skipped)}件")
    print("=" * 60)

    if icon_results:
        print("[アイコン検出結果]")
        for folder_name, method in icon_results:
            print(f"  - {folder_name}: {_method_label(method)}")
        print()

    if generated:
        print(f"[生成した{label}]")
        for name in generated:
            print(f"  - {name}")
    if skipped:
        print("[スキップ]")
        for m in skipped:
            print(f"  - {m}")
    if args.debug:
        print()
        print(f"確認画像フォルダ: {DEBUG_DIR}")
        print("青枠=探索範囲 / 赤枠=自動検出 / オレンジ枠=icon_crop。")
        print("赤枠がズレる・出ない場合は presets.json の auto_selected_card や icon_crop を調整してください。")


def _method_label(method):
    return {
        "auto": "auto detected",
        "fallback": "fallback manual crop",
        "manual": "manual crop",
    }.get(method, method)


if __name__ == "__main__":
    main()
