from datetime import datetime
from functools import wraps
from typing import List

import pytz
from flask import render_template, redirect, url_for, request, make_response, Response, current_app
from flask_login import login_user, current_user, logout_user
from werkzeug.urls import url_parse

from app import app, CI_SECURITY
from forms import QualificationForm, LoginForm
from models import Group, Player, User


def cookie_login_required(route_function):
    @wraps(route_function)
    def decorated_route(*args, **kwargs):
        if current_user.is_authenticated:
            return route_function(*args, **kwargs)
        token: str = request.cookies.get("token")
        user: User = User.objects.filter_by(token=token).first()
        if user and user.token_expiration < datetime.now(tz=pytz.UTC):
            login_user(user=user)
            return route_function(*args, **kwargs)
        return current_app.login_manager.unauthorized()

    return decorated_route


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/groups")
@cookie_login_required
def view_player_groups():
    groups: List[Group] = Group.objects.get()
    groups = [group for group in groups if group.player_count > 0]
    groups.sort(key=lambda group: group.group_rank / group.player_count)
    qualified: int = sum(1 for group in groups if group.qualification_locked)
    pending: int = sum(1 for group in groups if not group.qualification_locked and group.player_count >= 9)
    return render_template("player_groups.html", title="Player Groups", groups=groups, qualified=qualified,
                           pending=pending)


@app.route("/groups/<group_id>", methods=["GET", "POST"])
@cookie_login_required
def players_in_a_group(group_id: str):
    group: Group = Group.get_by_id(group_id)
    players: List[Player] = list()
    if group:
        players: List[Player] = Player.objects.filter_by(group_name=group.name).get()
    if not players or not group:
        return redirect(url_for("view_player_groups"))
    players.sort(key=lambda player: player.qualification_rank)
    playing_ix = [player for player in players if player.qualified]
    candidates = [player for player in players if not player.qualified]
    form = QualificationForm(group, playing_ix, candidates)
    if not form.validate_on_submit():
        return render_template("players_in_a_group.html", title=group.fullname, group=group, playingIX=playing_ix,
                               candidates=candidates, form=form)
    form.group.save()
    if form.updated_players:
        Player.objects.save_all(form.updated_players)
    return redirect(url_for("players_in_a_group", group_id=group_id))


@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if not form.validate_on_submit():
        return render_template("login.html", form=form)
    token = form.user.get_or_generate_token()
    login_user(user=form.user)
    next_page = request.args.get("next")
    if not next_page or url_parse(next_page).netloc != str():
        next_page = url_for("view_player_groups")
    response: Response = make_response(redirect(next_page))
    expiry = form.user.TOKEN_EXPIRY
    response.set_cookie("token", token, max_age=expiry, secure=CI_SECURITY, httponly=True, samesite="Strict")
    return response


@app.route("/logout")
def logout():
    if current_user.is_authenticated:
        current_user.revoke_token()
        logout_user()
    return redirect(url_for("home"))
