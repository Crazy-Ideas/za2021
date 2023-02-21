import json
from random import sample, shuffle
from typing import List

from munch import Munch

from adventure.models import Adventure
from adventure.response import StandardResponse, RequestType
from models import Group, Player


def read_groupwise_players() -> dict:
    with open("temp/groupwise_players.json") as file:
        groupwise_players = json.load(file)
    return groupwise_players


def get_latest_adventure() -> Adventure:
    query = Adventure.objects.order_by("season", Adventure.objects.ORDER_DESCENDING)
    current_adventure: Adventure = query.order_by("round", Adventure.objects.ORDER_DESCENDING).first()
    return current_adventure


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
    opponent_group_name: str = new_adventure.get_next_opponent()
    opponent_group: Group = next(group for group in groups if group.name == opponent_group_name)
    new_adventure.set_opponent(opponent_group, groupwise_players[opponent_group_name])
    new_adventure.create()
    rsp.message.success = "New season created successfully."
    return rsp.dict


def update_play_result(request: dict) -> Munch:
    rsp: StandardResponse = StandardResponse(request=request, request_type=RequestType.PLAY_RESULT)
    if rsp.message.error:
        return rsp.dict
    adventure: Adventure = Adventure.objects.filter_by(season=rsp.request.season, round=rsp.request.round).first()
    if not adventure:
        rsp.message.error = "Unable to find the adventure for this round and season."
        return rsp.dict
    if not adventure.is_winner_valid(rsp.request.winner):
        rsp.message.error = rsp.message.error_fields.winner = "Winner is not from the current match."
        return rsp.dict
    adventure.update_result(rsp.request.winner, rsp.request.acquired)
    adventure.save()
    if not adventure.is_round_over():
        return get_next_match(rsp, adventure)
    if adventure.is_game_over():
        result = "won" if adventure.adventurers_count > 0 else "lost"
        rsp.message.error = f"Game is over. You {result}. Create a new season to play again."
        return rsp.dict
    # Create a new round for the adventure in the same season
    new_round = Adventure.create_next_round(adventure)
    return get_next_match(rsp, new_round)


def get_next_match(response: StandardResponse = None, adventure: Adventure = None) -> Munch:
    rsp = StandardResponse() if response is None else response
    current_adventure: Adventure = get_latest_adventure() if adventure is None else adventure
    if not current_adventure or current_adventure.is_round_over() or current_adventure.is_game_over():
        rsp.message.error = f"Create a new season to play again."
        return rsp.dict
    adventurer, opponent = current_adventure.next_match_up()
    players: List[Player] = Player.objects.filter("name", Player.objects.IN, [adventurer, opponent]).get()
    adventurer_url = players[0].url if players[0].name == adventurer else players[1].url
    opponent_url = players[0].url if players[0].name == opponent else players[1].url
    data = Munch(season=current_adventure.season, round=current_adventure.round, adventurer=adventurer,
                 adventurer_url=adventurer_url, opponent=opponent, opponent_url=opponent_url,
                 score=current_adventure.score, size=current_adventure.adventurers)
    rsp.data.append(data)
    rsp.message.success = "Next match up ready."
    return rsp.dict
