from pathlib import Path
from dataclasses import dataclass

#This class is responsible for clearing the file path from symbols and finding the whole path in linux like systems with ~ symbol
#and also validate that the path exists and is a directory. 
class FolderPath:
    def __init__(self, raw_path: str):
        self.path = Path(raw_path.strip().strip('"')).expanduser()

    def validate(self) -> None:
        if not self.path.exists():
            raise FileNotFoundError(f"Folder does not exist: {self.path}")
        if not self.path.is_dir():
            raise NotADirectoryError(f"Not a directory: {self.path}")
        
#This class is responsible for printing the results of the scan in a nice format
#Also i use dataclass to store efficiently the results of the scan which also includes the count of files .
@dataclass
class ScannerResults:
    folder: Path
    files: list[Path]

    @property
    def count(self) -> int:
        return len(self.files)

#This class is responsible for scanning the folder and returning the list of files in it. It can also scan recursively if needed.
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

'''
class App:
    def run(self) -> None:
        folder_input = input("Δώσε path φακέλου: ")
        recursive = input("Να σκανάρει και υποφακέλους; (y/n): ").strip().lower() == "y"

        folder = FolderPath(folder_input)
        scanner = FolderScanner(folder, recursive=recursive)

        try:
            result = scanner.scan()
            print(f"\nΦάκελος: {result.folder}")
            print(f"Βρέθηκαν {result.count} αρχεία:\n")
            for f in result.files:
                print(f"- {f.name} | ext={f.suffix}")

        except Exception as e:
            print("Σφάλμα:", e)


if __name__ == "__main__":
    App().run()
'''