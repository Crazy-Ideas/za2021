from flask import request
from flask_wtf import FlaskForm
from munch import Munch
from wtforms import HiddenField, ValidationError

from adventure.response import StandardResponse, RequestType
from super_cup.models import CupSeries
from super_cup.play import update_play_result


def evaluate_error(rsp: Munch, field: str):
    if rsp.error_fields[field]:
        raise ValidationError(rsp.error_fields[field])


class PlayForm(FlaskForm):
    winner = HiddenField()

    def __init__(self, series: CupSeries, current_match_player1, current_match_player2, *args, **kwargs):
        super().__init__(*args, **kwargs)
        play_request = Munch(season=series.season, round_number=series.round_number, match_number=series.match_number,
                             winner=current_match_player1, loser=current_match_player2,
                             player_per_group=series.player_per_group)
        self.rsp: Munch = StandardResponse(play_request, RequestType.CUP_PLAY_RESULT).dict
        if request.method == "POST":
            loser: str = current_match_player1 if current_match_player2 == self.winner.data else current_match_player2
            play_request = Munch(season=series.season, round_number=series.round_number, match_number=series.match_number,
                                 winner=self.winner.data, loser=loser, player_per_group=series.player_per_group)
            self.rsp: Munch = update_play_result(play_request)

    def validate_winner(self, _):
        evaluate_error(self.rsp, "winner")

    def validate_loser(self, _):
        evaluate_error(self.rsp, "loser")
