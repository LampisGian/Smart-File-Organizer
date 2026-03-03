from pathlib import Path
import shutil
from log_storage import LogManager
from undo_history import HistoryManager

#This class is responsible for moving files to their respective folders based on their categories. 
#It ensures that the destination folders exist and handles naming conflicts by appending a number to the filename if a file with the same name already exists 
class FileMover:
    def __init__(self, base_folder: Path, log_manager: LogManager, history_manager: HistoryManager):
        self.base_folder = base_folder
        self.log_manager = log_manager
        self.history_manager = history_manager

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

    def move_files(self, files: list[Path], classifier) -> tuple[int, int]:
        moved = 0
        skipped = 0

        for f in files:
            try:
                category = classifier.classify(f)

                if category == "Other":
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