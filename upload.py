import json
import os
from datetime import datetime
from typing import List

import pytz
# noinspection PyPackageRequirements
from google.cloud.storage import Client
from munch import Munch

from main import generate_url
from models import Player, Group, Match


def load_from_temp():
    start_time: datetime = datetime.now(tz=pytz.UTC)
    last_status = seconds = 0
    bucket = Client().bucket("za-2021")
    players: List[Player] = Player.objects.get()
    groups: List[Group] = Group.objects.get()
    new_players: List[Player] = list()
    updated_groups: List[Group] = list()
    total_files: int = len(os.listdir("temp"))
    for index, filename in enumerate(os.listdir("temp")):
        player_name = filename[:5]
        group_name = filename[:2]
        if any(player.name == player_name for player in players):
            print(f"{player_name} already exists in players. Not uploaded.")
            continue
        group: Group = next((group for group in groups if group.name == group_name), None)
        if not group:
            print(f"{group} does not exists. {player_name} not uploaded")
            continue
        # Upload in cloud storage
        file_path = os.path.join("temp", filename)
        blob = bucket.blob(f"images/{filename}")
        if blob.exists():
            print(f"{filename} already exists in the images folder of cloud storage. Not uploaded.")
        else:
            blob.upload_from_filename(file_path)
        # New Player object
        new_player: Player = Player()
        new_player.name = player_name
        new_player.group_name = group_name
        new_player.qualification_rank = 99999
        # Generate signature
        result = generate_url(new_player)
        if not result:
            print(f"{player_name}: Issue in creating url. Not uploaded.")
            continue
        new_player = result
        # Update new players list and remove file
        os.remove(file_path)
        new_players.append(new_player)
        # Update group & list
        group.player_count += 1
        updated_groups.append(group)
        # Periodic status reporting and filing
        seconds: int = (datetime.now(tz=pytz.UTC) - start_time).seconds
        if seconds % 10 == 0 and seconds != last_status:
            last_status = seconds
            Player.objects.create_all(Player.objects.to_dicts(new_players))
            new_players: List[Player] = list()
            Group.objects.save_all(updated_groups)
            updated_groups: List[Group] = list()
            print(f"{(index + 1) / total_files:.0%} completed in {seconds} seconds.")
    Player.objects.create_all(Player.objects.to_dicts(new_players))
    Group.objects.save_all(updated_groups)
    print(f"{len(new_players)} players uploaded in {seconds} seconds.")


def score_groups():
    players: List[Player] = Player.objects.get()
    groups: List[Group] = Group.objects.get()
    update_groups: List[Group] = list()
    for group in groups:
        group_players: List[Player] = [player for player in players if player.group_name == group.name]
        if not group_players:
            continue
        update_groups.append(group)
        group.player_count = len(group_players)
        played = sum(player.played for player in group_players)
        won = sum(player.won for player in group_players)
        group.update_score(played, won)
        print(f"{group.name}, Played={group.played}, Won = {group.won}, Score = {group.score}")
    Group.objects.save_all(update_groups, workers=100)
    print(f"{len(update_groups)} players updated.")


def score_players():
    with open("temp/player.json") as file:
        json_players = Munch.fromDict(json.load(file))
    players: List[Player] = Player.objects.get()
    matches: List[Match] = Match.objects.get()
    for player in players:
        player.init_score()
        won = sum(len(p.won) for p in json_players if p.name == player.name)
        lost = sum(len(p.lost) for p in json_players if p.name == player.name)
        player.update_score(won + lost, won)
        played = sum(1 for m in matches if player.name in m.players)
        won = sum(1 for m in matches if player.name == m.winner)
        player.update_score(played, won)
    Player.objects.save_all(players, workers=100)
    print("Players updated.")
    return
