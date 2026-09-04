# -*- coding: utf-8 -*-
"""日志：同时输出到控制台与文件（方便排查问题）"""
from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler

from .config import app_data_dir

_initialized = False


def setup_logger(level: int = logging.INFO) -> logging.Logger:
    global _initialized
    logger = logging.getLogger("cainiao")
    if _initialized:
        return logger
    _initialized = True
    logger.setLevel(level)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    try:
        log_dir = app_data_dir()
        fh = RotatingFileHandler(os.path.join(log_dir, "cainiao.log"),
                                 maxBytes=2 * 1024 * 1024, backupCount=3, encoding="utf-8")
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    except Exception:
        pass
    logger.propagate = False
    return logger


def get_logger() -> logging.Logger:
    return setup_logger()
