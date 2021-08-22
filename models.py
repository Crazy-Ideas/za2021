from datetime import datetime

import pytz
from firestore_ci import FirestoreDocument


class Player(FirestoreDocument):

    def __init__(self):
        super().__init__()
        self.name: str = str()
        self.group_name: str = str()
        self.url: str = str()
        self.url_expiration: datetime = datetime.now(tz=pytz.UTC)
        self.qualified: bool = bool()
        self.league: int = int()
        self.league_rank: int = int()
        self.qualification_rank: int = int()

    def __repr__(self):
        return f"{self.name}"


Player.init()


class Group(FirestoreDocument):

    def __init__(self):
        super().__init__()
        self.group_rank: int = int()
        self.name: str = str()
        self.fullname: str = str()
        self.player_count: int = int()
        self.player_name: str = str()
        self.url: str = str()
        self.url_expiration: datetime = datetime.now(tz=pytz.UTC)
        self.qualification_locked: bool = bool()
        self.qualified_player_count: int = int()

    def __repr__(self):
        return f"{self.name}:{self.fullname}:P#{self.player_count}"

    @property
    def rank_average_str(self) -> str:
        return f"{(self.group_rank / self.player_count):07.2f}"

    @property
    def player_count_str(self) -> str:
        return f"{self.player_count:02}"

    @property
    def group_rank_str(self) -> str:
        return f"{self.group_rank:05}"

    @property
    def qualified_player_count_str(self) -> str:
        return f"{self.qualified_player_count:02}"

    @property
    def locked_str(self) -> str:
        return "Yes" if self.qualification_locked else "No"


Group.init()


class User(FirestoreDocument):

    def __init__(self):
        super().__init__()
        self.email: str = str()
        self.password_hash: str = str()
        self.token: str = str()
        self.token_expiration: datetime = datetime.now(tz=pytz.UTC)


User.init()
