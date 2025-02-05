import logging
import sys
from loguru import logger as loggeru
import streamlit
import os
from pathlib import Path
from typing import Final


LOG_LEVEL: Final[str] = os.getenv("LOG_LEVEL", "INFO")
LOG_RETENTION_DAYS: Final[str] = os.getenv("LOG_RETENTION_DAYS", "30 days")
LOG_ROTATION_SIZE: Final[str] = os.getenv("LOG_ROTATION_SIZE", "100 MB")

PROJECT_ROOT: Final[Path] = Path(__file__).parent
LOG_DIR: Final[Path] = PROJECT_ROOT / "logs"

LOG_DIR.mkdir(exist_ok=True)
for subdir in ['archive']:
    (LOG_DIR / subdir).mkdir(exist_ok=True)

LOG_FORMAT: Final[str] = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "<level>{message}</level>"
)

class InterceptHandler(logging.Handler):
    loglevel_mapping = {
        50: 'CRITICAL',
        40: 'ERROR',
        30: 'WARNING',
        20: 'INFO',
        10: 'DEBUG',
        0: 'NOTSET',
    }

    def emit(self, record):
        try:
            level = loggeru.level(record.levelname).name
        except AttributeError:
            level = self.loglevel_mapping[record.levelno]

        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        log = loggeru.bind(request_id='app')
        log.opt(
            depth=depth,
            exception=record.exc_info
        ).log(level, record.getMessage())


class CustomizeLogger:

    @classmethod
    def make_logger(cls, logger_name: str):
        loggeru.remove()

        loggeru.add(
            sys.stdout,
            format=LOG_FORMAT,
            level=LOG_LEVEL,
            colorize=True
        )

        loggeru.add(
            LOG_DIR / logger_name / "app.log",
            format=LOG_FORMAT,
            level=LOG_LEVEL,
            rotation=LOG_ROTATION_SIZE,
            retention=LOG_RETENTION_DAYS,
            compression="zip",
            encoding="utf-8"
        )

        loggeru.add(
            LOG_DIR / logger_name / "errors.log",
            format=LOG_FORMAT,
            level="ERROR",
            rotation="1 week",
            retention=LOG_RETENTION_DAYS,
            compression="zip",
            encoding="utf-8",
            backtrace=True,
            diagnose=True
        )

        logging.basicConfig(handlers=[InterceptHandler()], level=0)
        

        return loggeru.bind(request_id=None, method=None)

logger = CustomizeLogger.make_logger("tg-bot")
