from munch import Munch

from adventure.models import Adventure
from adventure.response import StandardResponse, RequestType


def create_season() -> Munch:
    rsp: StandardResponse = StandardResponse(request=Munch(), request_type=RequestType.CREATE_SEASON)
    query = Adventure.objects.order_by("season", Adventure.objects.ORDER_DESCENDING)
    current_adventure: Adventure = query.order_by("round", Adventure.objects.ORDER_DESCENDING).first()
    season: int = current_adventure.season if current_adventure else 0
    season_check_error: str = "Complete previous season before starting a new season."
    if current_adventure:
        if not current_adventure.is_round_over():
            rsp.message.error = season_check_error
            return rsp.dict
        if not current_adventure.get_next_group():
            rsp.message.error = season_check_error
            return rsp.dict
    new_adventure = Adventure()
    new_adventure.season = season + 1
    new_adventure.round = 1

    return rsp.dict
