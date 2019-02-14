import requests
import os
import stat

from .exceptions import *


_BASE_URL = 'https://api.life360.com/v3/'
_TOKEN_URL = _BASE_URL + 'oauth2/token.json'
_CIRCLES_URL = _BASE_URL + 'circles.json'
_CIRCLE_URL = _BASE_URL + 'circles/{}'
_CIRCLE_MEMBERS_URL = _CIRCLE_URL + '/members'
_CIRCLE_PLACES_URL = _CIRCLE_URL + '/places'
_AUTH_ERRS = (401, 403)


class life360(object):

    def __init__(self, auth_info_callback, timeout=None,
                 authorization_cache_file=None):
        self._auth_info_callback = auth_info_callback
        self._timeout = timeout
        self._authorization_cache_file = authorization_cache_file
        self._auth = None
        self._session = requests.Session()
        self._session.headers.update(
            {'Accept': 'application/json', 'cache-control': 'no-cache'})

    def _load_authorization(self):
        with open(self._authorization_cache_file) as f:
            self._auth = f.read()

    def _save_authorization(self):
        if self._authorization_cache_file:
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
            mode = stat.S_IRUSR | stat.S_IWUSR
            umask = 0o777 ^ mode
            umask_orig = os.umask(umask)
            try:
                with open(os.open(
                        self._authorization_cache_file, flags, mode), 'w') as f:
                    f.write(self._auth)
            finally:
                os.umask(umask_orig)

    def _discard_authorization(self):
        self._auth = None
        if self._authorization_cache_file:
            try:
                os.remove(self._authorization_cache_file)
            except:
                pass

    def _get_authorization(self):
        """Use authorization token, username & password to get access token."""
        try:
            auth_token, username, password = self._auth_info_callback()
        except (TypeError, ValueError) as exc:
            raise AuthInfoCallbackError(
                'auth_info_callback must be a function '
                'that returns a tuple of: '
                'authorization token, username, password') from exc

        data = {
            'grant_type': 'password',
            'username': username,
            'password': password,
        }
        resp = self._session.post(_TOKEN_URL, data=data, timeout=self._timeout,
            headers={'Authorization': 'Basic ' + auth_token})

        if not resp.ok:
            # If it didn't work, try to return a useful error message.
            try:
                err_msg = resp.json()['errorMessage']
            except (ValueError, KeyError):
                resp.raise_for_status()
                raise Life360Error('Unexpected response to {}: {}: {}'.format(
                    _TOKEN_URL, resp.status_code, resp.text))
            if resp.status_code in _AUTH_ERRS and 'login' in err_msg.lower():
                raise LoginError(err_msg)
            raise Life360Error(err_msg)

        try:
            resp = resp.json()
            self._auth = ' '.join([resp['token_type'], resp['access_token']])
        except (ValueError, KeyError):
            raise Life360Error('Unexpected response to {}: {}: {}'.format(
                _TOKEN_URL, resp.status_code, resp.text))

        self._save_authorization()

    @property
    def _authorization(self):
        if not self._auth:
            try:
                self._load_authorization()
            except:
                self._get_authorization()
        return self._auth

    def _get(self, url):
        resp = self._session.get(url, timeout=self._timeout,
            headers={'Authorization': self._authorization})
        # If authorization error try regenerating authorization
        # and sending again.
        if resp.status_code in (401, 403):
            self._discard_authorization()
            resp.request.headers['Authorization'] = self._authorization
            resp = self._session.send(resp.request)
            if resp.status_code in (401, 403):
                self._discard_authorization()

        resp.raise_for_status()
        return resp.json()

    def get_circles(self):
        return self._get(_CIRCLES_URL)['circles']

    def get_circle(self, circle_id):
        return self._get(_CIRCLE_URL.format(circle_id))

    def get_circle_members(self, circle_id):
        return self._get(_CIRCLE_MEMBERS_URL.format(circle_id))['members']

    def get_circle_places(self, circle_id):
        return self._get(_CIRCLE_PLACES_URL.format(circle_id))['places']
