from pathlib import Path
from dataclasses import dataclass
from extension_classifier import FileClassifier
from files_move import FileMover
from log_storage import LogManager
from folder_menu import FolderMenu
from undo_history import HistoryManager

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
            files = [p for p in self.folder.path.rglob("*") if p.is_file()] #Scanning subfolders too
        else:
            files = [p for p in self.folder.path.iterdir() if p.is_file()] #Scanning only the current folder

        return ScannerResults(folder=self.folder.path, files=files)

#This is the main application class that runs the program 
#it takes the folder path and the depth of the search and prints the results 
class App:
    def run(self) -> None:
        classifier = FileClassifier()
        log_manager = LogManager(Path("logs") / "moves_logs.log")
        history_manager = HistoryManager(Path("history") / "moved_files_history.json")

        while True:
            menu = FolderMenu()
            selected = menu.prompt_folder()

            if selected is None:
                print("Bye!")
                return  

            recursive = input("Should it scan subfolders too? (y/n): ").strip().lower() == "y"

            folder = FolderPath(str(selected))
            scanner = FolderScanner(folder, recursive=recursive)
            mover = FileMover(folder.path, log_manager, history_manager)

            while True:
                print("\n=== Actions Menu ===")
                print("1) Organize now")
                print("2) Undo last move")
                print("3) Undo ALL moves")
                print("4) Back to folder selection")

                choice = input("Choose: ").strip()

                if choice == "1":
                    try:
                        result = scanner.scan()
                        files = result.files

                        moved, skipped = mover.move_files(files, classifier)
                        print(f"\nMoved: {moved}, Skipped: {skipped}")

                    except Exception as e:
                        print("Error:", e)

                elif choice == "2":
                    ok = mover.undo_last()
                    if ok:
                        print("Undo completed.")
                    else:
                        print("No moves to undo.")

                elif choice == "3":
                    undone = mover.undo_all()
                    if undone == 0:
                        print("No moves to undo.")
                    else:
                        print(f"Undo completed for {undone} moves.")

                elif choice == "4":
                    break

if __name__ == "__main__":
    App().run()
