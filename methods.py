from itertools import groupby
from random import shuffle, choice
from typing import List, Tuple, Optional, Union

from flask import url_for

from models import Standing, Group, Series, INITIAL2, INITIAL1, DECIDER, TBD, WINNER, LOSER, Match, Player, FINAL
from utils import get_order, get_season, get_series_types, get_range_of_week, get_list_of_rounds, sort_standings, \
    RoundGroup, round_down, RoundTeam, SeriesStanding, MatchGroup, get_match_player, \
    get_tbd_series_to_update, get_next_round_series_to_update, get_conquest_names, get_lhs_names


def init_standings():
    season = get_season()
    if Standing.objects.filter_by(season=get_season()).first() is not None:
        print(f"Standings for season {season} already initialized.")
        return
    groups: List[Group] = Group.objects.filter_by(qualification_locked=True).get()
    if len(groups) != 128:
        print(f"Qualification for {128 - len(groups)} groups pending.")
        return
    new_standings = [Standing(season=season, group_name=group.name) for group in groups]
    Standing.objects.create_all(Standing.objects.to_dicts(new_standings))
    print(f"Standings for season {season} initialized.")


def init_series():
    season = get_season()
    query = Series.objects.order_by("week", Standing.objects.ORDER_DESCENDING)
    last_series: Series = query.filter_by(season=season).first()
    week: int = last_series.week + 1 if last_series else 1
    if week > 8:
        print("7 weeks of the season completed. Start a new season.")
        return
    new_series = [Series(season, week, round_number, series_type, order=get_order(week, round_number, series_type))
                  for week in get_range_of_week()
                  for round_number in get_list_of_rounds(week)
                  for series_type in get_series_types(week, round_number)]
    Series.objects.create_all(Series.objects.to_dicts(new_series))
    print(f"Series for season {season}  for all 7 weeks initialized.")


def setup_initial_matches():
    season = get_season()
    initial: Series = Series.objects.order_by("week").filter_by(season=season, group_name2=TBD, type=INITIAL1,
                                                                round=111).first()
    if not initial:
        print(f"There are no matches to setup. Init the series first for the season {season}.")
        return
    week = initial.week
    if week > 8:
        print(f"Invalid week {week} for season {season}.")
        return
    if week > 1:
        decider: Series = Series.objects.filter_by(season=season, week=week - 1, round=601, type=DECIDER).first()
        if decider.group_name1 == TBD:
            print(f"Complete week {week - 1} before setting initial matches for week {week} in season {season}.")
            return
    if week == 8:
        setup_initial_matches_for_playoff()
        return
    tbd_series: List[Series] = Series.objects.filter_by(season=season, week=week).filter("round", "<", 200) \
        .filter("type", Series.objects.IN, [INITIAL1, INITIAL2]).get()
    if len(tbd_series) != 64:
        print(f"Series for season {season} not setup correctly. Expected 64 TBD but found {len(tbd_series)}.")
        return
    group_names: List[str] = [standing.group_name for standing in Standing.objects.filter_by(season=season).get()]
    if len(group_names) != 128:
        print(f"Standings for season {season} not setup correctly. Expected 128 names but found {len(group_names)}.")
        return
    shuffle(group_names)
    for index, series in enumerate(tbd_series):
        series.group_name1 = group_names[index * 2]
        series.group_name2 = group_names[index * 2 + 1]
        series.group_names = [series.group_name1, series.group_name2]
    Series.objects.save_all(tbd_series)
    print(f"Initial matches for season {season} for week {week} setup.")


def setup_initial_matches_for_playoff():
    season = get_season()
    tbd_series: List[Series] = Series.objects.filter_by(season=season, week=8).filter("round", "<", 200).get()
    tbd_series.sort(key=lambda item: item.round)
    standings: List[Standing] = Standing.objects.get()
    standings = sort_standings(standings)
    top: List[Standing] = standings[:8]
    middle: List[Standing] = standings[8:24]
    bottom: List[Standing] = standings[24:32]
    shuffle(top)
    shuffle(middle)
    shuffle(bottom)
    for series in tbd_series:
        if series.type == INITIAL1:
            series.group_name1 = middle.pop().group_name
            series.group_name2 = middle.pop().group_name
            series.group_names = [series.group_name1, series.group_name2]
        elif series.type == WINNER:
            series.group_name2 = top.pop().group_name
            series.group_names = [TBD, series.group_name2]
        elif series.type == LOSER:
            series.group_name2 = bottom.pop().group_name
            series.group_names = [TBD, series.group_name2]
    Series.objects.save_all(tbd_series)
    return


def get_next_series() -> Series:
    return Series.objects.order_by("order").filter_by(season=get_season(), winner=str()).first()


def get_standings_with_url() -> List[Standing]:
    season = get_season()
    standings: List[Standing] = Standing.objects.filter_by(season=season).get()
    standings = sort_standings(standings)
    groups: List[Group] = Group.objects.get()
    for standing in standings:
        group: Group = next((group for group in groups if group.name == standing.group_name), None)
        if not group:
            continue
        standing.url = group.url
        standing.url_name = group.player_name
    return standings


def get_round_groups(season: int, week: int) -> List[RoundGroup]:
    week_series: List[Series] = Series.objects.filter_by(season=season, week=week).get()
    week_series.sort(key=lambda item: item.order)
    round_group_range: range = range(1, 6) if week < 8 else range(1, 3)
    round_group_count: int = len(list(round_group_range))
    round_group_last: int = list(round_group_range)[-1]
    round_groups: List[RoundGroup] = [RoundGroup(str(index)) if index != round_group_last else
                                      RoundGroup(f"{index} & {index + 1}") for index in round_group_range]
    standings: List[Standing] = get_standings_with_url()
    for round_number, round_series in groupby(week_series, key=lambda item: item.round):
        round_group_number: int = round_down(round_number, 100) // 100
        if round_group_number > round_group_count:
            round_group_number: int = round_group_last
        round_team: RoundTeam = RoundTeam(round_number)
        round_groups[round_group_number - 1].rounds.append(round_team)
        for series in round_series:
            series_standing: SeriesStanding = SeriesStanding()
            round_team.series_standings.append(series_standing)
            series_standing.series = series
            if series.group_name1 != TBD:
                series_standing.standing1 = next(item for item in standings if item.group_name == series.group_name1)
            else:
                series_standing.standing1.url = url_for("static", filename="default.jpg")
            if series.group_name2 != TBD:
                series_standing.standing2 = next(item for item in standings if item.group_name == series.group_name2)
            else:
                series_standing.standing2.url = url_for("static", filename="default.jpg")
    return round_groups


def get_match_group(series: Series) -> MatchGroup:
    if TBD in series.group_names:
        return MatchGroup()
    match_group = MatchGroup()
    matches: List[Match] = Match.objects.filter_by(season=series.season, week=series.week, type=series.type,
                                                   round=series.round).get()
    players: List[Player] = Player.objects.filter("group_name", Player.objects.IN, series.group_names) \
        .filter_by(qualified=True).get()
    standings: List[Standing] = Standing.objects.filter_by(season=series.season) \
        .filter("group_name", Series.objects.IN, series.group_names).get()
    past_matches: List[Match] = [match for match in matches if match.winner != str()]
    past_matches.sort(key=lambda match: match.order)
    match_group.past_matches = [get_match_player(match, players) for match in past_matches]
    current_match: Optional[Match] = next((match for match in matches if match.winner == str()), None)
    if not current_match and not series.winner:
        current_match = Match(series.season, series.week, series.round, series.type)
        if series.week in (1, 3, 5, 7, 8):
            player1_choices: List[str] = get_conquest_names(players, match_group, series.group_name1)
            player2_choices: List[str] = get_conquest_names(players, match_group, series.group_name2)
        else:
            player1_choices: List[str] = get_lhs_names(players, match_group, series.group_name1)
            player2_choices: List[str] = get_lhs_names(players, match_group, series.group_name2)
        current_match.player1 = choice(player1_choices)
        current_match.player2 = choice(player2_choices)
        current_match.players = [current_match.player1, current_match.player2]
        current_match.order = max(match.order for match in past_matches) + 1 if past_matches else 1
        current_match.create()
    match_group.current_match = get_match_player(current_match, players) if current_match else None
    match_group.standing1 = next(item for item in standings if item.group_name == series.group_name1)
    match_group.standing2 = next(item for item in standings if item.group_name == series.group_name2)
    return match_group


def get_series_score(series: Series, match_group: MatchGroup) -> Tuple[int, int]:
    score1: int = sum(1 for m_player in match_group.past_matches if m_player.winner_group_name == series.group_name1)
    score2: int = sum(1 for m_player in match_group.past_matches if m_player.winner_group_name == series.group_name2)
    return score1, score2


def update_results(series: Series, match_group: MatchGroup, winning_name: str) -> None:
    match_group.current_match.match.winner = winning_name
    match_group.current_match.match.save()
    match_group.past_matches.append(match_group.current_match)
    series.scores = get_series_score(series, match_group)
    standing: Standing = match_group.winner_standing
    if max(series.scores) == 5:
        series.winner = standing.group_name
    update_score(series, standing)
    if not update_tbd(series):
        series.save()
    standing.save()
    if series.winner and series.round == 601 and series.type == DECIDER:
        setup_initial_matches()
    return


def update_score(series: Series, standing: Standing) -> None:
    if series.week > 7:
        return
    index = series.week - 1
    standing.weekly_ties[index] += 1
    if series.winner:
        standing.weekly_scores[index] += 1
        if series.type == WINNER:
            standing.weekly_ties[index] += 10
    return


def update_tbd(series) -> bool:
    if series.round == 601 and series.type == DECIDER or series.round == 300 and series.type == FINAL:
        return False
    if not series.winner or not series.loser:
        return False
    series_to_update: List[Series] = [series]
    if series.type == INITIAL1:
        tbd_series: List[Series] = get_tbd_series_to_update(series, [WINNER, LOSER])
        tbd_series[0].set_group_name1(series.winner)
        tbd_series[1].set_group_name1(series.loser)
        series_to_update.extend(tbd_series)
    elif series.type == INITIAL2:
        tbd_series: List[Series] = get_tbd_series_to_update(series, [WINNER, LOSER])
        tbd_series[0].set_group_name2(series.winner)
        tbd_series[1].set_group_name2(series.loser)
        series_to_update.extend(tbd_series)
    elif series.type == WINNER:
        if series.round != 601:
            next_series: Series = get_next_round_series_to_update(series)
            next_series.set_group_name1(series.winner)
            series_to_update.append(next_series)
        decider: Series = get_tbd_series_to_update(series, [DECIDER])[0]
        decider.set_group_name1(series.loser)
        series_to_update.append(decider)
    elif series.type == LOSER:
        decider: Series = get_tbd_series_to_update(series, [DECIDER])[0]
        decider.set_group_name2(series.winner)
        series_to_update.append(decider)
    elif series.type == DECIDER:
        next_series: Series = get_next_round_series_to_update(series)
        next_series.set_group_name2(series.winner)
        series_to_update.append(next_series)
    else:  # Series type is final
        next_series: Series = get_next_round_series_to_update(series)
        if series.round in (210, 230):
            next_series.set_group_name1(series.winner)
        else:  # Series round is 220 or 240
            next_series.set_group_name2(series.winner)
        series_to_update.append(next_series)
    Series.objects.save_all(series_to_update)
    return True


def update_rank_and_save(items: List[Union[Player, Group]]):
    updated_items: List[Union[Player, Group]] = update_rank(items)
    items[0].__class__.objects.save_all(updated_items)
    return


def update_rank(items: List[Union[Player, Group]]) -> List[Union[Player, Group]]:
    updated_items: List[Union[Player, Group]] = list()
    items.sort(key=lambda item: item.score, reverse=True)
    previous_rank, previous_score = 0, 0
    for index, item in enumerate(items):
        new_rank = previous_rank if item.score == previous_score else index + 1
        previous_rank, previous_score = new_rank, item.score
        if item.rank == new_rank:
            continue
        item.rank = new_rank
        updated_items.append(item)
    return updated_items
