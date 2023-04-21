import json
import os
import pickle
from datetime import datetime
from itertools import groupby
from operator import itemgetter
from typing import List

import pytz
# noinspection PyPackageRequirements
from google.cloud.storage import Client
from munch import Munch

from main import generate_url
from models import Player, Group, Match

NEW_PLAYERS: dict = {
    "AR": "Alexandra Daddario",
    "BW": "Bonnie Wright",
    "DF": "Dakota Fanning",
    "EE": "Emily Deschanel",
    "EF": "Elle Fanning",
    "EU": "Erica Durance",
    "EV": "Evanna Lynch",
    "HH": "Helen Hunt",
    "JX": "Jamie Alexander",
    "MW": "Massie Williams",
    "RE": "Rache Weiz",
    "SS": "Sadie Sink",
    "TJ": "Anya-Taylor Joy",
    "ZC": "Zendaya Coleman",
    "ZD": "Zoey Deschanel",
}


def load_from_temp():
    start_time: datetime = datetime.now(tz=pytz.UTC)
    last_status = seconds = 0
    bucket = Client().bucket("za-2021")
    players: List[Player] = Player.objects.get()
    groups: List[Group] = Group.objects.get()
    new_players: List[Player] = list()
    updated_groups: List[Group] = list()
    created_groups: List[Group] = list()
    total_files: int = len(os.listdir("temp"))
    for index, filename in enumerate(os.listdir("temp")):
        if filename[-5:] == ".json":
            continue
        player_name = filename[:5]
        group_name = filename[:2]
        if any(player.name == player_name for player in players):
            print(f"{player_name} already exists in players. Not uploaded.")
            continue
        if not any(group.name == group_name for group in groups) and group_name not in NEW_PLAYERS:
            print(f"{player_name}: Invalid group name. Group not initialized in NEW_PLAYERS.")
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
        group: Group = next((group for group in groups if group.name == group_name), None)
        if group:
            updated_groups.append(group)
        else:
            group: Group = Group()
            group.name = group_name
            group.fullname = NEW_PLAYERS[group_name]
            group.url = new_player.url
            group.url_expiration = new_player.url_expiration
            groups.append(group)
            created_groups.append(group)
        group.player_count += 1
        # Periodic status reporting and filing
        seconds: int = (datetime.now(tz=pytz.UTC) - start_time).seconds
        if seconds % 10 == 0 and seconds != last_status:
            last_status = seconds
            Player.objects.create_all(Player.objects.to_dicts(new_players))
            new_players: List[Player] = list()
            Group.objects.save_all(updated_groups)
            updated_groups: List[Group] = list()
            Group.objects.create_all(Group.objects.to_dicts(created_groups))
            created_groups: List[Group] = list()
            print(f"{(index + 1) / total_files:.0%} completed in {seconds} seconds.")
    Player.objects.create_all(Player.objects.to_dicts(new_players))
    Group.objects.save_all(updated_groups)
    Group.objects.create_all(Group.objects.to_dicts(created_groups))
    print(f"{len(new_players)} players uploaded in {seconds} seconds.")


def _score_groups():
    players: List[Player] = Player.objects.get()
    groups: List[Group] = Group.objects.get()
    update_groups: List[Group] = list()
    for group in groups:
        group_players: List[Player] = [player for player in players if player.group_name == group.name]
        if not group_players:
            continue
        update_groups.append(group)
        group.player_count = len(group_players)
        group.init_score()
        played = sum(player.played for player in group_players)
        won = sum(player.won for player in group_players)
        group.update_score(played, won)
        print(f"{group.name}, Played={group.played}, Won = {group.won}, Score = {group.score}")
    Group.objects.save_all(update_groups, workers=100)
    print(f"{len(update_groups)} players updated.")


def _score_players():
    with open("temp/player.json") as file:
        json_players = Munch.fromDict(json.load(file))
    players: List[Player] = Player.objects.get()
    matches: List[Match] = Match.objects.get()
    matches = [match for match in matches if match.season != 2022 and match.winner]
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


def upload_players():
    start_time: datetime = datetime.now(tz=pytz.UTC)
    last_status = seconds = 0
    players: List[Player] = Player.objects.get()
    groups: List[Group] = Group.objects.get()
    new_players: List[Player] = list()
    total_files: int = len(os.listdir("temp"))
    for index, filename in enumerate(os.listdir("temp")):
        if filename[-5:] == ".json":
            continue
        player_name = filename[:5]
        group_name = filename[:2]
        if any(player.name == player_name for player in players):
            print(f"{player_name} already exists in players. Not uploaded.")
            continue
        if not any(group.name == group_name for group in groups) and group_name not in NEW_PLAYERS:
            print(f"{player_name}: Invalid group name. Group not initialized in NEW_PLAYERS.")
            continue
        # Upload in cloud storage
        file_path = os.path.join("temp", filename)
        # New Player object
        new_player: Player = Player()
        new_player.name = player_name
        new_player.group_name = group_name
        # Update new players list and remove file
        os.remove(file_path)
        new_players.append(new_player)
        # Periodic status reporting and filing
        seconds: int = (datetime.now(tz=pytz.UTC) - start_time).seconds
        if seconds % 10 == 0 and seconds != last_status:
            last_status = seconds
            Player.objects.create_all(Player.objects.to_dicts(new_players))
            new_players: List[Player] = list()
            print(f"{(index + 1) / total_files:.0%} completed in {seconds} seconds.")
    Player.objects.create_all(Player.objects.to_dicts(new_players))
    print(f"{len(new_players)} players uploaded in {seconds} seconds.")


def reset_player_score(player_name: str):
    player: Player = Player.objects.filter_by(name=player_name).first()
    if not player:
        print("Player not found.")
        return
    matches: List[Match] = Match.objects.filter("players", Match.objects.ARRAY_CONTAINS, player_name).get()
    if not matches:
        print("Player has not played any matches.")
        return
    with open("temp/player.json") as file:
        json_players = Munch.fromDict(json.load(file))
    json_matches = [p for p in json_players if p.name == player_name]
    if not json_matches:
        print("New Player. No matches in json file.")
    player.init_score()
    won = sum(len(p.won) for p in json_matches)
    lost = sum(len(p.lost) for p in json_matches)
    player.update_score(won + lost, won)
    played = sum(1 for m in matches if player.name in m.players)
    won = sum(1 for m in matches if player.name == m.winner)
    player.update_score(played, won)
    player.save()
    print("Player score updated.")


def rename_player_matches(old_name: str, new_name: str):
    player = Player.objects.filter_by(name=old_name).first()
    if player:
        print("Player with old name exists. No action done.")
        return
    player = Player.objects.filter_by(name=new_name).first()
    if not player:
        print("Player with new name does not exists. No action done.")
        return
    matches = Match.objects.filter("players", Match.objects.ARRAY_CONTAINS, old_name).get()
    if not matches:
        print("Player with old name has not played any matches. No action done.")
        return
    for match in matches:
        if match.player1 == old_name:
            match.player1 = new_name
        if match.player2 == old_name:
            match.player2 = new_name
        if match.winner == old_name:
            match.winner = new_name
        match.players.remove(old_name)
        match.players.append(new_name)
        print(match)
    Match.objects.save_all(matches)
    print("Matches updated.")
    reset_player_score(new_name)
    return


def update_json():
    players: List[Player] = Player.objects.get()
    player_list: List[str] = [player.name for player in players]
    with open("temp/player_names.json", "w") as file:
        json.dump(player_list, file)
    players.sort(key=lambda item: item.group_name)
    groupwise_players: dict = {group_name: [player.name for player in grouped_players]
                               for group_name, grouped_players in groupby(players, key=lambda item: item.group_name)}
    with open("temp/groupwise_players.json", "w") as file:
        json.dump(groupwise_players, file, indent=2)
    print("Files written.")


def analyze_player_rankings(upto: int = -1, team_count: int = 16, player_count_per_team: int = 5):
    with open("temp/players.pickle", "rb") as file:
        players: List[Player] = pickle.load(file)
    if upto > 0:
        players.sort(key=lambda item: (item.group_name, item.rank))
        groupwise_players = [(group_name, sum(1 if player.rank <= upto else 0 for player in grouped_players))
                             for group_name, grouped_players in groupby(players, key=lambda item: item.group_name)]
        groupwise_players.sort(key=itemgetter(1), reverse=True)
        print(groupwise_players)
        cumulative_team_count = 0
        for player_count, grouped_player_count in groupby(groupwise_players, key=itemgetter(1)):
            team_count = len([g for g in grouped_player_count])
            cumulative_team_count += team_count
            print(f"Player Count: {player_count:2} has {team_count} teams. (Cumulative Count: {cumulative_team_count})")
        return
    players.sort(key=lambda item: item.rank)
    selected_players: List[str] = list()
    expected_count: int = team_count * player_count_per_team
    selected_teams: set = set()
    nominated_teams: dict = dict()
    for player in players:
        if player.group_name in selected_teams:
            continue
        if player.group_name not in nominated_teams:
            nominated_teams[player.group_name] = list()
        nominated_teams[player.group_name].append(player.name)
        if len(nominated_teams[player.group_name]) != player_count_per_team:
            continue
        selected_teams.add(player.group_name)
        selected_players.extend(nominated_teams[player.group_name])
        if len(selected_players) >= expected_count:
            break
    print(selected_players)


def update_players_pickle():
    with open("temp/players.pickle", "wb") as file:
        pickle.dump(Player.objects.get(), file)
