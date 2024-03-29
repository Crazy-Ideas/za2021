from typing import List

from flask_wtf import FlaskForm
from wtforms import BooleanField, HiddenField, ValidationError

from models import Group, Player
from s2021.utils import MatchGroup


class QualificationForm(FlaskForm):
    locked = BooleanField()
    lock_status_changed = BooleanField()
    added_player_id = HiddenField()
    removed_player_id = HiddenField()
    star_player_id = HiddenField()

    def __init__(self, group: Group, playing_ix: List[Player], candidates: List[Player], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.group: Group = group
        self.playing_ix: List[Player] = playing_ix
        self.candidates: List[Player] = candidates
        self.updated_players: List[Player] = list()

    def validate_locked(self, locked: BooleanField):
        if not self.lock_status_changed.data:
            return
        if not locked.data:
            self.group.qualification_locked = False
            return
        if self.group.qualified_player_count != 9:
            raise ValidationError(f"Select exactly 9 players.")
        self.group.qualification_locked = True
        return

    def validate_added_player_id(self, added_player_id: HiddenField):
        if not added_player_id.data:
            return
        player = next((player for player in self.candidates if player.id == added_player_id.data), None)
        if not player or player.qualified is True:
            raise ValidationError("Not a valid player to add.")
        player.qualified = True
        self.updated_players.append(player)
        self.group.qualified_player_count += 1
        return

    def validate_removed_player_id(self, remove_player_id: HiddenField):
        if not remove_player_id.data:
            return
        player = next((player for player in self.playing_ix if player.id == remove_player_id.data), None)
        if not player or player.qualified is False:
            raise ValidationError("Not a valid player to remove.")
        player.qualified = False
        self.updated_players.append(player)
        self.group.qualified_player_count -= 1
        return

    def validate_star_player_id(self, star_player_id: HiddenField):
        if not star_player_id.data:
            return
        player = next((player for player in self.playing_ix if player.id == star_player_id.data), None)
        if not player or player.star_player is True:
            raise ValidationError("Not a valid player to make a star player.")
        old_star_player = next((player for player in self.playing_ix if player.star_player), None)
        player.star_player = True
        self.group.player_name = player.name
        self.group.url = player.url
        self.group.url_expiration = player.url_expiration
        self.updated_players.append(player)
        if not old_star_player:
            return
        old_star_player.star_player = False
        self.updated_players.append(old_star_player)
        return


class PlayForm(FlaskForm):
    winner = HiddenField()
    loser = HiddenField()

    def __init__(self, match_group: MatchGroup, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.match_group = match_group

    def validate_winner(self, winner: HiddenField):
        if winner.data not in self.match_group.current_match.match.players:
            raise ValidationError("Invalid winner")

    def validate_loser(self, loser: HiddenField):
        if loser.data not in self.match_group.current_match.match.players:
            raise ValidationError("Invalid loser")
