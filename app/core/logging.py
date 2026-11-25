import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime

# Set per request by RequestContextMiddleware; read by the log filter below.
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx.get()
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "time": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "request_id": getattr(record, "request_id", "-"),
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def configure_logging(level: str, json_logs: bool) -> None:
    formatter: logging.Formatter = (
        JsonFormatter()
        if json_logs
        else logging.Formatter(
            "%(asctime)s %(levelname)-8s [%(request_id)s] %(name)s: %(message)s"
        )
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(RequestIdFilter())
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)

    # Our middleware writes the access log (with request IDs) instead.
    logging.getLogger("uvicorn.access").disabled = True
