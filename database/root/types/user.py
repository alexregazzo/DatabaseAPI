import database.root
import database.root.types.token


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

    @classmethod
    def from_dict(cls, user_dict):
        return cls(**user_dict)

    @classmethod
    def get(cls, *, user_email: str = None, user_id: str = None):
        if user_id:
            with database.root.RootDatabase() as root_db:
                return root_db.select_user(user_id=user_id)
        elif user_email:
            with database.root.RootDatabase() as root_db:
                return root_db.select_user(user_email=user_email)
        else:
            raise Exception("Invalid inputs")

    @classmethod
    def create(cls, *, user_fullname, user_email, user_password):
        with database.root.RootDatabase() as root_db:
            return root_db.insert_user(
                user_fullname=user_fullname,
                user_email=user_email,
                user_password=user_password
            )

    def get_tokens(self):
        """
        :return: list of database names from this user
        :rtype: list[database.root.types.token.Token]
        """
        with database.root.RootDatabase() as root_db:
            return root_db.select_tokens(user_id=self.user_id)

    def check_pass(self, password) -> bool:
        """Return if the password is equal"""
        return self.user_password == password
