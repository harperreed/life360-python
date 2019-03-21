import json
import logging
import os
import stat

import requests

from .exceptions import *

_BASE_URL = 'https://api.life360.com/v3/'
_TOKEN_URL = _BASE_URL + 'oauth2/token.json'
_CIRCLES_URL = _BASE_URL + 'circles.json'
_CIRCLE_URL = _BASE_URL + 'circles/{}'
_CIRCLE_MEMBERS_URL = _CIRCLE_URL + '/members'
_CIRCLE_PLACES_URL = _CIRCLE_URL + '/places'
_AUTH_ERRS = (401, 403)

_LOGGER = logging.getLogger(__name__)


class life360(object):

    def __init__(self, api_token, username, password, timeout=None,
                 authorization_cache_file=None):
        self._credentials = {
            'api_token': api_token,
            'username': username,
            'password': password}
        self._timeout = timeout
        self._cache_file = authorization_cache_file
        self._auth = None
        self._session = requests.Session()
        self._session.headers.update(
            {'Accept': 'application/json', 'cache-control': 'no-cache'})

    def _load_authorization(self):
        if self._cache_file:
            try:
                with open(self._cache_file) as f:
                    cache = json.load(f)
            except FileNotFoundError:
                _LOGGER.debug('Authorization cache file does not exist')
                return
            except json.JSONDecodeError:
                credentials = authorization = None
            except Exception as error:
                _LOGGER.error(
                    'Could not load authorization from cache file: %s', error)
                self._discard_authorization()
                return
            else:
                credentials = cache.get('credentials')
                authorization = cache.get('authorization')
            if credentials != self._credentials or authorization is None:
                _LOGGER.warning(
                    'Authorization cache file out of date. Reauthorizing')
                self._discard_authorization()
            else:
                self._auth = authorization

    def _save_authorization(self):
        if self._cache_file:
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
            mode = stat.S_IRUSR | stat.S_IWUSR
            umask = 0o777 ^ mode
            umask_orig = os.umask(umask)
            cache = {'credentials': self._credentials,
                     'authorization': self._auth}
            try:
                with open(os.open(
                        self._cache_file, flags, mode), 'w') as f:
                    json.dump(cache, f)
            except Exception as error:
                _LOGGER.warning('Could not save authorization to cache file: %s', error)
            finally:
                os.umask(umask_orig)

    def _discard_authorization(self):
        self._auth = None
        if self._cache_file:
            try:
                os.remove(self._cache_file)
            except:
                pass

    def _get_authorization(self):
        data = {
            'grant_type': 'password',
            'username': self._credentials['username'],
            'password': self._credentials['password'],
        }
        resp = self._session.post(
            _TOKEN_URL, data=data, timeout=self._timeout, headers={
                'Authorization': 'Basic ' + self._credentials['api_token']})

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
            self._load_authorization()
            if not self._auth:
                self._get_authorization()
        return self._auth

    def _get(self, url):
        resp = self._session.get(url, timeout=self._timeout,
            headers={'Authorization': self._authorization})
        # If authorization error try regenerating authorization
        # and sending again.
        if resp.status_code in (401, 403):
            _LOGGER.warning('Error %i %s. Reauthorizing',
                            resp.status_code, resp.reason)
            self._discard_authorization()
            resp.request.headers['Authorization'] = self._authorization
            resp = self._session.send(resp.request)
            if resp.status_code in (401, 403):
                _LOGGER.error('Error %i %s', resp.status_code, resp.reason)
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
