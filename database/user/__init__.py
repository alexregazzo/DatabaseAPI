import sqlite3
import threading
import os
import database.settings
import database.user.response


class UserDatabase:
    lock = threading.RLock()

    def __init__(self, folder_name: str, database_name: str, autocommit: bool = True, autorollback: bool = True):
        """
        :param folder_name: name of the folder that the database will be in (inside USER_DATABASE_PATH)
        :param database_name: name of the database
        :param autocommit: Whether the the database will commit if all goes right
        :param autorollback: Whether the database will rollback if something goes wrong
        """
        assert type(folder_name) is str
        assert type(database_name) is str
        assert type(autocommit) is bool
        assert type(autorollback) is bool

        path = os.path.join(database.settings.USER_DATABASE_PATH, folder_name, database_name)
        if os.path.splitext(path)[1] != ".db":
            path += ".db"
        os.makedirs(os.path.split(path)[0], exist_ok=True)
        self.path = path
        self.autocommit = autocommit
        self.autorollback = autorollback
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = lambda c, r: dict([(col[0], r[idx]) for idx, col in enumerate(c.description)])
        self.cursor = self.conn.cursor()
        self.cursor.execute("PRAGMA foreign_keys = ON;")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Closing context manager, verify if rollsback or commit and if they are enabled
        Always raises (return False)
        """
        if exc_type:
            # something went wrong
            if self.autorollback:
                self.conn.rollback()
        else:
            # all good
            if self.autocommit:
                self.conn.commit()
        self.conn.close()
        return False  # raise exception

    def execute(self, query: str):
        """
        Generic execute statement for ONE query
        :rtype: database.user.response.UserDatabaseResponse
        """

        with self.lock:
            try:
                self.cursor.execute(query)
            except Exception as e:
                return database.user.response.UserDatabaseResponse.bad(query, error_message=str(e))
            else:
                return database.user.response.UserDatabaseResponse.good(query, results=self.cursor.fetchall(), lastrowid=self.cursor.lastrowid)

    def executescript(self, script: str):
        """
        Generic execute statement for MULTIPLE queries
        It does NOT provide any information other than error_message (useless in 'select' query)
        """
        with self.lock:
            try:
                self.cursor.executescript(script)
            except Exception as e:
                return database.user.response.UserDatabaseResponse.bad(script, error_message=str(e))
            else:
                return database.user.response.UserDatabaseResponse.good(script)


if __name__ == "__main__":
    print(database)
