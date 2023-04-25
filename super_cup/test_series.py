import os
import unittest

from munch import Munch

from adventure.response import SuccessMessage
from super_cup.models import CupSeries
from super_cup.play import create_season

os.environ["FIRESTORE_EMULATOR_HOST"] = "localhost:8080"


# Load emulator with data
# firebase emulators:start --import ./temp/firestore_export

class SuperCupTestCase(unittest.TestCase):

    def setUp(self) -> None:
        CupSeries.objects.delete()
        self.rsp = create_season(Munch())

    def test_create_season(self):
        self.assertEqual(SuccessMessage.CREATE_SEASON, self.rsp.message.success)
        rsp = create_season(Munch())
        self.assertEqual("Complete previous season before starting a new season.", rsp.message.error)
