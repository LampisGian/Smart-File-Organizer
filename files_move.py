from pathlib import Path
import shutil

#This class is responsible for moving files to their respective folders based on their categories. 
#It ensures that the destination folders exist and handles naming conflicts by appending a number to the filename if a file with the same name already exists 
from pathlib import Path
import shutil

class FileMover:
    def __init__(self, base_folder: Path):
        self.base_folder = base_folder

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
                    continue

                dst_path = self._safe_destination_path(dest_folder, f.name)
                shutil.move(str(f), str(dst_path))
                moved += 1

            except (PermissionError, OSError):
                skipped += 1

        return moved, skipped