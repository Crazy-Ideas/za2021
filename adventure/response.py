from typing import List

from munch import Munch

from adventure.errors import InvalidRequestTypeWhileCreatingRequest


class RequestType:
    PLAY_RESULT = Munch(season=int(), round=int(), winner=str(), loser=str(), acquired=bool())
    CREATE_SEASON = Munch()
    NEXT_MATCH = Munch()
    GET_SEASON = Munch(season=int(), round=int())
    CUP_GET_SEASON = Munch(season=int())


class SuccessMessage:
    NEXT_MATCH = "Next match up ready."
    CREATE_SEASON = "New season created successfully."
    PLAY_RESULT = NEXT_MATCH
    GET_SEASON = "Season retrieved successfully"

class StandardResponse:
    EMPTY_RESPONSE = "Invalid request. Request cannot be empty."
    INVALID_PREFIX = "Invalid request. Only "
    INVALID_DATA_TYPE = "Invalid data type."

    def __init__(self, request: dict = None, request_type: Munch = None):
        self.message: Munch = Munch()
        self.message.error = str()
        self.message.warning = str()
        self.message.success = str()
        self.error_fields: Munch = Munch()
        self.request: Munch = Munch() if request is None else Munch.fromDict(request)
        self.data: Munch = Munch()
        if request is None:
            return
        if not isinstance(request_type, dict):
            raise InvalidRequestTypeWhileCreatingRequest
        if not isinstance(request, dict):
            self.message.error = self.EMPTY_RESPONSE
            return
        valid_fields: List = list(request_type.__dict__)
        if set(request) != set(valid_fields):
            count = len(valid_fields)
            field_list = ", ".join([field for field in valid_fields])
            if count == 1:
                self.message.error = f"{self.INVALID_PREFIX}1 field ({field_list}) allowed and it is mandatory."
                return
            self.message.error = f"{self.INVALID_PREFIX}{count} fields ({field_list}) allowed and they are mandatory."
            return
        for field, value in request.items():
            error = str() if isinstance(value, type(getattr(request_type, field))) else self.INVALID_DATA_TYPE
            self.message.error = error
            setattr(self.error_fields, field, error)
        return

    @property
    def dict(self) -> Munch:
        return Munch.fromDict(self.__dict__)

    def get(self):
        return self.data

