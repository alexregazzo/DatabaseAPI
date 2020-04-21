import json


class DatabaseResponse:
    """Base class for all responses"""

    def __init__(self, status: int, query: str, results: list or None = None, lastrowid: int or None = None, error_message: str or None = None):
        """
        :param status: Status code of the query
        :param query: query requested to database
        :param results: database data answer (if select)
        :param lastrowid: database lastrowid (if insert)
        :param error_message: database error (if any)
        """
        assert type(status) == int
        assert type(query) is str
        assert type(results) is list or results is None
        assert type(lastrowid) is int or lastrowid is None
        assert type(error_message) is str or error_message is None

        self.status = status
        self.query = query
        self.error_message = error_message
        self.results = results
        self.lastrowid = lastrowid
        if type(self) is DatabaseResponse:
            print(self)

    @classmethod
    def good(cls, query: str, results: list or None = None, lastrowid: int or None = None):
        return cls(200, query, results, lastrowid)

    @classmethod
    def bad(cls, query: str, results: list or None = None, lastrowid: int or None = None, error_message: str or None = None):
        return cls(400, query, results, lastrowid, error_message)

    @property
    def ok(self) -> bool:
        """Retrun whether the request succeeded"""
        return self.status == 200

    def __repr__(self) -> str:
        """Representation of the class for debugging"""
        return f"""<{type(self).__name__} {self.status} || {'Error: "' + str(self.error_message) + '"' if self.error_message else 'OK'} | QUERY: "{self.query}" | LRID: "{self.lastrowid}" | Results: {self.results}>"""

    def json_object(self):
        """Return json object representation of the class"""
        return self.__dict__

    def json(self) -> str:
        """Return json representation of the class"""
        return json.dumps(self.json_object())


if __name__ == "__main__":
    pass
    # DatabaseResponse.good("ah")
