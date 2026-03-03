import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog
from pathlib import Path

def app_data_dir() -> Path:
    base = Path.home() / "Library" / "Application Support" / "Smart File Organizer"
    base.mkdir(parents=True, exist_ok=True)
    return base

# Optional drag & drop support
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_AVAILABLE = True
except Exception:
    DND_AVAILABLE = False
    TkinterDnD = tk.Tk
    DND_FILES = None

from file_scanner import FolderPath, FolderScanner
from extension_classifier import FileClassifier
from log_storage import LogManager
from undo_history import HistoryManager
from files_move import FileMover


class Toast:
    """Small modern notifications (top-right)."""
    def __init__(self, root: tk.Tk):
        self.root = root

    def show(self, title: str, message: str, kind: str = "info", duration_ms: int = 2500):
        win = tk.Toplevel(self.root)
        win.overrideredirect(True)
        win.attributes("-topmost", True)

        if kind == "success":
            bg, border, fg = "#0f2a1b", "#2ecc71", "#eafff3"
        elif kind == "error":
            bg, border, fg = "#2a0f0f", "#e74c3c", "#ffecec"
        elif kind == "warn":
            bg, border, fg = "#2a230f", "#f1c40f", "#fff6d6"
        else:
            bg, border, fg = "#111827", "#60a5fa", "#e5f1ff"

        frame = tk.Frame(win, bg=bg, highlightbackground=border, highlightthickness=2)
        frame.pack(fill="both", expand=True)

        tk.Label(frame, text=title, bg=bg, fg=fg, font=("Helvetica", 12, "bold")).pack(
            anchor="w", padx=12, pady=(10, 2)
        )
        tk.Label(frame, text=message, bg=bg, fg=fg, font=("Helvetica", 10),
                 wraplength=340, justify="left").pack(anchor="w", padx=12, pady=(0, 10))

        self.root.update_idletasks()
        w, h = 400, 92
        x = self.root.winfo_x() + self.root.winfo_width() - w - 20
        y = self.root.winfo_y() + 20
        win.geometry(f"{w}x{h}+{x}+{y}")

        win.after(duration_ms, win.destroy)


class StatusBar(tk.Frame):
    """Bottom status line with color."""
    def __init__(self, master):
        super().__init__(master, bg="#0b1220")
        self.var = tk.StringVar(value="Status: Idle")
        self.label = tk.Label(
            self,
            textvariable=self.var,
            bg="#0b1220",
            fg="#e5e7eb",
            anchor="w",
            padx=12,
            pady=8,
            font=("Helvetica", 11),
        )
        self.label.pack(fill="x")

    def set(self, text: str, kind: str = "info"):
        self.var.set(text)
        if kind == "success":
            self.label.config(fg="#2ecc71")  # green
        elif kind == "error":
            self.label.config(fg="#e74c3c")  # red
        elif kind == "warn":
            self.label.config(fg="#f1c40f")  # yellow
        else:
            self.label.config(fg="#e5e7eb")  # neutral


class ColorButton(tk.Frame):
    """
    Canvas-based button (stable colors on macOS, even when focused).
    """
    def __init__(self, master, text, command, bg, hover_bg, fg="#ffffff", width=140, height=42):
        super().__init__(master, bg=master["bg"])
        self.command = command
        self.bg = bg
        self.hover_bg = hover_bg
        self.fg = fg
        self.enabled = True

        self.canvas = tk.Canvas(self, width=width, height=height, highlightthickness=0, bd=0,
                                bg=master["bg"])
        self.canvas.pack()

        self.rect = self.canvas.create_rectangle(
            0, 0, width, height,
            outline=bg, fill=bg
        )
        self.text_id = self.canvas.create_text(
            width // 2, height // 2,
            text=text,
            fill=fg,
            font=("Helvetica", 11, "bold")
        )

        # bindings
        self.canvas.bind("<Enter>", self._on_enter)
        self.canvas.bind("<Leave>", self._on_leave)
        self.canvas.bind("<Button-1>", self._on_click)

        # also bind for objects
        self.canvas.tag_bind(self.rect, "<Enter>", self._on_enter)
        self.canvas.tag_bind(self.rect, "<Leave>", self._on_leave)
        self.canvas.tag_bind(self.rect, "<Button-1>", self._on_click)

        self.canvas.tag_bind(self.text_id, "<Enter>", self._on_enter)
        self.canvas.tag_bind(self.text_id, "<Leave>", self._on_leave)
        self.canvas.tag_bind(self.text_id, "<Button-1>", self._on_click)

        self.canvas.config(cursor="hand2")

    def set_enabled(self, enabled: bool):
        self.enabled = enabled
        if enabled:
            self.canvas.itemconfig(self.rect, fill=self.bg, outline=self.bg)
            self.canvas.itemconfig(self.text_id, fill=self.fg)
            self.canvas.config(cursor="hand2")
        else:
            disabled_bg = "#334155"
            disabled_fg = "#9ca3af"
            self.canvas.itemconfig(self.rect, fill=disabled_bg, outline=disabled_bg)
            self.canvas.itemconfig(self.text_id, fill=disabled_fg)
            self.canvas.config(cursor="arrow")

    def _on_enter(self, _e):
        if self.enabled:
            self.canvas.itemconfig(self.rect, fill=self.hover_bg, outline=self.hover_bg)

    def _on_leave(self, _e):
        if self.enabled:
            self.canvas.itemconfig(self.rect, fill=self.bg, outline=self.bg)

    def _on_click(self, _e):
        if self.enabled and callable(self.command):
            self.command()


class SmartOrganizerGUI:
    def __init__(self):
        self.root = TkinterDnD.Tk() if DND_AVAILABLE else tk.Tk()
        self.root.title("Smart File Organizer")
        self.root.geometry("860x520")
        self.root.minsize(820, 480)

        # Theme
        self.bg = "#0b1220"
        self.card = "#111827"
        self.card2 = "#0f172a"
        self.text = "#e5e7eb"
        self.muted = "#9ca3af"
        self.border = "#1f2937"
        self.accent = "#60a5fa"

        self.root.configure(bg=self.bg)

        # State
        self.selected_path = ""
        self.recursive_var = tk.BooleanVar(value=False)
        self.stop_event = threading.Event()
        self.worker_thread: threading.Thread | None = None

        # Core components
        self.classifier = FileClassifier()
        data_dir = app_data_dir()
        self.log_manager = LogManager(data_dir / "moves_logs.log")
        self.history_manager = HistoryManager(data_dir / "moved_files_history.json")

        # UI helpers
        self.toast = Toast(self.root)

        self._build_ui()

    def _build_ui(self):
        # Header
        header = tk.Frame(self.root, bg=self.bg)
        header.pack(fill="x", padx=18, pady=(14, 8))

        tk.Label(header, text="Smart File Organizer", bg=self.bg, fg=self.text,
                 font=("Helvetica", 20, "bold")).pack(side="left")

        tk.Label(
            header,
            text=("Drag a folder into the square" if DND_AVAILABLE else "Tip: install tkinterdnd2 for drag & drop"),
            bg=self.bg,
            fg=self.muted,
            font=("Helvetica", 10),
        ).pack(side="left", padx=14)

        # Main layout: left (drop) + right (controls)
        main = tk.Frame(self.root, bg=self.bg)
        main.pack(fill="both", expand=True, padx=18, pady=10)

        left = tk.Frame(main, bg=self.bg)
        left.pack(side="left", fill="y", padx=(0, 14))

        right = tk.Frame(main, bg=self.bg)
        right.pack(side="left", fill="both", expand=True)

        # Small square drop zone
        drop_wrap = tk.Frame(left, bg=self.card, highlightbackground=self.border, highlightthickness=1)
        drop_wrap.pack(pady=(0, 10))

        self.drop = tk.Frame(
            drop_wrap,
            bg=self.card2,
            highlightbackground=self.accent,
            highlightthickness=2,
            width=220,
            height=220,
        )
        self.drop.pack(padx=12, pady=12)
        self.drop.pack_propagate(False)

        tk.Label(self.drop, text="DROP HERE", bg=self.card2, fg=self.accent,
                 font=("Helvetica", 16, "bold")).pack(pady=(46, 10))

        self.path_label = tk.Label(
            self.drop,
            text="No folder selected",
            bg=self.card2,
            fg=self.muted,
            font=("Helvetica", 10),
            wraplength=190,
            justify="center",
        )
        self.path_label.pack(padx=12)

        if DND_AVAILABLE:
            self.drop.drop_target_register(DND_FILES)
            self.drop.dnd_bind("<<Drop>>", self._on_drop)

        # Browse button under drop zone
        browse_btn = ColorButton(
            left, "📂 Browse…", self.browse,
            bg="#334155", hover_bg="#475569",
            width=180, height=42
        )
        browse_btn.pack(fill="x")

        # Right side: controls card
        card = tk.Frame(right, bg=self.card, highlightbackground=self.border, highlightthickness=1)
        card.pack(fill="both", expand=True)

        tk.Label(card, text="Controls", bg=self.card, fg=self.text,
                 font=("Helvetica", 13, "bold")).pack(anchor="w", padx=14, pady=(12, 8))

        # Selected path (bigger)
        self.path_big = tk.Label(
            card,
            text="Selected: (none)",
            bg=self.card,
            fg=self.muted,
            font=("Helvetica", 11),
            anchor="w",
            justify="left",
            wraplength=520,
        )
        self.path_big.pack(fill="x", padx=14, pady=(0, 12))

        # Options
        options = tk.Frame(card, bg=self.card)
        options.pack(fill="x", padx=14, pady=(0, 10))

        tk.Checkbutton(
            options,
            text="Recursive scan",
            variable=self.recursive_var,
            bg=self.card,
            fg=self.text,
            activebackground=self.card,
            activeforeground=self.text,
            selectcolor=self.card2,
            font=("Helvetica", 11),
        ).pack(side="left")

        # Buttons grid (nice layout)
        btn_grid = tk.Frame(card, bg=self.card)
        btn_grid.pack(fill="x", padx=14, pady=(10, 12))

        self.start_btn = ColorButton(
            btn_grid, "▶ Start", self.start,
            bg="#16a34a", hover_bg="#22c55e",
            width=160, height=44
        )
        self.start_btn.grid(row=0, column=0, padx=(0, 10), pady=(0, 10), sticky="w")

        self.stop_btn = ColorButton(
            btn_grid, "⏹ Stop", self.stop,
            bg="#dc2626", hover_bg="#ef4444",
            width=160, height=44
        )
        self.stop_btn.grid(row=0, column=1, padx=(0, 10), pady=(0, 10), sticky="w")

        self.undo_last_btn = ColorButton(
            btn_grid, "↩ Undo last", self.undo_last,
            bg="#2563eb", hover_bg="#3b82f6",
            width=160, height=44
        )
        self.undo_last_btn.grid(row=1, column=0, padx=(0, 10), pady=(0, 0), sticky="w")

        self.undo_all_btn = ColorButton(
            btn_grid, "↺ Undo all", self.undo_all,
            bg="#0ea5e9", hover_bg="#38bdf8",
            width=160, height=44
        )
        self.undo_all_btn.grid(row=1, column=1, padx=(0, 10), pady=(0, 0), sticky="w")

        # Counters (no progress bar)
        counters = tk.Frame(card, bg=self.card)
        counters.pack(fill="x", padx=14, pady=(0, 12))

        self.scanned_var = tk.StringVar(value="Scanned: 0")
        self.moved_var = tk.StringVar(value="Moved: 0")
        self.skipped_var = tk.StringVar(value="Skipped: 0")

        tk.Label(counters, textvariable=self.scanned_var, bg=self.card, fg=self.muted, font=("Helvetica", 10)).pack(side="left")
        tk.Label(counters, textvariable=self.moved_var, bg=self.card, fg=self.muted, font=("Helvetica", 10)).pack(side="left", padx=16)
        tk.Label(counters, textvariable=self.skipped_var, bg=self.card, fg=self.muted, font=("Helvetica", 10)).pack(side="left", padx=16)

        # Hint
        hint = "Tip: Start organizes files. Stop requests a graceful stop. Undo works only after moves."
        tk.Label(card, text=hint, bg=self.card, fg=self.muted, font=("Helvetica", 10),
                 justify="left", wraplength=520).pack(anchor="w", padx=14, pady=(0, 12))

        # Status bar
        self.status = StatusBar(self.root)
        self.status.pack(fill="x", padx=10, pady=(0, 10))

    # ---------- Folder selection ----------
    def _set_folder(self, path: str):
        self.selected_path = path
        self.path_label.config(text=path, fg=self.text)
        self.path_big.config(text=f"Selected: {path}", fg=self.text)

    def browse(self):
        path = filedialog.askdirectory()
        if path:
            self._set_folder(path)

    def _on_drop(self, event):
        path = event.data.strip("{}")
        if Path(path).is_dir():
            self._set_folder(path)
        else:
            self.toast.show("Invalid drop", "Please drop a folder (not a file).", kind="error")

    # ---------- Actions ----------
    def start(self):
        if not self.selected_path:
            self.toast.show("No folder selected", "Please browse or drop a folder first.", kind="error")
            return

        if self.worker_thread and self.worker_thread.is_alive():
            self.toast.show("Already running", "The organizer is currently running.", kind="warn")
            return

        self.stop_event.clear()
        self.status.set("Status: Organizing...", "info")

        # reset counters
        self.scanned_var.set("Scanned: 0")
        self.moved_var.set("Moved: 0")
        self.skipped_var.set("Skipped: 0")

        self.worker_thread = threading.Thread(target=self._organize, daemon=True)
        self.worker_thread.start()

    def stop(self):
        self.stop_event.set()
        self.status.set("Status: Stop requested...", "warn")

    def _organize(self):
        try:
            folder = FolderPath(self.selected_path)
            scanner = FolderScanner(folder, recursive=self.recursive_var.get())
            result = scanner.scan()

            self.root.after(0, lambda: self.scanned_var.set(f"Scanned: {len(result.files)}"))

            mover = FileMover(Path(self.selected_path), self.log_manager, self.history_manager)
            moved, skipped = mover.move_files(result.files, self.classifier, stop_event=self.stop_event)

            self.root.after(0, lambda: self.moved_var.set(f"Moved: {moved}"))
            self.root.after(0, lambda: self.skipped_var.set(f"Skipped: {skipped}"))

            if self.stop_event.is_set():
                self.root.after(0, lambda: self.status.set(f"Stopped | Moved: {moved}  Skipped: {skipped}", "warn"))
                self.root.after(0, lambda: self.toast.show("Stopped", "Stop was requested.", "warn"))
            else:
                self.root.after(0, lambda: self.status.set(f"Done | Moved: {moved}  Skipped: {skipped}", "success"))
                self.root.after(0, lambda: self.toast.show("Done", f"Moved {moved} files (Skipped {skipped}).", "success"))

        except Exception as e:
            self.root.after(0, lambda: self.status.set(f"Failed: {str(e)}", "error"))
            self.root.after(0, lambda: self.toast.show("Failed", str(e), "error"))

    def undo_last(self):
        if not self.selected_path:
            self.toast.show("No folder selected", "Please select a folder first.", kind="error")
            return

        mover = FileMover(Path(self.selected_path), self.log_manager, self.history_manager)
        ok = mover.undo_last()
        if ok:
            self.toast.show("Undo completed", "Last move has been reverted.", "success")
            self.status.set("Undo completed", "success")
        else:
            self.toast.show("Nothing to undo", "There are no moves available.", "warn")
            self.status.set("Nothing to undo", "warn")

    def undo_all(self):
        if not self.selected_path:
            self.toast.show("No folder selected", "Please select a folder first.", kind="error")
            return

        mover = FileMover(Path(self.selected_path), self.log_manager, self.history_manager)
        count = mover.undo_all()
        if count > 0:
            self.toast.show("Undo completed", f"Reverted {count} moves.", "success")
            self.status.set(f"Undo completed | Reverted: {count}", "success")
        else:
            self.toast.show("Nothing to undo", "There are no moves available.", "warn")
            self.status.set("Nothing to undo", "warn")

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    SmartOrganizerGUI().run()