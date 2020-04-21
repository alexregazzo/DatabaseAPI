import database.response
import json
import flask
import urllib.parse
import database.root.types.use


class APIResponse:
    """Every API response is a call of json method from this class"""

    def __init__(self, *, status: int, query: str, token: str or None = None, database_response: database.response.DatabaseResponse or None = None, error_message: str or None = None):
        pass
        """
        :param status: status code of the request
        :param query: query requested to API (url)
        :param database_response: database data answer if request went well
        :param error_message: request error (if any)
        """
        assert type(status) == int
        assert type(query) is str
        assert type(token) is str or token is None
        assert isinstance(database_response, database.response.DatabaseResponse) or database_response is None
        assert type(error_message) is str or error_message is None

        self.status = status
        self.query = urllib.parse.unquote(query)
        self.token = token
        self.database_response = database_response
        self.error_message = error_message
        if self.token:
            print("OK" if database.root.types.use.Use.create(self) else "KO" )
        print(self)

    def get_response(self) -> flask.Response:
        """Return flask response of this class"""
        return flask.Response(response=self.json(), status=self.status, mimetype='application/json')

    @classmethod
    def good(cls, *, query: str, token: str or None = None, database_response: database.response.DatabaseResponse):
        return cls(status=200, query=query, token=token, database_response=database_response)

    @classmethod
    def bad(cls, *, query: str, token: str or None = None, error_message: str or None):
        return cls(status=400, query=query, token=token, error_message=error_message)

    @property
    def ok(self) -> bool:
        """Retrun whether the request succeeded"""
        return self.status == 200

    def __repr__(self) -> str:
        """Representation of the class for debugging"""
        return f"""<{type(self).__name__} {self.status} || {'Error: "' + str(self.error_message) + '"' if self.error_message else 'OK'} | QUERY: "{self.query}">"""

    def json_object(self):
        """Return json object representation of the class"""
        return self.__dict__

    def json(self, **kwargs) -> str:
        """Return json representation of the class"""
        return json.dumps(self.json_object(), default=lambda o: o.json_object(), **kwargs)


if __name__ == "__main__":
    pass
    # DatabaseResponse.good("ah")
