import os
import unittest

from munch import Munch

os.environ["FIRESTORE_EMULATOR_HOST"] = "localhost:8080"
# Load emulator with data
# firebase emulators:start --import ./temp/firestore_export

from adventure.response import SuccessMessage
from adventure.play import create_season, get_next_match, update_play_result, get_season
from adventure.models import Adventure, AdventureConfig
from models import Player


class AdventureTestCase(unittest.TestCase):

    def setUp(self) -> None:
        self.size = AdventureConfig.INITIAL_ADVENTURERS_COUNT = 3
        self.rsp = create_season(Munch())

    def tearDown(self) -> None:
        Adventure.objects.delete()

    def test_create_season(self):
        self.assertEqual(SuccessMessage.CREATE_SEASON, self.rsp.message.success)
        adventure: Adventure = Adventure.objects.first()
        self.assertEqual(self.size, adventure.adventurers_count)
        self.assertEqual(166, len(adventure.remaining_opponents))
        self.assertIn(len(adventure.opponents), [self.size - 1, self.size])
        rsp = create_season(Munch())
        self.assertEqual(str(), rsp.message.success)
        self.assertNotEqual(str(), rsp.message.error)

    def test_next_match_up(self):
        self.assertEqual(SuccessMessage.CREATE_SEASON, self.rsp.message.success)
        rsp = get_next_match(Munch())
        self.assertEqual(SuccessMessage.NEXT_MATCH, rsp.message.success)
        self.assertNotEqual(str(), rsp.data.adventurer_url)
        self.assertNotEqual(str(), rsp.data.opponent_url)
        self.assertNotEqual(int(), rsp.data.adventurer_rank)
        self.assertNotEqual(int(), rsp.data.opponent_rank)
        self.assertEqual(0, rsp.data.score)
        self.assertEqual(0, rsp.data.opponent_score)
        self.assertEqual(self.size, rsp.data.size)
        self.assertEqual(self.size, rsp.data.total_matches)
        self.assertEqual(1, rsp.data.match_number)
        adventurer_name = rsp.data.adventurer
        adventurer_played = Player.objects.filter_by(name=adventurer_name).first().played
        request = Munch()
        request.season = rsp.data.season
        request.round = rsp.data.round
        request.winner = rsp.data.adventurer
        request.loser = rsp.data.opponent
        request.acquired = True
        rsp = update_play_result(request)
        self.assertEqual(SuccessMessage.PLAY_RESULT, rsp.message.success)
        rsp = get_next_match(Munch())
        self.assertEqual(1, rsp.data.score)
        self.assertEqual(0, rsp.data.opponent_score)
        self.assertEqual(self.size + 1, rsp.data.size)
        self.assertEqual(self.size, rsp.data.total_matches)
        self.assertEqual(2, rsp.data.match_number)
        self.assertEqual(adventurer_played + 1, Player.objects.filter_by(name=adventurer_name).first().played)
        request = Munch()
        request.season = rsp.data.season
        request.round = rsp.data.round
        request.winner = rsp.data.opponent
        request.loser = rsp.data.adventurer
        request.acquired = False
        rsp = update_play_result(request)
        self.assertEqual(SuccessMessage.PLAY_RESULT, rsp.message.success)
        rsp = get_next_match(Munch())
        self.assertEqual(1, rsp.data.score)
        self.assertEqual(1, rsp.data.opponent_score)
        self.assertEqual(self.size, rsp.data.size)
        self.assertEqual(self.size, rsp.data.total_matches)
        self.assertEqual(3, rsp.data.match_number)

    def test_new_round(self):
        self.assertEqual(SuccessMessage.CREATE_SEASON, self.rsp.message.success)
        rsp = get_next_match(Munch())
        self.assertEqual(SuccessMessage.NEXT_MATCH, rsp.message.success)
        # opponent_fullname = rsp.data.opponent_fullname
        for index in range(self.size):
            rsp = get_next_match(Munch())
            request = Munch()
            request.season = rsp.data.season
            request.round = rsp.data.round
            request.winner = rsp.data.adventurer
            request.loser = rsp.data.opponent
            request.acquired = True
            rsp = update_play_result(request)
            if index < self.size - 1:
                self.assertEqual(SuccessMessage.NEXT_MATCH, rsp.message.success, rsp.message.error)
            else:
                self.assertEqual("New Round Created.", rsp.message.error)
        # self.assertEqual(2, rsp.data.round)
        # self.assertNotEqual(opponent_fullname, rsp.data.opponent_fullname)
        rsp = get_season(Munch(season=1, round=1))
        self.assertEqual(0, len(rsp.data.proximity))

    def test_get_season(self):
        self.assertEqual(SuccessMessage.CREATE_SEASON, self.rsp.message.success)
        rsp = get_season(Munch(season=1, round=1))
        self.assertEqual(self.size, len(rsp.data.adventurers))

if __name__ == '__main__':
    unittest.main()
