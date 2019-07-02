# This is what requests does.
try:
    import simplejson as json
except ImportError:
    import json
import logging

import requests

from .exceptions import *

_PROTOCOL = 'https://'
_HOST = 'api.life360.com'
_BASE_URL = '{}{}/v3/'.format(_PROTOCOL, _HOST)
_TOKEN_URL = _BASE_URL + 'oauth2/token.json'
_CIRCLES_URL = _BASE_URL + 'circles.json'
_CIRCLE_URL = _BASE_URL + 'circles/{}'
_CIRCLE_MEMBERS_URL = _CIRCLE_URL + '/members'
_CIRCLE_PLACES_URL = _CIRCLE_URL + '/places'
_AUTH_ERRS = (401, 403)

_LOGGER = logging.getLogger(__name__)

DEFAULT_API_TOKEN = (
    'cFJFcXVnYWJSZXRyZTRFc3RldGhlcnVmcmVQdW1hbUV4dWNyRU'
    'h1YzptM2ZydXBSZXRSZXN3ZXJFQ2hBUHJFOTZxYWtFZHI0Vg=='
)


class Life360:
    """Life360 API"""
    def __init__(self, timeout=None, max_retries=None, authorization=None):
        self._timeout = timeout
        self._max_retries = max_retries
        self._authorization = authorization
        self._session = None

    def _get_session(self):
        if not self._session:
            self._session = requests.Session()
            if self._max_retries:
                self._session.mount(_PROTOCOL,
                                    requests.adapters.HTTPAdapter(
                                        max_retries=self._max_retries))
            self._session.headers.update(
                {'Accept': 'application/json', 'cache-control': 'no-cache'})
        return self._session

    def get_authorization(self, username, password,
                          api_token=DEFAULT_API_TOKEN):
        """Obtain Authorization header value."""
        data = {
            'grant_type': 'password',
            'username': username,
            'password': password,
        }
        try:
            resp = self._get_session().post(
                _TOKEN_URL, data=data, timeout=self._timeout,
                headers={'Authorization': 'Basic ' + api_token})
            resp.raise_for_status()
        except requests.RequestException as error:
            _LOGGER.debug(
                'Error while getting authorization token: %s', error)
            # Try to return a useful error message.
            try:
                err_msg = resp.json()['errorMessage']
            except (UnboundLocalError, json.JSONDecodeError, ValueError,
                    KeyError):
                raise CommError(error)
            if resp.status_code in _AUTH_ERRS and 'login' in err_msg.lower():
                raise LoginError(err_msg)
            raise CommError(err_msg)
        try:
            resp = resp.json()
            self._authorization = ' '.join(
                [resp['token_type'], resp['access_token']])
        except (json.JSONDecodeError, ValueError, KeyError):
            raise Life360Error(
                'Unexpected response while getting authorization token: '
                '{}: {}'.format(resp.status_code, resp.text))
        return self._authorization

    def _get(self, url):
        if not self._authorization:
            raise Life360Error('No authorization. Call get_authorization')
        try:
            resp = self._get_session().get(url, timeout=self._timeout,
                headers={'Authorization': self._authorization})
            if resp.status_code in (401, 403):
                _LOGGER.debug('Error %i %s. Reauthorize',
                              resp.status_code, resp.reason)
                raise LoginError('Reauthorize')
            resp.raise_for_status()
            return resp.json()
        except (requests.RequestException, json.JSONDecodeError) as error:
            _LOGGER.debug('Error while getting: %s: %s', url, error)
            if isinstance(error, requests.RequestException):
                raise CommError(error)
            try:
                raise Life360Error(
                    'Unexpected response to query: {}: {}'.format(
                        resp.status_code, resp.text))
            except UnboundLocalError:
                raise Life360Error('Unexpected response to query')

    def get_circles(self):
        """Get basic data about all Circles."""
        return self._get(_CIRCLES_URL)['circles']

    def get_circle(self, circle_id):
        """Get details for given Circle."""
        return self._get(_CIRCLE_URL.format(circle_id))

    def get_circle_members(self, circle_id):
        """Get details for Members in given Circle."""
        return self._get(_CIRCLE_MEMBERS_URL.format(circle_id))['members']

    def get_circle_places(self, circle_id):
        """Get details for Places in given Circle."""
        return self._get(_CIRCLE_PLACES_URL.format(circle_id))['places']


class Urllib3Filter(logging.Filter):
    def filter(self, record):
        return not (
            record.levelno == logging.WARNING and _HOST in record.getMessage())


logging.getLogger('urllib3.connectionpool').addFilter(Urllib3Filter())
