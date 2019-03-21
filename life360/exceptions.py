class Life360Error(Exception):
    """Base class for Life360 exceptions"""
    pass


class LoginError(Life360Error):
    """Invalid login username or password"""
    pass
