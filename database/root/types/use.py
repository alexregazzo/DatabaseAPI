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
