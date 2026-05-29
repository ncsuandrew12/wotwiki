import enum

class Verbosity(enum.IntEnum):
    LOGQUIET = -2,
    APPQUIET = -1,
    NORMAL = 0,
    APPVERBOSE = 1,
    LOGVERBOSE = 2