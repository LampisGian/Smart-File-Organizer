from pathlib import Path
import logging

#This class is responsible for logging all the files movements
class LogManager:
    def __init__(self, log_file: Path):
        log_file.parent.mkdir(parents=True, exist_ok=True)

        self.logger = logging.getLogger("SmartFileOrganizer")
        self.logger.setLevel(logging.INFO)

        if not self.logger.handlers:
            handler = logging.FileHandler(log_file, encoding="utf-8")
            formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def log_move(self, src: Path, dst: Path) -> None:
        self.logger.info(f"MOVED | {src} -> {dst}")

    def log_skip(self, path: Path, reason: str) -> None:
        self.logger.info(f"SKIPPED | {path} | reason={reason}")

    def log_error(self, path: Path, error: Exception) -> None:
        self.logger.error(f"ERROR | {path} | {type(error).__name__}: {error}")