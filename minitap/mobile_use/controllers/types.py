from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class ScreenDataResponse(BaseModel):
    base64: str
    elements: list
    width: int
    height: int
    platform: str


class CoordinatesSelectorRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    x: int
    y: int

    def to_str(self):
        return f"{self.x}, {self.y}"


class PercentagesSelectorRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    """
    0%,0%        # top-left corner
    100%,100%    # bottom-right corner
    50%,50%      # center
    """

    x_percent: float = Field(description="X percentage (0-100)")
    y_percent: float = Field(description="Y percentage (0-100)")

    def normalize(self):
        if self.x_percent > 1:
            self.x_percent = self.x_percent / 100
        if self.y_percent > 1:
            self.y_percent = self.y_percent / 100

    def to_str(self):
        self.normalize()
        return f"{int(self.x_percent * 100)}%, {int(self.y_percent * 100)}%"

    def to_coords(self, width: int, height: int):
        self.normalize()
        x = int(round((width - 1) * self.x_percent))
        y = int(round((height - 1) * self.y_percent))
        return CoordinatesSelectorRequest(x=x, y=y)


class IdSelectorRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str

    def to_dict(self) -> dict[str, str | int]:
        return {"id": self.id}


# Useful to tap on an element when there are multiple views with the same id
class IdWithTextSelectorRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    text: str

    def to_dict(self) -> dict[str, str | int]:
        return {"id": self.id, "text": self.text}


class TextSelectorRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str

    def to_dict(self) -> dict[str, str | int]:
        return {"text": self.text}


class SelectorRequestWithCoordinates(BaseModel):
    model_config = ConfigDict(extra="forbid")
    coordinates: CoordinatesSelectorRequest

    def to_dict(self) -> dict[str, str | int]:
        return {"point": self.coordinates.to_str()}


class SelectorRequestWithPercentages(BaseModel):
    model_config = ConfigDict(extra="forbid")
    percentages: PercentagesSelectorRequest

    def to_dict(self) -> dict[str, str | int]:
        return {"point": self.percentages.to_str()}


SelectorRequest = (
    IdSelectorRequest
    | SelectorRequestWithCoordinates
    | SelectorRequestWithPercentages
    | TextSelectorRequest
    | IdWithTextSelectorRequest
)


class TapOutput(BaseModel):
    error: dict | None = None


class SwipeStartEndCoordinatesRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    start: CoordinatesSelectorRequest
    end: CoordinatesSelectorRequest

    def to_dict(self):
        return {"start": self.start.to_str(), "end": self.end.to_str()}


class SwipeStartEndPercentagesRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    start: PercentagesSelectorRequest
    end: PercentagesSelectorRequest

    def to_dict(self):
        return {"start": self.start.to_str(), "end": self.end.to_str()}

    def to_coords(self, width: int, height: int):
        return SwipeStartEndCoordinatesRequest(
            start=self.start.to_coords(width, height),
            end=self.end.to_coords(width, height),
        )


class SwipeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    swipe_mode: SwipeStartEndCoordinatesRequest | SwipeStartEndPercentagesRequest
    duration: int | None = None  # in ms, default is 400ms

    def to_dict(self):
        res = {}
        if isinstance(self.swipe_mode, SwipeStartEndCoordinatesRequest):
            res |= self.swipe_mode.to_dict()
        elif isinstance(self.swipe_mode, SwipeStartEndPercentagesRequest):
            res |= self.swipe_mode.to_dict()
        elif self.swipe_mode in ["UP", "DOWN", "LEFT", "RIGHT"]:
            res |= {"direction": self.swipe_mode}
        if self.duration:
            res |= {"duration": self.duration}
        return res


class Key(Enum):
    ENTER = "Enter"
    HOME = "Home"
    BACK = "Back"


class WaitTimeout(Enum):
    SHORT = "500"
    MEDIUM = "1000"
    LONG = "5000"
