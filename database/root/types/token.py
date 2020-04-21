import smtplib
import datetime
import jwt
import secrets
import database.settings
import database.root
import database.root.types.use


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
    def get(cls, *, token_id):
        with database.root.RootDatabase() as root_db:
            results = root_db.select_tokens(token_id=token_id)
        if results:
            return results[0]
        raise Exception('Token not found')

    def verify_code(self, activation_code: str) -> None:
        """Return whether the code was verified"""
        if self.token_activation_code is None or self.token_activation_code == "":
            raise Exception("No activation code")

        if self.token_activation_code.upper() == activation_code.upper():
            self.token_active = 1
            self.token_activation_code = ''
            self.token_activation_code_expiration = ''
            with database.root.RootDatabase() as root_db:
                root_db.update_token(token_id=self.token_id, **self.get_dict_update())
        raise Exception("Invalid activation code")

    def get_dict_update(self):
        return {k: v for k, v in self.__dict__.items() if k not in ['token_id']}

    def create_activation_code(self, user):
        self.token_activation_code = secrets.token_hex(3).upper()
        self.token_activation_code_expiration = (datetime.datetime.now() + datetime.timedelta(minutes=30)).strftime(database.settings.DATETIME_FORMAT)

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login("regazzo.database.api@gmail.com", database.settings.GMAIL_APP_PASSWORD)
            subject = "Confirmation Code from Database API"
            body = f"Confirmation code: {self.token_activation_code}"
            msg = f'Subject: {subject}\n\n{body}'
            smtp.sendmail("regazzo.database.api@gmail.com", user.user_email, msg)

        # print(f"MOCK EMAIL SEND: to: {user.user_email} code: {self.token_activation_code} creation: {self.token_creation}")

    def __repr__(self):
        return f"<{type(self).__name__} {self.__dict__}>"

    @classmethod
    def create(cls, *, user, dbname: str):
        """
        :rtype: Token
        """
        with database.root.RootDatabase() as root_db:
            token = root_db.insert_token(user_id=user.user_id, token_database_name=dbname)

            # Create token
            token.token_token = jwt.encode({
                "token_id": token.token_id,
                "user_id": user.user_id,
                "user_email": user.user_email,
                "database_name": token.token_database_name,
                "token_creation": token.token_creation,
            }, database.settings.TOKEN_KEY).decode('utf8')

            token.create_activation_code(user)
            root_db.update_token(token_id=token.token_id, **token.get_dict_update())
        return token

    def get_uses(self):
        """
        :return: list of uses from this token
        :rtype: list[database.root.types.use.Use]
        """
        with database.root.RootDatabase() as root_db:
            return root_db.select_uses(token_id=self.token_id)


if __name__ == "__main__":
    pass
    # print(TOKEN_KEY)
