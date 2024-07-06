import random
from typing import List, Tuple

from firestore_ci import FirestoreDocument

from adventure.errors import InvalidWinner, NextMatchUpNotPossibleWhenRoundOver, AdventuresNeedToBeSetBeforeOpponents, \
    OpponentRemovedFromRemainingOpponents, \
    NewRoundCreatedWhileRoundIsInProgress, UnableToSetOpponent
from models import Group, Player


class AdventureConfig:
    PROXIMITY_LIMIT: int = 10  # Change this to restrict / expand the proximity list. Higher than 10 won't have any effect
    INITIAL_ADVENTURERS_COUNT: int = 20  # Change this to update the initial adventurers count
    PLAYER_RANKS_UPTO: int = 1200


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
        self.opponent_rank: int = int()
        self.opponents: List[str] = list()
        self.remaining_opponents: List[str] = list()
        self.remaining_opponents_score: List[int] = list()

    def set_adventurers(self, adventurers: List[Player]):
        adventurers.sort(key=lambda item: item.rank)
        self.adventurers = [p.name for p in adventurers]


    @classmethod
    def create_next_round(cls, adventure: 'Adventure', adventurers: List[Player]) -> 'Adventure':
        if not adventure.is_round_over():
            raise NewRoundCreatedWhileRoundIsInProgress
        new_adventure = cls()
        new_adventure.season = adventure.season
        new_adventure.score = adventure.score
        new_adventure.round = adventure.round + 1
        new_adventure.set_adventurers(adventurers)
        new_adventure.remaining_opponents = adventure.remaining_opponents[:]
        new_adventure.remaining_opponents_score = adventure.remaining_opponents_score[:]
        return new_adventure

    @property
    def total_matches(self) -> int:
        return min(len(self.adventurers), len(self.opponents))

    @property
    def adventurers_count(self) -> int:
        return len(self.adventurers) + len(self.acquired) - len(self.released)

    @property
    def opponent_score(self) -> int:
        return len(self.released)

    @property
    def score_in_this_round(self) -> int:
        return self.matches_played - self.opponent_score

    def is_round_over(self) -> bool:
        return self.matches_played == self.total_matches

    def is_game_over(self) -> bool:
        return not self.remaining_opponents or self.adventurers_count == 0

    def is_adventurer(self, name: str) -> bool:
        return name in self.adventurers

    def is_opponent(self, name: str) -> bool:
        return name in self.opponents

    def has_player_played_current_match(self, player: str) -> bool:
        return player in self.next_match_up()

    def is_adventurer_or_opponent(self, name: str) -> bool:
        return self.is_adventurer(name) or self.is_opponent(name)

    def init_remaining_opponents(self, groups: List[Group]):
        # if not self.adventurers:
        #    raise AdventuresNeedToBeSetBeforeOpponents
        # adventure_groups: Set[str] = {adventurer[:2] for adventurer in self.adventurers}
        remaining_opponents = list(zip([group.player_name for group in groups], [group.rank for group in groups]))
        random.shuffle(remaining_opponents)
        self.remaining_opponents = [opponent[0] for opponent in remaining_opponents]
        self.remaining_opponents_score = [opponent[1] for opponent in remaining_opponents]
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
        self.released.append(self.adventurers[self.opponents.index(winner)])
        self.score -= 1
        # if not self.remaining_opponents:
        #     return
        # remaining_groups: List[str] = [opponent[:2] for opponent in self.remaining_opponents]
        # opponent_group = self.opponents[self.opponents.index(winner)][:2]
        # if opponent_group not in remaining_groups:  # The opponent has already played
        #     return
        # opponent_index = remaining_groups.index(opponent_group)
        # self.remaining_opponents_score[opponent_index] += 1
        return

    def get_proximity(self) -> List[Tuple[str, int]]:
        limit = AdventureConfig.PROXIMITY_LIMIT
        # score = self.score
        remaining_opponents = [(opponent, self.remaining_opponents_score[index])  # Just providing the rank will ensure same order
                               for index, opponent in enumerate(self.remaining_opponents)]
        # remaining_opponents.sort(key=itemgetter(1))
        return remaining_opponents[:limit]

    def get_next_opponent(self) -> str:  # return the group name of the next opponent.
        proximity_list: List[Tuple[str, int]] = self.get_proximity()
        if not proximity_list:
            return str()
        probable_opponents: List[str] = [opponent[:2] for opponent, proximity in proximity_list  # here proximity is just the rank
                                         if proximity == proximity_list[0][1]]
        # next_opponent = sample(probable_opponents, k=1)[0]
        next_opponent = probable_opponents[0]
        return next_opponent

    def set_opponent(self, group: Group, players: List[Player]) -> None:
        if not self.adventurers:
            raise AdventuresNeedToBeSetBeforeOpponents
        if not group or not players:
            raise UnableToSetOpponent
        self.opponent_star_player_name = group.player_name
        self.opponent_fullname = group.fullname
        self.opponent_rank = group.rank
        opponents: List[Player] = [player for player in players
                                   if player.name not in self.adventurers and player.rank <= AdventureConfig.PLAYER_RANKS_UPTO]
        if not opponents:
            opponents: List[Player] = [player for player in players if player.name not in self.adventurers]
            if not opponents:
                raise UnableToSetOpponent
            opponents.sort(key=lambda item: item.rank)
            opponents = opponents[:1]
        opponents.sort(key=lambda item: item.rank)
        self.opponents = [player.name for player in opponents]
        remaining_group_names = [player_name[:2] for player_name in self.remaining_opponents]
        try:
            group_index = remaining_group_names.index(group.name)
        except ValueError:
            raise OpponentRemovedFromRemainingOpponents
        del self.remaining_opponents[group_index]
        del self.remaining_opponents_score[group_index]

    def next_match_up(self) -> Tuple[str, str]:
        if self.is_round_over():
            raise NextMatchUpNotPossibleWhenRoundOver
        return self.adventurers[self.matches_played], self.opponents[self.matches_played]

    def get_loser(self, winner) -> str:
        adventurer, opponent = self.next_match_up()
        if winner not in (adventurer, opponent):
            raise InvalidWinner
        return adventurer if winner == opponent else opponent


Adventure.init()
