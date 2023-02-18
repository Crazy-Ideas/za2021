from typing import List, Tuple

from firestore_ci import FirestoreDocument

from adventure.errors import InvalidWinner, NextMatchUpNotPossibleWhenRoundOver
from models import Group


class Opponent(FirestoreDocument):

    def __init__(self, group: Group = None):
        super().__init__()
        self.fullname: str = str()
        self.name: str = str()
        self.score: int = int()
        self.season: int = int()
        self.count: int = int()
        self.played: bool = bool()
        if group:
            self.build(group)

    def build(self, group: Group):
        self.fullname = group.fullname
        self.name = group.name

    def proximity(self, count: int) -> int:
        return abs(self.count - count)


Opponent.init()


class Adventure(FirestoreDocument):

    def __init__(self):
        super().__init__()
        self.season: int = int()
        self.round: int = int()
        self.adventurers: List[str] = list()
        self.score: int = int()
        self.opponent_name: str = str()
        self.opponents: List[str] = list()
        self.matches_played: int = int()
        self.opponent_score: int = int()
        self.released: List[str] = list()
        self.acquired: List[str] = list()

    @property
    def total_matches(self) -> int:
        return min(len(self.adventurers), len(self.opponents))

    @property
    def is_round_over(self) -> int:
        return self.matches_played == self.total_matches

    def is_adventurer(self, name: str) -> bool:
        return name in self.adventurers

    def is_opponent(self, name: str) -> bool:
        return name in self.opponents

    def update_result(self, winner: str, opponent: Opponent, acquired: bool = False):
        if not self.is_adventurer(winner) and not self.is_opponent(winner):
            raise InvalidWinner
        if self.is_adventurer(winner):
            self.score += 1
            if acquired:
                self.acquired.append(self.opponents[self.adventurers.index(winner)])
                opponent.count -= 1
        else:  # opponent is the winner
            self.opponent_score += 1
            opponent.score += 1
            self.released.append(self.adventurers[self.opponents.index(winner)])
            opponent.count += 1
        self.matches_played += 1

    def next_match_up(self) -> Tuple[str, str]:
        if self.is_round_over:
            raise NextMatchUpNotPossibleWhenRoundOver
        return (self.adventurers[self.matches_played], self.opponents[self.matches_played])


Adventure.init()
