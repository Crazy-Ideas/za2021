import itertools
from random import shuffle
from typing import List, Callable

from munch import Munch

from adventure.response import StandardResponse, RequestType, SuccessMessage
from methods import perform_io_task
from models import Player, Group, Match
from super_cup.errors import InvalidNumberOfPlayersProvidedForInitialization, GroupAlreadyInitialized, PlayerNotFound, \
    InvalidPlayerPerGroup, SeriesNotCompleted, GroupNotInitialized, SeriesCompleted
from super_cup.models import CupConfig, CupSeries, RoundCalculator


def select_players(group_count: int, player_per_group: int) -> List[Player]:
    if player_per_group == 1:
        selected_players: List[Player] = Player.objects.order_by("rank").limit(CupConfig.get_total_group_count(player_per_group)).get()
        return selected_players
    filtered_player_count: int = group_count * player_per_group * player_per_group
    players: List[Player] = Player.objects.order_by("rank").limit(filtered_player_count).get()
    players.sort(key=lambda item: item.rank, reverse=False)
    selected_players: List[Player] = list()
    expected_count: int = group_count * player_per_group
    selected_groups: set = set()
    nominated_groups: dict = dict()
    for player in players:
        if player.group_name in selected_groups:
            continue
        if player.group_name not in nominated_groups:
            nominated_groups[player.group_name] = list()
        nominated_groups[player.group_name].append(player)
        if len(nominated_groups[player.group_name]) != player_per_group:
            continue
        selected_groups.add(player.group_name)
        selected_players.extend(nominated_groups[player.group_name])
        if len(selected_players) >= expected_count:
            return selected_players
    return list()


def get_current_active_series(player_per_group: int) -> CupSeries:
    query = CupSeries.objects.filter_by(series_completed_status=False, player_per_group=player_per_group)
    series: CupSeries = query.order_by("round_number").order_by("match_number").first()
    return series


def initialize_series(series: CupSeries, players: List[Player], groups: List[Group], group_index: int) -> int:
    players_in_this_series: List[Player] = [player for player in players if player.group_name == groups[group_index].name]
    series.initialize_group(groups[group_index], players_in_this_series)
    return group_index + 1


def create_season(request: Munch) -> Munch:
    rsp: StandardResponse = StandardResponse(request=request, request_type=RequestType.CUP_CREATE_SEASON)
    player_count_per_group = rsp.request.player_per_group
    try:
        group_count = CupConfig.get_total_group_count(player_count_per_group)
    except InvalidPlayerPerGroup:
        rsp.message.error = "Invalid type of Super Cup."
        return rsp.dict
    if get_current_active_series(player_count_per_group):
        rsp.message.error = "Complete previous season before starting a new season."
        return rsp.dict
    query = CupSeries.objects.filter_by(player_per_group=player_count_per_group)
    last_complete_series: CupSeries = query.order_by("season", CupSeries.objects.ORDER_DESCENDING).first()
    new_season = last_complete_series.season + 1 if last_complete_series else 1
    round_calculator = RoundCalculator(group_count)
    selected_players: List[Player] = select_players(group_count, player_count_per_group)
    if not selected_players:
        rsp.message.error = "Not enough players found to start the season."
        return rsp.dict
    group_names: List[str] = list({player.group_name for player in selected_players})
    get_group_tasks: List[Callable] = [Group.objects.filter_by(name=group_name).first for group_name in group_names]
    groups: List[Group] = perform_io_task(get_group_tasks)
    series_to_be_created: List[CupSeries] = list()
    if player_count_per_group != 1:
        shuffle(groups)
        group_index: int = 0
        for round_number in range(1, round_calculator.total_rounds + 1):
            for match_number in range(1, round_calculator.total_matches_per_round(round_number) + 1):
                series: CupSeries = CupSeries(new_season, round_number, match_number, group_count, player_count_per_group)
                series_to_be_created.append(series)
                if round_number != 1:
                    continue
                try:
                    players_in_this_series: List[Player] = [player for player in selected_players if
                                                            player.group_name == groups[group_index].name]
                    series.initialize_group(groups[group_index], players_in_this_series)
                    group_index += 1
                    players_in_this_series: List[Player] = [player for player in selected_players if
                                                            player.group_name == groups[group_index].name]
                    series.initialize_group(groups[group_index], players_in_this_series)
                    group_index += 1
                except InvalidNumberOfPlayersProvidedForInitialization:
                    rsp.message.error = "Invalid number of players provided for initialization."
                    return rsp.dict
                except GroupAlreadyInitialized:
                    rsp.message.error = "Group already initialized."
                    return rsp.dict
    else:  # When player count is 1 it is for top 1000 players which might be from the same groups
        shuffle(selected_players)  # TODO: consider seeding
        player_index: int = 0
        for round_number in range(1, round_calculator.total_rounds + 1):
            for match_number in range(1, round_calculator.total_matches_per_round(round_number) + 1):
                series: CupSeries = CupSeries(new_season, round_number, match_number, group_count, player_count_per_group)
                series_to_be_created.append(series)
                if round_number != 1:
                    continue
                try:
                    players_1: List[Player] = [selected_players[player_index]]
                    player_index += 1
                    series.initialize_group(next(group for group in groups if group.name == players_1[0].group_name), players_1)
                    players_2: List[Player] = [selected_players[player_index]]
                    player_index += 1
                    series.initialize_group(next(group for group in groups if group.name == players_2[0].group_name), players_2)
                except InvalidNumberOfPlayersProvidedForInitialization:
                    rsp.message.error = "Invalid number of players provided for initialization."
                    return rsp.dict
                except GroupAlreadyInitialized:
                    rsp.message.error = "Group already initialized."
                    return rsp.dict
    chunk_size: int = 350
    batch_series_to_be_created: List[List[CupSeries]] = [series_to_be_created[i: i + chunk_size]
                                                         for i in range(0, len(series_to_be_created), chunk_size)]
    for batch_series in batch_series_to_be_created:
        CupSeries.objects.create_all(CupSeries.objects.to_dicts(batch_series))
    rsp.message.success = SuccessMessage.CREATE_SEASON
    return rsp.dict


def get_season(request: Munch) -> Munch:
    rsp: StandardResponse = StandardResponse(request=request, request_type=RequestType.CUP_GET_SEASON)
    if rsp.message.error:
        return rsp.dict
    if not CupConfig.is_valid_player_per_group(rsp.request.player_per_group):
        rsp.message.error = "Invalid type of Super Cup."
        return rsp.dict
    total_group_count: int = CupConfig.get_total_group_count(rsp.request.player_per_group)
    round_calculator = RoundCalculator(total_group_count)
    if rsp.request.limited:
        # series_query = CupSeries.objects.filter_by(season=rsp.request.season, player_per_group=rsp.request.player_per_group)
        # series_list = series_query.filter("round_number", ">=", round_calculator.pre_quarter_final_round_number).get()
        get_series_tasks = list()
        for round_number in range(round_calculator.pre_quarter_final_round_number, round_calculator.final_round_number + 1):
            series_query = CupSeries.objects.filter_by(season=rsp.request.season, player_per_group=rsp.request.player_per_group)
            task = series_query.filter_by(round_number=round_number).get
            get_series_tasks.append(task)
        results = perform_io_task(get_series_tasks)
        series_list: List[CupSeries] = list(itertools.chain(*results))
    else:
        series_list = CupSeries.objects.filter_by(season=rsp.request.season, player_per_group=rsp.request.player_per_group).get()
    if not series_list:
        rsp.message.error = "Season not found."
        return rsp.dict
    series_list.sort(key=lambda item: (item.round_number, item.match_number))
    player_names: List[str] = [match.star_player1 for match in series_list if match.is_group1_initialized()]
    player_names += [match.star_player2 for match in series_list if match.is_group2_initialized()]
    player_names = list(set(player_names))
    if player_names:
        get_player_tasks = [Player.objects.filter_by(name=player_name).first for player_name in player_names]
        rsp.data.players = perform_io_task(get_player_tasks)
    else:
        rsp.data.players = list()
    if rsp.request.limited:
        rsp.data.earlier_rounds = [series for series in series_list
                                   if series.round_number == round_calculator.pre_quarter_final_round_number]
    else:
        rsp.data.earlier_rounds = [series for series in series_list if series.round_number in round_calculator.earlier_round_numbers]
    rsp.data.quarter_finals = [series for series in series_list if series.round_number == round_calculator.quarter_final_round_number]
    rsp.data.finals = [series for series in series_list
                       if series.round_number in (round_calculator.semi_final_round_number, round_calculator.final_round_number)]
    rsp.data.season = rsp.request.season
    rsp.message.success = SuccessMessage.GET_SEASON
    return rsp.dict


def get_next_match(request: Munch) -> Munch:
    rsp = StandardResponse(request, RequestType.CUP_NEXT_MATCH)
    if not CupConfig.is_valid_player_per_group(rsp.request.player_per_group):
        rsp.message.error = "Invalid type of Super Cup."
        return rsp.dict
    series: CupSeries = get_current_active_series(rsp.request.player_per_group)
    if not series:
        rsp.message.error = "Create a new season to play again."
        return rsp.dict
    rsp.data.series = series
    try:
        player_names: List[str] = [series.current_match_player1_name, series.current_match_player2_name]
    except GroupNotInitialized:
        rsp.message.error = "Exception. Group not initialized."
        return rsp.dict
    except SeriesCompleted:
        rsp.message.error = "Exception. Series completed."
        return rsp.dict
    players = Player.objects.filter("name", Player.objects.IN, player_names).get()
    if len(players) != 2:
        rsp.message.error = "Players for next match not found"
        return rsp.dict
    if players[0].name == series.current_match_player1_name:
        rsp.data.players = [players[0], players[1]]
    elif players[0].name == series.current_match_player2_name:
        rsp.data.players = [players[1], players[0]]
    else:
        rsp.message.error = "Invalid player found for next match"
        return rsp.dict
    rsp.message.success = SuccessMessage.NEXT_MATCH
    return rsp.dict


def update_play_result(request: Munch) -> Munch:
    rsp = StandardResponse(request, RequestType.CUP_PLAY_RESULT)
    if rsp.message.error:
        return rsp.dict
    player_names = [rsp.request.winner, rsp.request.loser]
    group_names = [rsp.request.winner[:2], rsp.request.loser[:2]]
    get_series_task = CupSeries.objects.filter_by(season=rsp.request.season, round_number=rsp.request.round_number,
                                                  match_number=rsp.request.match_number, player_per_group=rsp.request.player_per_group).get
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
    try:
        series.set_winner(rsp.request.winner)
    except PlayerNotFound:
        rsp.message.error = "Exception. Winner player not found."
        return rsp.dict
    update_tasks.append(series.save)
    if series.is_series_completed():
        series.series_completed_status = True
        if not series.is_season_over():
            query = CupSeries.objects.filter_by(player_per_group=series.player_per_group, round_number=rsp.request.round_number + 1)
            next_series: CupSeries = query.filter_by(season=rsp.request.season, match_number=series.get_next_rounds_match_number()).first()

            if not next_series:
                rsp.message.error = "Unable to update match. Invalid state."
                return rsp.dict
            try:
                next_series.copy_group(series)
            except GroupAlreadyInitialized:
                rsp.message.error = "Exception. Group already initialized."
                return rsp.dict
            except SeriesNotCompleted:
                rsp.message.error = "Exception. Series not completed."
                return rsp.dict
            except InvalidNumberOfPlayersProvidedForInitialization:
                rsp.message.error = "Exception. Invalid number of players."
                return rsp.dict
            update_tasks.append(next_series.save)
    perform_io_task(update_tasks)
    rsp.message.success = SuccessMessage.PLAY_RESULT
    return rsp.dict


def get_all_seasons(request: Munch) -> Munch:
    rsp = StandardResponse(request, RequestType.CUP_ALL_SEASONS)
    if rsp.message.error:
        return rsp.dict
    if not CupConfig.is_valid_player_per_group(rsp.request.player_per_group):
        return rsp.with_error_message("Invalid Cup type.")
    total_groups: int = CupConfig.get_total_group_count(rsp.request.player_per_group)
    final_round_number: int = RoundCalculator(total_groups).final_round_number
    finals: List[CupSeries] = CupSeries.objects.filter_by(player_per_group=rsp.request.player_per_group, round_number=final_round_number,
                                                          series_completed_status=True).get()
    if not finals:
        rsp.data.players = rsp.data.finals = list()
        return rsp.with_error_message("No completed series as yet.")
    finals.sort(key=lambda item: item.season, reverse=True)
    star_players = set(star_player for final in finals for star_player in final.star_players)
    get_players_task = [Player.objects.filter_by(name=star_player).first for star_player in star_players]
    players: List[Player] = perform_io_task(get_players_task)
    rsp.data.players = players
    rsp.data.finals = finals
    return rsp.with_success_message(SuccessMessage.GET_SEASON)
