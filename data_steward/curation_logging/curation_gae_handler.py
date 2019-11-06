import logging
from google.cloud import logging_v2 as gcp_logging_v2
from google.protobuf import json_format as gcp_json_format, any_pb2 as gcp_any_pb2
from curation_logging import gcp_request_log_pb2

_DEFAULT_GAE_LOGGER_NAME = 'curation_gae_logger'


class CurationLoggingHandler(logging.Handler):

    def __init__(
            self
    ):
        super(CurationLoggingHandler, self).__init__()
        self._logging_client = gcp_logging_v2.LoggingServiceV2Client()

    def emit(self, record: logging.LogRecord):

        proto_payload = {"@type": "type.googleapis.com/google.appengine.logging.v1.RequestLog",
                         "resource": "/data_steward/v1/ValidateAllHpoFiles/test",
                         "line": [{"logMessage": record.msg, "severity": record.levelname},
                                  {"logMessage": record.msg, "severity": record.levelname}]}

        proto_payload_log_pb2 = gcp_json_format.ParseDict(proto_payload, gcp_any_pb2.Any())

        log_body = {"operation": {"id": "test_operation_id_id"}, "severity": "INFO",
                    "resource": {"type": "gae_app"},
                    "proto_payload": proto_payload_log_pb2}

        log_entry_pb2 = gcp_logging_v2.types.log_entry_pb2.LogEntry(**log_body)

        self._logging_client.write_log_entries([log_entry_pb2],
                                               log_name='projects/aou-res-curation-test/logs/{log_name}'.format(
                                                   log_name=_DEFAULT_GAE_LOGGER_NAME))
