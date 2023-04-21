from itertools import product
from random import shuffle
from typing import List, Tuple

from firestore_ci import FirestoreDocument
from flask import url_for

from models import Player, Group
from super_cup.errors import PlayerNotFound, GroupAlreadyInitialized, InvalidNumberOfPlayersProvidedForInitialization


class CupConfig:
    TYPE = "super_cup"
    TBD = "TBD"
    # TOTAL_TEAM_COUNT = 16
    # PLAYER_PER_TEAM = 5


class CupPlayer(FirestoreDocument):

    def __init__(self):
        super().__init__()
        self.name: str = str()
        self.group_name: str = str()
        self.season: int = int()
        self.type: str = CupConfig.TYPE
        self.played: int = int()
        self.won: int = int()


CupPlayer.init("cup_player")


class CupSeries(FirestoreDocument):
    PLAYER1: str = "player1"
    PLAYER2: str = "player2"

    def __init__(self, season: int, round_number: int, match_number: int, total_group_count: int, player_per_group: int):
        super().__init__()
        self.season: int = season
        self.round_number: int = round_number
        self.match_number: int = match_number
        self.total_group_count: int = total_group_count
        self.player_per_group: int = player_per_group
        self.type: str = CupConfig.TYPE
        self.group_full_names: List[str] = [CupConfig.TBD, CupConfig.TBD]
        self.group_ranks: List[int] = [int(), int()]
        self.player1_names: List[str] = list()
        self.player2_names: List[str] = list()
        self.player1_ranks: List[str] = list()
        self.player2_ranks: List[str] = list()
        self.match_player1_names: List[str] = list()
        self.match_player2_names: List[str] = list()
        self.match_winner_names: List[str] = list()

    def initialize_group(self, group: Group, players: List[Player]):
        if self.are_groups_initialized():
            raise GroupAlreadyInitialized
        if len(players) != self.player_per_group:
            raise InvalidNumberOfPlayersProvidedForInitialization
        player_type = self.PLAYER2 if self.is_group1_initialized() else self.PLAYER1
        index = 1 if self.is_group1_initialized() else 0
        self.group_full_names[index] = group.fullname
        self.group_ranks[index] = group.rank
        setattr(self, f"{player_type}_names", [player.name for player in players])
        setattr(self, f"{player_type}_ranks", [player.rank for player in players])
        if not self.are_groups_initialized():
            return
        player_indices: List[Tuple[int, int]] = list(product(range(self.player_per_group, self.player_per_group)))
        player1_names = self.player1_names[:]
        player2_names = self.player2_names[:]
        shuffle(player1_names)
        shuffle(player2_names)
        self.match_player1_names = [player1_names[player_index[0]] for player_index in player_indices]
        self.match_player2_names = [player2_names[player_index[1]] for player_index in player_indices]

    @staticmethod
    def get_url(players: List[Player], player_name):
        if player_name == CupConfig.TBD:
            return url_for("static", filename="default.jpg")
        try:
            return next(player for player in players if player.name == player_name).url
        except StopIteration:
            raise PlayerNotFound

    def get_score(self, player_type: str) -> int:
        player_names = getattr(self, f"{player_type}_names")
        return sum(1 if winner in player_names else 0 for winner in self.match_winner_names)

    @property
    def group1_full_name(self) -> str:
        return self.group_full_names[0]

    @property
    def group2_full_name(self) -> str:
        return self.group_full_names[1]

    @property
    def group1_rank(self) -> int:
        return self.group_ranks[0]

    @property
    def group2_rank(self) -> int:
        return self.group_ranks[1]

    def get_group1_url(self, players: List[Player]) -> str:
        return self.get_url(players, self.player1_names[0] if self.player1_names else CupConfig.TBD)

    def get_group2_url(self, players: List[Player]) -> str:
        return self.get_url(players, self.player2_names[0] if self.player2_names else CupConfig.TBD)

    @property
    def group1_score(self):
        return self.get_score(self.PLAYER1)

    @property
    def group2_score(self):
        return self.get_score(self.PLAYER2)

    def is_group1_initialized(self) -> bool:
        return bool(self.player1_names)

    def is_group2_initialized(self) -> bool:
        return bool(self.player2_names)

    def are_groups_initialized(self) -> bool:
        return self.is_group1_initialized() and self.is_group2_initialized()

    def is_series_completed(self) -> bool:
        return self.are_groups_initialized() and len(self.match_winner_names) == len(self.match_player1_names)

    def is_group1_winner(self) -> bool:
        return self.is_series_completed() and self.group1_score > self.group2_score

    def is_group2_winner(self) -> bool:
        return self.is_series_completed() and self.group2_score > self.group1_score


CupSeries.init("cup_series")
