from pathlib import Path

#This class is responsible for classifying files based on their extensions. 
# It uses a set of rules to determine the category of each file and can also group files by their categories.
class FileClassifier:
 
    def __init__(self, rules: dict[str, set[str]] | None = None):
        self.rules = rules or self._default_rules()

    def classify(self, file_path: Path) -> str:
        ext = file_path.suffix.lower()

        for category, exts in self.rules.items():
            if ext in exts:
                return category

        return "Other"

    def group(self, files: list[Path]) -> dict[str, list[Path]]:
        
        grouped: dict[str, list[Path]] = {}
        for f in files:
            category = self.classify(f)
            grouped.setdefault(category, []).append(f)
        return grouped

    def _default_rules(self) -> dict[str, set[str]]:
        return {
            "Images": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff"},
            "Documents": {".pdf", ".txt", ".doc", ".docx", ".rtf", ".odt"},
            "Spreadsheets": {".xls", ".xlsx", ".csv", ".ods"},
            "Presentations": {".ppt", ".pptx", ".odp"},
            "Audio": {".mp3", ".wav", ".flac", ".aac", ".m4a", ".ogg"},
            "Video": {".mp4", ".mkv", ".mov", ".avi", ".wmv", ".webm"},
            "Archives": {".zip", ".rar", ".7z", ".tar", ".gz"},
            "Code": {".py", ".c", ".cpp", ".h", ".java", ".js", ".ts", ".html", ".css", ".json", ".xml"},
        }