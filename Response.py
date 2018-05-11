from django.shortcuts import HttpResponse
import json


class Response:

    request = None

    def __init__(self, request):
        self.request = request

    def send(self, result, error=None):
        data = {
            'id': self.request.id,
            'result': result,
            'error': error
        }
        return self.get_json(data)

    def error(self, code, message, data=None):
        data = {
            "error": {
                "code": code,
                "message": {
                    "ru": message,
                    "uz": message,
                    "en": message
                },
                "data": data
            },
            "result": None,
            "id": self.request.id
        }

        return self.get_json(data)

    @staticmethod
    def get_json(data):
        return json.dumps(data)



