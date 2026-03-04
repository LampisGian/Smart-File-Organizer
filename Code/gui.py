import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog
from pathlib import Path
from file_scanner import FolderPath, FolderScanner
from extension_classifier import FileClassifier
from log_storage import LogManager
from undo_history import HistoryManager
from files_move import FileMover


def app_data_dir() -> Path:
    base = Path.home() / "Library" / "Application Support" / "Smart File Organizer"
    base.mkdir(parents=True, exist_ok=True)
    return base
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD # Option for drag and drop support with the library tkinterdnd2.
    DND_AVAILABLE = True
except Exception:
    DND_AVAILABLE = False
    TkinterDnD = tk.Tk
    DND_FILES = None

#This class is responsible for the notifications that appear in the top right corner infroming the user about the status 
class Toast:
    def __init__(self, root: tk.Tk):
        self.root = root

        self.w = 400
        self.h = 92
        self.pad = 16

        self.container = tk.Frame(
            root,
            bg="#111827",
            highlightbackground="#60a5fa",
            highlightthickness=2
        )

        self.title_lbl = tk.Label(
            self.container, text="",
            bg="#111827", fg="#e5f1ff",
            font=("Helvetica", 12, "bold"),
            anchor="w"
        )
        self.title_lbl.pack(fill="x", padx=12, pady=(10, 2))

        self.msg_lbl = tk.Label(
            self.container, text="",
            bg="#111827", fg="#e5f1ff",
            font=("Helvetica", 10),
            justify="left", wraplength=self.w - 24,
            anchor="w"
        )
        self.msg_lbl.pack(fill="x", padx=12, pady=(0, 10))

        self._hide_after_id = None
        self.container.place_forget()  

    def show(self, title: str, message: str, kind: str = "info", duration_ms: int = 2500):
        if self._hide_after_id is not None:
            try:
                self.root.after_cancel(self._hide_after_id)
            except Exception:
                pass
            self._hide_after_id = None

        if kind == "success":
            bg, border, fg = "#0f2a1b", "#2ecc71", "#eafff3"
        elif kind == "error":
            bg, border, fg = "#2a0f0f", "#e74c3c", "#ffecec"
        elif kind == "warn":
            bg, border, fg = "#2a230f", "#f1c40f", "#fff6d6"
        else:
            bg, border, fg = "#111827", "#60a5fa", "#e5f1ff"

        self.container.config(bg=bg, highlightbackground=border)
        self.title_lbl.config(text=title, bg=bg, fg=fg)
        self.msg_lbl.config(text=message, bg=bg, fg=fg)

        self.root.update_idletasks()
        self.container.place(
            relx=1.0, x=-(self.pad), y=self.pad,
            anchor="ne",
            width=self.w, height=self.h
        )
        self.container.lift() 
        self._hide_after_id = self.root.after(duration_ms, self.hide)

    def hide(self):
        self.container.place_forget()
        self._hide_after_id = None

#This class is responsible for the status of the application with matching colours to the proccess
class StatusBar(tk.Frame):
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
            self.label.config(fg="#2ecc71")  
        elif kind == "error":
            self.label.config(fg="#e74c3c")  
        elif kind == "warn":
            self.label.config(fg="#f1c40f")  
        else:
            self.label.config(fg="#e5e7eb")  

#This class is responsiblr for the main buttons style and behaviour, it is used for the start, stop and undo buttons in the UI
class ColorButton(tk.Frame):
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

        #Using cnavas logic for hover and click effects in order to be stable 
        self.canvas.bind("<Enter>", self._on_enter)
        self.canvas.bind("<Leave>", self._on_leave)
        self.canvas.bind("<Button-1>", self._on_click)

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

#This class is responsible for handling the main GUI managing all the user interactions and buttons 
class SmartOrganizerGUI:
    def __init__(self):
        self.root = TkinterDnD.Tk() if DND_AVAILABLE else tk.Tk()
        self.root.title("Smart File Organizer")
        self.root.geometry("860x520")
        self.root.resizable(False, False)
        self.root.minsize(820, 480)

        self.bg = "#0b1220"
        self.card = "#111827"
        self.card2 = "#0f172a"
        self.text = "#e5e7eb"
        self.muted = "#9ca3af"
        self.border = "#1f2937"
        self.accent = "#60a5fa"

        self.root.configure(bg=self.bg)

        self.selected_path = ""
        self.recursive_var = tk.BooleanVar(value=False)
        self.stop_event = threading.Event()
        self.worker_thread: threading.Thread | None = None

        self.classifier = FileClassifier()
        data_dir = app_data_dir()
        self.log_manager = LogManager(data_dir / "moves_logs.log")
        self.history_manager = HistoryManager(data_dir / "moved_files_history.json")

        self.toast = Toast(self.root)

        self._build_ui()

    def _build_ui(self):
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

        main = tk.Frame(self.root, bg=self.bg)
        main.pack(fill="both", expand=True, padx=18, pady=10)

        left = tk.Frame(main, bg=self.bg)
        left.pack(side="left", fill="y", padx=(0, 14))

        right = tk.Frame(main, bg=self.bg)
        right.pack(side="left", fill="both", expand=True)

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

        browse_btn = ColorButton(
            left, "📂 Browse…", self.browse,
            bg="#334155", hover_bg="#475569",
            width=180, height=42
        )
        browse_btn.pack(fill="x")

        card = tk.Frame(right, bg=self.card, highlightbackground=self.border, highlightthickness=1)
        card.pack(fill="both", expand=True)

        tk.Label(card, text="Controls", bg=self.card, fg=self.text,
                 font=("Helvetica", 13, "bold")).pack(anchor="w", padx=14, pady=(12, 8))

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

        counters = tk.Frame(card, bg=self.card)
        counters.pack(fill="x", padx=14, pady=(0, 12))

        self.scanned_var = tk.StringVar(value="Scanned: 0")
        self.moved_var = tk.StringVar(value="Moved: 0")
        self.skipped_var = tk.StringVar(value="Skipped: 0")

        tk.Label(counters, textvariable=self.scanned_var, bg=self.card, fg=self.muted, font=("Helvetica", 10)).pack(side="left")
        tk.Label(counters, textvariable=self.moved_var, bg=self.card, fg=self.muted, font=("Helvetica", 10)).pack(side="left", padx=16)
        tk.Label(counters, textvariable=self.skipped_var, bg=self.card, fg=self.muted, font=("Helvetica", 10)).pack(side="left", padx=16)

        hint = "Tip: Start organizes files. Stop requests a graceful stop. Undo works only after moves."
        tk.Label(card, text=hint, bg=self.card, fg=self.muted, font=("Helvetica", 10),
                 justify="left", wraplength=520).pack(anchor="w", padx=14, pady=(0, 12))

        self.status = StatusBar(self.root)
        self.status.pack(fill="x", padx=10, pady=(0, 10))

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

    def start(self):
        if not self.selected_path:
            self.toast.show("No folder selected", "Please browse or drop a folder first.", kind="error")
            return

        if self.worker_thread and self.worker_thread.is_alive():
            self.toast.show("Already running", "The organizer is currently running.", kind="warn")
            return

        self.stop_event.clear()
        self.status.set("Status: Organizing...", "info")

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

        self.undo_all_btn.set_enabled(False)
        self.undo_last_btn.set_enabled(False)

        def worker():
            mover = FileMover(Path(self.selected_path), self.log_manager, self.history_manager)
            count = mover.undo_all()

            def done():
                self.undo_all_btn.set_enabled(True)
                self.undo_last_btn.set_enabled(True)
                if count > 0:
                    self.toast.show("Undo completed", f"Reverted {count} moves.", "success")
                    self.status.set(f"Undo completed | Reverted: {count}", "success")
                else:
                    self.toast.show("Nothing to undo", "There are no moves available.", "warn")
                    self.status.set("Nothing to undo", "warn")

            self.root.after(0, done)

        threading.Thread(target=worker, daemon=True).start()
        
    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    SmartOrganizerGUI().run()