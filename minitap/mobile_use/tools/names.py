from enum import StrEnum


class ToolName(StrEnum):
    """Enumeration of all available tool names."""

    BACK = "back"
    OPEN_LINK = "open_link"
    TAP = "tap"
    LONG_PRESS_ON = "long_press_on"
    SWIPE = "swipe"
    FOCUS_AND_INPUT_TEXT = "focus_and_input_text"
    ERASE_ONE_CHAR = "erase_one_char"
    LAUNCH_APP = "launch_app"
    STOP_APP = "stop_app"
    FOCUS_AND_CLEAR_TEXT = "focus_and_clear_text"
    PRESS_KEY = "press_key"
    WAIT_FOR_DELAY = "wait_for_delay"
