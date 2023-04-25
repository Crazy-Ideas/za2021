from flask import render_template, redirect, url_for, flash
from munch import Munch

from methods import cookie_login_required
from super_cup import bp
from super_cup.forms import PlayForm
from super_cup.models import CupSeries
from super_cup.play import get_season, create_season, get_next_match


@bp.route("/super_cup/seasons/<int:season>")
@cookie_login_required
def view_season(season: int):
    rsp = get_season(Munch(season=season))
    if rsp.message.error:
        flash(rsp.message.error)
        return redirect(url_for("super_cup.view_last_season"))
    return render_template("super_cup_series.html", title="View Season", **rsp.data, no_seasons=False)


@bp.route("/super_cup/last_season")
@cookie_login_required
def view_last_season():
    series: CupSeries = CupSeries.objects.order_by("season", CupSeries.objects.ORDER_DESCENDING).first()
    if not series:
        flash("Create a new season.")
        return render_template("super_cup_series.html", title="Create Season", no_seasons=True)
    return redirect(url_for("super_cup.view_season", season=series.season))


@bp.route("/super_cup/seasons")
@cookie_login_required
def seasons_create():
    rsp = create_season(Munch())
    if rsp.message.error:
        flash(rsp.message.error)
    return redirect(url_for("super_cup.view_last_season"))


@bp.route("/super_cup/play", methods=["GET", "POST"])
@cookie_login_required
def play():
    rsp = get_next_match(Munch())
    if rsp.message.error:
        flash(rsp.message.error)
        return redirect(url_for("super_cup.view_last_season"))
    form = PlayForm(rsp.data.series)
    if not form.validate_on_submit():
        flash(form.rsp.message.error)
        return render_template("super_cup_play.html", **rsp.data, title="Play Super Cup", form=form)
    if form.rsp.message.error:
        flash(form.rsp.message.error)
        return redirect(url_for("super_cup.view_last_season"))
    return redirect(url_for("super_cup.play"))
