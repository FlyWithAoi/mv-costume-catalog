# -*- coding: utf-8 -*-
"""batch_core のユニットテスト。

一時ディレクトリ上にダミーのプロジェクト構造を作って検証する。
実プロジェクトの _private / public には一切触れない。

実行:
    python -m unittest discover -s tools/screenshot-renamer/tests -v
"""

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import batch_core as core  # noqa: E402

PNG_1PX = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000d4944415478da63fcffff3f0300050201f34d85640000000049454e44ae426082"
)


def make_project(root):
    root = Path(root)
    (root / "_private" / "inbox" / "test-idol").mkdir(parents=True)
    (root / "_private" / "raw_screenshots").mkdir(parents=True)
    (root / "public" / "data").mkdir(parents=True)
    (root / "public" / "images" / "costumes").mkdir(parents=True)
    (root / "tools" / "costume-image-processor").mkdir(parents=True)

    def wj(rel, data):
        with open(root / rel, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)

    wj("public/data/idols.json", {"schema_version": 1, "idols": [
        {"slug": "test-idol", "name": "テスト"}]})
    wj("public/data/costumes.json", {"schema_version": 1, "updated_at": "2026-01-01",
                                     "costumes": [{"id": "test-idol_existing-01"}]})
    wj("tools/costume-image-processor/presets.json", {
        "output": {}, "body": {}, "collections": {}})
    return root


def make_png(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(PNG_1PX)


def base_manifest(**over):
    m = {
        "schema_version": 1,
        "idol_slug": "test-idol",
        "start_slot": 1,
        "end_slot": 2,
        "items": [
            {
                "slot": 1, "costume_name": "所持衣装", "slug": "owned-a",
                "select_file": "s1.png", "front_file": "f1.png", "back_file": "b1.png",
                "unlock_status": "unlocked", "requestable": True,
                "costume_group": "common", "tags": [],
                "icon_crop": {"x": 0, "y": 0, "width": 10, "height": 10},
            },
            {
                "slot": 2, "costume_name": "未所持衣装", "slug": "locked-b",
                "select_file": "s2.png", "front_file": None, "back_file": None,
                "unlock_status": "locked", "requestable": False,
                "costume_group": "other",
                "tags": ["暫定分類"],
            },
        ],
    }
    m.update(over)
    m["_path"] = "test-manifest.json"
    return m


class BatchCoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.root = make_project(self.tmp)
        self.inbox = self.root / "_private" / "inbox" / "test-idol"
        for name in ("s1.png", "f1.png", "b1.png", "s2.png"):
            make_png(self.inbox / name)
        self.ctx = core.BatchContext(self.root)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def validate(self, manifest):
        return core.validate_manifest(manifest, self.ctx)

    # --- 正常系 ---
    def test_valid_manifest_owned_and_locked(self):
        errors, warnings, plan = self.validate(base_manifest())
        self.assertEqual(errors, [])
        self.assertEqual(len(plan), 2)
        self.assertEqual(plan[0].folder_name, "01_owned-a")
        self.assertTrue(plan[0].owned)
        self.assertFalse(plan[1].owned)
        self.assertEqual(len(plan[0].copies), 3)
        self.assertEqual(len(plan[1].copies), 1)

    def test_all_accepted_top_level_keys_are_valid(self):
        m = base_manifest(
            collection="test-coll", input_dir="test-idol",
            output_dir="test-idol", inbox_dir="test-idol")
        errors, _, plan = self.validate(m)
        self.assertEqual(errors, [])
        self.assertEqual(len(plan), 2)

    def test_optional_top_level_keys_may_be_omitted(self):
        m = base_manifest()
        for key in ("collection", "input_dir", "output_dir", "inbox_dir"):
            m.pop(key, None)
        errors, _, plan = self.validate(m)
        self.assertEqual(errors, [])
        self.assertEqual(len(plan), 2)

    # --- 異常系 ---
    def test_unknown_inbox_key_is_error_before_plan_generation(self):
        m = base_manifest(inbox="test-idol")
        errors, _, plan = self.validate(m)
        self.assertTrue(any("inbox" in e for e in errors))
        self.assertEqual(plan, [])

    def test_all_unknown_top_level_keys_are_reported(self):
        m = base_manifest(inbox="test-idol", typo_key=True)
        errors, _, plan = self.validate(m)
        self.assertTrue(any("inbox" in e for e in errors))
        self.assertTrue(any("typo_key" in e for e in errors))
        self.assertEqual(plan, [])

    def test_back_missing_for_owned(self):
        m = base_manifest()
        m["items"][0]["back_file"] = None
        errors, _, _ = self.validate(m)
        self.assertTrue(any("back_file がありません" in e for e in errors))

    def test_slot_gap(self):
        m = base_manifest(end_slot=3)
        errors, _, _ = self.validate(m)
        self.assertTrue(any("欠番" in e for e in errors))

    def test_slot_duplicate(self):
        m = base_manifest()
        m["items"][1]["slot"] = 1
        errors, _, _ = self.validate(m)
        self.assertTrue(any("slot が重複" in e for e in errors))

    def test_file_double_use(self):
        m = base_manifest()
        m["items"][1]["select_file"] = "s1.png"
        errors, _, _ = self.validate(m)
        self.assertTrue(any("二重使用" in e for e in errors))

    def test_missing_file(self):
        m = base_manifest()
        m["items"][1]["select_file"] = "nope.png"
        errors, _, _ = self.validate(m)
        self.assertTrue(any("存在しません" in e for e in errors))

    def test_no_select_file(self):
        m = base_manifest()
        m["items"][1]["select_file"] = None
        errors, _, _ = self.validate(m)
        self.assertTrue(any("select_file がありません" in e for e in errors))

    def test_unowned_with_body(self):
        m = base_manifest()
        m["items"][1]["front_file"] = "f1.png"
        errors, _, _ = self.validate(m)
        # 二重使用エラーも出るが、未所持×bodyのエラーを確認
        self.assertTrue(any("未所持" in e and "front/back" in e for e in errors))

    def test_existing_raw_collision(self):
        dest = self.root / "_private" / "raw_screenshots" / "test-idol" / "01_owned-a"
        make_png(dest / "select.png")
        errors, _, _ = self.validate(base_manifest())
        self.assertTrue(any("既存rawフォルダと衝突" in e for e in errors))

    def test_existing_slot_number_collision(self):
        dest = self.root / "_private" / "raw_screenshots" / "test-idol" / "01_other-name"
        dest.mkdir(parents=True)
        errors, _, _ = self.validate(base_manifest())
        self.assertTrue(any("同じスロット番号" in e for e in errors))

    def test_existing_costume_id_collision(self):
        m = base_manifest()
        m["items"][0]["id"] = "test-idol_existing-01"
        errors, _, _ = self.validate(m)
        self.assertTrue(any("既存 costumes.json と衝突" in e for e in errors))

    def test_bad_slug(self):
        m = base_manifest()
        m["items"][0]["slug"] = "Bad_Slug!"
        errors, _, _ = self.validate(m)
        self.assertTrue(any("不正な文字" in e for e in errors))

    def test_requestable_mismatch(self):
        m = base_manifest()
        m["items"][1]["requestable"] = True
        errors, _, _ = self.validate(m)
        self.assertTrue(any("requestable=true" in e for e in errors))

    def test_unknown_idol(self):
        m = base_manifest(idol_slug="nobody",
                          inbox_dir="_private/inbox/test-idol")
        errors, _, _ = self.validate(m)
        self.assertTrue(any("idols.json に存在しません" in e for e in errors))

    # --- dry-run はファイルを変更しない ---
    def test_dry_run_no_changes(self):
        m = base_manifest()
        errors, warnings, plan = self.validate(m)
        before = sorted(str(p) for p in self.root.rglob("*"))
        core.dry_run_report(m, errors, warnings, plan, self.ctx)
        after = sorted(str(p) for p in self.root.rglob("*"))
        self.assertEqual(before, after)

    # --- apply はコピーのみ ---
    def test_apply_copies_only(self):
        m = base_manifest()
        errors, _, plan = self.validate(m)
        self.assertEqual(errors, [])
        inbox_before = sorted(p.name for p in self.inbox.iterdir())
        copied, log_path = core.apply_plan(m, plan, self.ctx)
        self.assertEqual(len(copied), 4)
        # inbox は無傷
        self.assertEqual(inbox_before, sorted(p.name for p in self.inbox.iterdir()))
        # コピー先の中身が一致
        raw = self.root / "_private" / "raw_screenshots" / "test-idol"
        self.assertEqual((raw / "01_owned-a" / "select.png").read_bytes(), PNG_1PX)
        self.assertEqual((raw / "02_locked-b" / "select.png").read_bytes(), PNG_1PX)
        self.assertFalse((raw / "02_locked-b" / "front.png").exists())
        # ログが completed
        log = json.loads(log_path.read_text(encoding="utf-8"))
        self.assertEqual(log["status"], "completed")
        self.assertEqual(len(log["copied"]), 4)
        self.assertEqual(core.find_incomplete_logs(self.ctx), [])

    def test_apply_never_overwrites(self):
        m = base_manifest()
        errors, _, plan = self.validate(m)
        # 検証後にコピー先が出現した場合、apply は中断してログに failed が残る
        dest = plan[0].dest_dir / "select.png"
        dest.parent.mkdir(parents=True)
        dest.write_bytes(b"sentinel")
        with self.assertRaises(core.ManifestError):
            core.apply_plan(m, plan, self.ctx)
        self.assertEqual(dest.read_bytes(), b"sentinel")
        bad = core.find_incomplete_logs(self.ctx)
        self.assertEqual(len(bad), 1)
        self.assertEqual(bad[0][1], "failed")

    # --- presets 生成 ---
    def test_presets_generation(self):
        m = base_manifest()
        errors, _, plan = self.validate(m)
        new_presets, diff, gen_warnings = core.build_presets_update(m, plan, self.ctx)
        coll = new_presets["collections"]["test-idol-slots-01-02"]
        self.assertEqual(coll["input_dir"], "test-idol")
        items = coll["items"]
        self.assertEqual(items["01_owned-a"]["icon_crop"]["width"], 10)
        self.assertTrue(items["01_owned-a"]["has_body_images"])
        # 未所持は固定popup crop
        self.assertEqual(items["02_locked-b"]["icon_crop"], core.LOCKED_POPUP_CROP)
        self.assertFalse(items["02_locked-b"]["has_body_images"])
        self.assertIn("test-idol-slots-01-02", diff)
        # 元の presets は書き換わっていない
        self.assertEqual(self.ctx.presets["collections"], {})

    # --- icon_crop 未指定（所持衣装）はブロッキングエラー ---
    def test_owned_icon_crop_missing_is_error(self):
        m = base_manifest()
        del m["items"][0]["icon_crop"]
        errors, warnings, plan = self.validate(m)
        self.assertTrue(any("icon_crop の明示指定が必須" in e for e in errors))

    def test_owned_icon_crop_missing_blocks_apply_and_presets(self):
        m = base_manifest()
        del m["items"][0]["icon_crop"]
        errors, _, plan = self.validate(m)
        self.assertTrue(errors)
        # CLI相当の判断: errorsがあればapply/生成に進まない（コアの防御も確認）
        with self.assertRaises(core.ManifestError):
            core.build_presets_update(m, plan, self.ctx)
        # applyはCLI/GUIがerrors非空で拒否する契約だが、raw側も無傷であること
        raw = self.root / "_private" / "raw_screenshots" / "test-idol"
        self.assertFalse(raw.exists())

    # --- パス安全性 ---
    def test_input_dir_traversal_rejected(self):
        m = base_manifest(input_dir="../x")
        errors, _, _ = self.validate(m)
        self.assertTrue(any("input_dir に使えない名前" in e for e in errors))

    def test_output_dir_traversal_rejected(self):
        m = base_manifest(output_dir="..\\x")
        errors, _, _ = self.validate(m)
        self.assertTrue(any("output_dir に使えない名前" in e for e in errors))

    def test_collection_with_separator_rejected(self):
        for bad in ("a/b", "a\\b", "..", "C:evil", "スロット"):
            m = base_manifest(collection=bad)
            errors, _, _ = self.validate(m)
            self.assertTrue(any("collection に使えない名前" in e for e in errors),
                            f"拒否されるべき: {bad!r}")

    def test_source_file_absolute_path_rejected(self):
        outside = Path(self.tmp) / "outside.png"
        make_png(outside)
        m = base_manifest()
        m["items"][1]["select_file"] = str(outside)
        errors, _, _ = self.validate(m)
        self.assertTrue(any("絶対パス" in e for e in errors))

    def test_source_file_escaping_inbox_rejected(self):
        outside = self.root / "_private" / "inbox" / "outside.png"
        make_png(outside)
        m = base_manifest()
        m["items"][1]["select_file"] = "../outside.png"
        errors, _, _ = self.validate(m)
        self.assertTrue(any("'..' を含むパス" in e for e in errors))

    def test_source_file_null_char_rejected(self):
        m = base_manifest()
        m["items"][1]["select_file"] = "s2\x00.png"
        errors, _, _ = self.validate(m)
        self.assertTrue(any("null文字" in e for e in errors))

    def test_source_file_in_inbox_subfolder_allowed(self):
        make_png(self.inbox / "sub" / "s3.png")
        m = base_manifest()
        m["items"][1]["select_file"] = "sub/s3.png"
        errors, _, plan = self.validate(m)
        self.assertEqual(errors, [])

    # --- inbox_dir の安全性 ---
    def test_inbox_dir_default_ok(self):
        m = base_manifest()  # inbox_dir 未指定 → _private/inbox/{idol_slug}
        errors, _, plan = self.validate(m)
        self.assertEqual(errors, [])
        self.assertEqual(len(plan), 2)

    def test_inbox_dir_subfolder_ok(self):
        sub = self.root / "_private" / "inbox" / "example" / "subfolder"
        for name in ("s1.png", "f1.png", "b1.png", "s2.png"):
            make_png(sub / name)
        m = base_manifest(inbox_dir="_private/inbox/example/subfolder")
        errors, _, plan = self.validate(m)
        self.assertEqual(errors, [])
        self.assertTrue(str(plan[0].sources["select"]).startswith(str(sub.resolve())))

    def test_inbox_dir_relative_without_prefix_ok(self):
        # `test-idol` だけの指定でも _private/inbox/test-idol と解釈される
        m = base_manifest(inbox_dir="test-idol")
        errors, _, plan = self.validate(m)
        self.assertEqual(errors, [])
        self.assertEqual(len(plan), 2)

    def test_inbox_dir_rejects_unsafe_values(self):
        for bad in ("C:/Windows", "C:\\Windows", "\\\\server\\share",
                    "//localhost/c$/Windows", "_private/inbox/../../../",
                    "_private/inbox/idol/../../outside", "bad\x00dir"):
            m = base_manifest(inbox_dir=bad)
            errors, _, plan = self.validate(m)
            self.assertTrue(
                any("inbox_dir" in e for e in errors),
                f"拒否されるべき inbox_dir: {bad!r} (errors={errors})")
            self.assertEqual(plan, [], f"PlanItem を作ってはいけない: {bad!r}")

    def test_inbox_dir_unsafe_blocks_all_operations(self):
        m = base_manifest(inbox_dir="C:/Windows")
        errors, _, plan = self.validate(m)
        self.assertTrue(errors)
        self.assertEqual(plan, [])
        # errors 非空 + plan 空なので apply / gen-presets / gen-costumes は
        # CLI・GUIとも実行拒否となる（rawにも何も作られないこと）
        raw = self.root / "_private" / "raw_screenshots" / "test-idol"
        self.assertFalse(raw.exists())

    # --- 既存collectionとの整合 ---
    def _presets_with_collection(self, coll):
        p = self.ctx.presets_path
        data = json.loads(p.read_text(encoding="utf-8"))
        data["collections"]["test-coll"] = coll
        p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        self.ctx = core.BatchContext(self.root)  # 再読込

    def test_existing_collection_idol_mismatch(self):
        self._presets_with_collection(
            {"idol_slug": "someone-else", "input_dir": "someone-else",
             "output_dir": "someone-else", "items": {}})
        m = base_manifest(collection="test-coll")
        errors, _, _ = self.validate(m)
        self.assertTrue(any("idol_slug が一致しません" in e for e in errors))

    def test_existing_collection_dir_mismatch(self):
        self._presets_with_collection(
            {"idol_slug": "test-idol", "input_dir": "other-dir",
             "output_dir": "test-idol", "items": {}})
        m = base_manifest(collection="test-coll")
        errors, _, _ = self.validate(m)
        self.assertTrue(any("input_dir が一致しません" in e for e in errors))

    def test_existing_collection_match_ok(self):
        self._presets_with_collection(
            {"idol_slug": "test-idol", "input_dir": "test-idol",
             "output_dir": "test-idol", "items": {}})
        m = base_manifest(collection="test-coll")
        errors, _, plan = self.validate(m)
        self.assertEqual(errors, [])
        new_presets, diff, _ = core.build_presets_update(m, plan, self.ctx)
        self.assertIn("01_owned-a", new_presets["collections"]["test-coll"]["items"])

    # --- 不正manifestでクラッシュしない ---
    def test_non_numeric_slot_no_crash(self):
        m = base_manifest()
        m["items"][0]["slot"] = "abc"
        errors, _, plan = self.validate(m)
        self.assertTrue(any("slot は整数" in e for e in errors))
        self.assertEqual(len(plan), 1)  # 不正itemは計画から除外

    def test_non_dict_item_no_crash(self):
        m = base_manifest()
        m["items"].append("garbage")
        errors, _, _ = self.validate(m)
        self.assertTrue(any("オブジェクト（dict）ではありません" in e for e in errors))

    def test_non_string_slug_no_crash(self):
        m = base_manifest()
        m["items"][0]["slug"] = 123
        errors, _, _ = self.validate(m)
        self.assertTrue(any("slug は文字列" in e for e in errors))

    def test_bad_icon_crop_type_no_crash(self):
        m = base_manifest()
        m["items"][0]["icon_crop"] = {"x": "0", "y": 0, "width": 10, "height": 10}
        errors, _, _ = self.validate(m)
        self.assertTrue(any("icon_crop は x/y/width/height の整数" in e for e in errors))

    # --- costumes 生成 ---
    def test_costumes_generation(self):
        m = base_manifest()
        errors, _, plan = self.validate(m)
        new_doc, diff, missing_images = core.build_costumes_update(
            m, plan, self.ctx, today="2026-07-12")
        recs = {r["id"]: r for r in new_doc["costumes"] if isinstance(r, dict) and "idol_slug" in r}
        owned = recs["test-idol_owned-a-01"]
        locked = recs["test-idol_locked-b-01"]
        self.assertEqual(owned["slot_order"], 1)
        self.assertEqual(locked["slot_order"], 2)
        self.assertEqual(owned["images"]["front"], "test-idol_owned-a-01_front.webp")
        self.assertIsNone(locked["images"]["front"])
        self.assertIsNone(locked["images"]["back"])
        self.assertEqual(new_doc["updated_at"], "2026-07-12")
        # WebP 未生成は missing_images に列挙される（プレビュー自体は可能）
        self.assertTrue(any("画像がありません" in m_ for m_ in missing_images))
        # 元データは無傷
        self.assertEqual(len(self.ctx.costumes_doc["costumes"]), 1)


class SlotOrderSyncTest(unittest.TestCase):
    """preset IDとslot prefixによる既存record同期を検証する。"""

    def make_docs(self):
        costumes = {
            "schema_version": 1,
            "updated_at": "2026-01-01",
            "costumes": [
                {"id": "idol-a_first-01", "idol_slug": "idol-a",
                 "costume_name": "First", "note_public": "keep"},
                {"id": "idol-a_third-01", "idol_slug": "idol-a",
                 "costume_name": "Third", "note_public": "keep"},
            ],
        }
        presets = {
            "collections": {
                "idol-a-slots-01-03": {
                    "idol_slug": "idol-a",
                    "items": {
                        "01_first": {"id": "idol-a_first-01"},
                        "03_third": {"id": "idol-a_third-01"},
                    },
                },
            },
        }
        return costumes, presets

    def test_full_id_match_and_slot_gap_allowed(self):
        costumes, presets = self.make_docs()
        new_doc, diff, errors = core.build_slot_order_sync(costumes, presets)
        self.assertEqual(errors, [])
        self.assertTrue(diff)
        self.assertEqual([r["slot_order"] for r in new_doc["costumes"]], [1, 3])
        self.assertNotIn("slot_order", costumes["costumes"][0])
        self.assertEqual(new_doc["costumes"][0]["note_public"], "keep")

    def test_non_positive_slot_rejected(self):
        costumes, presets = self.make_docs()
        items = presets["collections"]["idol-a-slots-01-03"]["items"]
        items["00_third"] = items.pop("03_third")
        _, diff, errors = core.build_slot_order_sync(costumes, presets)
        self.assertEqual(diff, "")
        self.assertTrue(any("正整数" in e for e in errors))

    def test_costume_without_preset_rejected(self):
        costumes, presets = self.make_docs()
        del presets["collections"]["idol-a-slots-01-03"]["items"]["03_third"]
        _, diff, errors = core.build_slot_order_sync(costumes, presets)
        self.assertEqual(diff, "")
        self.assertTrue(any("presetに対応がない" in e for e in errors))

    def test_preset_without_costume_rejected(self):
        costumes, presets = self.make_docs()
        presets["collections"]["idol-a-slots-01-03"]["items"]["04_extra"] = {
            "id": "idol-a_extra-01"}
        _, diff, errors = core.build_slot_order_sync(costumes, presets)
        self.assertEqual(diff, "")
        self.assertTrue(any("costumeに対応がない" in e for e in errors))

    def test_idol_mismatch_rejected(self):
        costumes, presets = self.make_docs()
        costumes["costumes"][1]["idol_slug"] = "idol-b"
        _, diff, errors = core.build_slot_order_sync(costumes, presets)
        self.assertEqual(diff, "")
        self.assertTrue(any("idol不一致" in e for e in errors))

    def test_duplicate_slot_rejected(self):
        costumes, presets = self.make_docs()
        items = presets["collections"]["idol-a-slots-01-03"]["items"]
        items["01_third"] = items.pop("03_third")
        _, diff, errors = core.build_slot_order_sync(costumes, presets)
        self.assertEqual(diff, "")
        self.assertTrue(any("slotが重複" in e for e in errors))

    def test_duplicate_preset_id_rejected(self):
        costumes, presets = self.make_docs()
        items = presets["collections"]["idol-a-slots-01-03"]["items"]
        items["03_third"]["id"] = "idol-a_first-01"
        _, diff, errors = core.build_slot_order_sync(costumes, presets)
        self.assertEqual(diff, "")
        self.assertTrue(any("preset IDが重複" in e for e in errors))


class PublicSlotOrderIntegrityTest(unittest.TestCase):
    """公開データ全件のslot_orderとpreset対応を検証する。"""

    def test_all_public_records_have_valid_unique_slot_order(self):
        root = Path(__file__).resolve().parents[3]
        costumes = json.loads(
            (root / "public/data/costumes.json").read_text(encoding="utf-8"))
        presets = json.loads(
            (root / "tools/costume-image-processor/presets.json").read_text(encoding="utf-8"))
        new_doc, diff, errors = core.build_slot_order_sync(costumes, presets)
        self.assertEqual(errors, [])
        self.assertEqual(diff, "")
        self.assertEqual(len(new_doc["costumes"]), 3537)

        seen = set()
        for record in new_doc["costumes"]:
            slot = record.get("slot_order")
            self.assertIs(type(slot), int)
            self.assertGreater(slot, 0)
            key = (record["idol_slug"], slot)
            self.assertNotIn(key, seen)
            seen.add(key)


class PublicSortTest(unittest.TestCase):
    """app.jsのcanonical sortとfilter後の順序維持をNodeで検証する。"""

    def test_canonical_sort_and_filtered_order(self):
        app_path = Path(__file__).resolve().parents[3] / "public/app.js"
        script = r"""
const fs = require("fs");
const vm = require("vm");
const source = fs.readFileSync(process.argv[1], "utf8");
const start = source.indexOf("// ---- canonical sort ----");
const end = source.indexOf("// ---- 状態 ----");
if (start < 0 || end <= start) throw new Error("canonical sort block not found");
const sandbox = {};
vm.createContext(sandbox);
vm.runInContext(source.slice(start, end), sandbox);

const idols = {
  "idol-a": {sort_order: 20},
  "idol-b": {sort_order: 10},
};
const records = [
  {id: "idol-a_slot-2", idol_slug: "idol-a", slot_order: 2,
   costume_name: "hit", unlock_status: "unlocked"},
  {id: "idol-a_slot-1-b", idol_slug: "idol-a", slot_order: 1,
   costume_name: "other", unlock_status: "locked"},
  {id: "unknown", idol_slug: "unknown", costume_name: "other",
   unlock_status: "locked"},
  {id: "idol-b_slot-3", idol_slug: "idol-b", slot_order: 3,
   costume_name: "hit", unlock_status: "unlocked"},
  {id: "idol-a_slot-1-a", idol_slug: "idol-a", slot_order: 1,
   costume_name: "hit", unlock_status: "card_missing"},
];
sandbox.sortCostumesCanonical(records, idols);
const ids = (xs) => xs.map((x) => x.id).join(",");
const expected = "idol-b_slot-3,idol-a_slot-1-a,idol-a_slot-1-b,idol-a_slot-2,unknown";
if (ids(records) !== expected) throw new Error(`sort: ${ids(records)}`);
if (ids(records.filter((c) => c.costume_name === "hit")) !==
    "idol-b_slot-3,idol-a_slot-1-a,idol-a_slot-2") throw new Error("search order");
const unitMembers = ["idol-a"];
if (ids(records.filter((c) => unitMembers.includes(c.idol_slug))) !==
    "idol-a_slot-1-a,idol-a_slot-1-b,idol-a_slot-2") throw new Error("unit order");
if (ids(records.filter((c) => c.unlock_status === "locked")) !==
    "idol-a_slot-1-b,unknown") throw new Error("status order");
"""
        completed = subprocess.run(
            ["node", "-e", script, str(app_path)],
            capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(
            completed.returncode, 0,
            msg=f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}")


class PublicLinkedFilterTest(unittest.TestCase):
    """事務所・ユニット・idol連動の候補とAND条件をNodeで検証する。"""

    def test_office_metadata_covers_each_master_once(self):
        root = Path(__file__).resolve().parents[3]
        idols = json.loads((root / "public/data/idols.json").read_text(encoding="utf-8"))["idols"]
        units = json.loads((root / "public/data/units.json").read_text(encoding="utf-8"))["units"]
        offices = json.loads((root / "public/data/offices.json").read_text(encoding="utf-8"))["offices"]

        idol_slugs = [slug for office in offices for slug in office["idol_slugs"]]
        unit_slugs = [slug for office in offices for slug in office["unit_slugs"]]
        self.assertEqual(len(idol_slugs), len(set(idol_slugs)))
        self.assertEqual(len(unit_slugs), len(set(unit_slugs)))
        self.assertEqual(set(idol_slugs), {idol["slug"] for idol in idols})
        self.assertEqual(set(unit_slugs), {unit["slug"] for unit in units})

    def test_linked_filter_options_and_identity_conditions(self):
        app_path = Path(__file__).resolve().parents[3] / "public/app.js"
        script = r"""
const fs = require("fs");
const vm = require("vm");
const source = fs.readFileSync(process.argv[1], "utf8");
const start = source.indexOf("// ---- canonical sort ----");
const end = source.indexOf("// ---- 状態 ----");
if (start < 0 || end <= start) throw new Error("filter helper block not found");
const sandbox = {};
vm.createContext(sandbox);
vm.runInContext(source.slice(start, end), sandbox);
const assert = (condition, message) => {
  if (!condition) throw new Error(message);
};
const offices = [
  {slug: "star", sort_order: 10, idol_slugs: ["a", "b"], unit_slugs: ["alpha"]},
  {slug: "cosmic", sort_order: 20, idol_slugs: ["c"], unit_slugs: ["beta"]},
  {slug: "new", sort_order: 30, idol_slugs: ["d"], unit_slugs: ["double"]},
];
const idols = [
  {slug: "c", name: "C", sort_order: 30},
  {slug: "a", name: "A", sort_order: 10},
  {slug: "d", name: "D", sort_order: 40},
  {slug: "b", name: "B", sort_order: 20},
];
const unitsBySlug = {
  beta: {slug: "beta", sort_order: 20, member_slugs: ["c"]},
  alpha: {slug: "alpha", sort_order: 10, member_slugs: ["a", "b"]},
  double: {slug: "double", sort_order: 30, member_slugs: ["b", "d"]},
};
const index = sandbox.buildOfficeIndex(offices);
const resolve = (officeSlug, unitSlug, idolSlug) => sandbox.resolveLinkedFilterOptions({
  offices,
  idols,
  unitsBySlug,
  officeByIdolSlug: index.officeByIdolSlug,
  officeByUnitSlug: index.officeByUnitSlug,
  officeSlug,
  unitSlug,
  idolSlug,
});
const slugs = (items) => items.map((item) => item.slug).join(",");

let state = resolve("", "", "");
assert(slugs(state.unitOptions) === "alpha,beta,double", "all units were not restored");
assert(slugs(state.idolOptions) === "a,b,c,d", "all idols were not restored canonically");

state = resolve("star", "", "");
assert(slugs(state.unitOptions) === "alpha", "office did not limit units");
assert(slugs(state.idolOptions) === "a,b", "office did not limit idols");

state = resolve("star", "beta", "c");
assert(state.unitSlug === "", "invalid unit was not reset after office change");
assert(state.idolSlug === "", "invalid idol was not reset after office change");

state = resolve("", "beta", "c");
assert(state.unitSlug === "beta" && state.idolSlug === "c", "valid unit + idol was reset");
assert(slugs(state.idolOptions) === "c", "unit did not limit idols");

state = resolve("new", "double", "b");
assert(state.unitSlug === "double", "office-compatible cross unit was reset");
assert(state.idolSlug === "", "office-incompatible idol was not reset");
assert(slugs(state.idolOptions) === "d", "office and unit intersection is incorrect");

const records = [
  {id: "a", idol_slug: "a"},
  {id: "b", idol_slug: "b"},
  {id: "c", idol_slug: "c"},
  {id: "d", idol_slug: "d"},
];
const matches = (record, officeSlug, unitMembers, idolSlug) =>
  sandbox.matchesCatalogIdentityFilters(record, {
    officeSlug, unitMembers, idolSlug, officeByIdolSlug: index.officeByIdolSlug,
  });
assert(records.filter((r) => matches(r, "star", ["a", "b"], "b")).map((r) => r.id).join(",") === "b",
  "office + unit + idol is not ANDed");
assert(records.filter((r) => matches(r, "star", ["c"], "")).length === 0,
  "zero-result combination did not remain empty");
"""
        completed = subprocess.run(
            ["node", "-e", script, str(app_path)],
            capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(
            completed.returncode, 0,
            msg=f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}")


class PublicSearchTest(unittest.TestCase):
    """app.jsの公開検索対象をNodeで検証する。"""

    def test_search_uses_only_public_fields(self):
        app_path = Path(__file__).resolve().parents[3] / "public/app.js"
        script = r"""
const fs = require("fs");
const vm = require("vm");
const source = fs.readFileSync(process.argv[1], "utf8");
const section = (startText, endText) => {
  const start = source.indexOf(startText);
  const end = source.indexOf(endText, start);
  if (start < 0 || end <= start) throw new Error(`section not found: ${startText}`);
  return source.slice(start, end);
};
const searchSource = [
  section("function normalizeForSearch", "// idol_slug -> 表示用アイドル名"),
  section("function buildCostumeSearchText", "function buildSearchIndex"),
].join("\n");
const sandbox = {};
vm.createContext(sandbox);
vm.runInContext(searchSource, sandbox);

const costume = {
  id: "hiddenS-id",
  idol_slug: "hiddenS-idol",
  slot_order: 123,
  costume_name: "通常衣装",
  costume_group: "hiddenS-group",
  unlock_status: "hiddenS-status",
  images: {icon: "hiddenS.webp"},
  tags: ["帽子・ヘッドパーツあり"],
  note_public: "",
};
const idol = {
  slug: "hiddenS-idol",
  name: "天祥院 英智",
  name_kana: "てんしょういん えいち",
  name_romaji: "hiddenS romaji",
  aliases: ["hiddenS alias"],
};
const internalUnit = {
  slug: "hiddenS-unit",
  name: "公開ユニット名",
  aliases: ["hiddenS alias"],
};
const visibleUnit = {slug: "switch", name: "Switch", aliases: []};
const matches = (record, displayIdol, units, query) =>
  sandbox.buildCostumeSearchText(record, displayIdol, units)
    .includes(sandbox.normalizeForSearch(query));
const assert = (condition, message) => {
  if (!condition) throw new Error(message);
};

assert(!matches(costume, idol, [internalUnit], "S"), "hidden fields matched S");
assert(matches(costume, idol, [visibleUnit], "S"), "visible Switch did not match S");
assert(matches(costume, idol, [visibleUnit], "s"), "search is not case-insensitive");
assert(matches(costume, idol, [internalUnit], "パ"), "tag did not match パ");
assert(
  !matches({...costume, costume_group: "campaign"}, idol, [internalUnit], "ペ"),
  "costume_group label matched ペ"
);
assert(
  matches({...costume, costume_name: "迎春飛翔"}, idol, [internalUnit], "迎春飛翔"),
  "costume_name did not match"
);
assert(matches(costume, idol, [internalUnit], "天祥院英智"), "idol display name did not match");
assert(
  matches({...costume, note_public: "公開メモ限定語"}, idol, [internalUnit], "限定語"),
  "note_public did not match"
);
"""
        completed = subprocess.run(
            ["node", "-e", script, str(app_path)],
            capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(
            completed.returncode, 0,
            msg=f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}")


class CliWriteGateTest(unittest.TestCase):
    """gen-costumes --write の画像存在ゲートをCLI経由で検証する。"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.root = make_project(self.tmp)
        inbox = self.root / "_private" / "inbox" / "test-idol"
        for name in ("s1.png", "f1.png", "b1.png", "s2.png"):
            make_png(inbox / name)
        m = base_manifest()
        m.pop("_path", None)
        self.manifest_path = Path(self.tmp) / "manifest.json"
        self.manifest_path.write_text(
            json.dumps(m, ensure_ascii=False), encoding="utf-8")
        import batch_import
        self.cli = batch_import

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_cli(self, *argv):
        return self.cli.main(["--root", str(self.root), *argv])

    def _webp_names(self):
        return ["test-idol_owned-a-01_icon.webp",
                "test-idol_owned-a-01_front.webp",
                "test-idol_owned-a-01_back.webp",
                "test-idol_locked-b-01_icon.webp"]

    def test_preview_allowed_without_webp(self):
        rc = self.run_cli("gen-costumes", str(self.manifest_path))
        self.assertEqual(rc, 0)  # プレビューは画像不足でも成功
        # 実ファイルは無変更
        doc = json.loads((self.root / "public/data/costumes.json").read_text(encoding="utf-8"))
        self.assertEqual(len(doc["costumes"]), 1)

    def test_write_blocked_without_webp(self):
        rc = self.run_cli("gen-costumes", str(self.manifest_path), "--write", "--yes")
        self.assertEqual(rc, 1)
        doc = json.loads((self.root / "public/data/costumes.json").read_text(encoding="utf-8"))
        self.assertEqual(len(doc["costumes"]), 1)  # 書き込まれていない

    def test_write_succeeds_with_all_webp(self):
        img_dir = self.root / "public" / "images" / "costumes" / "test-idol"
        for name in self._webp_names():
            make_png(img_dir / name)  # 中身はダミーでよい（存在チェックのみ）
        rc = self.run_cli("gen-costumes", str(self.manifest_path), "--write", "--yes")
        self.assertEqual(rc, 0)
        doc = json.loads((self.root / "public/data/costumes.json").read_text(encoding="utf-8"))
        self.assertEqual(len(doc["costumes"]), 3)

    def test_unknown_key_blocks_apply(self):
        manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        manifest["inbox"] = "test-idol"
        self.manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
        rc = self.run_cli("apply", str(self.manifest_path), "--yes")
        self.assertEqual(rc, 1)
        raw = self.root / "_private" / "raw_screenshots" / "test-idol"
        self.assertFalse(raw.exists())

    def test_unknown_key_fails_dry_run(self):
        manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        manifest["inbox"] = "test-idol"
        self.manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
        rc = self.run_cli("dry-run", str(self.manifest_path))
        self.assertEqual(rc, 1)


class ProcessImagesGuardTest(unittest.TestCase):
    """process_images.py 側の二重防御（ルート脱出拒否）を検証する。"""

    def test_is_under(self):
        sys.path.insert(0, str(
            Path(__file__).resolve().parents[3] / "tools" / "costume-image-processor"))
        import process_images as pi
        base = pi.INPUT_ROOT_BASE
        self.assertTrue(pi.is_under(base / "test-idol", base))
        self.assertTrue(pi.is_under(base / "a" / "b", base))
        self.assertFalse(pi.is_under(base / "..", base))
        self.assertFalse(pi.is_under(base / ".." / "evil", base))
        self.assertFalse(pi.is_under(base.parent, base))
        out = pi.OUTPUT_DIR_BASE
        self.assertFalse(pi.is_under(out / ".." / ".." / "x", out))


class AppliedStateTest(unittest.TestCase):
    """apply後の再検証で『適用済み』として gen 系に進めることを検証する。"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.root = make_project(self.tmp)
        self.inbox = self.root / "_private" / "inbox" / "test-idol"
        for name in ("s1.png", "f1.png", "b1.png", "s2.png"):
            make_png(self.inbox / name)
        m = base_manifest()
        m.pop("_path", None)
        self.manifest_path = Path(self.tmp) / "manifest.json"
        self.manifest_path.write_text(
            json.dumps(m, ensure_ascii=False), encoding="utf-8")
        import batch_import
        self.cli = batch_import
        self.ctx = core.BatchContext(self.root)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_cli(self, *argv):
        return self.cli.main(["--root", str(self.root), *argv])

    def _apply(self):
        rc = self.run_cli("apply", str(self.manifest_path), "--yes")
        self.assertEqual(rc, 0)

    def test_no_collision_before_apply(self):
        m = core.load_manifest(self.manifest_path)
        errors, warnings, plan = core.validate_manifest(m, self.ctx)
        self.assertEqual(errors, [])
        self.assertFalse(any(p.already_applied for p in plan))

    def test_applied_state_after_apply(self):
        self._apply()
        m = core.load_manifest(self.manifest_path)
        errors, warnings, plan = core.validate_manifest(m, core.BatchContext(self.root))
        self.assertEqual(errors, [])
        self.assertTrue(all(p.already_applied for p in plan))
        self.assertTrue(any("適用済み" in w for w in warnings))

    def test_gen_presets_after_apply(self):
        self._apply()
        rc = self.run_cli("gen-presets", str(self.manifest_path), "--write", "--yes")
        self.assertEqual(rc, 0)
        p = json.loads((self.root / "tools/costume-image-processor/presets.json")
                       .read_text(encoding="utf-8"))
        self.assertIn("test-idol-slots-01-02", p["collections"])

    def test_gen_costumes_preview_after_apply(self):
        self._apply()
        rc = self.run_cli("gen-costumes", str(self.manifest_path))
        self.assertEqual(rc, 0)  # プレビューはWebP未生成でも可

    def test_second_apply_rejected(self):
        self._apply()
        rc = self.run_cli("apply", str(self.manifest_path), "--yes")
        self.assertEqual(rc, 1)
        # rawは1回目のまま（上書きなし）
        raw = self.root / "_private" / "raw_screenshots" / "test-idol"
        self.assertEqual((raw / "01_owned-a" / "select.png").read_bytes(), PNG_1PX)

    def test_tampered_raw_is_error(self):
        self._apply()
        target = (self.root / "_private" / "raw_screenshots" / "test-idol"
                  / "01_owned-a" / "front.png")
        target.write_bytes(b"tampered")
        m = core.load_manifest(self.manifest_path)
        errors, _, _ = core.validate_manifest(m, core.BatchContext(self.root))
        self.assertTrue(any("内容がこのmanifestと一致しません" in e for e in errors))

    def test_applied_without_log_is_error(self):
        self._apply()
        for f in (self.root / "_private" / "import_logs").glob("*.json"):
            f.unlink()
        m = core.load_manifest(self.manifest_path)
        errors, _, _ = core.validate_manifest(m, core.BatchContext(self.root))
        self.assertTrue(any("applyログに記録がありません" in e for e in errors))

    def test_other_manifest_same_raw_target_is_error(self):
        self._apply()
        # 同じ slot/slug（=同じrawフォルダ）を別のソースファイルで指す別manifest
        make_png(self.inbox / "alt1.png")
        make_png(self.inbox / "alt2.png")
        make_png(self.inbox / "alt3.png")
        m2 = base_manifest()
        m2["items"][0]["select_file"] = "alt1.png"
        m2["items"][0]["front_file"] = "alt2.png"
        m2["items"][0]["back_file"] = "alt3.png"
        # ダミーPNGは全て同一バイトなので、内容を変えて不一致にする
        (self.inbox / "alt1.png").write_bytes(PNG_1PX + b"x")
        errors, _, _ = core.validate_manifest(m2, core.BatchContext(self.root))
        self.assertTrue(any("既存rawフォルダと衝突" in e or "一致しません" in e
                            for e in errors))


class GuiSmokeTest(unittest.TestCase):
    """GUIの基本動作（起動・検証表示・エラー時のボタン無効化）。

    ヘッドレス環境等で Tk が使えない場合はスキップする。
    """

    def setUp(self):
        try:
            import tkinter
            self.tk_root = tkinter.Tk()
            self.tk_root.withdraw()
        except Exception as e:  # TclError 等
            self.skipTest(f"Tk が利用できない環境: {e}")
        self.tmp = tempfile.mkdtemp()
        self.root = make_project(self.tmp)
        inbox = self.root / "_private" / "inbox" / "test-idol"
        for name in ("s1.png", "f1.png", "b1.png", "s2.png"):
            make_png(inbox / name)

    def tearDown(self):
        if hasattr(self, "tk_root"):
            self.tk_root.destroy()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _open(self, manifest_dict):
        import batch_gui
        path = Path(self.tmp) / "m.json"
        manifest_dict.pop("_path", None)
        path.write_text(json.dumps(manifest_dict, ensure_ascii=False), encoding="utf-8")
        win = batch_gui.BatchImportWindow(self.tk_root, project_root=self.root)
        win.manifest_var.set(str(path))
        win.reload()
        return win

    def test_valid_manifest_enables_apply(self):
        win = self._open(base_manifest())
        self.assertEqual(str(win.btn_apply["state"]), "normal")
        self.assertEqual(len(win.plan), 2)

    def test_icon_crop_missing_disables_apply(self):
        m = base_manifest()
        del m["items"][0]["icon_crop"]
        win = self._open(m)
        self.assertEqual(str(win.btn_apply["state"]), "disabled")
        self.assertTrue(any("icon_crop" in e for e in win.errors))


if __name__ == "__main__":
    unittest.main()
