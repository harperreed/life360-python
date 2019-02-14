class Life360Error(Exception):
    """Base class for Life360 exceptions"""
    pass

class AuthInfoCallbackError(Life360Error):
    """Invalid auth_info_callback function"""
    pass

class LoginError(Life360Error):
    """Invalid login username or password"""
    pass
