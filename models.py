import os
from base64 import b64encode
from datetime import datetime, timedelta
from typing import List

import pytz
from firestore_ci import FirestoreDocument
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

INITIAL1, INITIAL2, WINNER, LOSER, DECIDER, FINAL = "Initial 1", "Initial 2", "Winner", "Loser", "Decider", "Final"
SERIES_TYPES = (INITIAL1, INITIAL2, WINNER, LOSER, DECIDER)
BYE_SERIES_TYPES = (INITIAL1, WINNER, LOSER, DECIDER)
FINAL_SERIES_TYPES = (INITIAL1, INITIAL2, WINNER, LOSER, DECIDER, FINAL)

TBD = "TBD"


class Match(FirestoreDocument):

    def __init__(self):
        super().__init__()
        self.season: int = int()
        self.week: int = int()
        self.round: int = int()
        self.type: str = str()
        self.player1: str = TBD
        self.player2: str = TBD
        self.players: List[str] = [TBD, TBD]
        self.winner: str = str()

    def __repr__(self):
        return f"S{self.season}:W{self.week}:R{self.round}:{self.type}:{self.player1}v{self.player2}" \
               f":W={self.winner if self.winner else TBD}"


Match.init("matches")


class Series(FirestoreDocument):

    def __init__(self, season: int = None, week: int = None, round_number: int = None, series_type: str = None,
                 order: int = None):
        super().__init__()
        self.season: int = season if season else int()
        self.week: int = week if week else int()
        self.round: int = round_number if round_number else int()
        self.type: str = series_type if series_type else str()
        self.group_name1: str = TBD
        self.group_name2: str = TBD
        self.group_names: List[str] = [TBD, TBD]
        self.order: int = order if order else int()
        self.winner: str = str()

    def __repr__(self):
        return f"S{self.season}:O{self.order}:W{self.week}:R{self.round}:" \
               f"{self.type}:{self.group_name1}v{self.group_name2}:W={self.winner if self.winner else TBD}"

    @property
    def is_name1_winner(self) -> bool:
        return self.winner == self.group_name1

    @property
    def is_name1_loser(self) -> bool:
        return self.winner != self.group_name1 if self.winner else False

    @property
    def is_name2_winner(self) -> bool:
        return self.winner == self.group_name2

    @property
    def is_name2_loser(self) -> bool:
        return self.winner != self.group_name2 if self.winner else False


Series.init("series")


class Standing(FirestoreDocument):

    def __init__(self, season: int = None, group_name: str = None):
        super().__init__()
        self.season: int = season if season else int()
        self.group_name: str = group_name if group_name else str()
        self.group_fullname: str = TBD
        self.player_name: str = str()
        self.url: str = str()
        self.weekly_scores: List[int] = [int()] * 7
        self.weekly_ties: List[int] = [int()] * 7

    def __repr__(self):
        return f"S{self.season}:{self.group_name}:S{self.total_score}:T{self.total_ties}"

    @property
    def total_score(self) -> int:
        return sum(self.weekly_scores)

    @property
    def total_ties(self) -> int:
        return sum(self.weekly_ties)


Standing.init()


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
        self.season: int = 1
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
