from typing import Tuple, List, Optional

from flask_login import current_user

from models import SERIES_TYPES, BYE_SERIES_TYPES, FINAL_SERIES_TYPES, Standing, Series, Match, Player, WINNER, \
    DECIDER, INITIAL1, INITIAL2, FINAL


class MatchGroup:
    def __init__(self):
        self.past_matches: List[MatchPlayer] = list()
        self.current_match: MatchPlayer = MatchPlayer()
        self.standing1: Standing = Standing()
        self.standing2: Standing = Standing()

    def __repr__(self):
        return f"PMC={len(self.past_matches)}, CM={self.current_match}"

    @property
    def winner_standing(self) -> Optional[Standing]:
        if not self.current_match.match.winner:
            return None
        return self.standing1 if self.current_match.winner_group_name == self.standing1.group_name else self.standing2


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


class RoundGroup:
    def __init__(self, round_group_text: str):
        self.round_group_text: str = round_group_text
        self.rounds: List[RoundTeam] = list()

    def __repr__(self):
        return f"{self.round_group_text}:{len(self.rounds)}"


class RoundTeam:
    def __init__(self, round_number: int):
        self.round_number: int = round_number
        self.series_standings: List = list()

    def __repr__(self):
        return f"{self.round_number}:{len(self.series_standings)}"


class SeriesStanding:
    def __init__(self):
        self.series: Series = Series()
        self.standing1: Standing = Standing()
        self.standing2: Standing = Standing()

    def __repr__(self):
        return f"{self.series}::{self.standing1}::{self.standing2}"


def get_order(week: int, round_number: int, series_type: str) -> int:
    round_list = get_list_of_rounds(week)
    if week <= 7:
        return ((week - 1) * len(round_list) * len(SERIES_TYPES)
                + round_list.index(round_number) * len(SERIES_TYPES)
                + SERIES_TYPES.index(series_type) + 1)
    # Playoff
    weekly_count: int = (len(list(get_range_of_week())) - 1) * len(get_list_of_rounds(1)) * len(SERIES_TYPES)
    series_types: Tuple[str] = get_series_types(week, round_number)
    return (weekly_count
            + sum(len(BYE_SERIES_TYPES) if number < 200 else len(FINAL_SERIES_TYPES)
                  for number in round_list if number < round_number)
            + series_types.index(series_type) + 1)


def get_season() -> int:
    return current_user.season if current_user and current_user.is_authenticated else 1


def get_series_types(week: int, round_number: int) -> Tuple[str]:
    if week <= 7:
        return SERIES_TYPES
    # Playoff with byes
    if round_number < 200:
        return BYE_SERIES_TYPES
    # Playoff with finals
    return FINAL_SERIES_TYPES


def get_range_of_week() -> range:
    return range(1, 9)


def get_list_of_rounds(week: int) -> List[int]:
    if week <= 7:
        return [round_group + round_team
                for round_group in range(100, 601, 100)
                for round_team in range(1, get_total_round_team(round_group) + 1)]
    # For Playoff
    return [111, 112, 121, 122, 131, 132, 141, 142, 210, 220, 230, 240, 300]


def get_total_round_team(number: int) -> int:
    return 2 ** (6 - round_down(number, 100) // 100)


def round_down(number: int, factor: int) -> int:
    return number - number % factor


def sort_standings(standings: List[Standing]) -> List[Standing]:
    return sorted(standings, key=lambda standing: (-standing.total_score, -standing.total_ties))


def get_match_player(match: Match, players: List[Player]) -> MatchPlayer:
    match_player = MatchPlayer()
    match_player.match = match
    match_player.player1 = next(player for player in players if player.name == match.player1)
    match_player.player2 = next(player for player in players if player.name == match.player2)
    return match_player


def get_tbd_series_to_update(series: Series, series_types: List[str]) -> List[Series]:
    tbd_series: List[Series] = Series.objects.filter_by(season=series.season, week=series.week, round=series.round) \
        .filter("type", Series.objects.IN, series_types).get()
    tbd_series.sort(key=lambda item: FINAL_SERIES_TYPES.index(item.type))
    return tbd_series


def get_next_round_series_to_update(series: Series) -> Series:
    return Series.objects.filter_by(season=series.season, week=series.week, round=get_next_round(series),
                                    type=get_next_series_type(series)).first()


def get_next_round(series: Series) -> int:
    next_round_group: int = round_down(series.round, 100) + 100
    current_round_team_number: int = series.round % 100
    if series.week <= 7:
        next_round_total_count: int = get_total_round_team(series.round) // 2
        if series.type == WINNER:
            next_round_team_number = current_round_team_number
            if next_round_team_number > next_round_total_count:
                next_round_team_number -= next_round_total_count
        else:  # Series type is DECIDER:
            next_round_team_number = next_round_total_count + 1 - current_round_team_number
            if next_round_team_number <= 0:
                next_round_team_number += next_round_total_count
        return next_round_group + next_round_team_number
    # Playoff is Week 8
    if series.type in (WINNER, DECIDER) and series.round >= 200:
        return series.round
    if next_round_group == 300:
        return next_round_group
    # Next round group is 200 - Use the face value of ten
    return next_round_group + round_down(current_round_team_number, 10)


def get_next_series_type(series: Series) -> str:
    next_round_total_count: int = get_total_round_team(series.round) // 2
    current_round_team_number: int = series.round % 100
    if series.week <= 7:
        if series.type == WINNER:
            return INITIAL1 if current_round_team_number <= next_round_total_count else INITIAL2
        # Series type is DECIDER
        return INITIAL2 if current_round_team_number <= next_round_total_count else INITIAL1
    # Playoff is week 8
    if series.round >= 200:
        if series.type in (WINNER, DECIDER):
            return FINAL
        # Series type is FINAL
        return INITIAL1 if round_down(current_round_team_number, 10) in (10, 20) else INITIAL2
    # Playoff for going to round 200+
    if series.type == WINNER:
        return INITIAL1 if series.round % 2 == 1 else INITIAL2
    # Series type is DECIDER
    return INITIAL2 if series.round % 2 == 1 else INITIAL1
