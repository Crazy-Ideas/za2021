import json
import random
from datetime import datetime
from typing import List, Callable

import pytz
from flask import render_template, redirect, url_for, request, make_response, Response, flash
from flask_login import login_user, current_user, logout_user
from werkzeug.urls import url_parse

from app import app, CI_SECURITY
from forms import LoginForm, PlayFriendlyForm
from methods import update_rank_and_save, MatchPlayer, cookie_login_required, perform_io_task
from models import Group, Player, Match


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/players/ranked")
@cookie_login_required
def ranked_players():
    players = Player.objects.order_by("score", Player.objects.ORDER_DESCENDING).limit(100).get()
    update_rank_and_save(players)
    return render_template("players_ranked.html", title="Top 100 Players", players=players, multi_groups=True)


@app.route("/scored_groups")
@cookie_login_required
def ranked_groups():
    groups = Group.objects.get()
    update_rank_and_save(groups)
    return render_template("groups_ranked.html", title="Groups", groups=groups)


@app.route("/scored_groups/<group_name>")
@cookie_login_required
def view_group(group_name: str):
    players = Player.objects.filter_by(group_name=group_name).get()
    group = Group.objects.filter_by(name=group_name).first()
    players.sort(key=lambda item: item.score, reverse=True)
    return render_template("players_ranked.html", title=group_name, players=players, group=group)


@app.route("/play/friendly", methods=["GET", "POST"])
@cookie_login_required
def play_friendly():
    play_from = request.args.get("play_from", "top")
    match: Match = Match.objects.filter_by(type="friendly", winner=str()).first()
    if not match:
        if play_from == "top":
            players = Player.objects.order_by("score", Player.objects.ORDER_DESCENDING).limit(100).get()
            selection: List[Player] = random.sample(players, k=2)
        elif play_from == "bottom":
            players = Player.objects.order_by("played").limit(20).get()
            selection: List[Player] = random.sample(players, k=2)
        elif play_from == "random":
            with open("temp/player_names.json") as file:
                player_names: List[str] = json.load(file)
            select_names: List[str] = random.sample(player_names, k=2)
            selection: List[Player] = Player.objects.filter("name", Player.objects.IN, select_names).get()
        elif len(play_from) == 7 and play_from[:5] == "group":
            group_name = play_from[-2:].upper()
            players = Player.objects.filter_by(group_name=group_name).get()
            selection: List[Player] = random.sample(players, k=2)
        else:
            flash("Invalid play option. Defaulting to playing from top.")
            return redirect(url_for("play_friendly", play_from="top"))
        match = Match(series_type="friendly")
        match.player1 = selection[0].name
        match.player2 = selection[1].name
        match.players = [selection[0].name, selection[1].name]
        match.create()
    else:
        selection: List[Player] = Player.objects.filter("name", Player.objects.IN, [match.player1, match.player2]).get()
    match_player: MatchPlayer = MatchPlayer()
    match_player.match = match
    match_player.player1 = next(s for s in selection if s.name == match.player1)
    match_player.player2 = next(s for s in selection if s.name == match.player2)
    form = PlayFriendlyForm(match_player)
    if not form.validate_on_submit():
        return render_template("play_friendly.html", form=form, title="Play Friendly", match_player=match_player)
    match_player.match.winner = form.winner.data
    match_player.match.date_played = datetime.now(tz=pytz.UTC)
    match_player.winner.update_score(played=1, won=1)
    match_player.loser.update_score(played=1, won=0)
    update_tasks: List[Callable] = [match_player.winner.save, match_player.loser.save]
    group_names = [match_player.player1.group_name, match_player.player2.group_name]
    if group_names[0] == group_names[1]:
        group: Group = Group.objects.filter_by(name=group_names[0]).first()
        group.update_score(played=2, won=1)
        update_tasks.append(group.save)
    else:
        groups: List[Group] = Group.objects.filter("name", Group.objects.IN, group_names).get()
        winner: Group = next(group for group in groups if group.name == match_player.winner_group_name)
        loser: Group = next(group for group in groups if group.name != winner.name)
        winner.update_score(played=1, won=1)
        loser.update_score(played=1, won=0)
        update_tasks.extend([winner.save, loser.save])
    update_tasks.append(match_player.match.save)
    perform_io_task(update_tasks)
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
        next_page = url_for("adventure.view_last_round")
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
