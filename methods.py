from typing import List, Union, Optional

from models import Standing, Group, Player, Match


def update_rank_and_save(items: List[Union[Player, Group, Standing]], rank="rank", score="score"):
    updated_items: List[Union[Player, Group, Standing]] = update_rank(items, rank, score)
    items[0].__class__.objects.save_all(updated_items)
    return


def update_rank(items: List[Union[Player, Group, Standing]], rank="rank", score="score") -> List[Union[Player, Group]]:
    updated_items: List[Union[Player, Group]] = list()
    items.sort(key=lambda p_item: getattr(p_item, score), reverse=True)
    previous_rank, previous_score = 0, 0
    for index, item in enumerate(items):
        new_rank = previous_rank if getattr(item, score) == previous_score else index + 1
        previous_rank, previous_score = new_rank, getattr(item, score)
        if getattr(item, rank) == new_rank:
            continue
        setattr(item, rank, new_rank)
        updated_items.append(item)
    return updated_items


class MatchPlayer:
    def __init__(self):
        self.match: Match = Match()
        self.player1: Player = Player()
        self.player2: Player = Player()

    def __repr__(self):
        return f"{self.match}"

    @property
    def winner_group_name(self) -> str:
        if not self.match.winner:
            return str()
        return self.player1.group_name if self.match.winner == self.player1.name else self.player2.group_name

    @property
    def loser_group_name(self) -> str:
        if not self.match.winner:
            return str()
        return self.player1.group_name if self.match.winner != self.player1.name else self.player2.group_name

    @property
    def winner(self) -> Optional[Player]:
        if not self.match.winner:
            return None
        return self.player1 if self.match.winner == self.player1.name else self.player2

    @property
    def loser(self) -> Optional[Player]:
        if not self.match.winner:
            return None
        return self.player1 if self.match.winner != self.player1.name else self.player2
