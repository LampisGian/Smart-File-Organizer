from pathlib import Path
from dataclasses import dataclass

# This class is responsible for scanning the selected folder and returning a list of files that can be organized.
class FolderPath:
    def __init__(self, raw_path: str):
        self.path = Path(raw_path.strip().strip('"')).expanduser()

    def validate(self) -> None:
        if not self.path.exists():
            raise FileNotFoundError(f"Folder does not exist: {self.path}")
        if not self.path.is_dir():
            raise NotADirectoryError(f"Not a directory: {self.path}")

#This class represents the results of scanning a folder, including the folder path and the list of files found.
@dataclass
class ScannerResults:
    folder: Path
    files: list[Path]

    @property
    def count(self) -> int:
        return len(self.files)

#This class is responsible for scanning the selected folder and returning a list of files that can be organized. 
class FolderScanner:
    def __init__(self, folder: FolderPath, recursive: bool = False):
        self.folder = folder
        self.recursive = recursive

    def scan(self) -> ScannerResults:
        self.folder.validate()

        if self.recursive:
            files = [p for p in self.folder.path.rglob("*") if p.is_file()]
        else:
            files = [p for p in self.folder.path.iterdir() if p.is_file()]

        return ScannerResults(folder=self.folder.path, files=files)