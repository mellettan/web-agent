import sys
from pathlib import Path

from loguru import logger


def setup_logging(logs_dir: Path, level: str = "INFO") -> None:
    """Короткие логи в консоль и подробные (DEBUG) в файл на каждый запуск."""
    logs_dir.mkdir(parents=True, exist_ok=True)
    logger.remove()
    logger.add(
        sys.stderr, level=level, format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}"
    )
    logger.add(logs_dir / "run_{time:YYYY-MM-DD_HH-mm-ss}.log", level="DEBUG", rotation="10 MB", encoding="utf-8")
