import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import threading
from pathlib import Path

try:
    from pillow_heif import register_heif_opener
    from PIL import Image
    register_heif_opener()
    HEIF_AVAILABLE = True
except ImportError:
    HEIF_AVAILABLE = False

class HEICConverter(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("HEIC → JPG Converter")
        self.geometry("520x420")
        self.resizable(False, False)
        self.configure(bg="#1e1e2e")

        self.files = []
        self.output_dir = tk.StringVar(value="")

        self._build_ui()
        self._setup_drop()

    def _build_ui(self):
        PAD = 14
        BG = "#1e1e2e"
        CARD = "#2a2a3e"
        ACCENT = "#7c6af7"
        FG = "#e0e0f0"
        MUTED = "#888aaa"

        # Title
        tk.Label(self, text="HEIC → JPG", font=("Segoe UI", 18, "bold"),
                 bg=BG, fg=ACCENT).pack(pady=(18, 2))
        tk.Label(self, text="Drag & drop files below or click to browse",
                 font=("Segoe UI", 9), bg=BG, fg=MUTED).pack()

        # Drop zone
        self.drop_frame = tk.Frame(self, bg=CARD, bd=0, highlightthickness=2,
                                   highlightbackground=ACCENT, highlightcolor=ACCENT,
                                   width=480, height=130)
        self.drop_frame.pack(padx=PAD, pady=(12, 6))
        self.drop_frame.pack_propagate(False)

        self.drop_label = tk.Label(self.drop_frame,
                                   text="Drop .heic files here\nor click to browse",
                                   font=("Segoe UI", 11), bg=CARD, fg=MUTED,
                                   cursor="hand2")
        self.drop_label.pack(expand=True)
        self.drop_frame.bind("<Button-1>", lambda e: self._browse_files())
        self.drop_label.bind("<Button-1>", lambda e: self._browse_files())

        # File count label
        self.count_label = tk.Label(self, text="No files selected",
                                    font=("Segoe UI", 9), bg=BG, fg=MUTED)
        self.count_label.pack()

        # Output dir row
        out_frame = tk.Frame(self, bg=BG)
        out_frame.pack(padx=PAD, pady=(10, 4), fill="x")

        tk.Label(out_frame, text="Save to:", font=("Segoe UI", 9, "bold"),
                 bg=BG, fg=FG, width=7, anchor="w").pack(side="left")

        self.out_entry = tk.Entry(out_frame, textvariable=self.output_dir,
                                  font=("Segoe UI", 9), bg=CARD, fg=FG,
                                  insertbackground=FG, relief="flat", bd=4)
        self.out_entry.pack(side="left", fill="x", expand=True, padx=(4, 6))

        tk.Button(out_frame, text="Browse", font=("Segoe UI", 9),
                  bg=ACCENT, fg="white", relief="flat", bd=0, padx=10,
                  cursor="hand2", command=self._browse_output).pack(side="left")

        # Progress bar
        self.progress = ttk.Progressbar(self, mode="determinate", length=480)
        style = ttk.Style()
        style.theme_use("default")
        style.configure("TProgressbar", troughcolor=CARD, background=ACCENT, thickness=10)
        self.progress.pack(padx=PAD, pady=(10, 4))

        self.status_label = tk.Label(self, text="", font=("Segoe UI", 9),
                                     bg=BG, fg=MUTED)
        self.status_label.pack()

        # Convert button
        self.go_btn = tk.Button(self, text="⚡  Convert", font=("Segoe UI", 12, "bold"),
                                bg=ACCENT, fg="white", relief="flat", bd=0,
                                padx=24, pady=8, cursor="hand2",
                                command=self._start_convert)
        self.go_btn.pack(pady=(10, 0))

    def _setup_drop(self):
        """Enable native drag-and-drop via tkinterdnd2 if available, else skip."""
        try:
            from tkinterdnd2 import DND_FILES
            self.drop_frame.drop_target_register(DND_FILES)
            self.drop_frame.dnd_bind("<<Drop>>", self._on_drop)
            self.drop_label.drop_target_register(DND_FILES)
            self.drop_label.dnd_bind("<<Drop>>", self._on_drop)
        except Exception:
            pass  # drag-drop not available; browse still works

    def _on_drop(self, event):
        raw = event.data
        # tkdnd wraps paths with spaces in braces
        import re
        paths = re.findall(r'\{([^}]+)\}|(\S+)', raw)
        paths = [a or b for a, b in paths]
        heic = [p for p in paths if p.lower().endswith((".heic", ".heif"))]
        if heic:
            self.files = heic
            self._update_count()

    def _browse_files(self):
        selected = filedialog.askopenfilenames(
            title="Select HEIC files",
            filetypes=[("HEIC/HEIF files", "*.heic *.heif"), ("All files", "*.*")]
        )
        if selected:
            self.files = list(selected)
            self._update_count()

    def _browse_output(self):
        d = filedialog.askdirectory(title="Select output folder")
        if d:
            self.output_dir.set(d)

    def _update_count(self):
        n = len(self.files)
        self.count_label.config(text=f"{n} file{'s' if n != 1 else ''} selected")
        self.drop_label.config(text=f"{n} file{'s' if n != 1 else ''} ready to convert")

    def _start_convert(self):
        if not HEIF_AVAILABLE:
            messagebox.showerror("Missing Library", "pillow-heif is not installed.")
            return
        if not self.files:
            messagebox.showwarning("No Files", "Please select some HEIC files first.")
            return
        out = self.output_dir.get().strip()
        if not out:
            messagebox.showwarning("No Output", "Please choose a save location.")
            return
        self.go_btn.config(state="disabled")
        threading.Thread(target=self._convert, args=(list(self.files), out), daemon=True).start()

    def _convert(self, files, out_dir):
        total = len(files)
        ok = 0
        errors = []
        for i, fp in enumerate(files):
            try:
                img = Image.open(fp)
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                name = Path(fp).stem + ".jpg"
                dest = os.path.join(out_dir, name)
                # avoid overwrite
                counter = 1
                while os.path.exists(dest):
                    dest = os.path.join(out_dir, f"{Path(fp).stem}_{counter}.jpg")
                    counter += 1
                img.save(dest, "JPEG", quality=92)
                ok += 1
            except Exception as e:
                errors.append(f"{os.path.basename(fp)}: {e}")

            pct = int((i + 1) / total * 100)
            self.progress["value"] = pct
            self.status_label.config(text=f"Converting {i+1}/{total}…")

        self.go_btn.config(state="normal")
        if errors:
            messagebox.showwarning("Done with errors",
                f"Converted {ok}/{total}.\n\nErrors:\n" + "\n".join(errors))
        else:
            messagebox.showinfo("Done! ✅", f"Converted {ok} file{'s' if ok != 1 else ''} to JPG.\n\nSaved to:\n{out_dir}")
        self.progress["value"] = 0
        self.status_label.config(text="")
        self.files = []
        self.drop_label.config(text="Drop .heic files here\nor click to browse")
        self.count_label.config(text="No files selected")


if __name__ == "__main__":
    app = HEICConverter()
    app.mainloop()
