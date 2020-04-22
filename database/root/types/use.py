import jwt
import database.settings
import json


class Use:
    def __init__(self, *, use_id: int, token_id: int, use_data: str, use_creation: str):
        """
        :param use_id: Integer that uniquely identifies use
        :param token_id: Token id to which this use belong
        :param use_creation: date of the use creation
        """
        self.use_id = use_id
        self.token_id = token_id
        self.use_data = use_data
        self.use_creation = use_creation

    @staticmethod
    def create(api_response) -> bool:
        """
        :param api_response: APIResponse object
        """
        try:
            with database.root.RootDatabase() as root_db:
                root_db.insert_use(token_token=api_response.token, use_data=api_response.json())
        except:
            return False
        return True

    @classmethod
    def from_dict(cls, use_dict):
        return cls(**use_dict)

    def json_object(self):
        return self.__dict__

    def json(self):
        return json.dumps(self.json_object())

    @property
    def data(self):
        return json.loads(self.use_data)
