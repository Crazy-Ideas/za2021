import math
from itertools import product
from random import shuffle
from typing import List, Tuple

from firestore_ci import FirestoreDocument
from flask import url_for

from models import Player, Group
from super_cup.errors import PlayerNotFound, GroupAlreadyInitialized, InvalidNumberOfPlayersProvidedForInitialization, SeriesNotCompleted, \
    GroupNotInitialized, SeriesCompleted, InvalidPlayerPerGroup


class CupConfig:
    TYPE = "super_cup"
    TBD = "TBD"
    VALID_PLAYERS_PER_GROUP = (1, 2, 3, 4, 5, 7, 9)
    INDEXED_GROUP_COUNT = (1024, 128, 64, 32, 16, 8, 8)
    FILTERED_PLAYER_COUNT = (1024, 1500, 1500, 1500, 1500, 7 * 7 * 8, 9 * 9 * 8)

    # TODO: For Seeding top 32 in players in 1024 players  list(zip_longest(*[iter(l2)]*31))

    @classmethod
    def is_valid_player_per_group(cls, player_per_group) -> bool:
        return player_per_group in cls.VALID_PLAYERS_PER_GROUP

    @classmethod
    def get_total_group_count(cls, player_per_group: int):
        if not cls.is_valid_player_per_group(player_per_group):
            raise InvalidPlayerPerGroup
        return cls.INDEXED_GROUP_COUNT[cls.VALID_PLAYERS_PER_GROUP.index(player_per_group)]

    @classmethod
    def get_filtered_player_count(cls, player_per_group: int):
        if not cls.is_valid_player_per_group(player_per_group):
            raise InvalidPlayerPerGroup
        return cls.FILTERED_PLAYER_COUNT[cls.VALID_PLAYERS_PER_GROUP.index(player_per_group)]

class CupSeries(FirestoreDocument):
    PLAYER1: str = "player1"
    PLAYER2: str = "player2"

    def __init__(self, season: int = 0, round_number: int = 0, match_number: int = 0, total_group_count: int = 0,
                 player_per_group: int = 0):
        super().__init__()
        self.season: int = season
        self.round_number: int = round_number
        self.match_number: int = match_number
        self.total_group_count: int = total_group_count
        self.player_per_group: int = player_per_group
        self.group_full_names: List[str] = [CupConfig.TBD, CupConfig.TBD]
        self.group_ranks: List[int] = [int(), int()]
        self.player1_names: List[str] = list()
        self.player2_names: List[str] = list()
        self.player1_ranks: List[int] = list()
        self.player2_ranks: List[int] = list()
        self.match_player1_names: List[str] = list()
        self.match_player2_names: List[str] = list()
        self.match_winner_names: List[str] = list()
        self.series_completed_status: bool = False

    def __repr__(self):
        return f"SC{self.player_per_group}S{self.season}:{self.match_identity}:" \
               f"{self.group_full_names[0]} {'(W)' if self.is_group1_winner() else ''} v " \
               f"{self.group_full_names[1]} {'(W)' if self.is_group2_winner() else ''}"

    def initialize_group(self, group: Group, players: List[Player]):
        if len(players) != self.player_per_group:
            raise InvalidNumberOfPlayersProvidedForInitialization
        player_type, index = self.get_player_type_and_index()
        self.group_full_names[index] = group.fullname
        self.group_ranks[index] = group.rank
        setattr(self, f"{player_type}_names", [player.name for player in players])
        setattr(self, f"{player_type}_ranks", [player.rank for player in players])
        if self.are_groups_initialized():
            self.initialize_matches()
        return

    def initialize_matches(self):
        if len(self.player1_names) != self.player_per_group or len(self.player2_names) != self.player_per_group:
            raise InvalidNumberOfPlayersProvidedForInitialization
        player_indices: List[Tuple[int, int]] = list(product(range(self.player_per_group), range(self.player_per_group)))
        shuffle(player_indices)
        self.match_player1_names = [self.player1_names[player_index[0]] for player_index in player_indices]
        self.match_player2_names = [self.player2_names[player_index[1]] for player_index in player_indices]
        if self.player_per_group % 2 == 0:  # If even number of players then add a match for the highest rank in each group
            self.match_player1_names.append(self.star_player1)
            self.match_player2_names.append(self.star_player2)
        return


    def copy_group(self, series: 'CupSeries'):
        player_type, index = self.get_player_type_and_index()
        from_player_type = series.get_winner_player_type()
        if len(getattr(series, f"{from_player_type}_names")) != self.player_per_group:
            raise InvalidNumberOfPlayersProvidedForInitialization
        from_index = 0 if from_player_type == self.PLAYER1 else 1
        self.group_full_names[index] = series.group_full_names[from_index]
        self.group_ranks[index] = series.group_ranks[from_index]
        setattr(self, f"{player_type}_names", getattr(series, f"{from_player_type}_names")[:])
        setattr(self, f"{player_type}_ranks", getattr(series, f"{from_player_type}_ranks")[:])
        if self.are_groups_initialized():
            self.initialize_matches()
        return

    def get_player_type_and_index(self) -> Tuple[str, int]:
        if self.are_groups_initialized():
            raise GroupAlreadyInitialized
        player_type = self.PLAYER2 if self.is_group1_initialized() else self.PLAYER1
        index = 1 if self.is_group1_initialized() else 0
        return player_type, index

    @staticmethod
    def get_url(players: List[Player], player_name) -> str:
        # used in html file. Cannot error. Fail gracefully
        if player_name == CupConfig.TBD:
            return url_for("static", filename="default.jpg")
        try:
            return next(player for player in players if player.name == player_name).url
        except StopIteration:
            return url_for("static", filename="default.jpg")

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

    @property
    def star_player1(self) -> str:
        return self.player1_names[0] if self.player1_names else CupConfig.TBD

    @property
    def star_player2(self) -> str:
        return self.player2_names[0] if self.player2_names else CupConfig.TBD

    @property
    def star_players(self) -> List[str]:
        return [self.star_player1, self.star_player2]

    def get_group1_url(self, players: List[Player]) -> str:
        return self.get_url(players, self.star_player1)

    def get_group2_url(self, players: List[Player]) -> str:
        return self.get_url(players, self.star_player2)

    @property
    def group1_score(self):
        return self.get_score(self.PLAYER1)

    @property
    def group2_score(self) -> int:
        return self.get_score(self.PLAYER2)

    @property
    def group_scores(self) -> List[int]:
        return [self.group1_score, self.group2_score]

    @property
    def match_identity(self) -> str:
        round_calculator = RoundCalculator(self.total_group_count)
        if self.round_number in round_calculator.earlier_round_numbers:
            return f"R{self.round_number}M{self.match_number}"
        if self.round_number == round_calculator.quarter_final_round_number:
            return f"QF{self.match_number}"
        if self.round_number == round_calculator.semi_final_round_number:
            return f"SF{self.match_number}"
        return f"Final"

    def is_group1_initialized(self) -> bool:
        return bool(self.player1_names)

    def is_group2_initialized(self) -> bool:
        return bool(self.player2_names)

    def are_groups_initialized(self) -> bool:
        return self.is_group1_initialized() and self.is_group2_initialized()

    def is_series_completed(self) -> bool:
        if not self.are_groups_initialized():
            return False
        expected_win_count_to_win_series: int = int(self.total_games / 2) + 1
        return self.group1_score >= expected_win_count_to_win_series or self.group2_score >= expected_win_count_to_win_series

    def is_group1_winner(self) -> bool:
        return self.is_series_completed() and self.group1_score > self.group2_score

    def is_group2_winner(self) -> bool:
        return self.is_series_completed() and self.group2_score > self.group1_score

    def get_winner_player_type(self) -> str:
        if not self.is_series_completed():
            raise SeriesNotCompleted
        return self.PLAYER1 if self.is_group1_winner() else self.PLAYER2

    def get_current_match_index(self) -> int:
        if not self.are_groups_initialized():
            raise GroupNotInitialized
        if self.is_series_completed():
            raise SeriesCompleted
        return len(self.match_winner_names)

    @property
    def current_match_player1_name(self) -> str:
        return self.match_player1_names[self.get_current_match_index()]

    @property
    def current_match_player2_name(self) -> str:
        return self.match_player2_names[self.get_current_match_index()]

    @property
    def current_match_player1_rank(self) -> int:
        try:
            return self.player1_ranks[self.player1_names.index(self.current_match_player1_name)]
        except (SeriesCompleted, GroupNotInitialized, ValueError, IndexError):
            return 0

    @property
    def current_match_player2_rank(self) -> int:
        try:
            return self.player2_ranks[self.player2_names.index(self.current_match_player2_name)]
        except (SeriesCompleted, GroupNotInitialized, ValueError, IndexError):
            return 0

    def get_current_match_player1_url(self, players: List[Player]) -> str:
        try:
            return self.get_url(players, self.current_match_player1_name)
        except (GroupNotInitialized, SeriesCompleted):
            return url_for("static", filename="default.jpg")

    def get_current_match_player2_url(self, players: List[Player]) -> str:
        try:
            return self.get_url(players, self.current_match_player2_name)
        except (GroupNotInitialized, SeriesCompleted):
            return url_for("static", filename="default.jpg")

    def set_winner(self, winner_name: str):
        if not self.is_player_in_current_match(winner_name):
            raise PlayerNotFound
        self.match_winner_names.append(winner_name)

    def is_player_in_current_match(self, player_name: str) -> bool:
        try:
            return player_name in (self.current_match_player1_name, self.current_match_player2_name)
        except (GroupNotInitialized, SeriesCompleted):
            return False

    def get_next_rounds_match_number(self):
        return int((self.match_number - 1) / 2) + 1

    def is_season_over(self):
        return self.round_number == RoundCalculator(self.total_group_count).final_round_number and self.is_series_completed()

    @property
    def game_number(self):
        return len(self.match_winner_names) + 1

    @property
    def total_games(self) -> int:
        return len(self.match_player1_names)

    def get_winner_index(self):
        if not self.is_series_completed():
            raise SeriesNotCompleted
        return 0 if self.is_group1_winner() else 1

    def get_loser_index(self):
        return 0 if self.get_winner_index() == 1 else 1

    @property
    def winner_full_name(self) -> str:
        try:
            return self.group_full_names[self.get_winner_index()]
        except SeriesNotCompleted:
            return CupConfig.TBD

    @property
    def winner_star_player_name(self) -> str:
        try:
            return self.star_players[self.get_winner_index()]
        except SeriesNotCompleted:
            return CupConfig.TBD

    @property
    def loser_star_player_name(self) -> str:
        try:
            return self.star_players[self.get_loser_index()]
        except SeriesNotCompleted:
            return CupConfig.TBD

    @property
    def loser_group_name(self) -> str:
        loser_name: str = self.loser_star_player_name
        return CupConfig.TBD if loser_name == CupConfig.TBD else loser_name[:2]

    @property
    def winner_rank(self) -> int:
        try:
            return self.group_ranks[self.get_winner_index()]
        except SeriesNotCompleted:
            return 0

    @property
    def loser_rank(self) -> int:
        try:
            return self.group_ranks[self.get_loser_index()]
        except SeriesNotCompleted:
            return 0

    @property
    def winner_score(self) -> int:
        try:
            return self.group_scores[self.get_winner_index()]
        except SeriesNotCompleted:
            return 0

    @property
    def loser_score(self) -> int:
        try:
            return self.group_scores[self.get_loser_index()]
        except SeriesNotCompleted:
            return 0

    def get_winner_url(self, players: List[Player]) -> str:
        try:
            return self.get_url(players, self.winner_star_player_name)
        except SeriesNotCompleted:
            return url_for("static", filename="default.jpg")

    def get_loser_url(self, players: List[Player]) -> str:
        try:
            return self.get_url(players, self.loser_star_player_name)
        except SeriesNotCompleted:
            return url_for("static", filename="default.jpg")


CupSeries.init("cup_series")


class RoundCalculator:

    def __init__(self, group_count: int):
        self.group_count: int = group_count

    @property
    def total_rounds(self):
        return int(math.log2(self.group_count))

    def total_matches_per_round(self, round_number: int):
        return int(self.group_count / 2 ** round_number)

    @property
    def pre_quarter_final_round_number(self) -> int:
        return self.total_rounds - 3

    @property
    def quarter_final_round_number(self) -> int:
        return self.total_rounds - 2

    @property
    def semi_final_round_number(self) -> int:
        return self.total_rounds - 1

    @property
    def final_round_number(self) -> int:
        return self.total_rounds

    @property
    def earlier_round_numbers(self) -> List[int]:
        return list(range(1, self.quarter_final_round_number))
