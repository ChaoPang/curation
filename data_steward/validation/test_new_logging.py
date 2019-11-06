# Imports the Google Cloud client library
import logging
from google.cloud.logging import client
from google.cloud import logging_v2 as gcp_logging_v2
from google.protobuf import json_format as gcp_json_format, any_pb2 as gcp_any_pb2
import gcp_request_log_pb2
from google.cloud.logging.handlers import CloudLoggingHandler

LOG_NAME = 'test_logger'

if __name__ == '__main__':
    # Instantiates a client
    # logging_client = client.Client()

    # handler = CloudLoggingHandler(logging_client, name=LOG_NAME)
    #
    # cloud_logger = logging.getLogger("cloudLogger")
    # cloud_logger.setLevel(logging.INFO)
    # cloud_logger.addHandler(handler)

    # logger = logging_client.logger(LOG_NAME)

    logging_client = gcp_logging_v2.LoggingServiceV2Client()

    protoPayload = {"@type": "type.googleapis.com/google.appengine.logging.v1.RequestLog",
                    "resource": "/data_steward/v1/ValidateAllHpoFiles",
                    "line": [{"logMessage": "Hello world number one", "severity": "INFO"},
                             {"logMessage": "Hello world number two", "severity": "INFO"}]}

    protoPayload_log_pb2 = gcp_json_format.ParseDict(protoPayload, gcp_any_pb2.Any())

    # print(protoPayload_log_pb2)

    log_body = {"operation": {"id": "test_operation_id_id"}, "severity": "INFO",
                "resource": {"type": "global"},
                "proto_payload": protoPayload_log_pb2}

    log_entry_pb2 = gcp_logging_v2.types.log_entry_pb2.LogEntry(**log_body)

    logging_client.write_log_entries([log_entry_pb2], log_name='projects/aou-res-curation-test/logs/{log_name}'.format(log_name=LOG_NAME))

    #
    # print(protoPayload_log_pb2)
    #
    # logger.log_proto(log_body)
    # cloud_logger.error("bad news")
    # cloud_logger.error("worst news")
    # cloud_logger.info("Good news now!")
