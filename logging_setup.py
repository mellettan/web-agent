from loguru import logger
import sys
import os
from config import settings


def setup_logger():
    """Настраивает и конфигурирует логгер Loguru."""

    logger.remove()
    logger.add(
        sys.stdout,
        level="INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}:{function}:{line}</cyan> - <level>{message}</level>",
    )
    log_file_path = os.path.join(
        settings.LOGS_DIR, "run_{time:YYYY-MM-DD_HH-mm-ss}.log"
    )
    logger.add(log_file_path, level="DEBUG", rotation="10 MB", compression="zip")
    logger.info("Логгер успешно настроен.")
