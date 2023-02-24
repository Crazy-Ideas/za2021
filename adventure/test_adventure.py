import os
import unittest

from munch import Munch

os.environ["FIRESTORE_EMULATOR_HOST"] = "localhost:8080"
# Load emulator with data
# firebase emulators:start --import ./temp/firestore_export

from adventure.response import SuccessMessage
from adventure.play import create_season, get_next_match, update_play_result
from adventure.models import Adventure, AdventureConfig
from models import Player


class AdventureTestCase(unittest.TestCase):

    def setUp(self) -> None:
        self.size = AdventureConfig.INITIAL_ADVENTURERS_COUNT = 3

    def tearDown(self) -> None:
        Adventure.objects.delete()

    def test_create_season(self):
        rsp = create_season()
        self.assertEqual(SuccessMessage.CREATE_SEASON, rsp.message.success)
        adventure: Adventure = Adventure.objects.first()
        self.assertEqual(self.size, adventure.adventurers_count)
        self.assertEqual(166, len(adventure.remaining_opponents))
        self.assertIn(len(adventure.opponents), [self.size - 1, self.size])
        rsp = create_season()
        self.assertEqual(str(), rsp.message.success)
        self.assertNotEqual(str(), rsp.message.error)

    def test_next_match_up(self):
        rsp = create_season()
        self.assertEqual(SuccessMessage.CREATE_SEASON, rsp.message.success)
        rsp = get_next_match()
        self.assertEqual(SuccessMessage.NEXT_MATCH, rsp.message.success)
        self.assertNotEqual(str(), rsp.data[0].adventurer_url)
        self.assertNotEqual(str(), rsp.data[0].opponent_url)
        self.assertNotEqual(int(), rsp.data[0].adventurer_rank)
        self.assertNotEqual(int(), rsp.data[0].opponent_rank)
        self.assertEqual(0, rsp.data[0].score)
        self.assertEqual(0, rsp.data[0].opponent_score)
        self.assertEqual(self.size, rsp.data[0].size)
        self.assertEqual(self.size, rsp.data[0].total_matches)
        self.assertEqual(1, rsp.data[0].match_number)
        adventurer_name = rsp.data[0].adventurer
        adventurer_played = Player.objects.filter_by(name=adventurer_name).first().played
        request = Munch()
        request.season = rsp.data[0].season
        request.round = rsp.data[0].round
        request.winner = rsp.data[0].adventurer
        request.loser = rsp.data[0].opponent
        request.acquired = True
        rsp = update_play_result(request)
        self.assertEqual(SuccessMessage.PLAY_RESULT, rsp.message.success)
        self.assertEqual(1, rsp.data[0].score)
        self.assertEqual(0, rsp.data[0].opponent_score)
        self.assertEqual(self.size + 1, rsp.data[0].size)
        self.assertEqual(self.size, rsp.data[0].total_matches)
        self.assertEqual(2, rsp.data[0].match_number)
        self.assertEqual(adventurer_played + 1, Player.objects.filter_by(name=adventurer_name).first().played)
        request = Munch()
        request.season = rsp.data[0].season
        request.round = rsp.data[0].round
        request.winner = rsp.data[0].opponent
        request.loser = rsp.data[0].adventurer
        request.acquired = False
        rsp = update_play_result(request)
        self.assertEqual(SuccessMessage.PLAY_RESULT, rsp.message.success)
        self.assertEqual(1, rsp.data[0].score)
        self.assertEqual(1, rsp.data[0].opponent_score)
        self.assertEqual(self.size, rsp.data[0].size)
        self.assertEqual(self.size, rsp.data[0].total_matches)
        self.assertEqual(3, rsp.data[0].match_number)

    def test_new_round(self):
        rsp = create_season()
        adventure: Adventure = Adventure.objects.first()
        print(adventure.adventurers)
        print(adventure.opponents)
        self.assertEqual(SuccessMessage.CREATE_SEASON, rsp.message.success)
        rsp = get_next_match()
        self.assertEqual(SuccessMessage.NEXT_MATCH, rsp.message.success)
        opponent_fullname = rsp.data[0].opponent_fullname
        for _ in range(self.size):
            request = Munch()
            request.season = rsp.data[0].season
            request.round = rsp.data[0].round
            request.winner = rsp.data[0].adventurer
            request.loser = rsp.data[0].opponent
            request.acquired = True
            rsp = update_play_result(request)
            self.assertEqual(SuccessMessage.NEXT_MATCH, rsp.message.success)
        self.assertEqual(2, rsp.data[0].round)
        self.assertNotEqual(opponent_fullname, rsp.data[0].opponent_fullname)
        adventure: Adventure = Adventure.objects.filter_by(round=2).first()
        print(adventure.adventurers)
        print(adventure.opponents)

if __name__ == '__main__':
    unittest.main()
