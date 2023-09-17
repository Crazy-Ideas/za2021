import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from itertools import groupby
from random import sample, shuffle
from typing import Optional, List, Callable

import pytz

from models import Match, Player, Standing, Group

SEASON = 2022


class WorldCupMatch:

    def __init__(self):
        self.match: Optional[Match] = None
        self.player1: Optional[Player] = None
        self.player2: Optional[Player] = None
        self.standing1: Optional[Standing] = None
        self.standing2: Optional[Standing] = None
        self.last_order: int = int()

    def update_result(self, winning_name: str, winning_margin: str):
        self.match.winner = winning_name
        self.match.win_margin = winning_margin
        self.match.date_played = datetime.now(tz=pytz.UTC)
        group_names: List[str] = [self.player1.group_name, self.player2.group_name]
        query = Standing.objects.filter("group_name", Standing.objects.IN, group_names)
        standings: List[Standing] = query.filter_by(season=SEASON).get()
        groups: List[Group] = Group.objects.filter("name", Group.objects.IN, group_names).get()
        winner: Player = self.player1 if winning_name == self.player1.name else self.player2
        loser: Player = self.player2 if winning_name == self.player1.name else self.player1
        winning_group: Group = groups[0] if groups[0].name == winner.group_name else groups[1]
        losing_group: Group = groups[1] if groups[0].name == winner.group_name else groups[0]
        winning_standing: Standing = standings[0] if standings[0].group_name == winner.group_name else standings[1]
        losing_standing: Standing = standings[1] if standings[0].group_name == winner.group_name else standings[0]
        winner.wc_update_score(won=True, margin=winning_margin)
        loser.wc_update_score(won=False, margin=winning_margin)
        winning_standing.wc_update_score(won=True, margin=winning_margin, group=winning_group)
        losing_standing.wc_update_score(won=False, margin=winning_margin, group=losing_group)
        with ThreadPoolExecutor() as executor:
            task_list: List[Callable] = [self.match.save, winner.save, loser.save, winning_group.save,
                                         losing_group.save, winning_standing.save, losing_standing.save]
            threads = [executor.submit(task) for task in task_list]
            [future.result() for future in as_completed(threads)]
        return


def get_wc_match() -> Optional[WorldCupMatch]:
    match_query = Match.objects.filter_by(season=SEASON)
    match: Match = match_query.filter_by(winner=str()).order_by("order").first()
    if not match:
        last_match: Match = match_query.order_by("order", Match.objects.ORDER_DESCENDING).first()
        next_round: int = last_match.round + 1 if last_match else 1
        match_number: int = last_match.order + 1 if last_match else 1
        standings: List[Standing] = Standing.objects.filter_by(season=SEASON, eliminated=0).get()
        if len(standings) <= 1:  # Game over OR Season Not setup
            return None
        if next_round != 1:
            # Eliminate group with the lowest score
            min_score = min(standings, key=lambda item: item.wc_score).wc_score
            eliminated = [s for s in standings if s.wc_score == min_score]
            for group in eliminated:
                group.eliminated = next_round - 1  # last round
            Standing.objects.save_all(eliminated)
            standings = [s for s in standings if s.wc_score != min_score]
        setup_matches(next_round, match_number, standings)
        return None
    wc_match = WorldCupMatch()
    wc_match.match = match
    players: List[Player] = Player.objects.filter("name", Player.objects.IN, [match.player1, match.player2]).get()
    wc_match.player1 = next(player for player in players if player.name == match.player1)
    wc_match.player2 = next(player for player in players if player.name == match.player2)
    wc_match.last_order = Match.objects.filter_by(season=SEASON).order_by("order", Match.objects.ORDER_DESCENDING).first().order
    group_names: List[str] = [wc_match.player1.group_name, wc_match.player2.group_name]
    standings: List[Standing] = Standing.objects.filter("group_name", Player.objects.IN, group_names).get()
    standings = [standing for standing in standings if standing.season == SEASON]
    wc_match.standing1 = next(standing for standing in standings if standing.group_name == wc_match.player1.group_name)
    wc_match.standing2 = next(standing for standing in standings if standing.group_name == wc_match.player2.group_name)
    return wc_match


def setup_matches(next_round: int, next_match_number: int, standings: list) -> None:
    with open("temp/player_names.json") as file:
        player_names: List[str] = json.load(file)
    group_names = {s.group_name for s in standings}
    remaining_players: set = {name for name in player_names if name[:2] in group_names}
    priority_players: set = set()
    if next_round > 1:
        players: List[Player] = Player.objects.filter("wc_played", "<", next_round - 1).get()
        played_count: set = {player.name for player in players}
        priority_players: set = {name for name in remaining_players if name in played_count}
    matches: List[Match] = list()
    remaining_groups: set = set(group_names)
    while len(remaining_groups) >= 2:
        selected_players = priority_players or remaining_players
        sorted_players = sorted(list(selected_players))
        select: List[list] = [list(player_group) for _, player_group in
                              groupby(sorted_players, key=lambda item: item[:2])]
        selection: List[str] = max(select, key=lambda item: len(item))
        # Remove all players of selected group for opposition selection
        remaining_opposition: List[str] = [name for name in remaining_players if name[:2] != selection[0][:2]]
        if len(selection) > len(remaining_opposition):
            selection = sample(selection, k=len(remaining_opposition))
            opposition: List[str] = remaining_opposition
        else:
            opposition: List[str] = sample(remaining_opposition, k=len(selection))
        matches.extend([Match(season=SEASON, round_number=next_round, player1=player1, player2=player2)
                        for player1, player2 in zip(selection, opposition)])
        matched_players: set = set(selection) | set(opposition)
        remaining_players -= matched_players
        priority_players -= matched_players
        remaining_groups = {name[:2] for name in remaining_players}
    shuffle(matches)
    for index, match in enumerate(matches):
        match.order = next_match_number + index
    Match.objects.create_all(Match.objects.to_dicts(matches))
    return
