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


class NewRoundCreatedWhileRoundIsInProgress(Exception):
    pass


class UpdateUrlError(Exception):
    pass


class GroupwiseFileError(Exception):
    pass


class UnableToSetOpponent(Exception):
    pass
