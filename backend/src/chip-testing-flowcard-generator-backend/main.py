import os
import logging
from logging.handlers import TimedRotatingFileHandler

from config import common_config
import api_router

logger = logging.getLogger(__name__)


def init_logging():
    """初始化日志系统"""
    log_format_str = '[%(asctime)s][%(name)s][%(levelname)s] %(message)s'
    os.makedirs(common_config.log_dir, exist_ok=True)

    if common_config.log_level == 'CRITICAL':
        level = logging.CRITICAL
    elif common_config.log_level == 'ERROR':
        level = logging.ERROR
    elif common_config.log_level == 'WARNING':
        level = logging.WARNING
    elif common_config.log_level == 'INFO':
        level = logging.INFO
    else:
        level = logging.DEBUG

    logging.basicConfig(
        level=level,
        format=log_format_str,
    )

    file_handler = TimedRotatingFileHandler(
        filename=os.path.join(common_config.log_dir, 'app.log'),
        when="midnight",
        interval=1,
        backupCount=common_config.log_rotation_days,
        encoding="utf-8"
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(logging.Formatter(log_format_str))
    logging.getLogger().addHandler(file_handler)


if __name__ == '__main__':
    init_logging()
    logger.info('Chip Testing Flowcard Generator')
    logger.info('Starting backend...')

    api_router.run()

    logger.info('Shutting down backend...')
