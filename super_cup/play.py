from concurrent.futures import ThreadPoolExecutor, as_completed
from random import shuffle
from typing import List, Callable

from munch import Munch

from adventure.response import StandardResponse, RequestType, SuccessMessage
from models import Player, Group
from super_cup.models import CupConfig, CupSeries, RoundCalculator


def select_players(group_count: int, player_count_per_group: int) -> List[Player]:
    players: List[Player] = Player.objects.get()
    players.sort(key=lambda item: item.rank, reverse=False)
    selected_players: List[Player] = list()
    expected_count: int = group_count * player_count_per_group
    selected_groups: set = set()
    nominated_groups: dict = dict()
    for player in players:
        if player.group_name in selected_groups:
            continue
        if player.group_name not in nominated_groups:
            nominated_groups[player.group_name] = list()
        nominated_groups[player.group_name].append(player)
        if len(nominated_groups[player.group_name]) != player_count_per_group:
            continue
        selected_groups.add(player.group_name)
        selected_players.extend(nominated_groups[player.group_name])
        if len(selected_players) >= expected_count:
            break
    return selected_players


def perform_io_task(task_list: List[Callable]):
    with ThreadPoolExecutor(max_workers=len(task_list)) as executor:
        threads = [executor.submit(task) for task in task_list]
        results = [future.result() for future in as_completed(threads)]
    return results


def get_latest_series() -> CupSeries:
    query = CupSeries.objects.order_by("season", CupSeries.objects.ORDER_DESCENDING)
    series: CupSeries = query.order_by("round_number", CupSeries.objects.ORDER_DESCENDING).first()
    return series


def initialize_series(series: CupSeries, players: List[Player], groups: List[Group], group_index: int) -> int:
    players_in_this_series: List[Player] = [player for player in players if player.group_name == groups[group_index].name]
    series.initialize_group(groups[group_index], players_in_this_series)
    return group_index + 1


def create_season(request: Munch) -> Munch:
    group_count = CupConfig.TOTAL_GROUP_COUNT
    player_count_per_group = CupConfig.PLAYER_PER_GROUP
    rsp: StandardResponse = StandardResponse(request=request, request_type=RequestType.CREATE_SEASON)
    current_series: CupSeries = get_latest_series()
    if current_series and not current_series.is_series_completed():
        rsp.message.error = "Complete previous season before starting a new season."
        return rsp.dict
    current_season = current_series.season if current_series else 0
    new_season = current_season + 1
    round_calculator = RoundCalculator(group_count)
    selected_players: List[Player] = select_players(group_count, player_count_per_group)
    group_names: List[str] = list({player.group_name for player in selected_players})
    get_group_tasks: List[Callable] = [Group.objects.filter_by(name=group_name).first for group_name in group_names]
    groups: List[Group] = perform_io_task(get_group_tasks)
    shuffle(groups)
    series_to_be_created: List[CupSeries] = list()
    group_index: int = 0
    for round_number in range(1, round_calculator.total_rounds + 1):
        for match_number in range(1, round_calculator.total_matches_per_round(round_number) + 1):
            series: CupSeries = CupSeries(new_season, round_number, match_number, group_count, player_count_per_group)
            series_to_be_created.append(series)
            if round_number != 1:
                continue
            group_index = initialize_series(series, selected_players, groups, group_index)
            group_index = initialize_series(series, selected_players, groups, group_index)
    CupSeries.objects.create_all(CupSeries.objects.to_dicts(series_to_be_created))
    rsp.message.success = SuccessMessage.CREATE_SEASON
    return rsp.dict


def get_season(request: Munch) -> Munch:
    rsp: StandardResponse = StandardResponse(request=request, request_type=RequestType.CUP_GET_SEASON)
    if rsp.message.error:
        return rsp.dict
    series_list: List[CupSeries] = CupSeries.objects.filter_by(season=rsp.request.season).get()
    if not series_list:
        rsp.message.error = "Season not found."
        return rsp.dict
    series_list.sort(key=lambda item: (item.round_number, item.match_number))
    player_names: List[str] = [match.star_player1 for match in series_list if match.is_group1_initialized()]
    player_names += [match.star_player2 for match in series_list if match.is_group2_initialized()]
    player_names = list(set(player_names))
    get_player_tasks = [Player.objects.filter_by(name=player_name).first for player_name in player_names]
    rsp.data.players = perform_io_task(get_player_tasks)
    round_calculator = RoundCalculator(series_list[0].total_group_count)
    rsp.data.earlier_rounds = [series for series in series_list if series.round_number in round_calculator.earlier_round_numbers]
    rsp.data.quarter_finals = [series for series in series_list if series.round_number == round_calculator.quarter_final_round_number]
    rsp.data.finals = [series for series in series_list
                       if series.round_number in (round_calculator.semi_final_round_number, round_calculator.final_round_number)]
    rsp.message.success = SuccessMessage.GET_SEASON
    return rsp.dict
