# enums.py
"""Contains global enums"""

from enum import IntEnum


class ReadyPopupMode(IntEnum):
    label: str
    
    def __new__(cls, value, label=""):
        obj = int.__new__(cls, value)
        obj._value_ = value
        obj.label = label
        return obj

    MANUAL = (0, "No automatic popup")
    SHOW_AFTER_PRUNE = (1, "After prune")
    SHOW_AFTER_EVERY_COMMAND = (2, "After all supported commands")