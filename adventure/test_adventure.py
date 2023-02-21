import os
import unittest

os.environ["FIRESTORE_EMULATOR_HOST"] = "localhost:8080"

from adventure.play import create_season
from adventure.models import Adventure


class AdventureTestCase(unittest.TestCase):
    def test_create_season(self):
        rsp = create_season()
        self.assertEqual("New season created successfully.", rsp.message.success)
        adventure: Adventure = Adventure.objects.first()
        self.assertEqual(20, adventure.adventurers_count)
        self.assertEqual(166, len(adventure.remaining_opponents))


if __name__ == '__main__':
    unittest.main()
