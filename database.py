import sqlite3
import threading
import json
import os
import datetime
import jwt
import secrets

with open("config.json") as file:
    CONFIG = json.load(file)

TOKEN_KEY = CONFIG["token_secret_key"]
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


class User:
    def __init__(self, user_id: int, user_fullname: str, user_email: str, user_active: int, user_password: str, user_creation: str):
        """
        :param user_id: Integer that uniquely identifies user
        :param user_fullname: User full name
        :param user_email: User email
        :param user_active: 1 or 0 representing active and inactive, respectively
        :param user_password: user hashed (**always**) password
        :param user_creation: date of the user creation
        """
        self.user_id = user_id
        self.user_fullname = user_fullname
        self.user_email = user_email
        self.user_active = user_active
        self.user_password = user_password
        self.user_creation = user_creation

    def __repr__(self):
        return f"<{type(self).__name__} {self.user_id} {self.user_fullname} {self.user_email}>"

    def get_tokens(self) -> list:
        """
        :return: list of database names from this user
        """
        with Database.root() as root_db:
            return root_db.get_all_tokens_by(self.user_id)

    def check_pass(self, password) -> bool:
        """Return if the password is equal"""
        return self.user_password == password

    @classmethod
    def get(cls, user_id: int):
        with Database.root() as root_db:
            return root_db.select_user_by_id(user_id)

    @classmethod
    def create(cls, user_fullname, user_email, user_password):
        with Database.root() as root_db:
            return root_db.insert_user(
                user_fullname=user_fullname,
                user_email=user_email,
                user_password=user_password
            )

    @classmethod
    def from_dict(cls, user_dict):
        return cls(**user_dict)

    @classmethod
    def get_user_by_email(cls, user_email):
        with Database.root() as root_db:
            return root_db.select_user_by_email(user_email)

    @classmethod
    def get_user_by_id(cls, user_id):
        with Database.root() as root_db:
            return root_db.select_user_by_id(user_id)


class Token:
    def __init__(self, token_id: int, user_id: int, token_token: str, token_database_name: str, token_creation: str or datetime.datetime, token_active: int, token_activation_code: str = None,
                 token_activation_code_expiration: str or datetime.datetime = None):
        """
        :param token_id: Integer that uniquely identifies tokens
        :param user_id: User integer to which this token belongs
        :param token_token: The token itself
        :param token_database_name: Name of the database associated with token: user shouldn't have repeated db names
        :param token_creation: date of the token creation
        :param token_active: 1 or 0 representing active and inactive, respectively
        :param token_activation_code: Activation code sent by email
        :param token_activation_code_expiration: Date when the activation code expires
        """
        self.token_id = token_id
        self.user_id = user_id
        self.token_token = token_token
        self.token_database_name = token_database_name
        self.token_creation = token_creation
        self.token_active = token_active
        self.token_activation_code = token_activation_code
        self.token_activation_code_expiration = token_activation_code_expiration

    @classmethod
    def from_dict(cls, token_dict):
        return cls(**token_dict)

    @classmethod
    def get(cls, token_id):
        with Database.root() as root_db:
            return root_db.select_token_by_id(token_id)

    def verify_code(self, activation_code) -> bool:
        """Return whether the code was verified"""
        if self.token_activation_code is None or self.token_activation_code == "":
            return False

        if self.token_activation_code == activation_code:
            self.token_active = 1
            self.token_activation_code = ''
            self.token_activation_code_expiration = ''
            with Database.root() as root_db:
                return root_db.update_token(self)

        return False

    def create_activation_code(self, user: User):
        self.token_activation_code = secrets.token_hex(3).upper()
        self.token_activation_code_expiration = (datetime.datetime.now() + datetime.timedelta(minutes=30)).strftime(DATETIME_FORMAT)
        # send email
        # TODO: send email
        print(f"MOCK EMAIL SEND: to: {user.user_email} code: {self.token_activation_code} creation: {self.token_creation}")

    def __repr__(self):
        return f"<{type(self).__name__} {self.__dict__}>"

    @classmethod
    def create(cls, user: User, dbname: str):
        """
        :rtype: Token or None
        """
        with Database.root() as root_db:
            token = root_db.insert_token(user_id=user.user_id, token_database_name=dbname)
            if token is None:
                return None
            # Create token
            token.token_token = jwt.encode({
                "token_id": token.token_id,
                "user_id": user.user_id,
                "user_email": user.user_email,
                "database_name": token.token_database_name,
                "token_creation": token.token_creation,
            }, TOKEN_KEY).decode('utf8')

            token.create_activation_code(user)

            if root_db.update_token(token):
                return token

        return None


class Use:
    def __init__(self, use_id, token_id, use_creation):
        """
        :param use_id: Integer that uniquely identifies use
        :param token_id: Token id to which this use belong
        :param use_creation: date of the use creation
        """
        self.use_id = use_id
        self.token_id = token_id
        self.use_creation = use_creation


class DatabaseResponse:
    def __init__(self, status, query, error_message="", response=None):
        """
        Respond user with this class applying json method when database is used
        :param status: whether the message went ok
        :param query: SQL query requested
        :param error_message: error message if there was an error
        :param response: Database response if succeed
        """
        if response is None:
            response = []

        self.status = status
        self.query = query
        self.error_message = error_message
        self.response = response
        print(self)

    @property
    def ok(self):
        return self.status == 200

    def json(self):
        return json.dumps(self.__dict__)

    def __repr__(self):
        return f"<{type(self).__name__} {self.status} '{self.query}' error:{self.error_message}>"

    @classmethod
    def good(cls, query, response):
        return cls(200, query, response=response)

    @classmethod
    def bad(cls, query, error_message):
        return cls(400, query, error_message=error_message)


class Database:
    DEST_PATH = "data"
    lock = threading.RLock()
    ALLOWED_ATRIBUTES = ["select", "delete", "update", "insert", "create"]

    def __init__(self, path, dbname):
        path = os.path.join(path, dbname)
        if os.path.commonprefix([self.DEST_PATH + "/", path]) != self.DEST_PATH:
            path = os.path.join(self.DEST_PATH, path)
        if os.path.splitext(path)[1] != ".db":
            path += ".db"
        os.makedirs(os.path.split(path)[0], exist_ok=True)
        self.path = path
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = lambda c, r: dict([(col[0], r[idx]) for idx, col in enumerate(c.description)])
        self.cursor = self.conn.cursor()
        self.cursor.execute("PRAGMA foreign_keys = ON;")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.conn.close()

    def select(self, query) -> DatabaseResponse:
        with self.lock:
            try:
                self.cursor.execute(query)
            except Exception as e:
                return DatabaseResponse.bad(query, str(e))
            else:
                results = self.cursor.fetchall()
                if results is not None:
                    return DatabaseResponse.good(query, results)

    def delete(self, query) -> DatabaseResponse:
        with self.lock:
            try:
                self.cursor.execute(query)
            except Exception as e:
                return DatabaseResponse.bad(query, str(e))
            else:
                self.conn.commit()
                return DatabaseResponse.good(query, None)

    def update(self, query) -> DatabaseResponse:
        with self.lock:
            try:
                self.cursor.execute(query)
            except Exception as e:
                return DatabaseResponse.bad(query, str(e))
            else:
                self.conn.commit()
                return DatabaseResponse.good(query, None)

    def insert(self, query) -> DatabaseResponse:
        with self.lock:
            try:
                self.cursor.execute(query)
            except Exception as e:
                return DatabaseResponse.bad(query, str(e))
            else:
                self.conn.commit()
                return DatabaseResponse.good(query, self.cursor.lastrowid)

    def create(self, query) -> DatabaseResponse:
        with self.lock:
            try:
                self.cursor.execute(query)
            except Exception as e:
                return DatabaseResponse.bad(query, str(e))
            else:
                self.conn.commit()
                return DatabaseResponse.good(query, None)

    @classmethod
    def root(cls):
        root_db = Database("root", "user")
        with open("root_tables.sql") as f:
            root_db.cursor.executescript(f.read())
        return root_db

    def insert_user(self, user_fullname: str, user_email: str, user_password: str) -> User or None:
        """
        Return User or None if error
        Warning: user_id ignored
        """
        response = self.insert(f"INSERT INTO user "
                               f"(user_fullname, user_email, user_password) VALUES"
                               f"('{user_fullname}', '{user_email}', '{user_password}')")
        if response.ok:
            response = self.select(f"SELECT * FROM user WHERE user_email='{user_email}'")
            if response.ok:
                if response.response:
                    return User.from_dict(response.response[0])
        return None

    def select_user_by_id(self, user_id: int) -> User or None:
        """Return user match or None"""
        response = self.select(f"SELECT * FROM user WHERE user_id='{user_id}'")
        if response.ok:
            if response.response:
                return User.from_dict(response.response[0])
        return None

    def select_user_by_email(self, user_email: str):
        """Return user match or None"""
        response = self.select(f"SELECT * FROM user WHERE user_email='{user_email}'")
        if response.ok:
            if response.response:
                return User.from_dict(response.response[0])
        return None

    def insert_token(self, user_id: int, token_database_name: str) -> Token or None:
        """
        Return token_id or None if error
        Warning: user_id ignored
        """
        current_dbname = f"{user_id}/{token_database_name}"
        response = self.select("SELECT user_id || '/' || token_database_name as dbname FROM token")
        if response.ok:
            for dbname_dict in response.response:
                dbname = dbname_dict['dbname']
                if current_dbname == dbname:
                    return None
            response = self.insert(f"INSERT INTO token "
                                   f"(user_id, token_database_name) VALUES"
                                   f"('{user_id}', '{token_database_name}')")
            if response.ok:
                token_id = response.response
                response = self.select(f"SELECT * FROM token WHERE token_id = '{token_id}'")
                if response.ok:
                    return Token.from_dict(response.response[0])
        return None

    def update_token(self, token: Token) -> bool:
        """Return bool whether the operation has gone right"""
        sets = ", ".join([f"'{key}' = '{value}'" for key, value in token.__dict__.items() if key not in ['token_id', 'user_id', 'token_database_name']])
        response = self.update(f"UPDATE token SET {sets} WHERE token_id='{token.token_id}'")
        return response.ok

    def get_all_tokens_by(self, user_id: int) -> list:
        """Return list of tokens by user"""
        response = self.select(f"SELECT * FROM token WHERE user_id = '{user_id}'")
        results = []
        if response.ok:
            for token_dict in response.response:
                results.append(Token.from_dict(token_dict))
        return results

    def select_token_by_id(self, token_id):
        """Return Token or None"""
        response = self.select(f"SELECT * FROM token WHERE token_id='{token_id}'")
        if response.ok:
            if response.response:
                return Token.from_dict(response.response[0])
        return None


if __name__ == "__main__":
    pass
