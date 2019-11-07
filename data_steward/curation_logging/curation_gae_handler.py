import logging
import os
import random
import string
from flask import request
from google.cloud import logging_v2 as gcp_logging_v2
from google.protobuf import json_format as gcp_json_format, any_pb2 as gcp_any_pb2
from curation_logging import gcp_request_log_pb2

_DEFAULT_GAE_LOGGER_NAME = 'curation_gae_logger'
REQUEST_LOG_TYPE = "type.googleapis.com/google.appengine.logging.v1.RequestLog"
GAE_APP = "gae_app"


class CurationLoggingHandler(logging.Handler):

    def __init__(
            self
    ):
        super(CurationLoggingHandler, self).__init__()
        self._logging_client = gcp_logging_v2.LoggingServiceV2Client()
        self._operation_id = None
        self._request = None
        self._log_records = []

    def emit(self, record: logging.LogRecord):
        self._log_records.append(record)

    def _cleanup(self):
        self._operation_id = None
        self._request = None
        self._log_records.clear()

    def setup_from_request(self, _request):
        self._request = _request
        self._operation_id = ''.join(
            random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(16))

    def publish_to_stack_driver(self):
        proto_payload = {
            "@type": REQUEST_LOG_TYPE,
            "resource": 'ValidateAllHpoFiles',
            "line": None
        }

        log_messages = []
        for record in self._log_records:
            log_messages.append({"logMessage": record.msg, "severity": record.levelname})

        proto_payload["line"] = log_messages
        proto_payload_log_pb2 = gcp_json_format.ParseDict(proto_payload, gcp_any_pb2.Any())

        log_severity = self._get_highest_log_level()

        log_body = {
            "operation": {
                "id": self._operation_id
            },
            "severity": log_severity,
            "resource": {
                "type": GAE_APP
            },
            "proto_payload": proto_payload_log_pb2
        }

        log_entry_pb2 = gcp_logging_v2.types.log_entry_pb2.LogEntry(**log_body)

        log_name = 'projects/aou-res-curation-test/logs/{log_name}'.format(log_name=_DEFAULT_GAE_LOGGER_NAME)
        self._logging_client.write_log_entries([log_entry_pb2], log_name)

    def finalize(self, response):

        self.publish_to_stack_driver()
        self._cleanup()

    def _get_highest_log_level(self):
        if self._log_records:
            s = sorted(self._log_records, key=lambda log_record: -log_record.levelno)
            return s[0].levelname
        else:
            return gcp_logging_v2.gapic.enums.LogSeverity(200)


class FlaskGCPStackDriverLogging:
    """
    Context Manager to handle logging to GCP StackDriver logging service.
    """

    _log_handler = None

    def __init__(self, log_level=logging.INFO):
        # Configure root logger
        self.root_logger = logging.getLogger()
        self.root_logger.setLevel(log_level)
        # Configure StackDriver logging handler
        self._log_handler = CurationLoggingHandler()
        self._log_handler.setLevel(log_level)
        # Add StackDriver logging handler to root logger.
        self.root_logger.addHandler(self._log_handler)

    def begin_request(self):
        """
        Initialize logging for a new request.
        """
        if self._log_handler:
            self._log_handler.setup_from_request(request)

    def end_request(self, response):
        """
        Finalize and send any log entries.  Not guarantied to always be called.
        """
        if self._log_handler:
            self._log_handler.finalize(response)
        return response


app_log_service = FlaskGCPStackDriverLogging()


def setup_request_logging():
    app_log_service.begin_request()


def finalize_request_logging(response):
    """
    Finalize and send log message(s) for request.
    :param response: Flask response object
    """
    app_log_service.end_request(response)
    return response
