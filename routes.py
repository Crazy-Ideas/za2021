import random
from datetime import datetime
from functools import wraps
from typing import List, Tuple

import pytz
from flask import render_template, redirect, url_for, request, make_response, Response, current_app
from flask_login import login_user, current_user, logout_user
from werkzeug.urls import url_parse

from app import app, CI_SECURITY
from forms import QualificationForm, LoginForm, PlayForm, PlayFriendlyForm
from methods import get_standings_with_url, get_round_groups, get_next_series, get_match_group, update_results, \
    update_rank
from models import Group, Player, User, Standing, Series, Match
from utils import RoundGroup, get_season, MatchGroup, MatchPlayer


def cookie_login_required(route_function):
    @wraps(route_function)
    def decorated_route(*args, **kwargs):
        if current_user.is_authenticated:
            return route_function(*args, **kwargs)
        token: str = request.cookies.get("token")
        user: User = User.objects.filter_by(token=token).first()
        if user and user.token_expiration > datetime.now(tz=pytz.UTC):
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


@app.route("/standings")
@cookie_login_required
def view_standings():
    standings: List[Standing] = get_standings_with_url()
    ranked_standings: List[Tuple[int, Standing]] = [(index + 1, standing) for index, standing in enumerate(standings)]
    return render_template("standings.html", standings=standings, title="Standings", ranked_standings=ranked_standings)


@app.route("/rounds")
@cookie_login_required
def view_rounds():
    series: Series = get_next_series()
    season = get_season()
    week = series.week if series else 8
    return redirect(url_for("rounds_for_week", season=season, week=week))


@app.route("/play", methods=["GET", "POST"])
@cookie_login_required
def play():
    series: Series = get_next_series()
    if not series:
        return render_template("not_found_404.html")
    match_group: MatchGroup = get_match_group(series)
    form = PlayForm(match_group)
    if not form.validate_on_submit():
        return render_template("play.html", form=form, match_group=match_group, series=series, title="Play")
    update_results(series, match_group, form.winner.data)
    return redirect(url_for("play"))


@app.route("/rounds/seasons/<int:season>/weeks/<int:week>")
@cookie_login_required
def rounds_for_week(season: int, week: int):
    if not 1 <= season <= get_season() or not 1 <= week <= 8:
        return render_template("not_found_404.html")
    round_groups: List[RoundGroup] = get_round_groups(season, week)
    return render_template("rounds.html", round_groups=round_groups, current_week=week, title="Fixtures & Results")


@app.route("/series/<series_id>")
@cookie_login_required
def view_series(series_id: str):
    series: Series = Series.get_by_id(series_id)
    if not series or not series.is_setup_done:
        return render_template("not_found_404.html")
    match_group: MatchGroup = get_match_group(series)
    return render_template("series.html", series=series, match_group=match_group, title="Series")


@app.route("/players/ranked")
@cookie_login_required
def ranked_players():
    players = Player.objects.order_by("score", Player.objects.ORDER_DESCENDING).limit(100).get()
    players.sort(key=lambda item: item.score, reverse=True)
    return render_template("players_ranked.html", title="Top 100 Players", players=players)


@app.route("/scored_groups")
@cookie_login_required
def ranked_groups():
    groups = Group.objects.get()
    update_rank(groups)
    groups.sort(key=lambda item: item.score, reverse=True)
    return render_template("groups_ranked.html", title="Groups", players=groups)


@app.route("/scored_groups/<group_name>")
@cookie_login_required
def view_group(group_name: str):
    players = Player.objects.filter_by(group_name=group_name).get()
    players.sort(key=lambda item: item.score, reverse=True)
    return render_template("players_ranked.html", title=group_name, players=players)


@app.route("/play_friendly", methods=["GET", "POST"])
@cookie_login_required
def play_friendly():
    play_from = request.args.get("play_from", "top")
    match: Match = Match.objects.filter_by(winner=str()).first()
    if not match:
        if play_from == "top":
            players = Player.objects.order_by("score", Player.objects.ORDER_DESCENDING).limit(20).get()
        else:
            players = Player.objects.order_by("played").limit(20).get()
        selection: List[Player] = random.sample(players, k=2)
        match = Match(series_type="friendly")
        match.player1 = selection[0].name
        match.player2 = selection[1].name
        match.players = [selection[0].name, selection[1].name]
        match.create()
    else:
        selection: List[Player] = Player.objects.filter("name", Player.objects.IN, [match.player1, match.player2]).get()
    match_player: MatchPlayer = MatchPlayer()
    match_player.match = match
    match_player.player1 = selection[0]
    match_player.player2 = selection[1]
    form = PlayFriendlyForm(match_player)
    if not form.validate_on_submit():
        return render_template("play_friendly.html", form=form, title="Play Friendly", match_player=match_player)
    match_player.match.winner = form.winner.data
    match_player.winner.update_score(played=1, won=1)
    match_player.loser.update_score(played=1, won=0)
    group_names = [match_player.player1.group_name, match_player.player2.group_name]
    if group_names[0] == group_names[1]:
        group: Group = Group.objects.filter_by(name=group_names[0]).first()
        group.update_score(played=2, won=1)
        groups = [group]
    else:
        groups: List[Group] = Group.objects.filter("name", Group.objects.IN, group_names).get()
        winner: Group = next(group for group in groups if group.name == match_player.winner_group_name)
        loser: Group = next(group for group in groups if group.name != winner.name)
        winner.update_score(played=1, won=1)
        loser.update_score(played=1, won=0)
    match_player.match.save()
    Player.objects.save_all([match_player.player1, match_player.player2])
    Group.objects.save_all(groups)
    return redirect(url_for("play_friendly", play_from=play_from))


@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if not form.validate_on_submit():
        return render_template("login.html", form=form)
    token = form.user.get_or_generate_token()
    login_user(user=form.user)
    next_page = request.args.get("next")
    if not next_page or url_parse(next_page).netloc != str():
        next_page = url_for("play_friendly", play_from="top")
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


@app.errorhandler(404)
def not_found(_):
    return render_template("not_found_404.html")
