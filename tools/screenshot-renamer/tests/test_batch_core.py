# -*- coding: utf-8 -*-
"""batch_core のユニットテスト。

一時ディレクトリ上にダミーのプロジェクト構造を作って検証する。
実プロジェクトの _private / public には一切触れない。

実行:
    python -m unittest discover -s tools/screenshot-renamer/tests -v
"""

import json
import shutil
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

    # --- 異常系 ---
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
        self.assertEqual(owned["images"]["front"], "test-idol_owned-a-01_front.webp")
        self.assertIsNone(locked["images"]["front"])
        self.assertIsNone(locked["images"]["back"])
        self.assertEqual(new_doc["updated_at"], "2026-07-12")
        # WebP 未生成は missing_images に列挙される（プレビュー自体は可能）
        self.assertTrue(any("画像がありません" in m_ for m_ in missing_images))
        # 元データは無傷
        self.assertEqual(len(self.ctx.costumes_doc["costumes"]), 1)


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
