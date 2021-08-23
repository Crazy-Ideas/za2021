from typing import List, Optional

from flask_wtf import FlaskForm
from wtforms import BooleanField, HiddenField, ValidationError, StringField, PasswordField, SubmitField

from models import Player, Group, User


class QualificationForm(FlaskForm):
    locked = BooleanField()
    added_player_id = HiddenField()
    removed_player_id = HiddenField()

    def __init__(self, group: Group, playing_ix: List[Player], candidates: List[Player], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.group: Group = group
        self.playing_ix: List[Player] = playing_ix
        self.candidates: List[Player] = candidates
        self.player_to_update: Optional[Player] = None

    def validate_locked(self, locked: BooleanField):
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
        self.player_to_update = next((player for player in self.candidates if player.id == added_player_id.data), None)
        if not self.player_to_update or self.player_to_update.qualified is True:
            raise ValidationError("Not a valid player to add.")
        self.player_to_update.qualified = True
        self.group.qualified_player_count += 1
        return

    def validate_removed_player_id(self, remove_player_id: HiddenField):
        if not remove_player_id.data:
            return
        self.player_to_update = next((player for player in self.playing_ix if player.id == remove_player_id.data), None)
        if not self.player_to_update or self.player_to_update.qualified is False:
            raise ValidationError("Not a valid player to remove.")
        self.player_to_update.qualified = False
        self.group.qualified_player_count -= 1
        return


class LoginForm(FlaskForm):
    email = StringField("Email")
    password = PasswordField("Password")
    submit = SubmitField("Submit")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user: User = User()

    def validate_email(self, email: StringField):
        if not email.data:
            raise ValidationError("Email is required.")
        self.user.email = email.data

    def validate_password(self, password: PasswordField):
        if not password.data:
            raise ValidationError("Password is required.")
        user: User = User.objects.filter_by(email=self.email.data).first()
        if not user or not user.is_password_valid(password.data):
            raise ValidationError("Invalid email or password.")
        return