from typing import List

from flask import render_template, url_for
from werkzeug.utils import redirect

from methods import update_rank_and_save, cookie_login_required
from models import Player, Standing, MarginTag
from s2022 import bp
from s2022.forms import PlayWorldCupForm
from s2022.wc_methods import WorldCupMatch, get_wc_match, SEASON


@bp.route("/s2022/play", methods=["GET", "POST"])
@cookie_login_required
def play_world_cup():
    wc_match: WorldCupMatch = get_wc_match()
    if not wc_match:
        return redirect(url_for("view_wc_standings"))
    form: PlayWorldCupForm = PlayWorldCupForm(wc_match)
    if not form.validate_on_submit():
        return render_template("s2022_play.html", mt=MarginTag, match_player=wc_match, title="Play World Cup",
                               form=form)
    wc_match.update_result(form.winner.data, form.margin.data)
    return redirect(url_for("s2022.play_world_cup"))


@bp.route("/s2022/standings")
@cookie_login_required
def view_wc_standings():
    standings: List[Standing] = Standing.objects.filter_by(season=SEASON).get()
    update_rank_and_save(standings, "wc_rank", "wc_score_for_ranking")
    return render_template("s2022_standings.html", standings=standings, title="World Cup 2022 - Standings")


@bp.route("/s2022/standings/<group_name>")
@cookie_login_required
def view_wc_players_in_a_group(group_name: str):
    players = Player.objects.filter_by(group_name=group_name).get()
    group = Standing.objects.filter_by(group_name=group_name, season=SEASON).first()
    title = f"{group.wc_rank}  {group.group_fullname}   S={group.wc_score}"
    players.sort(key=lambda item: (item.wc_played, item.wc_score), reverse=True)
    return render_template("s2022_players.html", title=title, players=players)
