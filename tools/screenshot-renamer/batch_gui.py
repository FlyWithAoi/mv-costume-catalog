# -*- coding: utf-8 -*-
"""バッチ取り込みモード GUI。

manifest.json を読み込んで検証結果とサムネイル付き一覧を表示し、
確認してから raw へコピー（apply）できる。presets / costumes への
反映は差分プレビューを表示してから書き込む。

起動:
    python tools/screenshot-renamer/batch_gui.py
    （または app.py の「バッチ取り込み...」ボタンから）

サムネイル表示には Pillow を使う（画像加工CLIと同じ依存）。
Pillow がない場合はサムネイルなしのテキスト表示になる。
"""

import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

sys.path.insert(0, str(Path(__file__).resolve().parent))
import batch_core as core  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[2]
THUMB = 90  # サムネイルの長辺px

try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


class BatchImportWindow:
    def __init__(self, window, project_root=PROJECT_ROOT):
        """window には tk.Tk または tk.Toplevel を渡す。"""
        self.win = window
        self.win.title("バッチ取り込みモード")
        self.win.minsize(980, 640)
        self.project_root = Path(project_root)

        self.manifest = None
        self.errors = []
        self.warnings = []
        self.plan = []
        self.ctx = None
        self._thumbs = []  # PhotoImage の参照保持

        self._build_ui()

    # ---------- UI ----------
    def _build_ui(self):
        top = tk.Frame(self.win)
        top.pack(fill="x", padx=8, pady=6)
        self.manifest_var = tk.StringVar()
        tk.Label(top, text="manifest.json:").pack(side="left")
        tk.Entry(top, textvariable=self.manifest_var, width=60).pack(
            side="left", fill="x", expand=True, padx=4)
        tk.Button(top, text="選択...", command=self.choose_manifest).pack(side="left")
        tk.Button(top, text="再読込", command=self.reload).pack(side="left", padx=4)

        btns = tk.Frame(self.win)
        btns.pack(fill="x", padx=8, pady=2)
        self.btn_dry = tk.Button(btns, text="dry-run表示", command=self.show_dry_run,
                                 state="disabled")
        self.btn_apply = tk.Button(btns, text="rawへコピー (apply)", command=self.do_apply,
                                   state="disabled", bg="#4a7", fg="white")
        self.btn_presets = tk.Button(btns, text="presets差分...", command=self.show_presets_diff,
                                     state="disabled")
        self.btn_webp = tk.Button(btns, text="WebP生成（この分のみ）", command=self.run_webp,
                                  state="disabled")
        self.btn_costumes = tk.Button(btns, text="costumes差分...", command=self.show_costumes_diff,
                                      state="disabled")
        for b in (self.btn_dry, self.btn_apply, self.btn_presets,
                  self.btn_webp, self.btn_costumes):
            b.pack(side="left", padx=4)

        self.status_var = tk.StringVar(value="manifest を選択してください。")
        tk.Label(self.win, textvariable=self.status_var, anchor="w",
                 fg="#333").pack(fill="x", padx=8)

        # 一覧（スクロール可能キャンバス）
        wrap = tk.Frame(self.win)
        wrap.pack(fill="both", expand=True, padx=8, pady=4)
        self.canvas = tk.Canvas(wrap, highlightthickness=0)
        vsb = ttk.Scrollbar(wrap, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.list_frame = tk.Frame(self.canvas)
        self.canvas.create_window((0, 0), window=self.list_frame, anchor="nw")
        self.list_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind_all(
            "<MouseWheel>",
            lambda e: self.canvas.yview_scroll(-1 * (e.delta // 120), "units"))

        # エラー・警告欄
        tk.Label(self.win, text="検証結果:", anchor="w").pack(fill="x", padx=8)
        self.issue_text = tk.Text(self.win, height=8, state="disabled")
        self.issue_text.pack(fill="x", padx=8, pady=(0, 8))

    # ---------- actions ----------
    def choose_manifest(self):
        chosen = filedialog.askopenfilename(
            title="manifest.json を選択",
            filetypes=[("JSON", "*.json"), ("すべて", "*.*")],
            initialdir=str(self.project_root))
        if chosen:
            self.manifest_var.set(chosen)
            self.reload()

    def reload(self):
        path = self.manifest_var.get().strip()
        if not path:
            return
        try:
            self.ctx = core.BatchContext(self.project_root)
            self.manifest = core.load_manifest(path)
            self.errors, self.warnings, self.plan = core.validate_manifest(
                self.manifest, self.ctx)
        except core.ManifestError as e:
            messagebox.showerror("エラー", str(e), parent=self.win)
            return
        except Exception as e:
            # presets.json / costumes.json 等の破損もダイアログで知らせる（GUIは落とさない）
            messagebox.showerror("読み込みエラー",
                                 f"データの読み込みに失敗しました:\n{e}", parent=self.win)
            return
        self._render()

    def _render(self):
        for w in self.list_frame.winfo_children():
            w.destroy()
        self._thumbs.clear()

        item_errors = {}   # slot -> True（該当エラーの目印）
        for e in self.errors:
            m = e.split(":")[0]
            if m.startswith("slot "):
                try:
                    item_errors[int(m[5:])] = True
                except ValueError:
                    pass

        for row, p in enumerate(self.plan):
            bg = "#fdd" if item_errors.get(p.slot) else ("#fff" if row % 2 else "#f2f2f2")
            f = tk.Frame(self.list_frame, bg=bg, bd=1, relief="solid")
            f.pack(fill="x", pady=1)

            info = tk.Frame(f, bg=bg)
            info.pack(side="left", padx=6, pady=4)
            item = p.item
            dest_rel = p.dest_dir.relative_to(self.project_root)
            dup = "既存重複あり" if item_errors.get(p.slot) else ""
            lines = [
                f"slot {p.slot:02d}  {p.costume_name}   [{p.slug}]",
                f"id: {p.costume_id}   状態: {item.get('unlock_status')}"
                f"   group: {item.get('costume_group')}   tags: {', '.join(item.get('tags') or [])}",
                f"コピー先: {dest_rel}   {dup}",
            ]
            slot_warns = [w for w in self.warnings if w.startswith(f"slot {p.slot}:")]
            lines += [f"警告: {w.split(': ', 1)[1]}" for w in slot_warns]
            tk.Label(info, text="\n".join(lines), justify="left", anchor="w",
                     bg=bg, fg="#a00" if item_errors.get(p.slot) else "#000"
                     ).pack(anchor="w")

            thumbs = tk.Frame(f, bg=bg)
            thumbs.pack(side="right", padx=6)
            for role in ("select", "front", "back"):
                src = p.sources.get(role)
                cell = tk.Frame(thumbs, bg=bg)
                cell.pack(side="left", padx=3)
                img = self._make_thumb(src) if src else None
                if img is not None:
                    self._thumbs.append(img)
                    tk.Label(cell, image=img, bd=1, relief="solid").pack()
                else:
                    txt = "—" if not src else ("なし" if not src.is_file() else "画像?")
                    tk.Label(cell, text=txt, width=12, height=4, bd=1,
                             relief="solid", bg="#eee").pack()
                tk.Label(cell, text=role, bg=bg).pack()

        self._show_issues()
        applied = [p for p in self.plan if p.already_applied]
        can_apply = not self.errors and bool(self.plan) and not applied
        self.btn_apply.configure(state="normal" if can_apply else "disabled")
        for b in (self.btn_dry, self.btn_presets, self.btn_webp, self.btn_costumes):
            b.configure(state="normal" if self.plan else "disabled")
        if can_apply:
            note = "  — apply 可能"
        elif applied and not self.errors:
            note = f"  — 適用済み{len(applied)}件（再applyは不可。presets/WebP/costumesへ進めます）"
        elif self.errors:
            note = "  — エラーを解消するまで apply できません"
        else:
            note = ""
        self.status_var.set(
            f"衣装 {len(self.plan)}件 / エラー {len(self.errors)}件 / 警告 {len(self.warnings)}件"
            + note)

    def _make_thumb(self, src):
        if not (HAS_PIL and src and src.is_file()):
            return None
        try:
            with Image.open(src) as im:
                im.thumbnail((THUMB * 2, THUMB))  # 横長スクショなので横広め
                return ImageTk.PhotoImage(im.copy())
        except Exception:
            return None

    def _show_issues(self):
        self.issue_text.configure(state="normal")
        self.issue_text.delete("1.0", "end")
        lines = [f"[エラー] {e}" for e in self.errors] + \
                [f"[警告] {w}" for w in self.warnings]
        self.issue_text.insert("1.0", "\n".join(lines) or "問題なし")
        self.issue_text.configure(state="disabled")

    def show_dry_run(self):
        text = core.dry_run_report(self.manifest, self.errors, self.warnings,
                                   self.plan, self.ctx)
        self._show_text_window("dry-run", text)

    def run_webp(self):
        """このmanifestのcollectionだけを対象にWebPを生成する。"""
        import subprocess
        coll = core.default_collection_name(self.manifest)
        script = self.project_root / "tools" / "costume-image-processor" / "process_images.py"
        if not messagebox.askyesno(
                "WebP生成",
                f"collection '{coll}' のみを対象にWebPを生成します。\n"
                "（他のcollectionは再生成しません）\n\n実行しますか？", parent=self.win):
            return
        try:
            result = subprocess.run(
                [sys.executable, str(script), "--collection", coll],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                cwd=str(self.project_root), timeout=600)
            output = (result.stdout or "") + ("\n" + result.stderr if result.stderr else "")
        except Exception as e:
            messagebox.showerror("WebP生成失敗", str(e), parent=self.win)
            return
        self._show_text_window(f"WebP生成結果: {coll}", output)

    def do_apply(self):
        if self.errors:
            return
        if any(p.already_applied for p in self.plan):
            messagebox.showinfo("適用済み",
                                "適用済みのスロットがあるため apply しません（上書き禁止）。",
                                parent=self.win)
            return
        n = sum(len(p.copies) for p in self.plan)
        if not messagebox.askyesno(
                "最終確認",
                f"{len(self.plan)}衣装 / {n}ファイルを raw へコピーします。\n"
                "元ファイルは変更しません。既存ファイルの上書きもしません。\n\n"
                "実行しますか？", parent=self.win):
            return
        try:
            copied, log_path = core.apply_plan(self.manifest, self.plan, self.ctx)
        except Exception as e:
            messagebox.showerror("apply失敗",
                                 f"{e}\n\nログを確認してください: _private/import_logs/",
                                 parent=self.win)
            return
        messagebox.showinfo("完了",
                            f"{len(copied)}ファイルをコピーしました。\nログ: {log_path}",
                            parent=self.win)
        self.reload()

    def show_presets_diff(self):
        try:
            new_presets, diff, gen_warnings = core.build_presets_update(
                self.manifest, self.plan, self.ctx)
        except core.ManifestError as e:
            messagebox.showerror("エラー", str(e), parent=self.win)
            return
        text = "\n".join(f"[警告] {w}" for w in gen_warnings)
        text += ("\n" if text else "") + (diff or "差分はありません。")
        self._show_text_window(
            "presets.json 差分プレビュー", text,
            write_label="presets.json に書き込む" if diff and not self.errors else None,
            on_write=lambda: self._write_json(self.ctx.presets_path, new_presets))

    def show_costumes_diff(self):
        new_doc, diff, missing_images = core.build_costumes_update(
            self.manifest, self.plan, self.ctx)
        text = "\n".join(f"[画像不足] {m}" for m in missing_images)
        if missing_images:
            text += ("\n\n※ 参照するWebPが不足しているため書き込みできません。"
                     "process_images.py で生成後にやり直してください。\n")
        text += ("\n" if text else "") + (diff or "差分はありません。")
        # 画像不足・検証エラーがある間は書き込み導線を出さない
        can_write = bool(diff) and not self.errors and not missing_images
        self._show_text_window(
            "costumes.json 差分プレビュー", text,
            write_label="costumes.json に書き込む" if can_write else None,
            on_write=lambda: self._write_json(self.ctx.costumes_path, new_doc))

    def _write_json(self, path, data):
        if not messagebox.askyesno("確認", f"{path.name} に書き込みますか？",
                                   parent=self.win):
            return
        core.write_json_atomic(path, data)
        messagebox.showinfo("完了", f"書き込みました: {path}", parent=self.win)
        self.reload()

    def _show_text_window(self, title, text, write_label=None, on_write=None):
        top = tk.Toplevel(self.win)
        top.title(title)
        top.minsize(760, 480)
        t = tk.Text(top, wrap="none")
        vsb = ttk.Scrollbar(top, orient="vertical", command=t.yview)
        t.configure(yscrollcommand=vsb.set)
        t.insert("1.0", text)
        t.configure(state="disabled")
        if write_label and on_write:
            tk.Button(top, text=write_label, bg="#4a7", fg="white",
                      command=lambda: (top.destroy(), on_write())).pack(pady=4)
        vsb.pack(side="right", fill="y")
        t.pack(fill="both", expand=True)


def main():
    root = tk.Tk()
    BatchImportWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()
