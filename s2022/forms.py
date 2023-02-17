from flask_wtf import FlaskForm
from wtforms import HiddenField, ValidationError

from models import MarginTag
from s2022.wc_methods import WorldCupMatch


class PlayWorldCupForm(FlaskForm):
    winner = HiddenField()
    margin = HiddenField()
    valid_margins = {MarginTag.HIGH, MarginTag.LOW, MarginTag.MEDIUM}

    def __init__(self, match: WorldCupMatch, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.match_player = match

    def validate_winner(self, winner: HiddenField):
        if winner.data not in self.match_player.match.players:
            raise ValidationError("Invalid winner")

    def validate_margin(self, margin: HiddenField):
        if margin.data not in self.valid_margins:
            raise ValidationError("Invalid Margin")
