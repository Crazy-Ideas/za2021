from operator import itemgetter
from random import sample, shuffle
from typing import List, Tuple, Set

from firestore_ci import FirestoreDocument

from adventure.errors import InvalidWinner, NextMatchUpNotPossibleWhenRoundOver, AdventuresNeedToBeSetBeforeOpponents, \
    OpponentRemovedFromRemainingOpponents, \
    NewRoundCreatedAfterRoundIsOver
from models import Group


class Adventure(FirestoreDocument):

    def __init__(self):
        super().__init__()
        self.season: int = int()
        self.round: int = int()
        self.score: int = int()
        self.adventurers: List[str] = list()
        self.released: List[str] = list()
        self.acquired: List[str] = list()
        self.matches_played: int = int()
        self.opponent_star_player_name: str = str()
        self.opponent_fullname: str = str()
        self.opponents: List[str] = list()
        self.opponent_score: int = int()
        self.remaining_opponents: List[str] = list()
        self.remaining_opponents_player_count: List[int] = list()

    @classmethod
    def create_next_round(cls, adventure: 'Adventure') -> 'Adventure':
        if adventure.is_round_over():
            raise NewRoundCreatedAfterRoundIsOver
        new_adventure = cls()
        new_adventure.season = adventure.season
        new_adventure.round = adventure.round + 1
        new_adventure.score = adventure.score
        new_adventure.adventurers = [adventurer for adventurer in adventure.adventurers
                                     if adventurer not in adventure.released]
        new_adventure.adventurers.extend(adventure.acquired)
        shuffle(new_adventure.adventurers)
        return new_adventure

    @property
    def total_matches(self) -> int:
        return min(len(self.adventurers), len(self.opponents))

    @property
    def adventurers_count(self) -> int:
        return len(self.adventurers) + len(self.acquired) - len(self.released)

    def is_round_over(self) -> bool:
        return self.matches_played == self.total_matches

    def is_game_over(self) -> bool:
        return not self.remaining_opponents or self.adventurers_count == 0

    def is_adventurer(self, name: str) -> bool:
        return name in self.adventurers

    def is_opponent(self, name: str) -> bool:
        return name in self.opponents

    def is_winner_valid(self, winner: str) -> bool:
        return winner in self.next_match_up()

    def is_adventurer_or_opponent(self, name: str) -> bool:
        return self.is_adventurer(name) or self.is_opponent(name)

    def init_remaining_opponents(self, groups: List[Group]):
        if not self.adventurers:
            raise AdventuresNeedToBeSetBeforeOpponents
        adventure_groups: Set[str] = {adventurer[:2] for adventurer in self.adventurers}
        self.remaining_opponents = [group.player_name for group in groups]
        self.remaining_opponents_player_count = [
            group.player_count - 1 if group.name in adventure_groups else group.player_count for group in groups]
        return

    def update_result(self, winner: str, acquired: bool = False):
        if not self.is_adventurer_or_opponent(winner):
            raise InvalidWinner
        self.matches_played += 1
        if self.is_adventurer(winner):
            self.score += 1
            if acquired:
                self.acquired.append(self.opponents[self.adventurers.index(winner)])
            return
        # Opponent is the winner
        self.opponent_score += 1
        self.released.append(self.adventurers[self.opponents.index(winner)])
        remaining_groups: List[str] = [opponent[:2] for opponent in self.remaining_opponents]
        opponent_group = self.opponents.index(winner)[:2]
        if opponent_group not in remaining_groups:
            return
        opponent_index = remaining_groups.index(opponent_group)
        self.remaining_opponents_player_count[opponent_index] = self.remaining_opponents_player_count[
                                                                    opponent_index] + 1
        return

    def get_proximity(self) -> List[Tuple[str, int]]:
        limit = 5  # Change this to restrict / expand the proximity list
        count = self.adventurers_count
        remaining_opponents = [(opponent, abs(self.remaining_opponents_player_count[index] - count))
                               for index, opponent in enumerate(self.remaining_opponents)]
        remaining_opponents.sort(key=itemgetter(1))
        near_opponents: List[Tuple[str, int]] = remaining_opponents[:limit]
        near_opponents.extend(
            [opponent for opponent in remaining_opponents[limit:] if opponent[1] == remaining_opponents[limit - 1]])
        return near_opponents

    def get_next_opponent(self) -> str:
        proximity_list: List[Tuple[str, int]] = self.get_proximity()
        if not proximity_list:
            return str()
        probable_opponents: List[str] = [opponent[:2] for opponent, proximity in proximity_list
                                         if proximity == proximity_list[0][1]]
        return sample(probable_opponents, k=1)[0]

    def set_opponent(self, group: Group, player_names: List[str]) -> None:
        if not self.adventurers:
            raise AdventuresNeedToBeSetBeforeOpponents
        self.opponent_star_player_name = group.player_name
        self.opponent_fullname = group.fullname
        self.opponents = [player_name for player_name in player_names if player_name not in self.adventurers]
        shuffle(self.opponents)
        remaining_group_names = [player_name[:2] for player_name in self.remaining_opponents]
        try:
            group_index = remaining_group_names.index(group.name)
        except ValueError:
            raise OpponentRemovedFromRemainingOpponents
        del self.remaining_opponents[group_index]
        del self.remaining_opponents_player_count[group_index]

    def next_match_up(self) -> Tuple[str, str]:
        if self.is_round_over():
            raise NextMatchUpNotPossibleWhenRoundOver
        return self.adventurers[self.matches_played], self.opponents[self.matches_played]


Adventure.init()
