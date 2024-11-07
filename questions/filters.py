import threading
import logging
import uuid

class CorrelationIdFilter(logging.Filter):
   def filter(self, record):
        correlation_id = getattr(record, 'correlation_id', None)
        if not correlation_id:
            correlation_id = str(uuid.uuid4())
        record.correlation_id = correlation_id
        return True