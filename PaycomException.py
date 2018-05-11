from .Response import Response


class PaycomException(Exception):

    ERROR_NOT_POST_REQUEST = -32300
    ERROR_CAN_NOT_PARSING_JSON = -32700
    ERROR_INTERNAL_SYSTEM = -32400
    ERROR_INSUFFICIENT_PRIVILEGE = -32504
    ERROR_INVALID_JSON_RPC_OBJECT = -32600
    ERROR_METHOD_NOT_FOUND = -32601
    ERROR_INVALID_AMOUNT = -31001
    ERROR_TRANSACTION_NOT_FOUND = -31003
    ERROR_INVALID_ACCOUNT = -31050
    ERROR_COULD_NOT_CANCEL = -31007
    ERROR_COULD_NOT_PERFORM = -31008

    request_id = None
    error = {}
    data = None
    message = None
    code = None

    def __init__(self, request_id, message, code, data=None):
        self.request_id = request_id
        self.message = message
        self.code = code
        self.data = data
        self.error = {
            'code': self.code
        }
        if self.message:
            self.error['message'] = self.message
            return_message = "Error: {}".format(self.error['message'])
        if self.data:
            self.error['data'] = self.data
            return_message = "Error: {}, in {}".format(self.error['message'], self.error['data'])

        Exception.__init__(self, return_message)

    @staticmethod
    def message(ru, en='', uz=''):
        return {
            'ru': ru,
            'en': en,
            'uz': uz
        }