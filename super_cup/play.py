from concurrent.futures import ThreadPoolExecutor, as_completed
from random import shuffle
from typing import List, Callable

from munch import Munch

from adventure.response import StandardResponse, RequestType, SuccessMessage
from models import Player, Group, Match
from super_cup.models import CupConfig, CupSeries, RoundCalculator


def select_players(group_count: int, player_count_per_group: int) -> List[Player]:
    players: List[Player] = Player.objects.order_by("rank").limit(group_count * player_count_per_group * 5).get()
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
            return selected_players
    return list()

def perform_io_task(task_list: List[Callable]):
    with ThreadPoolExecutor(max_workers=len(task_list)) as executor:
        threads = [executor.submit(task) for task in task_list]
        results = [future.result() for future in as_completed(threads)]
    return results


def get_current_active_series() -> CupSeries:
    query = CupSeries.objects.filter_by(series_completed_status=False)
    series: CupSeries = query.order_by("round_number").order_by("match_number").first()
    return series


def initialize_series(series: CupSeries, players: List[Player], groups: List[Group], group_index: int) -> int:
    players_in_this_series: List[Player] = [player for player in players if player.group_name == groups[group_index].name]
    series.initialize_group(groups[group_index], players_in_this_series)
    return group_index + 1


def create_season(request: Munch) -> Munch:
    group_count = CupConfig.TOTAL_GROUP_COUNT
    player_count_per_group = CupConfig.PLAYER_PER_GROUP
    rsp: StandardResponse = StandardResponse(request=request, request_type=RequestType.CREATE_SEASON)
    if get_current_active_series():
        rsp.message.error = "Complete previous season before starting a new season."
        return rsp.dict
    last_complete_series: CupSeries = CupSeries.objects.order_by("season", CupSeries.objects.ORDER_DESCENDING).first()
    new_season = last_complete_series.season + 1 if last_complete_series else 1
    round_calculator = RoundCalculator(group_count)
    selected_players: List[Player] = select_players(group_count, player_count_per_group)
    if not selected_players:
        rsp.message.error = "Not enough players found to start the season."
        return rsp.dict
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
    rsp.data.season = rsp.request.season
    rsp.message.success = SuccessMessage.GET_SEASON
    return rsp.dict


def get_next_match(request: Munch) -> Munch:
    rsp = StandardResponse(request, RequestType.NEXT_MATCH)
    series: CupSeries = get_current_active_series()
    if not series:
        rsp.message.error = "Create a new season to play again."
        return rsp.dict
    rsp.data.series = series
    player_names: List[str] = [series.current_match_player1_name, series.current_match_player2_name]
    rsp.data.players = Player.objects.filter("name", Player.objects.IN, player_names).get()
    rsp.message.success = SuccessMessage.NEXT_MATCH
    return rsp.dict


def update_play_result(request: Munch) -> Munch:
    rsp = StandardResponse(request, RequestType.CUP_PLAY_RESULT)
    if rsp.message.error:
        return rsp.dict
    player_names = [rsp.request.winner, rsp.request.loser]
    group_names = [rsp.request.winner[:2], rsp.request.loser[:2]]
    get_series_task = CupSeries.objects.filter_by(season=rsp.request.season, round_number=rsp.request.round_number,
                                                  match_number=rsp.request.match_number).get
    get_players_task = Player.objects.filter("name", Player.objects.IN, player_names).get
    get_group_task = Group.objects.filter("name", Group.objects.IN, group_names).get
    get_document_tasks: List[Callable] = [get_series_task, get_players_task, get_group_task]
    results = perform_io_task(get_document_tasks)
    series: CupSeries = next((result[0] for result in results if result and isinstance(result[0], CupSeries)), None)
    players: List[Player] = next((result for result in results if result and isinstance(result[0], Player)), list())
    groups: List[Group] = next((result for result in results if result and isinstance(result[0], Group)), list())
    if not series or series.is_series_completed():
        rsp.message.error = "Invalid season, round number or match number."
        return rsp.dict
    if not series.is_player_in_current_match(rsp.request.winner):
        rsp.message.error = rsp.error_fields.winner = "Winner is not from the current match."
        return rsp.dict
    if not series.is_player_in_current_match(rsp.request.loser):
        rsp.message.error = rsp.error_fields.loser = "Loser is not from the current match."
        return rsp.dict
    if len(players) != 2:
        rsp.message.error = "Unable to find Players."
        return rsp.dict
    if not 1 <= len(groups) <= 2:
        rsp.message.error = "Unable to find Groups."
        return rsp.dict
    winning_player = players[0] if players[0].name == rsp.request.winner else players[1]
    losing_player = players[0] if players[0].name == rsp.request.loser else players[1]
    winning_player.update_score(played=1, won=1)
    losing_player.update_score(played=1, won=0)
    update_tasks = [winning_player.save, losing_player.save]
    if len(groups) == 1:
        groups[0].update_score(played=2, won=1)
        update_tasks.append(groups[0].save)
    else:
        winning_group = groups[0] if groups[0].name == rsp.request.winner[:2] else groups[1]
        losing_group = groups[0] if groups[0].name == rsp.request.loser[:2] else groups[1]
        winning_group.update_score(played=1, won=1)
        losing_group.update_score(played=1, won=0)
        update_tasks.extend([winning_group.save, losing_group.save])
    match: Match = Match(season=rsp.request.season, series_type=CupConfig.TYPE, round_number=rsp.request.round_number,
                         player1=rsp.request.winner, player2=rsp.request.loser)
    match.winner = rsp.request.winner
    update_tasks.append(match.save)
    series.set_winner(rsp.request.winner)
    update_tasks.append(series.save)
    if series.is_series_completed():
        series.series_completed_status = True
        if not series.is_season_over():
            next_series: CupSeries = CupSeries.objects.filter_by(season=rsp.request.season, round_number=rsp.request.round_number + 1,
                                                                 match_number=series.get_next_rounds_match_number()).first()
            if not next_series:
                rsp.message.error = "Unable to update match. Invalid state."
                return rsp.dict
            next_series.copy_group(series)
            update_tasks.append(next_series.save)
    perform_io_task(update_tasks)
    rsp.message.success = SuccessMessage.PLAY_RESULT
    return rsp.dict
