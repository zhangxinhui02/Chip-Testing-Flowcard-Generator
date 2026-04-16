import logging
from util import init_logging

init_logging()
logger = logging.getLogger(__name__)
logger.info('Chip Testing Flowcard Generator')
logger.info('Starting backend...')

import api_server

if __name__ == '__main__':
    api_server.run()
    logger.info('Backend terminated.')
