import logging
import app_identity
import random
import string
from datetime import datetime, timezone
from flask import request
from google.cloud import logging_v2 as gcp_logging_v2
from google.protobuf import json_format as gcp_json_format, any_pb2 as gcp_any_pb2
from googleapiclient import discovery
from curation_logging import gcp_request_log_pb2

REQUEST_LOG_TYPE = "type.googleapis.com/google.appengine.logging.v1.RequestLog"
LOG_NAME_TEMPLATE = "projects/{project_id}/logs/appengine.googleapis.com%2Frequest_log"
GAE_APP = "gae_app"
BUFFER_SIZE = 50


class CurationLoggingHandler(logging.Handler):

    def __init__(
            self
    ):
        super(CurationLoggingHandler, self).__init__()
        self._logging_client = gcp_logging_v2.LoggingServiceV2Client()
        self._operation_id = None
        self._request_url_rule = None
        self._request_start_time = None
        self._request_end_time = None
        self._request_method = None
        self._request_endpoint = None
        self._request_resource = None
        self._request_agent = None
        self._request_remote_addr = None
        self._request_host = None
        self._request_log_id = None

        self._request_taskname = None
        self._request_queue = None

        self.trace_id = None
        self._trace = None

        self._log_records = []

    def setup_from_request(self, _request):

        self._operation_id = ''.join(
            random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(16))
        self._request_start_time = datetime.now(timezone.utc).isoformat()

        if _request:
            self._request_method = _request.method
            self._request_url_rule = str(_request.url_rule)
            self._request_endpoint = _request.endpoint
            self._request_resource = _request.path
            self._request_agent = str(_request.user_agent)
            self._request_remote_addr = _request.headers.get('X-Appengine-User-Ip', _request.remote_addr)
            self._request_host = _request.headers.get('X-Appengine-Default-Version-Hostname', _request.host)
            self._request_log_id = _request.headers.get('X-Appengine-Request-Log-Id', 'None')

            self._request_taskname = _request.headers.get('X-Appengine-Taskname', None)
            self._request_queue = _request.headers.get('X-Appengine-Queuename', None)

            trace_id = _request.headers.get('X-Cloud-Trace-Context', '')
            if trace_id:
                trace_id = trace_id.split('/')[0]
                trace = 'projects/{0}/traces/{1}'.format(app_identity.get_application_id(), trace_id)
                self._trace = trace

    def emit(self, record: logging.LogRecord):

        time = datetime.fromtimestamp(record.created).replace(tzinfo=timezone.utc).isoformat()
        func_name = record.funcName if record.funcName else ''
        file = record.pathname if record.pathname else ''
        line_no = record.lineno if record.lineno else 0
        source_location = {
            "file": file,
            "functionName": func_name,
            "line": line_no
        }

        record_line = {
            "levelname": record.levelname,
            "levelno": record.levelno,
            "msg": record.msg % record.args if record.args else record.msg,
            "time": time,
            "sourceLocation": source_location
        }

        self._log_records.append(record_line)

        if len(self._log_records) >= BUFFER_SIZE:
            self.publish_to_stack_driver()

    def publish_to_stack_driver(self):

        self._request_end_time = datetime.now(timezone.utc).isoformat()

        log_severity = self._get_highest_log_level()

        log_request_body = {
            "operation": {
                "id": self._operation_id
            },
            "severity": log_severity,
            "resource": {
                "type": GAE_APP
            },
            "proto_payload": self._setup_proto_payload()
        }

        log_entry_pb2 = gcp_logging_v2.types.log_entry_pb2.LogEntry(**log_request_body)

        self._logging_client.write_log_entries([log_entry_pb2],
                                               LOG_NAME_TEMPLATE.format(project_id=app_identity.get_application_id()))

        self._log_records.clear()

    def finalize(self, response):
        self.publish_to_stack_driver()
        self._cleanup()

    def _setup_proto_payload(self):

        proto_payload = {
            "@type": REQUEST_LOG_TYPE,
            "startTime": self._request_start_time,
            "endTime": self._request_end_time,
            "method": self._request_method,
            "resource": self._request_url_rule,
            "userAgent": self._request_agent,
            "host": self._request_host,
            "ip": self._request_remote_addr,
            "requestId": self._request_log_id,
            "traceId": self._trace,
            "line": [],
            "userAgent": self._request_agent,
            "urlMapEntry": "validation.main.app"
        }

        log_messages = []
        for record in self._log_records:
            log_messages.append({
                "logMessage": record["msg"],
                "severity": record["levelname"],
                "sourceLocation": record["sourceLocation"],
                "time": record["time"]
            })
        proto_payload["line"] = log_messages

        return gcp_json_format.ParseDict(proto_payload, gcp_any_pb2.Any())

    def _get_highest_log_level(self):
        if self._log_records:
            s = sorted(self._log_records, key=lambda log_record: -log_record['levelno'])
            return s[0]['levelname']
        else:
            return gcp_logging_v2.gapic.enums.LogSeverity(200)

    def _cleanup(self):
        self._operation_id = None
        self._request_start_time = None
        self._request_end_time = None
        self._request_url_rule = None
        self._request_method = None
        self._request_endpoint = None
        self._request_resource = None
        self._request_agent = None
        self._request_remote_addr = None
        self._request_log_id = None
        self._request_host = None

        # cloud tasks
        self._request_task_name = None
        self._request_queue = None
        self._reuqest_user_agent = None

        self._log_records.clear()


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

        logger = logging.getLogger('projects/aou-res-curation-test/logs/stderr')
        logger.propagate = False
        logger.setLevel(logging.ERROR)
        logging.getLogger('stderr').setLevel(logging.ERROR)
        logging.getLogger('discovery').setLevel(logging.ERROR)
        discovery.logger.setLevel(logging.ERROR)

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
