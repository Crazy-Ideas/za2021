from flask import render_template, redirect, url_for, flash
from munch import Munch

from methods import cookie_login_required
from super_cup import bp
from super_cup.errors import GroupNotInitialized, SeriesCompleted
from super_cup.forms import PlayForm
from super_cup.models import CupSeries
from super_cup.play import get_season, create_season, get_next_match, get_all_seasons


@bp.route("/super_cup/<int:player_per_group>/seasons/<int:season>/limited/<int:limited>")
@cookie_login_required
def view_season(player_per_group: int, season: int, limited: int):
    rsp = get_season(Munch(season=season, player_per_group=player_per_group, limited=bool(limited)))
    if rsp.message.error:
        flash(rsp.message.error)
        return redirect(url_for("home"))
    return render_template("super_cup_series.html", title="View Season", **rsp.data, no_seasons=False, player_per_group=player_per_group)


@bp.route("/super_cup/<int:player_per_group>/last_season")
@cookie_login_required
def view_last_season(player_per_group: int):
    query = CupSeries.objects.filter_by(player_per_group=player_per_group)
    series: CupSeries = query.order_by("season", CupSeries.objects.ORDER_DESCENDING).first()
    if not series:
        flash("Create a new season.")
        return render_template("super_cup_series.html", title="Create Season", no_seasons=True, player_per_group=player_per_group)
    return redirect(url_for("super_cup.view_season", season=series.season, player_per_group=player_per_group, limited=1))


@bp.route("/super_cup/<int:player_per_group>/seasons")
@cookie_login_required
def seasons_create(player_per_group: int):
    rsp = create_season(Munch(player_per_group=player_per_group))
    if rsp.message.error:
        flash(rsp.message.error)
    return redirect(url_for("super_cup.play", player_per_group=player_per_group))


@bp.route("/super_cup/<int:player_per_group>/play", methods=["GET", "POST"])
@cookie_login_required
def play(player_per_group: int):
    rsp = get_next_match(Munch(player_per_group=player_per_group))
    if rsp.message.error:
        flash(rsp.message.error)
        return redirect(url_for("super_cup.view_last_season", player_per_group=player_per_group))
    try:
        current_match_player1 = rsp.data.series.current_match_player1_name
        current_match_player2 = rsp.data.series.current_match_player2_name
    except GroupNotInitialized:
        flash("Exception. Group not initialized.")
        return redirect(url_for("super_cup.view_last_season", player_per_group=player_per_group))
    except SeriesCompleted:
        flash("Exception. Series completed.")
        return redirect(url_for("super_cup.view_last_season", player_per_group=player_per_group))
    form = PlayForm(rsp.data.series, current_match_player1, current_match_player2)
    if not form.validate_on_submit():
        flash(form.rsp.message.error)
        return render_template("super_cup_play.html", **rsp.data, title="Play Super Cup", form=form,
                               current_match_player1=current_match_player1, current_match_player2=current_match_player2)
    if form.rsp.message.error:
        flash(form.rsp.message.error)
        return redirect(url_for("super_cup.view_last_season", player_per_group=player_per_group))
    return redirect(url_for("super_cup.play", player_per_group=player_per_group))


@bp.route("/super_cup/<int:player_per_group>/all_seasons")
@cookie_login_required
def view_all_seasons(player_per_group: int):
    rsp = get_all_seasons(Munch(player_per_group=player_per_group))
    if rsp.message.error:
        flash(rsp.message.error)
        return redirect(url_for("super_cup.play", player_per_group=player_per_group))
    return render_template("super_cup_seasons.html", title="All Season", **rsp.data)
