import database.response


class UserDatabaseResponse(database.response.DatabaseResponse):
    def __init__(self, status: int, query: str, response: list or None = None, lastrowid: int or None = None, error_message: str or None = None):
        super().__init__(status, query, response, lastrowid, error_message)
        print(self)


if __name__ == "__main__":
    # pass
    UserDatabaseResponse(200, "select * from cool", ["sei", "lah"], 7, "No error")
