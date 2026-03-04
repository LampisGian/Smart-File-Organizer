from pathlib import Path

#This class is responsible for showing the menu to the user and getting the folder path to scan.
#  It also provides some default options for common folders like Downloads, Desktop and Documents.
class FolderMenu:
    def __init__(self):
        home = Path.home()
        self.options = {
            "1": ("Downloads", home / "Downloads"),
            "2": ("Desktop", home / "Desktop"),
            "3": ("Documents", home / "Documents"),
            "4": ("Custom path", None),
            "5": ("Exit", None),
        }

    def prompt_folder(self) -> Path | None:
        while True:
            print("\n=== Choose folder to organize ===")
            for key, (label, path) in self.options.items():
                shown = str(path) if path else ""
                print(f"{key}) {label} {shown}")

            choice = input("Select option: ").strip()

            if choice not in self.options:
                print("Invalid choice.")
                continue

            label, path = self.options[choice]

            if label == "Exit":
                return None

            if label == "Custom path":
                raw = input("Provide folder path: ").strip().strip('"')
                return Path(raw).expanduser()

            return path