# -*- coding: utf-8 -*-
"""_private/raw_screenshots/{idol_slug}/ の親フォルダ生成補助ツール

public/data/idols.json に登録されている全idolについて、
raw_screenshots 直下に idol_slug 名の空フォルダを作るだけのスクリプト。

- 衣装サブフォルダ（01_common など）は作らない
- 既存フォルダは上書き・削除しない（skip する）
- ファイルの削除・移動は行わない
- 標準ライブラリのみ使用
"""

import argparse
import json
import sys
from pathlib import Path

# このファイルは tools/raw-folder-generator/ にある想定なので、
# 2つ上がプロジェクトルート
DEFAULT_ROOT = Path(__file__).resolve().parent.parent.parent

IDOLS_JSON_RELATIVE = Path("public") / "data" / "idols.json"
RAW_SCREENSHOTS_RELATIVE = Path("_private") / "raw_screenshots"


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description="public/data/idols.json を元に _private/raw_screenshots/{idol_slug}/ を作成する"
    )
    parser.add_argument(
        "--root",
        type=str,
        default=str(DEFAULT_ROOT),
        help="リポジトリルートのパス（デフォルト: このスクリプトから自動判定）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="実際にはフォルダを作成せず、作成予定だけ表示する",
    )
    return parser.parse_args(argv)


def load_idol_slugs(idols_json_path: Path):
    if not idols_json_path.is_file():
        raise FileNotFoundError(f"idols.json が見つかりません: {idols_json_path}")

    with open(idols_json_path, encoding="utf-8") as f:
        data = json.load(f)

    idols = data.get("idols")
    if not isinstance(idols, list):
        raise ValueError(f"idols.json の形式が想定と異なります（idols配列がありません）: {idols_json_path}")

    slugs = []
    for i, idol in enumerate(idols):
        slug = idol.get("slug") if isinstance(idol, dict) else None
        if not slug or not isinstance(slug, str):
            raise ValueError(f"idols.json の {i} 番目の要素に有効な slug がありません")
        slugs.append(slug)

    return slugs


def main(argv=None):
    # Windows環境（PowerShell等）でコンソールの既定コードページが原因で
    # 日本語出力が文字化けするのを防ぐため、標準出力をUTF-8に固定する。
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

    args = parse_args(argv if argv is not None else sys.argv[1:])

    root = Path(args.root).resolve()
    idols_json_path = root / IDOLS_JSON_RELATIVE
    raw_screenshots_dir = root / RAW_SCREENSHOTS_RELATIVE

    try:
        slugs = load_idol_slugs(idols_json_path)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 1

    if args.dry_run:
        print(f"[dry-run] リポジトリルート: {root}")
        print(f"[dry-run] idols.json: {idols_json_path}")
        print(f"[dry-run] raw_screenshots ルート: {raw_screenshots_dir}")
        print(f"[dry-run] 対象idol数: {len(slugs)}")
        print()

    created = 0
    skipped = 0

    for slug in slugs:
        target_dir = raw_screenshots_dir / slug

        if target_dir.exists():
            print(f"skip    : {target_dir}")
            skipped += 1
            continue

        if args.dry_run:
            print(f"[dry-run] created (予定): {target_dir}")
            created += 1
            continue

        try:
            target_dir.mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            # 実行中に他プロセスが作成した等、極めて稀なケース
            print(f"skip    : {target_dir}")
            skipped += 1
            continue
        except OSError as e:
            print(f"エラー: フォルダを作成できませんでした: {target_dir}\n  {e}", file=sys.stderr)
            return 1

        print(f"created : {target_dir}")
        created += 1

    print()
    print(f"対象idol数: {len(slugs)}")
    print(f"作成数    : {created}{'（dry-run）' if args.dry_run else ''}")
    print(f"既存数    : {skipped}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
