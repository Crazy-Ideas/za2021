import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from random import sample, shuffle
from typing import List, Callable, Tuple

from munch import Munch

from adventure.errors import UpdateUrlError, GroupwiseFileError, UnableToSetOpponent
from adventure.models import Adventure
from adventure.response import StandardResponse, RequestType, SuccessMessage
from models import Group, Player, Match


def read_groupwise_players() -> dict:
    with open("temp/groupwise_players.json") as file:
        groupwise_players = json.load(file)
    return groupwise_players


def get_latest_adventure() -> Adventure:
    query = Adventure.objects.order_by("season", Adventure.objects.ORDER_DESCENDING)
    current_adventure: Adventure = query.order_by("round", Adventure.objects.ORDER_DESCENDING).first()
    return current_adventure


def set_opponent(adventure: Adventure, groupwise_players: dict, groups: List[Group]) -> None:
    opponent_group_name: str = adventure.get_next_opponent()
    if not opponent_group_name:
        raise UnableToSetOpponent
    if groups:
        opponent_group: Group = next((group for group in groups if group.name == opponent_group_name), None)
    else:
        opponent_group: Group = Group.objects.filter_by(name=opponent_group_name).first()
    try:
        player_names = groupwise_players[opponent_group_name]
    except KeyError:
        raise GroupwiseFileError
    adventure.set_opponent(opponent_group, player_names)
    return


def create_season() -> Munch:
    rsp: StandardResponse = StandardResponse(request=Munch(), request_type=RequestType.CREATE_SEASON)
    current_adventure: Adventure = get_latest_adventure()
    season: int = current_adventure.season if current_adventure else 0
    if current_adventure:
        if not current_adventure.is_round_over() or not current_adventure.is_game_over():
            rsp.message.error = "Complete previous season before starting a new season."
            return rsp.dict
    new_adventure = Adventure()
    new_adventure.season = season + 1
    new_adventure.round = 1
    groupwise_players: dict = read_groupwise_players()
    adventurer_group_names: List[str] = sample(list(groupwise_players), k=20)
    new_adventure.adventurers = [sample(groupwise_players[group_name], k=1)[0] for group_name in adventurer_group_names]
    shuffle(new_adventure.adventurers)
    groups: List[Group] = Group.objects.get()
    new_adventure.init_remaining_opponents(groups)
    set_opponent(new_adventure, groupwise_players, groups)
    new_adventure.create()
    rsp.message.success = SuccessMessage.CREATE_SEASON
    return rsp.dict


def create_match(season: int, round_number: int, player1: str, player2: str, winner: str) -> Match:
    match = Match(season=season, series_type="adventure", round_number=round_number, player1=player1, player2=player2)
    match.winner = winner
    return match


def get_adventure_players_groups(rsp) -> Tuple[Adventure, List[Player], List[Group]]:
    player_names: List[str] = [rsp.request.winner, rsp.request.loser]
    group_names: List[str] = [rsp.request.winner[:2], rsp.request.loser[:2]]
    with ThreadPoolExecutor() as executor:
        task_list: List[Callable] = list()
        task_list.append(Adventure.objects.filter_by(season=rsp.request.season, round=rsp.request.round).get)
        task_list.append(Player.objects.filter("name", Player.objects.IN, player_names).get)
        task_list.append(Group.objects.filter("name", Group.objects.IN, group_names).get)
        threads = [executor.submit(task) for task in task_list]
        results = [future.result() for future in as_completed(threads)]
    players: List[Player] = next((result for result in results if result and isinstance(result[0], Player)), list())
    groups: List[Group] = next((result for result in results if result and isinstance(result[0], Group)), list())
    adventure: Adventure = next((result[0] for result in results if result and isinstance(result[0], Adventure)), None)
    return adventure, players, groups


def update_score(players, groups, winner) -> None:
    if len(groups) == 1:
        groups[0].update_score(played=2, won=1)
    if players[0].name == winner:
        players[0].update_score(played=1, won=1)
        players[1].update_score(played=1, won=0)
        if len(groups) == 2:
            groups[0].update_score(played=1, won=1)
            groups[1].update_score(played=1, won=0)
    else:
        players[0].update_score(played=1, won=0)
        players[1].update_score(played=1, won=1)
        if len(groups) == 2:
            groups[0].update_score(played=1, won=0)
            groups[1].update_score(played=1, won=1)
    return


def update_play_result(request: dict) -> Munch:
    rsp: StandardResponse = StandardResponse(request=request, request_type=RequestType.PLAY_RESULT)
    if rsp.message.error:
        return rsp.dict
    adventure, players, groups = get_adventure_players_groups(rsp)
    if not adventure:
        rsp.message.error = "Unable to find the adventure for this round and season."
        return rsp.dict
    if not adventure.has_player_played_current_match(rsp.request.winner):
        rsp.message.error = rsp.message.error_fields.winner = "Winner is not from the current match."
        return rsp.dict
    if not adventure.has_player_played_current_match(rsp.request.loser):
        rsp.message.error = rsp.message.error_fields.loser = "Loser is not from the current match."
        return rsp.dict
    if len(players) != 2:
        rsp.message.error = "Unable to find Players."
        return rsp.dict
    if not 1 <= len(groups) <= 2:
        rsp.message.error = "Unable to find Groups."
        return rsp.dict
    update_score(players, groups, rsp.request.winner)
    task_list: List[Callable] = [player.save for player in players]
    task_list.extend([group.save for group in groups])
    adventurer, opponent = adventure.next_match_up()
    match = create_match(adventure.season, adventure.round, adventurer, opponent, rsp.request.winner)
    task_list.append(match.create)
    adventure.update_result(rsp.request.winner, rsp.request.acquired)
    task_list.append(adventure.save)
    with ThreadPoolExecutor(max_workers=len(task_list)) as executor:
        threads = [executor.submit(task) for task in task_list]
        temp = [future.result() for future in as_completed(threads)]
    # for task in task_list:
    #     task()
    if not adventure.is_round_over():
        return get_next_match(rsp, adventure)
    if adventure.is_game_over():
        result = "won" if adventure.adventurers_count > 0 else "lost"
        rsp.message.error = f"Game is over. You {result}. Create a new season to play again."
        return rsp.dict
    # Create a new round for the adventure in the same season
    new_round = Adventure.create_next_round(adventure)
    groupwise_players: dict = read_groupwise_players()
    set_opponent(new_round, groupwise_players, groups=list())
    new_round.create()
    return get_next_match(rsp, new_round)


def get_urls(input_player_names: Munch) -> Munch:
    player_urls: Munch = Munch.fromDict({key: [{"name": name, "url": str(), "rank": int()} for name in player_list]
                                         for key, player_list in input_player_names.items()})
    player_names: List[str] = [name for _, player_list in input_player_names.items() for name in player_list]
    with ThreadPoolExecutor() as executor:
        task_list: List[Callable] = [Player.objects.filter_by(name=player_name).first for player_name in player_names]
        threads = [executor.submit(task) for task in task_list]
        players = [future.result() for future in as_completed(threads)]

    def update_player_url(player: Player):
        for key, player_list in player_urls.items():
            for index, _ in enumerate(player_list):
                if player_urls[key][index].name == player.name:
                    player_urls[key][index].url = player.url
                    player_urls[key][index].rank = player.rank
                    return
        raise UpdateUrlError

    for player_record in players:
        update_player_url(player_record)
    return player_urls


def get_next_match(response: StandardResponse = None, adventure: Adventure = None) -> Munch:
    rsp = StandardResponse() if response is None else response
    current_adventure: Adventure = get_latest_adventure() if adventure is None else adventure
    if not current_adventure or current_adventure.is_round_over() or current_adventure.is_game_over():
        rsp.message.error = f"Create a new season to play again."
        return rsp.dict
    adventurer, opponent = current_adventure.next_match_up()
    player_urls = get_urls(Munch(adventurer=[adventurer], opponent=[opponent]))
    data = Munch(season=current_adventure.season, round=current_adventure.round, adventurer=adventurer,
                 adventurer_url=player_urls.adventurer[0].url, adventurer_rank=player_urls.adventurer[0].rank,
                 opponent=opponent, opponent_url=player_urls.opponent[0].url,
                 opponent_rank=player_urls.opponent[0].rank, score=current_adventure.score,
                 size=current_adventure.adventurers_count, opponent_score=current_adventure.opponent_score,
                 match_number=current_adventure.matches_played + 1, total_matches=current_adventure.total_matches)
    rsp.data.append(data)
    rsp.message.success = SuccessMessage.NEXT_MATCH
    return rsp.dict