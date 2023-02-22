import os
import unittest

from adventure.response import SuccessMessage

os.environ["FIRESTORE_EMULATOR_HOST"] = "localhost:8080"
# Load emulator with data
# firebase emulators:start --import ./temp/firestore_export

from adventure.play import create_season, get_next_match
from adventure.models import Adventure


class AdventureTestCase(unittest.TestCase):

    def tearDown(self) -> None:
        Adventure.objects.delete()

    def test_create_season(self):
        rsp = create_season()
        self.assertEqual(SuccessMessage.CREATE_SEASON, rsp.message.success)
        adventure: Adventure = Adventure.objects.first()
        self.assertEqual(20, adventure.adventurers_count)
        self.assertEqual(166, len(adventure.remaining_opponents))
        self.assertIn(len(adventure.opponents), [19, 20])

    def test_next_match_up(self):
        rsp = create_season()
        self.assertEqual(SuccessMessage.CREATE_SEASON, rsp.message.success)
        rsp = get_next_match()
        self.assertEqual(SuccessMessage.NEXT_MATCH, rsp.message.success)
        self.assertNotEqual(str(), rsp.data[0].adventurer_url)
        self.assertNotEqual(str(), rsp.data[0].opponent_url)
        self.assertNotEqual(int(), rsp.data[0].adventurer_rank)
        self.assertNotEqual(int(), rsp.data[0].opponent_rank)
        print(rsp.data[0].adventurer_rank)
        print(rsp.data[0].opponent_rank)


if __name__ == '__main__':
    unittest.main()
