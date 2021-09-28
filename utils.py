from typing import Tuple, List

from flask_login import current_user

from models import SERIES_TYPES, BYE_SERIES_TYPES, FINAL_SERIES_TYPES, Standing, Series


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
    return 2 ** (6 - get_round_group_from_round(number) // 100)


def get_round_group_from_round(number: int) -> int:
    return number - number % 100


def sort_standings(standings: List[Standing]) -> List[Standing]:
    return sorted(standings, key=lambda standing: (-standing.total_score, -standing.total_ties))
