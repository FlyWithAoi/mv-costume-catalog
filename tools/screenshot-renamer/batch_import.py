# -*- coding: utf-8 -*-
"""バッチ取り込みモード CLI。

使い方:
    cd L:\\Studio\\02_Projects\\FlyWithAoi\\mv-costume-catalog

    # 検証のみ
    python tools/screenshot-renamer/batch_import.py validate manifest.json

    # 何も書き込まずに適用内容を表示
    python tools/screenshot-renamer/batch_import.py dry-run manifest.json

    # raw へコピー（実行前に確認あり。--yes で確認スキップ）
    python tools/screenshot-renamer/batch_import.py apply manifest.json

    # presets.json への差分プレビュー / 書き込み
    python tools/screenshot-renamer/batch_import.py gen-presets manifest.json
    python tools/screenshot-renamer/batch_import.py gen-presets manifest.json --write

    # costumes.json への差分プレビュー / 書き込み
    python tools/screenshot-renamer/batch_import.py gen-costumes manifest.json
    python tools/screenshot-renamer/batch_import.py gen-costumes manifest.json --write

    # 途中失敗ログの確認
    python tools/screenshot-renamer/batch_import.py check-logs
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import batch_core as core  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Windows コンソール(cp932)でも落ちないようにする
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")
    sys.stderr.reconfigure(errors="replace")


def _load(args):
    ctx = core.BatchContext(args.root)
    manifest = core.load_manifest(args.manifest)
    errors, warnings, plan = core.validate_manifest(manifest, ctx)
    return ctx, manifest, errors, warnings, plan


def _print_issues(errors, warnings):
    for w in warnings:
        print(f"[警告] {w}")
    for e in errors:
        print(f"[エラー] {e}")
    print()
    print(f"エラー {len(errors)}件 / 警告 {len(warnings)}件")


def cmd_validate(args):
    _, _, errors, warnings, plan = _load(args)
    _print_issues(errors, warnings)
    print(f"衣装数 {len(plan)}件")
    return 1 if errors else 0


def cmd_dry_run(args):
    ctx, manifest, errors, warnings, plan = _load(args)
    print(core.dry_run_report(manifest, errors, warnings, plan, ctx))
    return 1 if errors else 0


def cmd_apply(args):
    ctx, manifest, errors, warnings, plan = _load(args)
    if errors:
        _print_issues(errors, warnings)
        print("\nエラーがあるため apply できません。")
        return 1
    applied = [p for p in plan if p.already_applied]
    if applied:
        for p in applied:
            print(f"[適用済み] slot {p.slot:02d}: {p.dest_dir}")
        print("\n適用済みのスロットがあるため apply しません（上書き禁止）。")
        print("presets / costumes の生成には gen-presets / gen-costumes を使ってください。")
        return 1
    incomplete = core.find_incomplete_logs(ctx)
    if incomplete:
        print("[警告] 途中失敗した過去の apply ログがあります:")
        for f, st in incomplete:
            print(f"  - {f} (status={st})")
        print("内容を確認してから続行してください。")
    print(core.dry_run_report(manifest, errors, warnings, plan, ctx))
    if not args.yes:
        answer = input("\nrawへコピーします。よろしいですか？ [y/N]: ").strip().lower()
        if answer != "y":
            print("中止しました。ファイルは変更されていません。")
            return 0
    copied, log_path = core.apply_plan(manifest, plan, ctx)
    print(f"\n{len(copied)}ファイルをコピーしました。")
    print(f"ログ: {log_path}")
    return 0


def cmd_gen_presets(args):
    ctx, manifest, errors, warnings, plan = _load(args)
    if errors:
        _print_issues(errors, warnings)
        print("\nエラーがあるため生成できません。")
        return 1
    new_presets, diff, gen_warnings = core.build_presets_update(manifest, plan, ctx)
    for w in gen_warnings:
        print(f"[警告] {w}")
    if not diff:
        print("presets.json に差分はありません。")
        return 0
    print(diff)
    if args.write:
        if not args.yes:
            answer = input("presets.json に書き込みますか？ [y/N]: ").strip().lower()
            if answer != "y":
                print("中止しました。")
                return 0
        core.write_json_atomic(ctx.presets_path, new_presets)
        print(f"書き込みました: {ctx.presets_path}")
    else:
        print("\n（プレビューのみ。書き込むには --write を付けてください）")
    return 0


def cmd_gen_costumes(args):
    ctx, manifest, errors, warnings, plan = _load(args)
    if errors:
        _print_issues(errors, warnings)
        print("\nエラーがあるため生成できません。")
        return 1
    new_doc, diff, missing_images = core.build_costumes_update(manifest, plan, ctx)
    for m in missing_images:
        print(f"[画像不足] {m}")
    if not diff:
        print("costumes.json に差分はありません。")
        return 0
    print(diff)
    if args.write:
        if missing_images and not args.allow_missing_images:
            print(f"\n[エラー] 参照するWebPが {len(missing_images)}件 不足しているため書き込みません。")
            print("process_images.py で画像を生成してから再実行してください。")
            print("（緊急時のみ --allow-missing-images で強行できます）")
            return 1
        if not args.yes:
            answer = input("costumes.json に書き込みますか？ [y/N]: ").strip().lower()
            if answer != "y":
                print("中止しました。")
                return 0
        core.write_json_atomic(ctx.costumes_path, new_doc)
        print(f"書き込みました: {ctx.costumes_path}")
    else:
        print("\n（プレビューのみ。書き込むには --write を付けてください）")
    return 0


def cmd_check_logs(args):
    ctx = core.BatchContext(args.root)
    incomplete = core.find_incomplete_logs(ctx)
    if not incomplete:
        print("途中失敗した apply ログはありません。")
        return 0
    print("途中失敗（または不明状態）の apply ログ:")
    for f, st in incomplete:
        print(f"  - {f} (status={st})")
    return 1


def main(argv=None):
    parser = argparse.ArgumentParser(description="MV衣装カタログ バッチ取り込みCLI")
    parser.add_argument("--root", default=str(PROJECT_ROOT),
                        help="プロジェクトルート（テスト用）")
    sub = parser.add_subparsers(dest="command", required=True)

    for name, fn, needs_manifest in [
        ("validate", cmd_validate, True),
        ("dry-run", cmd_dry_run, True),
        ("apply", cmd_apply, True),
        ("gen-presets", cmd_gen_presets, True),
        ("gen-costumes", cmd_gen_costumes, True),
        ("check-logs", cmd_check_logs, False),
    ]:
        p = sub.add_parser(name)
        p.set_defaults(func=fn)
        if needs_manifest:
            p.add_argument("manifest")
            p.add_argument("--yes", action="store_true", help="確認プロンプトをスキップ")
        if name in ("gen-presets", "gen-costumes"):
            p.add_argument("--write", action="store_true", help="差分を実ファイルへ書き込む")
        if name == "gen-costumes":
            p.add_argument("--allow-missing-images", action="store_true",
                           help="参照WebPが未生成でも書き込みを許可する（通常は使わない）")

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except core.ManifestError as e:
        print(f"[エラー] {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
