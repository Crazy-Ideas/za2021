from flask import render_template, redirect, url_for
from munch import Munch

from methods import cookie_login_required
from super_cup import bp
from super_cup.models import CupSeries
from super_cup.play import get_latest_series, get_season, create_season


@bp.route("/super_cup/seasons/<int:season>")
@cookie_login_required
def view_season(season: int):
    rsp = get_season(Munch(season=season))
    if rsp.message.error:
        return redirect(url_for("super_cup.view_last_season"))
    return render_template("super_cup_series.html", title="View Season", **rsp.data)


@bp.route("/super_cup/last_season")
@cookie_login_required
def view_last_season():
    series: CupSeries = get_latest_series()
    if not series:
        return render_template("not_found_404.html")
    return redirect(url_for("super_cup.view_season", season=series.season))


@bp.route("/super_cup/seasons")
@cookie_login_required
def seasons_create():
    create_season(Munch())
    return redirect(url_for("super_cup.view_last_series"))
