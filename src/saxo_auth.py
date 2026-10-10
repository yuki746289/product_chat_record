# Created: 2026-10-10 JST
"""Saxo OAuth Authorization Code (registered app 'Code') and Windows credential vault.

Never print or commit tokens. The embedded HTTP callback only listens on loopback.
App secrets and rotating tokens are stored via Windows Credential Manager (keyring).
"""
import argparse
from getpass import getpass
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import secrets
import threading
import time
from urllib.parse import parse_qs, urlencode, urlparse
import webbrowser

import requests

from .config import load_settings

AUTH_HOSTS = {'sim': 'https://sim.logonvalidation.net',
              'live': 'https://logonvalidation.net'}
VAULT_PREFIX = 'ChartRecorder.SaxoOpenAPI'


class SaxoLoginRequired(RuntimeError):
    """An interactive Saxo browser login is required to resume."""


def vault_for(environment):
    if environment not in AUTH_HOSTS:
        raise ValueError('Saxo environment must be sim or live')
    return f'{VAULT_PREFIX}.{environment}'


def get_keyring():
    try:
        import keyring
    except ImportError as exc:
        raise RuntimeError('Install requirements-windows.txt (keyring)') from exc
    return keyring


def local_redirect_uri(cfg):
    uri = cfg['saxo']['redirect_uri']
    parsed = urlparse(uri)
    if parsed.scheme != 'http' or parsed.hostname not in ('localhost', '127.0.0.1') or not parsed.port:
        raise ValueError('Saxo redirect must be http://localhost:<port>/path')
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError('Unexpected redirect URI components')
    return uri


def credentials(environment, vault=None):
    vault = vault or get_keyring()
    service = vault_for(environment)
    key = vault.get_password(service, 'app_key')
    secret = vault.get_password(service, 'app_secret')
    if not key or not secret:
        raise SaxoLoginRequired('Saxo App Key/Secret not configured. Run: python -m src.saxo_auth configure')
    return key, secret


def save_credentials(environment, app_key, app_secret, vault=None):
    if not app_key or not app_secret:
        raise ValueError('App Key and App Secret required')
    vault = vault or get_keyring()
    service = vault_for(environment)
    vault.set_password(service, 'app_key', app_key)
    vault.set_password(service, 'app_secret', app_secret)


def make_authorize_url(environment, client_id, redirect_uri, state):
    return AUTH_HOSTS[environment] + '/authorize?' + urlencode({
        'response_type': 'code', 'client_id': client_id,
        'state': state, 'redirect_uri': redirect_uri})


def _token_from_response(payload, now):
    if not isinstance(payload, dict) or not payload.get('access_token') or not payload.get('refresh_token'):
        raise RuntimeError('Unexpected Saxo token response; login may be required')
    expires = int(payload.get('expires_in', 0))
    refresh_expires = int(payload.get('refresh_token_expires_in', 0))
    if expires <= 0 or refresh_expires <= 0:
        raise RuntimeError('Saxo did not return token expiry intervals')
    return {'access_token': payload['access_token'], 'refresh_token': payload['refresh_token'],
            'access_expires_at': now + expires, 'refresh_expires_at': now + refresh_expires}


class SaxoSession:
    """Manages rotating tokens and renews them before expiry; one process per vault."""
    def __init__(self, cfg, vault=None, http=None, clock=None):
        self.environment = cfg['saxo']['environment']
        self.redirect_uri = local_redirect_uri(cfg)
        self.vault = vault or get_keyring()
        self.http = http or requests.Session()
        self.clock = clock or time.time
        self.lock = threading.RLock()

    @property
    def service(self):
        return vault_for(self.environment)

    def save_token_response(self, payload):
        tokens = _token_from_response(payload, self.clock())
        # One credential-store write prevents partial refresh-token rotation.
        self.vault.set_password(self.service, 'tokens', json.dumps(tokens))
        return tokens

    def read_tokens(self):
        raw = self.vault.get_password(self.service, 'tokens')
        if not raw:
            raise SaxoLoginRequired('No stored Saxo OAuth session. Run: python -m src.saxo_auth login')
        try:
            return json.loads(raw)
        except (ValueError, TypeError) as exc:
            raise SaxoLoginRequired('Saxo token store corrupt; sign in again') from exc

    def exchange_code(self, code):
        app_key, app_secret = credentials(self.environment, self.vault)
        resp = self.http.post(AUTH_HOSTS[self.environment] + '/token',
                              auth=(app_key, app_secret), timeout=25,
                              data={'grant_type': 'authorization_code', 'code': code,
                                    'redirect_uri': self.redirect_uri})
        resp.raise_for_status()
        return self.save_token_response(resp.json())

    def access_token(self):
        with self.lock:
            tokens = self.read_tokens()
            now = self.clock()
            if float(tokens['access_expires_at']) > now + 120:
                return tokens['access_token']
            if float(tokens['refresh_expires_at']) <= now + 60:
                raise SaxoLoginRequired('Saxo refresh token expired; browser login required')
            app_key, app_secret = credentials(self.environment, self.vault)
            try:
                resp = self.http.post(AUTH_HOSTS[self.environment] + '/token',
                                      auth=(app_key, app_secret), timeout=25,
                                      data={'grant_type': 'refresh_token',
                                            'refresh_token': tokens['refresh_token'],
                                            'redirect_uri': self.redirect_uri})
                resp.raise_for_status()
                return self.save_token_response(resp.json())['access_token']
            except requests.HTTPError as exc:
                if exc.response is not None and exc.response.status_code in (400, 401, 403):
                    raise SaxoLoginRequired('Saxo token refresh rejected; browser login required') from exc
                raise RuntimeError('Saxo token service error; retry later') from exc

    def sign_in_interactively(self, timeout=180, open_browser=True):
        key, _ = credentials(self.environment, self.vault)
        parsed = urlparse(self.redirect_uri)
        state = secrets.token_urlsafe(32)
        result = {}

        class Callback(BaseHTTPRequestHandler):
            def do_GET(self):
                req = urlparse(self.path)
                if req.path != parsed.path:
                    self.send_error(404)
                    return
                q = parse_qs(req.query)
                if not secrets.compare_digest(q.get('state', [''])[0], state):
                    result['error'] = 'OAuth state mismatch'
                elif 'error' in q:
                    result['error'] = 'Saxo authorization was declined'
                elif not q.get('code'):
                    result['error'] = 'Saxo authorization code absent'
                else:
                    result['code'] = q['code'][0]
                self.send_response(200 if 'code' in result else 400)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Cache-Control', 'no-store')
                self.end_headers()
                self.wfile.write('<html><body>Authentication received. Return to ChartRecorder.</body></html>'.encode())

            def log_message(self, *_):
                # Prevent code/state from appearing in HTTP access logs.
                pass

        with HTTPServer(('127.0.0.1', parsed.port), Callback) as server:
            server.timeout = timeout
            url = make_authorize_url(self.environment, key, self.redirect_uri, state)
            if open_browser:
                webbrowser.open(url)
            else:
                print('Open the Saxo authorization page in your browser:', url)
            server.handle_request()
        if not result.get('code'):
            raise SaxoLoginRequired(result.get('error') or 'Saxo login timed out; try again')
        self.exchange_code(result['code'])
        return True


def main():
    parser = argparse.ArgumentParser(description='Configure or sign in to Saxo on the LOCAL PC only')
    parser.add_argument('command', choices=('configure', 'login', 'status'))
    parser.add_argument('--config', default=str(Path(__file__).resolve().parents[1] / 'setting.yaml'))
    args = parser.parse_args()
    cfg = load_settings(args.config)
    env = cfg['saxo']['environment']
    if args.command == 'configure':
        key = input('Saxo App Key: ').strip()
        secret = getpass('Saxo App Secret (hidden input): ').strip()
        save_credentials(env, key, secret)
        print('Saved locally in Windows Credential Manager (not Git).')
        return
    session = SaxoSession(cfg)
    if args.command == 'login':
        session.sign_in_interactively()
        print('Saxo OAuth connected (credentials are not shown).')
    else:
        tokens = session.read_tokens()
        print('Stored session:', 'refresh valid' if tokens['refresh_expires_at'] > session.clock() else 'login required')


if __name__ == '__main__':
    main()
