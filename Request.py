import json
import sys
from .PaycomException import PaycomException
from .Format import Format


class Request:
    id = None
    method = None
    payload = None
    amount = None
    params = None

    def __init__(self, request):
        try:
            payload = request.body.decode("utf-8")
            self.payload = json.loads(payload)
            if self.payload is None:
                PaycomException(None, message='ERROR INVALID JSON RPC OBJECT',
                                code=PaycomException.ERROR_INVALID_JSON_RPC_OBJECT)
        except TypeError or ValueError:
            PaycomException(None, message='ERROR INVALID JSON RPC OBJECT',
                            code=PaycomException.ERROR_INVALID_JSON_RPC_OBJECT)
        self.id = self.payload['id'] if 'id' in self.payload else None
        self.method = self.payload['method'] if 'method' in self.payload else None
        self.params = self.payload['params'] if 'params' in self.payload else []
        self.amount = self.payload['params']['amount'] if 'amount' in self.payload['params'] and not \
            Format.is_not_numeric(self.payload['params']['amount']) else None

