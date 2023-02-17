from flask_wtf import FlaskForm
from wtforms import HiddenField, ValidationError, StringField, PasswordField, SubmitField

from methods import MatchPlayer
from models import User


class PlayFriendlyForm(FlaskForm):
    winner = HiddenField()
    loser = HiddenField()

    def __init__(self, match: MatchPlayer, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.match_player = match

    def validate_winner(self, winner: HiddenField):
        if winner.data not in self.match_player.match.players:
            raise ValidationError("Invalid winner")

    def validate_loser(self, loser: HiddenField):
        if loser.data not in self.match_player.match.players:
            raise ValidationError("Invalid loser")


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
        self.user = user
        return
