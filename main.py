import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from datetime import timedelta, datetime
from typing import List, Optional

import pytz

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "google-cloud.json"

# noinspection PyPackageRequirements
from google.cloud.storage import Client
from models import Player, Group, Standing
from methods import update_rank


def generate_url(player: Player) -> Optional[Player]:
    bucket = Client().bucket("za-2021")
    possible_filenames: List[str] = [f"images/{player.name}.{ext}" for ext in ("jpg", "jpeg", "png", "webp")]
    filename: str = next((filename for filename in possible_filenames if bucket.blob(filename).exists()), str())
    if not filename:
        print(f"{player} Storage Image does not exists.")
        return None
    expiration: timedelta = timedelta(days=7)
    player_with_url: Player = deepcopy(player)
    player_with_url.url = bucket.blob(filename).generate_signed_url(version="v4", expiration=expiration)
    player_with_url.url_expiration = datetime.now(tz=pytz.UTC) + expiration
    return player_with_url


# noinspection PyUnusedLocal
def update_url(*args, **kwargs):
    max_workers: int = 10
    print("Update url process started")
    start_time = datetime.now(tz=pytz.UTC)
    players: List[Player] = Player.objects.get()
    player_count: int = len(players)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        threads: set = set()
        for player in players:
            threads.add(executor.submit(generate_url, player))
            thread_count: int = len(threads)
            if thread_count in {1, player_count} or thread_count % max_workers == 0:
                print(f"{thread_count} of {player_count} threads created.")
        updated_players: List[Player] = list()
        for future in as_completed(threads):
            if future.result():
                updated_players.append(future.result())
            result_count: int = len(updated_players)
            if result_count in {1, player_count} or result_count % max_workers == 0:
                print(f"{result_count} of {player_count} url generated.")
    update_rank(updated_players)
    update_rank(updated_players, "wc_rank", "wc_score")
    groups: List[Group] = Group.objects.get()
    standings: List[Standing] = Standing.objects.filter_by(season=2022).get()
    for group in groups:
        players_in_this_group: List[Player] = [player for player in updated_players if player.group_name == group.name]
        group.player_count = len(players_in_this_group)
        top_player: Player = max(players_in_this_group, key=lambda item: item.score)
        if not top_player:
            continue
        for player in players_in_this_group:
            player.star_player = False
        top_player.star_player = True
        group.player_name = top_player.name
        group.url = top_player.url
        group.url_expiration = top_player.url_expiration
        standing = next(s for s in standings if s.group_name == group.name)
        standing.player_name = top_player.name
        standing.url = top_player.url
        standing.url_expiration = top_player.url_expiration
    update_rank(groups)
    Player.objects.save_all(updated_players)
    Group.objects.save_all(groups)
    Standing.objects.save_all(standings)
    seconds: int = (datetime.now(tz=pytz.UTC) - start_time).seconds
    print(f"All urls updated in {seconds} seconds.")
