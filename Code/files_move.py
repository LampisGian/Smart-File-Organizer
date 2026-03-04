from __future__ import annotations
from pathlib import Path
import shutil
from log_storage import LogManager
from undo_history import HistoryManager
from threading import Event

#This class is responsible for moving files to their respective folders based on their categories. 
#It ensures that the destination folders exist and handles naming conflicts by appending a number to the filename if a file with the same name already exists 
class FileMover:
    def __init__(self, base_folder, log_manager, history_manager, use_other_folder: bool = True):
        self.base_folder = base_folder
        self.log_manager = log_manager
        self.history_manager = history_manager
        self.use_other_folder = use_other_folder

    def ensure_folder(self, category: str) -> Path:
        destination = self.base_folder / category
        destination.mkdir(parents=True, exist_ok=True)
        return destination

    def _safe_destination_path(self, destination_folder: Path, filename: str) -> Path:
        candidate = destination_folder / filename
        if not candidate.exists():
            return candidate

        stem = Path(filename).stem
        suffix = Path(filename).suffix
        i = 1
        while True:
            candidate = destination_folder / f"{stem} ({i}){suffix}"
            if not candidate.exists():
                return candidate
            i += 1

    def move_files(self, files: list[Path], classifier, stop_event: Event | None = None) -> tuple[int, int]:
        moved = 0
        skipped = 0

        category_names = set(getattr(classifier, "rules", {}).keys())

        for f in files:
            if stop_event is not None and stop_event.is_set():
                break

            try:
                if f.suffix.lower() in {".log"}:
                    skipped += 1
                    self.log_manager.log_skip(f, "internal_log_file")
                    continue
                if f.name.lower().endswith(".json") and f.parent.name.lower() == "history":
                    skipped += 1
                    self.log_manager.log_skip(f, "internal_history_file")
                    continue
                try:
                    rel_parent = f.parent.resolve().relative_to(self.base_folder.resolve())
                    if rel_parent.parts and rel_parent.parts[0] in category_names:
                        skipped += 1
                        self.log_manager.log_skip(f, "inside_category_folder")
                        continue
                except ValueError:
                    skipped += 1
                    self.log_manager.log_skip(f, "outside_base_folder")
                    continue

                category = classifier.classify(f)

                if category == "Other" and not self.use_other_folder:
                    skipped += 1
                    self.log_manager.log_skip(f, "unknown_extension_keep_in_root")
                    continue

                dest_folder = self.ensure_folder(category)

                if f.parent.resolve() == dest_folder.resolve():
                    skipped += 1
                    self.log_manager.log_skip(f, "already_in_destination")
                    continue

                dst_path = self._safe_destination_path(dest_folder, f.name)

                shutil.move(str(f), str(dst_path))
                self.log_manager.log_move(f, dst_path)
                self.history_manager.append_move(f, dst_path)
                moved += 1

            except (PermissionError, OSError) as e:
                skipped += 1
                self.log_manager.log_error(f, e)

        return moved, skipped

    def undo_last(self) -> bool:
        rec = self.history_manager.pop_last()
        if rec is None:
            return False

        src = Path(rec.src)
        dst = Path(rec.dst)

        if not dst.exists():
            return False

        try:
            src.parent.mkdir(parents=True, exist_ok=True)

            safe_src = self._safe_destination_path(src.parent, src.name)

            shutil.move(str(dst), str(safe_src))
            self.log_manager.log_move(dst, safe_src)
            return True
        except (PermissionError, OSError) as e:
            self.log_manager.log_error(dst, e)
            return False

    def undo_all(self) -> int:
        count = 0
        while True:
            ok = self.undo_last()
            if not ok:
                break
            count += 1
        return count