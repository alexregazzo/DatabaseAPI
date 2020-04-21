import database.response


class RootDatabaseResponse(database.response.DatabaseResponse):
    def __init__(self, status: int, query: str, response: list or None = None, lastrowid: int or None = None, error_message: str or None = None):
        super().__init__(status, query, response, lastrowid, error_message)
        print(self)


if __name__ == "__main__":
    pass
    # RootDatabaseResponse(200, "select * from test", ["sei", "lah"], 7, "No error")
