import sqlite3
import threading
import os
import database.settings
import database.root.response
import database.root.types.user
import database.root.types.token
import database.root.types.use
import datetime


class RootDatabase:
    lock = threading.RLock()

    def __init__(self, database_name: str = 'root', autocommit: bool = True, autorollback: bool = True):
        """
        :param database_name: name of the database
        :param autocommit: Whether the the database will commit if all goes right
        :param autorollback: Whether the database will rollback if something goes wrong
        """
        assert type(database_name) is str
        assert type(autocommit) is bool
        assert type(autorollback) is bool

        path = os.path.join(database.settings.ROOT_DATABASE_PATH, database_name)
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
        with open(database.settings.ROOT_TABLES_SCRIPT_PATH) as f:
            self.cursor.executescript(f.read())
        self.conn.commit()

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

    @staticmethod
    def make_query_from_dict(joinwith: str, **kwargs):
        return joinwith.join([f"`{k}` = '{v}'" for k, v in kwargs.items()])

    def execute(self, query: str):
        """
        Generic execute statement for ONE query
        :rtype: database.root.response.RootDatabaseResponse
        """

        with self.lock:
            try:
                self.cursor.execute(query)
            except Exception as e:
                return database.root.response.RootDatabaseResponse.bad(query, error_message=str(e))
            else:
                return database.root.response.RootDatabaseResponse.good(query, results=self.cursor.fetchall(), lastrowid=self.cursor.lastrowid)

    def executescript(self, script: str):
        """
        Generic execute statement for MULTIPLE queries
        It does NOT provide any information other than error_message (useless in 'select' query)
        :rtype: database.root.response.RootDatabaseResponse
        """
        with self.lock:
            try:
                self.cursor.executescript(script)
            except Exception as e:
                return database.root.response.RootDatabaseResponse.bad(script, error_message=str(e))
            else:
                return database.root.response.RootDatabaseResponse.good(script)

    def insert_user(self, *, user_fullname: str, user_email: str, user_password: str):
        """
        Return User
        Warning: user_id ignored
        :rtype: database.root.types.user.User
        """
        user_creation = datetime.datetime.now().strftime(database.settings.DATETIME_FORMAT)
        response = self.execute(f"INSERT INTO user (user_fullname, user_email, user_password, user_creation) VALUES ('{user_fullname}', '{user_email}', '{user_password}', '{user_creation}')")
        if response.ok:
            response = self.execute(f"SELECT * FROM user WHERE user_email='{user_email}'")
            if response.ok:
                if response.results:
                    return database.root.types.user.User.from_dict(response.results[0])
        raise Exception('Could not add user')

    def select_user(self, **kwargs):
        """
        :return: User
        :rtype: database.root.types.user.User
        """
        response = self.execute(f"SELECT * FROM user WHERE {self.make_query_from_dict(' and ', **kwargs)}")
        if response.ok:
            if response.results:
                return database.root.types.user.User.from_dict(response.results[0])
        raise Exception("Could not get user")

    # def update_user(self):
    #     pass

    def insert_token(self, *, user_id: int, token_token: str, token_database_name: str):
        """
        :return: Token
        Warning: user_id ignored
        :rtype
        """
        current_dbname = f"{user_id}/{token_database_name}"
        response = self.execute("SELECT user_id || '/' || token_database_name as dbname FROM token")
        if response.ok:
            for dbname_dict in response.results:
                dbname = dbname_dict['dbname']
                if current_dbname == dbname:
                    raise Exception("Database already exists")
            token_creation = datetime.datetime.now().strftime(database.settings.DATETIME_FORMAT)
            response = self.execute(f"INSERT INTO token (user_id, token_token, token_database_name, token_creation) VALUES ('{user_id}', '{token_token}','{token_database_name}', '{token_creation}')")
            if response.ok:
                token_id = response.lastrowid
                response = self.execute(f"SELECT * FROM token WHERE token_id = '{token_id}'")
                if response.ok:
                    return database.root.types.token.Token.from_dict(response.results[0])
        raise Exception("Could not add token")

    def select_tokens(self, **kwargs):
        """
        :return: list of tokens match according to kwargs
        :rtype: list[database.root.types.token.Token]
        """
        response = self.execute(f"SELECT * FROM token WHERE {self.make_query_from_dict(' and ', **kwargs)}")
        results = []
        if response.ok:
            for token_dict in response.results:
                results.append(database.root.types.token.Token.from_dict(token_dict))
        return results

    def update_token(self, *, token_id, **kwargs):
        """
        :return: bool whether the operation has gone right
        :rtype: None
        """
        response = self.execute(f"UPDATE token SET {self.make_query_from_dict(', ', **kwargs)} WHERE token_id='{token_id}'")
        if not response.ok:
            raise Exception("Could not update token")

    def insert_use(self, *, token_token: str, use_data: str):
        """
        :return: Use
        Warning: user_id ignored
        :rtype: bool
        """
        use_creation = datetime.datetime.now().strftime(database.settings.DATETIME_FORMAT)
        response = self.execute(f"INSERT INTO use (token_id, use_data, use_creation) VALUES ((SELECT token_id FROM token WHERE token_token = '{token_token}'), '{use_data}', '{use_creation}')")
        return response.ok

    def select_uses(self, **kwargs):
        """
        :return: list of uses match according to kwargs
        :rtype: list[database.root.types.use.Use]
        """
        response = self.execute(f"SELECT * FROM use WHERE {self.make_query_from_dict(' and ', **kwargs)}")
        results = []
        if response.ok:
            for use_dict in response.results:
                results.append(database.root.types.use.Use.from_dict(use_dict))
        return results


if __name__ == "__main__":
    pass
