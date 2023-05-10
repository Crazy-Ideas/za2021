from flask import render_template, redirect, url_for, flash
from munch import Munch

from adventure import bp
from adventure.forms import PlayForm
from adventure.models import Adventure
from adventure.play import create_season, get_next_match, get_latest_adventure, get_season
from methods import cookie_login_required


@bp.route("/adventure/play", methods=["GET", "POST"])
@cookie_login_required
def play():
    rsp = get_next_match(Munch())
    if rsp.message.error:
        flash(rsp.message.error)
        return redirect(url_for("adventure.view_last_round"))
    form = PlayForm(rsp.data.season, rsp.data.round, rsp.data.adventurer, rsp.data.opponent)
    if not form.validate_on_submit():
        return render_template("adventure_play.html", **rsp.data, title="Play Adventure", form=form)
    if form.rsp.message.error:
        flash(form.rsp.message.error)
        return redirect(url_for("adventure.view_last_round"))
    return redirect(url_for("adventure.play"))


@bp.route("/adventure/last_round")
@cookie_login_required
def view_last_round():
    adventure: Adventure = get_latest_adventure()
    if not adventure:
        flash("No season created yet. Create new season.")
        return render_template("adventure_round.html", title="No Season", no_season=True)
    return redirect(url_for("adventure.view_season", season=adventure.season, round_number=adventure.round))


@bp.route("/adventure/seasons/<int:season>/rounds/<int:round_number>")
@cookie_login_required
def view_season(season: int, round_number: int):
    rsp = get_season(Munch(season=season, round=round_number))
    if rsp.message.error:
        return redirect(url_for("adventure.view_last_round"))
    return render_template("adventure_round.html", title="View Season", no_season=False, **rsp.data)


@bp.route("/adventure/seasons")
@cookie_login_required
def seasons_create():
    create_season(Munch())
    return redirect(url_for("adventure.view_last_round"))
