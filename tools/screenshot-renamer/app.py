# -*- coding: utf-8 -*-
"""スクショ画像リネーム補助ツール（コピー方式）

選んだ画像を _private/raw_screenshots/{collection}/{item}/ に
select.png / front.png / back.png としてコピーする。
元ファイルは移動・リネームしない。標準ライブラリのみ使用。
"""

import os
import shutil
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

# app.py は tools/screenshot-renamer/ にある想定なので、
# 2つ上がプロジェクトルート
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_ROOT = PROJECT_ROOT / "_private" / "raw_screenshots"

SLOTS = ("select", "front", "back")
IMAGE_FILETYPES = [
    ("画像ファイル", "*.png *.jpg *.jpeg *.webp"),
    ("すべてのファイル", "*.*"),
]

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def is_real_png(path: Path) -> bool:
    """先頭バイトでPNGかどうかを簡易チェックする"""
    try:
        with open(path, "rb") as f:
            return f.read(8) == PNG_SIGNATURE
    except OSError:
        return False


class RenamerApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("スクショリネーム補助ツール (コピー方式)")
        root.minsize(560, 420)

        self.root_var = tk.StringVar(value=str(DEFAULT_ROOT))
        self.collection_var = tk.StringVar()
        self.item_var = tk.StringVar()
        self.slot_vars = {slot: tk.StringVar() for slot in SLOTS}

        self._build_ui()

    # ---------- UI ----------

    def _build_ui(self):
        pad = {"padx": 8, "pady": 4}
        frame = tk.Frame(self.root)
        frame.pack(fill="both", expand=True, **pad)

        row = 0
        tk.Label(frame, text="raw_screenshots ルート:").grid(row=row, column=0, sticky="w")
        tk.Entry(frame, textvariable=self.root_var, width=52).grid(row=row, column=1, sticky="we")
        tk.Button(frame, text="選択...", command=self.choose_root).grid(row=row, column=2, **pad)

        row += 1
        tk.Label(frame, text="collectionフォルダ名:").grid(row=row, column=0, sticky="w")
        tk.Entry(frame, textvariable=self.collection_var, width=30).grid(row=row, column=1, sticky="w")
        tk.Label(frame, text="例: tori_test").grid(row=row, column=2, sticky="w")

        row += 1
        tk.Label(frame, text="衣装フォルダ名:").grid(row=row, column=0, sticky="w")
        tk.Entry(frame, textvariable=self.item_var, width=30).grid(row=row, column=1, sticky="w")
        tk.Label(frame, text="例: 05_new_outfit").grid(row=row, column=2, sticky="w")

        for slot in SLOTS:
            row += 1
            tk.Label(frame, text=f"{slot}画像:").grid(row=row, column=0, sticky="w")
            tk.Label(frame, textvariable=self.slot_vars[slot], anchor="w",
                     relief="sunken", width=52).grid(row=row, column=1, sticky="we")
            tk.Button(frame, text=f"{slot}を選択...",
                      command=lambda s=slot: self.choose_image(s)).grid(row=row, column=2, **pad)

        row += 1
        btn_frame = tk.Frame(frame)
        btn_frame.grid(row=row, column=0, columnspan=3, pady=8)
        tk.Button(btn_frame, text="コピー実行", command=self.run_copy,
                  bg="#4a7", fg="white", width=16).pack(side="left", padx=6)
        tk.Button(btn_frame, text="保存先フォルダを開く",
                  command=self.open_dest_folder, width=20).pack(side="left", padx=6)
        tk.Button(btn_frame, text="選択をクリア", command=self.clear_slots,
                  width=14).pack(side="left", padx=6)
        tk.Button(btn_frame, text="バッチ取り込み...", command=self.open_batch_mode,
                  width=16).pack(side="left", padx=6)

        row += 1
        tk.Label(frame, text="結果:").grid(row=row, column=0, sticky="nw")
        self.result_text = tk.Text(frame, height=8, width=64, state="disabled")
        self.result_text.grid(row=row, column=1, columnspan=2, sticky="nsew", pady=4)

        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(row, weight=1)

    def log(self, lines):
        self.result_text.configure(state="normal")
        self.result_text.delete("1.0", "end")
        self.result_text.insert("1.0", "\n".join(lines))
        self.result_text.configure(state="disabled")

    # ---------- actions ----------

    def choose_root(self):
        initial = self.root_var.get() or str(PROJECT_ROOT)
        chosen = filedialog.askdirectory(title="raw_screenshots ルートを選択",
                                         initialdir=initial)
        if chosen:
            self.root_var.set(chosen)

    def choose_image(self, slot: str):
        chosen = filedialog.askopenfilename(
            title=f"{slot}画像を選択", filetypes=IMAGE_FILETYPES)
        if chosen:
            self.slot_vars[slot].set(chosen)

    def clear_slots(self):
        for var in self.slot_vars.values():
            var.set("")
        self.log(["選択をクリアしました。"])

    def get_dest_dir(self):
        root_dir = self.root_var.get().strip()
        collection = self.collection_var.get().strip()
        item = self.item_var.get().strip()
        if not root_dir:
            messagebox.showwarning("入力エラー", "raw_screenshots ルートを指定してください。")
            return None
        if not collection:
            messagebox.showwarning("入力エラー", "collectionフォルダ名を入力してください。")
            return None
        if not item:
            messagebox.showwarning("入力エラー", "衣装フォルダ名を入力してください。")
            return None
        # フォルダ名にパス区切りが混ざっていないか簡易チェック
        for name in (collection, item):
            if any(sep in name for sep in ("/", "\\", "..")):
                messagebox.showwarning("入力エラー",
                                       f"フォルダ名に使えない文字が含まれています: {name}")
                return None
        return Path(root_dir) / collection / item

    def run_copy(self):
        dest_dir = self.get_dest_dir()
        if dest_dir is None:
            return

        selected = {slot: var.get().strip() for slot, var in self.slot_vars.items()}
        if not any(selected.values()):
            messagebox.showwarning("入力エラー", "画像が1枚も選択されていません。")
            return

        # select.png がない場合は警告（続行は可能）
        if not selected["select"]:
            if not messagebox.askyesno(
                    "確認",
                    "select画像が未選択です。\n"
                    "画像加工CLIは select.png を必要とします。\n"
                    "このまま続行しますか？"):
                return

        # 元ファイルの存在チェック
        for slot, src in selected.items():
            if src and not Path(src).is_file():
                messagebox.showerror("エラー", f"{slot}画像が見つかりません:\n{src}")
                return

        # PNG以外の中身チェック（拡張子ではなく先頭バイトで判定）
        non_png = [slot for slot, src in selected.items()
                   if src and not is_real_png(Path(src))]
        if non_png:
            if not messagebox.askyesno(
                    "確認",
                    "以下の画像はPNG形式ではないようです:\n"
                    + "\n".join(f"- {s}: {Path(selected[s]).name}" for s in non_png)
                    + "\n\n変換はせず、そのまま .png という名前でコピーします。\n続行しますか？"):
                return

        # 上書き確認
        existing = [f"{slot}.png" for slot, src in selected.items()
                    if src and (dest_dir / f"{slot}.png").exists()]
        if existing:
            if not messagebox.askyesno(
                    "上書き確認",
                    "コピー先に既存ファイルがあります:\n"
                    + "\n".join(f"- {name}" for name in existing)
                    + f"\n\n保存先: {dest_dir}\n\n上書きしますか？"):
                self.log(["上書きをキャンセルしました。ファイルは変更されていません。"])
                return

        # コピー実行（フォルダは自動作成）
        try:
            dest_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            messagebox.showerror("エラー", f"フォルダを作成できませんでした:\n{e}")
            return

        results = []
        for slot in SLOTS:
            src = selected[slot]
            dest = dest_dir / f"{slot}.png"
            if not src:
                results.append(f"- {slot}.png は未選択です")
                continue
            try:
                shutil.copy2(src, dest)
                results.append(f"- {slot}.png を作成しました")
            except OSError as e:
                results.append(f"- {slot}.png のコピーに失敗: {e}")
        results.append(f"- 保存先: {dest_dir}")
        self.log(results)

    def open_batch_mode(self):
        """manifest.json ベースのバッチ取り込みモードを開く。"""
        try:
            import batch_gui
        except ImportError as e:
            messagebox.showerror("エラー", f"batch_gui を読み込めませんでした:\n{e}")
            return
        batch_gui.BatchImportWindow(tk.Toplevel(self.root))

    def open_dest_folder(self):
        dest_dir = self.get_dest_dir()
        if dest_dir is None:
            return
        if not dest_dir.exists():
            if messagebox.askyesno("確認",
                                   f"フォルダがまだありません:\n{dest_dir}\n\n作成して開きますか？"):
                dest_dir.mkdir(parents=True, exist_ok=True)
            else:
                return
        if sys.platform == "win32":
            os.startfile(str(dest_dir))  # noqa: S606 - local folder open
        else:
            subprocess.run(["open" if sys.platform == "darwin" else "xdg-open",
                            str(dest_dir)], check=False)


def main():
    root = tk.Tk()
    RenamerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
