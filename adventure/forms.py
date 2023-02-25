from flask import request
from flask_wtf import FlaskForm
from munch import Munch
from wtforms import HiddenField, ValidationError

from adventure.play import update_play_result
from adventure.response import StandardResponse, RequestType


def evaluate_error(rsp: Munch, field: str):
    if rsp.error_fields[field]:
        raise ValidationError(rsp.error_fields[field])


class PlayForm(FlaskForm):
    winner = HiddenField()
    acquired = HiddenField()

    def __init__(self, season: int, round_number: int, adventurer: str, opponent: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rsp: Munch = StandardResponse(Munch(), RequestType.PLAY_RESULT).dict
        if request.method == "POST":
            loser: str = adventurer if opponent == self.winner.data else opponent
            acquired: bool = self.acquired.data.lower() == "yes"
            play_request = Munch(season=season, round=round_number, winner=self.winner.data, loser=loser, acquired=acquired)
            self.rsp: Munch = update_play_result(play_request)

    def validate_winner(self, _):
        evaluate_error(self.rsp, "winner")

    def validate_loser(self, _):
        evaluate_error(self.rsp, "loser")
