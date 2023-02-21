class InvalidWinner(Exception):
    pass


class NextMatchUpNotPossibleWhenRoundOver(Exception):
    pass


class InvalidRequestTypeWhileCreatingRequest(Exception):
    pass


class AdventuresNeedToBeSetBeforeOpponents(Exception):
    pass


class OpponentGroupSelectionHappensAfterRoundIsOver(Exception):
    pass


class OpponentRemovedFromRemainingOpponents(Exception):
    pass


class NewRoundCreatedAfterRoundIsOver(Exception):
    pass
