# -*- coding: utf-8 -*-
"""バッチ取り込みモードのコアロジック。

AI等が作成した確定済み manifest.json を読み込み、
  1. 検証（エラー / 警告）
  2. 適用計画（コピー元→コピー先）の作成
  3. raw への安全コピー（コピーのみ・上書きなし・ログつき）
  4. presets.json 用 collection の生成と差分プレビュー
  5. costumes.json 用レコードの生成と差分プレビュー
を提供する。GUI(batch_gui.py) と CLI(batch_import.py) の両方から使う。

安全ルール:
  - inbox 側のファイルは読み取りのみ（削除・移動・リネームしない）
  - raw への書き込みはコピーのみ。既存ファイルは絶対に上書きしない
  - presets.json / costumes.json への書き込みは差分プレビュー後の明示操作のみ
  - apply のログを _private/import_logs/ に残し、途中失敗を検出できるようにする
"""

import copy
import difflib
import filecmp
import json
import re
import shutil
from datetime import date, datetime
from pathlib import Path

SCHEMA_VERSION = 1

# manifest で正式に受理するトップレベルキー。
MANIFEST_TOP_LEVEL_KEYS = {
    "schema_version", "idol_slug", "start_slot", "end_slot", "items",
    "collection", "input_dir", "output_dir", "inbox_dir",
}

# load_manifest が読込元の記録用に付与する内部キー（manifest 自体のキーではない）。
MANIFEST_INTERNAL_KEYS = {"_path"}

# 未所持ポップアップ型の固定crop（presets.json 内の既存locked勢と同じ値）
LOCKED_POPUP_CROP = {"x": 770, "y": 340, "width": 320, "height": 300}

# front/back を持てる unlock_status（所持扱い）
OWNED_STATUSES = {"unlocked", "card_only"}
# front/back を持てない unlock_status（未所持扱い）
UNOWNED_STATUSES = {"locked", "not_purchased", "card_missing"}
ALL_STATUSES = OWNED_STATUSES | UNOWNED_STATUSES

# docs/costume-group-rules.md の候補値
KNOWN_GROUPS = {
    "common", "unit", "feature", "scout", "cross",
    "shuffle", "event", "exchange", "campaign", "other",
}

SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

# collection / input_dir / output_dir に許可する文字（slug相当。パス区切り等は不可）
DIR_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


def is_safe_dir_name(name):
    """collection / input_dir / output_dir として安全な名前か。"""
    return isinstance(name, str) and bool(DIR_NAME_RE.match(name))


def check_source_file(name, inbox_dir):
    """manifestの画像ファイル指定を検証する。

    許可: inbox_dir 配下（サブフォルダ可）に実在する通常ファイルへの相対パスのみ。
    拒否: 絶対パス / ドライブレター / UNC / null文字 / `..` /
          resolve後に inbox_dir の外へ出るもの。
    戻り値: (resolved_path または None, エラーメッセージまたは None)
    """
    if not isinstance(name, str) or not name:
        return None, "ファイル名が不正です"
    if "\x00" in name:
        return None, "ファイル名にnull文字が含まれています"
    p = Path(name)
    if p.is_absolute() or p.drive or name.startswith(("\\\\", "//")):
        return None, f"絶対パス・ドライブ・UNCパスは指定できません: {name}"
    if ".." in p.parts:
        return None, f"'..' を含むパスは指定できません: {name}"
    resolved = (inbox_dir / p).resolve()
    try:
        resolved.relative_to(inbox_dir.resolve())
    except ValueError:
        return None, f"inbox_dir の外を指しています: {name}"
    if not resolved.is_file():
        return None, f"ファイルが存在しません: {resolved}"
    return resolved, None


def resolve_inbox_dir(manifest, project_root):
    """manifest の inbox_dir を安全に解決する。

    許可: {project_root}/_private/inbox/ 配下へresolveされる相対パスのみ
          （サブフォルダ可）。未指定時は _private/inbox/{idol_slug}。
    拒否: 絶対パス / ドライブレター / UNC / `//`・`\\\\` 始まり /
          null文字 / `..` / resolve後に基準ディレクトリ外となるもの。
    戻り値: (resolved_path または None, エラーメッセージまたは None)
    """
    inbox_base = (Path(project_root) / "_private" / "inbox").resolve()
    raw = manifest.get("inbox_dir")
    if raw is None:
        idol_slug = manifest.get("idol_slug") or ""
        resolved = (inbox_base / idol_slug).resolve()
        # 既定値でも防御的に確認（idol_slug は別途検証されるが二重防御）
        try:
            resolved.relative_to(inbox_base)
        except ValueError:
            return None, f"inbox_dir を解決できません（idol_slug が不正）: {idol_slug!r}"
        return resolved, None

    if not isinstance(raw, str) or not raw:
        return None, f"inbox_dir が不正です: {raw!r}"
    if "\x00" in raw:
        return None, "inbox_dir にnull文字が含まれています"
    p = Path(raw)
    if p.is_absolute() or p.drive or raw.startswith(("\\\\", "//")):
        return None, f"inbox_dir に絶対パス・ドライブ・UNCパスは指定できません: {raw}"
    if ".." in p.parts:
        return None, f"inbox_dir に '..' は使えません: {raw}"
    # `_private/inbox/...` 形式と `xxx`（inbox直下）形式の両方を受け付ける
    parts = p.parts
    if parts[:2] == ("_private", "inbox"):
        candidate = Path(project_root) / p
    else:
        candidate = inbox_base / p
    resolved = candidate.resolve()
    try:
        resolved.relative_to(inbox_base)
    except ValueError:
        return None, f"inbox_dir は _private/inbox 配下のみ指定できます: {raw}"
    if resolved == inbox_base:
        return None, f"inbox_dir には _private/inbox 直下のフォルダを指定してください: {raw}"
    return resolved, None


class ManifestError(Exception):
    pass


# ---------------------------------------------------------------------------
# コンテキスト（プロジェクトのパスと既存データ）
# ---------------------------------------------------------------------------
class BatchContext:
    def __init__(self, project_root):
        self.project_root = Path(project_root)
        self.raw_root = self.project_root / "_private" / "raw_screenshots"
        self.log_dir = self.project_root / "_private" / "import_logs"
        self.presets_path = (
            self.project_root / "tools" / "costume-image-processor" / "presets.json"
        )
        self.costumes_path = self.project_root / "public" / "data" / "costumes.json"
        self.idols_path = self.project_root / "public" / "data" / "idols.json"
        self.images_root = self.project_root / "public" / "images" / "costumes"

        self.presets = self._load_json(self.presets_path)
        self.costumes_doc = self._load_json(self.costumes_path)
        idols_doc = self._load_json(self.idols_path)
        self.idol_slugs = {i["slug"] for i in idols_doc.get("idols", [])}
        self.existing_ids = {c["id"] for c in self.costumes_doc.get("costumes", [])}

    @staticmethod
    def _load_json(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)


# ---------------------------------------------------------------------------
# manifest 読み込み
# ---------------------------------------------------------------------------
def load_manifest(path):
    path = Path(path)
    try:
        with open(path, encoding="utf-8") as f:
            manifest = json.load(f)
    except FileNotFoundError:
        raise ManifestError(f"manifest が見つかりません: {path}")
    except json.JSONDecodeError as e:
        raise ManifestError(f"manifest のJSONが壊れています: {e}")
    if not isinstance(manifest, dict):
        raise ManifestError("manifest のトップレベルはオブジェクトである必要があります")
    manifest["_path"] = str(path)
    return manifest


def default_collection_name(manifest):
    return manifest.get("collection") or "{}-slots-{:02d}-{:02d}".format(
        manifest.get("idol_slug", "unknown"),
        int(manifest.get("start_slot", 0)),
        int(manifest.get("end_slot", 0)),
    )


def item_folder_name(item):
    return "{:02d}_{}".format(int(item["slot"]), item["slug"])


def item_costume_id(manifest, item):
    return item.get("id") or "{}_{}-01".format(manifest["idol_slug"], item["slug"])


# ---------------------------------------------------------------------------
# 検証と適用計画
# ---------------------------------------------------------------------------
class PlanItem:
    """1衣装分の適用計画。"""

    def __init__(self, item, manifest, ctx):
        self.item = item
        self.slot = int(item["slot"])
        self.slug = item.get("slug", "")
        self.costume_name = item.get("costume_name", "")
        self.folder_name = item_folder_name(item)
        self.costume_id = item_costume_id(manifest, item)
        self.owned = item.get("unlock_status") in OWNED_STATUSES
        self.dest_dir = ctx.raw_root / manifest["idol_slug"] / self.folder_name
        self.sources = {}  # role -> Path（指定されたものだけ）
        self.copies = []   # (src Path, dst Path)
        self.warnings = []
        # rawが既にこのmanifestのapply結果と一致している場合 True
        # （gen-presets / gen-costumes は続行可、二度目のapplyは拒否）
        self.already_applied = False

    def resolve_sources(self, inbox_dir):
        """ソースファイルを検証しつつ解決する。エラーメッセージのリストを返す。

        inbox_dir 配下に実在するファイルのみ許可（絶対パス・`..`・inbox外は拒否）。
        """
        errors = []
        for role in ("select", "front", "back"):
            name = self.item.get(f"{role}_file")
            if not name:
                continue
            resolved, err = check_source_file(name, inbox_dir)
            if err:
                errors.append(f"slot {self.slot}: {role}_file: {err}")
                continue
            self.sources[role] = resolved
            self.copies.append((resolved, self.dest_dir / f"{role}.png"))
        return errors


def validate_manifest(manifest, ctx):
    """manifest 全体を検証し (errors, warnings, plan_items) を返す。

    errors が空でない限り apply してはならない。
    """
    errors = []
    warnings = []
    plan = []

    # --- トップレベル ---
    unknown_keys = sorted(
        set(manifest) - MANIFEST_TOP_LEVEL_KEYS - MANIFEST_INTERNAL_KEYS)
    for key in unknown_keys:
        errors.append(f"未知のmanifestキーです: {key}")
    if unknown_keys:
        return errors, warnings, plan

    if manifest.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version は {SCHEMA_VERSION} を指定してください")
    idol_slug = manifest.get("idol_slug")
    if not idol_slug:
        errors.append("idol_slug がありません")
    elif idol_slug not in ctx.idol_slugs:
        errors.append(f"idol_slug が idols.json に存在しません: {idol_slug}")

    # collection / input_dir / output_dir はslug相当の安全な名前のみ許可
    # （パス区切り・`..`・絶対パス・ドライブレター等を含む名前を排除）
    for key in ("collection", "input_dir", "output_dir"):
        val = manifest.get(key)
        if val is not None and not is_safe_dir_name(val):
            errors.append(f"{key} に使えない名前です"
                          f"（小文字英数字・ハイフン・アンダースコアのみ）: {val!r}")

    items = manifest.get("items")
    if not isinstance(items, list) or not items:
        errors.append("items が空です")
        return errors, warnings, plan

    try:
        start = int(manifest["start_slot"])
        end = int(manifest["end_slot"])
    except (KeyError, TypeError, ValueError):
        errors.append("start_slot / end_slot が正しく指定されていません")
        return errors, warnings, plan
    if start > end:
        errors.append(f"start_slot({start}) > end_slot({end}) です")

    # inbox_dir は {project_root}/_private/inbox/ 配下のみ許可
    #（リポジトリ外の任意ファイルを取り込めないようにする）
    inbox_dir, inbox_err = resolve_inbox_dir(manifest, ctx.project_root)
    if inbox_err:
        errors.append(inbox_err)
        return errors, warnings, plan  # 基準点が不正なら item 検証・PlanItem 生成へ進まない
    if not inbox_dir.is_dir():
        errors.append(f"inbox_dir が存在しません: {inbox_dir}")

    if errors and idol_slug is None:
        return errors, warnings, plan

    # --- item の型を先に検証（不正itemは以降の処理から除外し、クラッシュさせない） ---
    valid_items = []
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append(f"items[{idx}] がオブジェクト（dict）ではありません: {item!r}")
            continue
        slot = item.get("slot")
        slug = item.get("slug")
        if isinstance(slot, bool) or not isinstance(slot, int):
            errors.append(f"items[{idx}]: slot は整数で指定してください: {slot!r}"
                          f"（slug={slug!r}）")
            continue
        if slot < 1:
            errors.append(f"items[{idx}]: slot は1以上で指定してください: {slot}")
            continue
        if not isinstance(slug, str) or not slug:
            errors.append(f"items[{idx}] (slot {slot}): slug は文字列で指定してください: {slug!r}")
            continue
        if not isinstance(item.get("costume_name", ""), str):
            errors.append(f"slot {slot}: costume_name は文字列で指定してください")
            continue
        crop = item.get("icon_crop")
        if crop is not None and not (
                isinstance(crop, dict)
                and all(isinstance(crop.get(k), int) and not isinstance(crop.get(k), bool)
                        for k in ("x", "y", "width", "height"))):
            errors.append(f"slot {slot}: icon_crop は x/y/width/height の整数で指定してください: {crop!r}")
            continue
        valid_items.append(item)
    items = valid_items
    if not items:
        return errors, warnings, plan

    # --- slot の重複・欠番 ---
    slots = [item["slot"] for item in items]
    seen = set()
    for s in slots:
        if s in seen:
            errors.append(f"slot が重複しています: {s}")
        seen.add(s)
    missing = sorted(set(range(start, end + 1)) - seen)
    if missing:
        errors.append(f"slot に欠番があります: {missing}")
    outside = sorted(seen - set(range(start, end + 1)))
    if outside:
        errors.append(f"start_slot〜end_slot の範囲外の slot があります: {outside}")

    # --- 各 item ---
    used_files = {}   # 解決済みパス -> "slot17/select" のような使用元
    seen_ids = set()
    seen_slugs = set()
    _log_dsts = None  # completedログのコピー先集合（適用済み判定用・遅延読み込み）
    collection_name = default_collection_name(manifest)
    existing_coll = ctx.presets.get("collections", {}).get(collection_name, {})
    existing_coll_items = existing_coll.get("items", {})

    # 既存collectionへ追加する場合は idol_slug / input_dir / output_dir の一致を必須にする
    # （別アイドルのcollectionへの誤混入を防ぐ）
    if existing_coll and idol_slug:
        want = {
            "idol_slug": idol_slug,
            "input_dir": manifest.get("input_dir", idol_slug),
            "output_dir": manifest.get("output_dir", idol_slug),
        }
        have = {
            "idol_slug": existing_coll.get("idol_slug"),
            # process_images.py の既定値に合わせて解決した実効値で比較する
            "input_dir": existing_coll.get("input_dir", collection_name),
            "output_dir": existing_coll.get(
                "output_dir", existing_coll.get("idol_slug", collection_name)),
        }
        for field in ("idol_slug", "input_dir", "output_dir"):
            if want[field] != have[field]:
                errors.append(
                    f"既存collection '{collection_name}' と {field} が一致しません"
                    f"（manifest: {want[field]!r} / presets: {have[field]!r}）。"
                    "items は追加できません")

    for item in items:
        pi = PlanItem(item, manifest, ctx)

        # slug
        if not SLUG_RE.match(pi.slug):
            errors.append(f"slot {pi.slot}: slug に不正な文字があります: {pi.slug!r}"
                          "（小文字英数字とハイフンのみ）")
        if pi.slug in seen_slugs:
            errors.append(f"slug が重複しています: {pi.slug}")
        seen_slugs.add(pi.slug)

        # id
        if pi.costume_id in seen_ids:
            errors.append(f"manifest 内で id が重複しています: {pi.costume_id}")
        seen_ids.add(pi.costume_id)
        if pi.costume_id in ctx.existing_ids:
            errors.append(f"slot {pi.slot}: id が既存 costumes.json と衝突: {pi.costume_id}")

        # unlock_status / requestable
        status = item.get("unlock_status")
        if status not in ALL_STATUSES:
            errors.append(f"slot {pi.slot}: unlock_status が不正です: {status!r}"
                          f"（許容値: {sorted(ALL_STATUSES)}）")
        requestable = item.get("requestable", False)
        if requestable and status != "unlocked":
            errors.append(f"slot {pi.slot}: unlock_status={status} なのに requestable=true です")

        # ファイル指定の整合
        if not item.get("select_file"):
            errors.append(f"slot {pi.slot}: select_file がありません")
        has_front = bool(item.get("front_file"))
        has_back = bool(item.get("back_file"))
        if pi.owned:
            if has_front != has_back:
                lack = "back" if has_front else "front"
                errors.append(f"slot {pi.slot}: 所持衣装なのに {lack}_file がありません")
            elif not has_front:
                warnings.append(f"slot {pi.slot}: 所持衣装ですが front/back が未指定です"
                                "（アイコンのみ生成されます）")
        else:
            if has_front or has_back:
                errors.append(f"slot {pi.slot}: 未所持（{status}）なのに front/back が指定されています")

        # costume_group / tags
        group = item.get("costume_group")
        if group not in KNOWN_GROUPS:
            errors.append(f"slot {pi.slot}: costume_group が不正です: {group!r}"
                          f"（許容値: {sorted(KNOWN_GROUPS)}）")
        elif group == "other" and "暫定分類" not in (item.get("tags") or []):
            warnings.append(f"slot {pi.slot}: costume_group=other です。"
                            "後で見直すなら tags に「暫定分類」を推奨")
        if not isinstance(item.get("tags", []), list):
            errors.append(f"slot {pi.slot}: tags はリストで指定してください")

        # icon_crop（所持衣装の一覧型は crop 必須。仮値での続行は誤crop事故のもと）
        if pi.owned and not item.get("icon_crop"):
            errors.append(f"slot {pi.slot}: 所持衣装（{status}）は icon_crop の明示指定が必須です"
                          "（未指定のまま apply / presets書き込みはできません）")

        # ソースファイル解決（inbox外・絶対パス・`..` は拒否）
        errors.extend(pi.resolve_sources(inbox_dir))
        for role, src in pi.sources.items():
            key = str(src)
            if key in used_files:
                errors.append(f"slot {pi.slot}/{role}: 同一ファイルが二重使用されています "
                              f"({used_files[key]} と重複): {src.name}")
            else:
                used_files[key] = f"slot {pi.slot}/{role}"

        # 既存rawフォルダとの衝突 / 適用済み判定
        # 「このmanifestのapply結果と完全一致（ファイル名・数・内容）かつ
        #  completedのapplyログに記録がある」場合のみ『適用済み』として続行可。
        # それ以外の既存rawはすべて衝突エラー（上書き防止は従来どおり）。
        if pi.dest_dir.exists():
            existing_files = sorted(p.name for p in pi.dest_dir.iterdir() if p.is_file())
            expected_files = sorted(dst.name for _, dst in pi.copies)
            if not existing_files:
                warnings.append(f"slot {pi.slot}: コピー先フォルダは既にありますが空です: {pi.dest_dir}")
            elif existing_files == expected_files and all(
                    src.is_file() and dst.is_file()
                    and filecmp.cmp(src, dst, shallow=False)
                    for src, dst in pi.copies):
                if _log_dsts is None:
                    _log_dsts = completed_log_dsts(ctx)
                if all(str(dst.resolve()) in _log_dsts for _, dst in pi.copies):
                    pi.already_applied = True
                    warnings.append(f"slot {pi.slot}: 適用済みです"
                                    f"（rawはこのmanifestのapply結果と一致。再applyは不可）")
                else:
                    errors.append(f"slot {pi.slot}: rawの内容はmanifestと一致しますが、"
                                  f"completedのapplyログに記録がありません: {pi.dest_dir}")
            else:
                errors.append(f"slot {pi.slot}: 既存rawフォルダと衝突します"
                              f"（内容がこのmanifestと一致しません）: {pi.dest_dir}"
                              f"（既存: {', '.join(existing_files)}）")
        # 同じ idol の別フォルダ名で同じ slot 番号が既に使われていないか
        idol_raw = ctx.raw_root / idol_slug if idol_slug else None
        if idol_raw and idol_raw.is_dir():
            prefix = "{:02d}_".format(pi.slot)
            for d in idol_raw.iterdir():
                if d.is_dir() and d.name.startswith(prefix) and d.name != pi.folder_name:
                    errors.append(f"slot {pi.slot}: 同じスロット番号の既存rawフォルダがあります: {d.name}")

        # presets の既存 collection との衝突
        if pi.folder_name in existing_coll_items:
            existing_id = existing_coll_items[pi.folder_name].get("id")
            if existing_id != pi.costume_id:
                errors.append(f"slot {pi.slot}: presets の collection "
                              f"'{collection_name}' に別idの同名フォルダがあります: "
                              f"{pi.folder_name} (既存 id={existing_id})")
            else:
                warnings.append(f"slot {pi.slot}: presets に同じ項目が既にあります"
                                f"（再実行？）: {collection_name}/{pi.folder_name}")

        plan.append(pi)

    return errors, warnings, plan


# ---------------------------------------------------------------------------
# dry-run サマリ
# ---------------------------------------------------------------------------
def dry_run_report(manifest, errors, warnings, plan, ctx):
    """dry-run 用のテキストレポートを返す。何も書き込まない。"""
    lines = []
    coll = default_collection_name(manifest)
    lines.append(f"=== dry-run: {manifest.get('idol_slug')} / collection={coll} ===")
    lines.append("")

    n_raw = sum(len(p.copies) for p in plan)
    n_icons = len(plan)
    n_bodies = sum(2 for p in plan if p.owned and "front" in p.sources)
    lines.append(f"衣装数            : {len(plan)}")
    lines.append(f"コピー予定rawファイル : {n_raw}")
    lines.append(f"生成予定WebP        : {n_icons + n_bodies} (icon {n_icons} / body {n_bodies})")
    lines.append(f"新規costumesレコード : {len(plan)}")
    lines.append("")

    lines.append("[作成予定フォルダ / コピー予定ファイル]")
    for p in plan:
        rel = p.dest_dir.relative_to(ctx.project_root)
        lines.append(f"  {p.slot:02d} {p.costume_name} ({p.costume_id})")
        lines.append(f"      -> {rel}")
        for src, dst in p.copies:
            lines.append(f"         {src.name}  ->  {dst.name}")
    lines.append("")

    if errors:
        lines.append(f"[エラー] {len(errors)}件 — apply できません")
        lines.extend(f"  - {e}" for e in errors)
    else:
        lines.append("[エラー] なし — apply 可能です")
    if warnings:
        lines.append(f"[警告] {len(warnings)}件")
        lines.extend(f"  - {w}" for w in warnings)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# apply（rawへの安全コピー）
# ---------------------------------------------------------------------------
def apply_plan(manifest, plan, ctx):
    """検証済み plan を raw へコピーする。コピーのみ・上書きなし。

    ログを _private/import_logs/ に残す。ログの status が
    "in_progress" のまま残っていたら途中失敗（半端な状態）を意味する。
    戻り値: (copied [(src,dst)], log_path)
    """
    ctx.log_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_path = ctx.log_dir / f"{stamp}_{default_collection_name(manifest)}.json"

    log = {
        "status": "in_progress",
        "manifest": manifest.get("_path"),
        "idol_slug": manifest.get("idol_slug"),
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "copied": [],
    }

    def write_log():
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(log, f, ensure_ascii=False, indent=2)

    write_log()
    copied = []
    try:
        # 実行直前の最終チェック（検証後に状況が変わっていないか）
        for p in plan:
            for src, dst in p.copies:
                if dst.exists():
                    raise ManifestError(f"コピー先が既に存在します（中断）: {dst}")
                if not src.is_file():
                    raise ManifestError(f"コピー元が消えています（中断）: {src}")
        for p in plan:
            p.dest_dir.mkdir(parents=True, exist_ok=True)
            for src, dst in p.copies:
                shutil.copy2(src, dst)
                copied.append((src, dst))
                log["copied"].append({"src": str(src), "dst": str(dst)})
                write_log()
        log["status"] = "completed"
        log["finished_at"] = datetime.now().isoformat(timespec="seconds")
        write_log()
    except Exception as e:
        log["status"] = "failed"
        log["error"] = str(e)
        write_log()
        raise
    return copied, log_path


def completed_log_dsts(ctx):
    """completed な applyログに記録された全コピー先パス（resolve済み文字列）を返す。"""
    dsts = set()
    if not ctx.log_dir.is_dir():
        return dsts
    for f in ctx.log_dir.glob("*.json"):
        try:
            with open(f, encoding="utf-8") as fh:
                log = json.load(fh)
        except (OSError, json.JSONDecodeError):
            continue
        if log.get("status") == "completed":
            for c in log.get("copied", []):
                try:
                    dsts.add(str(Path(c["dst"]).resolve()))
                except (KeyError, OSError):
                    continue
    return dsts


def find_incomplete_logs(ctx):
    """途中失敗（in_progress / failed）のログを返す。"""
    bad = []
    if not ctx.log_dir.is_dir():
        return bad
    for f in sorted(ctx.log_dir.glob("*.json")):
        try:
            with open(f, encoding="utf-8") as fh:
                log = json.load(fh)
            if log.get("status") != "completed":
                bad.append((f, log.get("status")))
        except (OSError, json.JSONDecodeError):
            bad.append((f, "unreadable"))
    return bad


# ---------------------------------------------------------------------------
# presets.json 生成
# ---------------------------------------------------------------------------
def build_presets_update(manifest, plan, ctx):
    """presets.json の更新後データと差分テキストを返す（書き込みはしない）。"""
    new_presets = copy.deepcopy(ctx.presets)
    collections = new_presets.setdefault("collections", {})
    coll_name = default_collection_name(manifest)
    idol_slug = manifest["idol_slug"]
    coll = collections.setdefault(coll_name, {
        "idol_slug": idol_slug,
        "input_dir": manifest.get("input_dir", idol_slug),
        "output_dir": manifest.get("output_dir", idol_slug),
        "items": {},
    })
    items = coll.setdefault("items", {})

    gen_warnings = []
    for p in plan:
        entry = {
            "id": p.costume_id,
            "icon_mode": p.item.get("icon_mode", "manual_crop"),
            "has_body_images": bool(p.owned and "front" in p.sources),
        }
        crop = p.item.get("icon_crop")
        if crop:
            entry["icon_crop"] = dict(crop)
        elif not p.owned:
            # 未所持ポップアップ型は既存の固定cropを使う
            entry["icon_crop"] = dict(LOCKED_POPUP_CROP)
        else:
            # 所持衣装のicon_crop未指定はvalidateでエラーになるため通常ここへ来ない。
            # 仮cropの自動採用は誤crop事故の原因になるため行わない（防御的に拒否）。
            raise ManifestError(
                f"{p.folder_name}: 所持衣装に icon_crop がありません。"
                "presets を生成できません")
        if p.folder_name in items and items[p.folder_name] != entry:
            gen_warnings.append(f"{p.folder_name}: 既存項目と内容が異なるため上書きしません")
            continue
        items[p.folder_name] = entry

    diff = _json_diff(ctx.presets, new_presets, "presets.json")
    return new_presets, diff, gen_warnings


# ---------------------------------------------------------------------------
# costumes.json 生成
# ---------------------------------------------------------------------------
def build_costumes_update(manifest, plan, ctx, today=None):
    """costumes.json の更新後データと差分テキストを返す（書き込みはしない）。

    戻り値: (new_doc, diff, missing_images)
    missing_images はレコードが参照するのに存在しないWebPの一覧。
    プレビューは missing があっても可能だが、実書き込みは呼び出し側で
    missing が空であることを必須にすること。
    """
    today = today or date.today().isoformat()
    new_doc = copy.deepcopy(ctx.costumes_doc)
    records = new_doc.setdefault("costumes", [])
    idol_slug = manifest["idol_slug"]

    missing_images = []
    for p in plan:
        has_body = bool(p.owned and "front" in p.sources)
        rec = {
            "id": p.costume_id,
            "idol_slug": idol_slug,
            "costume_name": p.costume_name,
            "costume_group": p.item.get("costume_group", "other"),
            "unlock_status": p.item.get("unlock_status"),
            "requestable": bool(p.item.get("requestable", False)),
            "images": {
                "icon": f"{p.costume_id}_icon.webp",
                "front": f"{p.costume_id}_front.webp" if has_body else None,
                "back": f"{p.costume_id}_back.webp" if has_body else None,
            },
            "tags": list(p.item.get("tags") or []),
            "note_public": p.item.get("note_public", ""),
            "updated_at": today,
        }
        # 画像の存在チェック（欠けている間はプレビューのみ可・書き込み不可）
        img_dir = ctx.images_root / idol_slug
        for kind, fname in rec["images"].items():
            if fname and not (img_dir / fname).is_file():
                missing_images.append(f"{p.costume_id}: {kind} 画像がありません: "
                                      f"public/images/costumes/{idol_slug}/{fname}"
                                      "（process_images.py で生成してから書き込んでください）")
        records.append(rec)

    new_doc["updated_at"] = today
    # JSON として妥当かラウンドトリップ検証
    json.loads(json.dumps(new_doc, ensure_ascii=False))
    diff = _json_diff(ctx.costumes_doc, new_doc, "costumes.json")
    return new_doc, diff, missing_images


# ---------------------------------------------------------------------------
def _json_diff(old, new, name):
    old_s = json.dumps(old, ensure_ascii=False, indent=2).splitlines(keepends=True)
    new_s = json.dumps(new, ensure_ascii=False, indent=2).splitlines(keepends=True)
    return "".join(difflib.unified_diff(old_s, new_s,
                                        fromfile=f"a/{name}", tofile=f"b/{name}"))


def write_json_atomic(path, data):
    """一時ファイル経由で書き込む（途中失敗で壊さない）。"""
    path = Path(path)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    tmp.replace(path)
