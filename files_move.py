from pathlib import Path
import shutil
from log_storage import LogManager

#This class is responsible for moving files to their respective folders based on their categories. 
#It ensures that the destination folders exist and handles naming conflicts by appending a number to the filename if a file with the same name already exists 

class FileMover:
    def __init__(self, base_folder: Path , log_manager: LogManager):
        self.base_folder = base_folder
        self.log_manager = log_manager

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
                dest_folder = self.ensure_folder(category)

                if f.parent.resolve() == dest_folder.resolve():
                    skipped += 1
                    self.log_manager.log_skip(f, "already_in_destination")
                    continue

                dst_path = self._safe_destination_path(dest_folder, f.name)
                shutil.move(str(f), str(dst_path))             
                self.log_manager.log_move(f, dst_path)  
                moved += 1

            except (PermissionError, OSError) as e:
                skipped += 1
                self.log_manager.log_error(f, e)

        return moved, skipped