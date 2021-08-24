import os
from typing import List

from google.cloud.storage import Client

from main import generate_url
from models import Player, Group


def load_from_temp():
    bucket = Client().bucket("za-2021")
    players: List[Player] = Player.objects.get()
    groups: List[Group] = Group.objects.get()
    new_players: List[Player] = list()
    updated_groups: List[Group] = list()
    for filename in os.listdir("temp"):
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
            continue
        blob.upload_from_filename(file_path)
        os.remove(file_path)
        # Update player and group.
        new_player: Player = Player()
        new_player.name = player_name
        new_player.group_name = group_name
        new_player.qualification_rank = 99999
        group.player_count += 1
        # Generate signature & update list
        new_player = generate_url(new_player)
        new_players.append(new_player)
        updated_groups.append(group)
        print(f"Player {player_name} uploaded.")
    Player.objects.create_all(Player.objects.to_dicts(new_players))
    Group.objects.save_all(updated_groups)
    print(f"{len(new_players)} players uploaded.")
