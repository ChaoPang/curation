# Imports the Google Cloud client library
import logging
from google.cloud.logging import client
from curation_logging.curation_gae_handler import CurationLoggingHandler

LOG_NAME = 'curation_gae_logger'

if __name__ == '__main__':
    # Instantiates a client
    logging_client = client.Client()
    logger = logging_client.logger(LOG_NAME)
    logger.delete()


    # curation_logging_handler = CurationLoggingHandler()
    #
    # cloud_logger = logging.getLogger(LOG_NAME)
    # cloud_logger.setLevel(logging.INFO)
    # cloud_logger.addHandler(curation_logging_handler)
    #
    # cloud_logger.info("Hello world!")
    #
    # cloud_logger.error("Terrible world!")
