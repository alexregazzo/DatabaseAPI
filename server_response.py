import json


class BadResponse:
    def __init__(self, error_message):
        self.error_message = error_message

    def json(self):
        return json.dumps(self.__dict__)
