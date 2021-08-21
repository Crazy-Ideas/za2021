from typing import List

from flask import render_template, redirect, url_for

from app import app
from models import Group, Player


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/groups")
def view_player_groups():
    groups: List[Group] = Group.objects.get()
    groups = [group for group in groups if group.player_count > 0]
    groups.sort(key=lambda group: group.group_rank / group.player_count)
    return render_template("player_groups.html", title="Player Groups", groups=groups)


@app.route("/groups/<group_id>")
def players_in_a_group(group_id: str):
    group: Group = Group.get_by_id(group_id)
    players: List[Player] = list()
    if group:
        players: List[Player] = Player.objects.filter_by(group_name=group.name).get()
    if not players or not group:
        return redirect(url_for("view_player_groups"))
    players.sort(key=lambda player: player.qualification_rank)
    playingIX = [player for player in players if player.qualified]
    candidates = [player for player in players if not player.qualified]
    return render_template("players_in_a_group.html", title=group.fullname, group=group, playingIX=playingIX,
                           candidates=candidates)
