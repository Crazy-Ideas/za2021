from typing import List

from flask import render_template

from app import app
from models import Group


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/groups")
def view_player_groups():
    groups: List[Group] = Group.objects.get()
    groups = [group for group in groups if group.group_rank > 0]
    groups.sort(key=lambda group: group.group_rank / group.player_count)
    return render_template("player_groups.html", title="Player Groups", groups=groups)
