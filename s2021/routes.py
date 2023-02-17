from typing import List, Tuple

from flask import render_template, redirect, url_for

from models import Group, Player, Standing, Series
from routes import cookie_login_required
from s2021 import bp
from s2021.forms import QualificationForm, PlayForm
from s2021.methods import get_standings_with_url, get_next_series, get_round_groups, get_match_group, update_results
from s2021.utils import get_season, RoundGroup, MatchGroup


@bp.route("/s2021/groups")
@cookie_login_required
def view_player_groups():
    groups: List[Group] = Group.objects.get()
    groups = [group for group in groups if group.player_count > 0]
    groups.sort(key=lambda group: group.group_rank / group.player_count)
    qualified: int = sum(1 for group in groups if group.qualification_locked)
    pending: int = sum(1 for group in groups if not group.qualification_locked and group.player_count >= 9)
    return render_template("s2021_player_groups.html", title="Player Groups", groups=groups, qualified=qualified,
                           pending=pending)


@bp.route("/s2021/groups/<group_id>", methods=["GET", "POST"])
@cookie_login_required
def players_in_a_group(group_id: str):
    group: Group = Group.get_by_id(group_id)
    players: List[Player] = list()
    if group:
        players: List[Player] = Player.objects.filter_by(group_name=group.name).get()
    if not players or not group:
        return redirect(url_for("s2021.view_player_groups"))
    players.sort(key=lambda player: player.qualification_rank)
    playing_ix = [player for player in players if player.qualified]
    candidates = [player for player in players if not player.qualified]
    form = QualificationForm(group, playing_ix, candidates)
    if not form.validate_on_submit():
        return render_template("s2021_players_in_a_group.html", title=group.fullname, group=group, playingIX=playing_ix,
                               candidates=candidates, form=form)
    form.group.save()
    if form.updated_players:
        Player.objects.save_all(form.updated_players)
    return redirect(url_for("s2021.players_in_a_group", group_id=group_id))


@bp.route("/s2021/standings")
@cookie_login_required
def view_standings():
    standings: List[Standing] = get_standings_with_url()
    ranked_standings: List[Tuple[int, Standing]] = [(index + 1, standing) for index, standing in enumerate(standings)]
    return render_template("s2021_standings.html", standings=standings, title="Standings",
                           ranked_standings=ranked_standings)


@bp.route("/s2021/rounds")
@cookie_login_required
def view_rounds():
    series: Series = get_next_series()
    season = get_season()
    week = series.week if series else 8
    return redirect(url_for("s2021.rounds_for_week", season=season, week=week))


@bp.route("/s2021/rounds/seasons/<int:season>/weeks/<int:week>")
@cookie_login_required
def rounds_for_week(season: int, week: int):
    if not 1 <= season <= get_season() or not 1 <= week <= 8:
        return render_template("not_found_404.html")
    round_groups: List[RoundGroup] = get_round_groups(season, week)
    return render_template("s2021_rounds.html", round_groups=round_groups, current_week=week,
                           title="Fixtures & Results")


@bp.route("/s2021/series/<series_id>")
@cookie_login_required
def view_series(series_id: str):
    series: Series = Series.get_by_id(series_id)
    if not series or not series.is_setup_done:
        return render_template("not_found_404.html")
    match_group: MatchGroup = get_match_group(series)
    return render_template("s2021_series.html", series=series, match_group=match_group, title="Series")


@bp.route("/s2021/play", methods=["GET", "POST"])
@cookie_login_required
def play():
    series: Series = get_next_series()
    if not series:
        return render_template("not_found_404.html")
    match_group: MatchGroup = get_match_group(series)
    form = PlayForm(match_group)
    if not form.validate_on_submit():
        return render_template("s2021_play.html", form=form, match_group=match_group, series=series, title="Play")
    update_results(series, match_group, form.winner.data)
    return redirect(url_for("s2021.play"))
