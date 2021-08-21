import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from datetime import timedelta, datetime
from typing import List

import pytz

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "google-cloud.json"

from google.cloud.storage import Client
from models import Player, Group


def generate_url(player: Player) -> Player:
    bucket = Client().bucket("za-2021")
    possible_filenames: List[str] = [f"images/{player.name}.{ext}" for ext in ("jpg", "jpeg", "png")]
    filename: str = next((filename for filename in possible_filenames if bucket.blob(filename).exists()), str())
    if not filename:
        print(f"{player} Storage Image does not exists.")
        return player
    expiration: timedelta = timedelta(days=7)
    player_with_url: Player = deepcopy(player)
    player_with_url.url = bucket.blob(filename).generate_signed_url(version="v4", expiration=expiration)
    player_with_url.url_expiration = datetime.now(tz=pytz.UTC) + expiration
    return player_with_url


# noinspection PyUnusedLocal
def update_url(*args, **kwargs):
    max_workers: int = 100
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
            updated_players.append(future.result())
            result_count: int = len(updated_players)
            if result_count in {1, player_count} or result_count % max_workers == 0:
                print(f"{result_count} of {player_count} url generated.")
    Player.objects.save_all(updated_players)
    groups: List[Group] = Group.objects.get()
    for group in groups:
        if group.player_name:
            player: Player = next(player for player in updated_players if player.name == group.player_name)
        else:
            player: Player = next((player for player in updated_players if player.group_name == group.name), None)
            if not player:
                continue
            group.player_name = player.name
        group.url = player.url
        group.url_expiration = player.url_expiration
    Group.objects.save_all(groups)
    seconds: int = (datetime.now(tz=pytz.UTC) - start_time).seconds
    print(f"All urls updated in {seconds} seconds.")
