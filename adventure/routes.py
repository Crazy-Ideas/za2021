from flask import render_template, flash, redirect, url_for
from munch import Munch

from adventure import bp
from adventure.models import Adventure
from adventure.play import create_season, get_next_match, get_latest_adventure, get_season
from methods import cookie_login_required


@bp.route("/adventure/play")
@cookie_login_required
def play():
    create_season(Munch())
    rsp = get_next_match()
    return render_template("adventure_play.html", **rsp.data[0], title="Play Adventure")


@bp.route("/adventure/last_round")
@cookie_login_required
def view_last_round():
    adventure: Adventure = get_latest_adventure()
    if not adventure:
        flash("Create season to start the game")
        return render_template("not_found_404.html")
    return redirect(url_for("adventure.view_season", season=adventure.season, round_number=adventure.round))


@bp.route("/adventure/seasons/<int:season>/rounds/<int:round_number>")
@cookie_login_required
def view_season(season: int, round_number: int):
    rsp = get_season(Munch(season=season, round=round_number))
    return render_template("adventure_round.html", title="View Season")
