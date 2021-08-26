import os
from base64 import b64encode
from datetime import datetime, timedelta

import pytz
from firestore_ci import FirestoreDocument
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash


class Player(FirestoreDocument):

    def __init__(self):
        super().__init__()
        self.name: str = str()
        self.group_name: str = str()
        self.star_player: bool = bool()
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
        return "Yes" if self.qualification_locked else ("No" if self.player_count >= 9 else "Disqualified")


Group.init()


class User(FirestoreDocument, UserMixin):
    TOKEN_EXPIRY = 3600  # 1 hour = 3600 seconds

    def __init__(self):
        super().__init__()
        self.email: str = str()
        self.password_hash: str = str()
        self.token: str = str()
        self.token_expiration: datetime = datetime.now(tz=pytz.UTC)

    def __repr__(self):
        return f"{self.email}"

    def get_id(self):
        return self.email

    def get_or_generate_token(self) -> str:
        now: datetime = datetime.now(tz=pytz.UTC)
        if self.token and self.token_expiration > now + timedelta(seconds=60):
            return self.token
        self.token: str = b64encode(os.urandom(24)).decode()
        self.token_expiration: datetime = now + timedelta(seconds=self.TOKEN_EXPIRY)
        self.save()
        return self.token

    def revoke_token(self) -> None:
        self.token_expiration: datetime = datetime.utcnow() - timedelta(seconds=1)
        self.save()

    def set_password(self, password) -> None:
        self.password_hash: str = generate_password_hash(password)
        self.save()

    def is_password_valid(self, password) -> bool:
        return check_password_hash(self.password_hash, password)


User.init()
