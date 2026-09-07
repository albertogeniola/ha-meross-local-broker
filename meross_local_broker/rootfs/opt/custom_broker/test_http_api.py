"""API compatibility checks. Run with: python3 -m unittest test_http_api."""
import base64
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class HttpApiCompatibilityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Rebind before importing the API, whose import initializes the database.
        # Never open or modify the configured /data database during these tests.
        import database
        from sqlalchemy import create_engine

        temporary = tempfile.TemporaryDirectory()
        cls.addClassCleanup(temporary.cleanup)
        engine = create_engine(f"sqlite:///{Path(temporary.name) / 'api.db'}")
        cls.addClassCleanup(engine.dispose)
        original_bind = database.db_session.session_factory.kw['bind']
        database.db_session.remove()
        database.db_session.configure(bind=engine)
        cls.addClassCleanup(database.db_session.configure, bind=original_bind)
        cls.addClassCleanup(database.db_session.remove)
        engine_patch = patch.object(database, 'engine', engine)
        engine_patch.start()
        cls.addClassCleanup(engine_patch.stop)

        import http_api
        cls.app = http_api.app
        cls.database = database

    def setUp(self):
        self.database.db_session.remove()
        self.database.Base.metadata.drop_all(bind=self.database.engine)
        self.database.init_db()
        from db_helper import dbhelper
        self.user = dbhelper.add_update_user(
            email='test@example.com', password='test-password',
            user_id=1, user_key='0123456789abcdef0123456789abcdef')
        self.user_id = str(self.user.user_id)
        self.mqtt_key = self.user.mqtt_key
        self.client = self.app.test_client()

    def tearDown(self):
        self.database.db_session.remove()

    @staticmethod
    def envelope(payload):
        from constants import _SECRET
        params = base64.b64encode(json.dumps(payload).encode()).decode()
        timestamp, nonce = '1788750000', 'testnonce'
        signature = hashlib.md5(f'{_SECRET}{timestamp}{nonce}{params}'.encode()).hexdigest()
        return dict(params=params, timestamp=timestamp, nonce=nonce, sign=signature)

    def sign_in(self, form=False):
        envelope = self.envelope(dict(email='test@example.com', password='test-password'))
        kwargs = {'data': envelope} if form else {'json': envelope}
        return self.client.post('/v1/Auth/signIn', **kwargs)

    def test_signed_json_and_form_login_and_authenticated_request(self):
        for form in (False, True):
            with self.subTest(form=form):
                response = self.sign_in(form)
                self.assertEqual(response.status_code, 200)
                result = response.get_json()
                self.assertEqual(result['apiStatus'], 0)
                self.assertEqual(result['data']['userid'], self.user_id)
                response = self.client.post(
                    '/v1/Device/devList', json=self.envelope({}),
                    headers={'Authorization': f"Basic {result['data']['token']}"})
                self.assertEqual(response.get_json(), {'apiStatus': 0, 'info': None, 'data': []})

    def test_invalid_signature_returns_meross_error(self):
        envelope = self.envelope({})
        envelope['sign'] = 'invalid'
        response = self.client.post('/v1/Auth/signIn', data=envelope)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()['info'], 'Key verification failed')

    def test_non_object_json_returns_bad_request(self):
        response = self.client.post('/v1/Auth/signIn', json=[])
        self.assertEqual(response.status_code, 400)

    def test_missing_token_returns_meross_token_error(self):
        from meross_iot.http_api import ErrorCodes
        response = self.client.post('/v1/Device/devList', json=self.envelope({}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['apiStatus'], ErrorCodes.CODE_TOKEN_ERROR.value)

    def test_mqtt_app_auth_accepts_valid_and_denies_invalid_password(self):
        password = hashlib.md5(f'{self.user_id}{self.mqtt_key}'.encode()).hexdigest()
        for supplied, status, body in ((password, 200, b'ok'), ('wrong', 403, b'ko')):
            with self.subTest(status=status):
                response = self.client.post('/_devs_/auth', json={
                    'username': self.user_id, 'password': supplied, 'clientid': 'app:test'})
                self.assertEqual((response.status_code, response.data), (status, body))

    def test_invalid_mqtt_json_is_denied(self):
        for kwargs in ({'data': 'not json'}, {'json': []},
                       {'data': '{', 'content_type': 'application/json'}):
            with self.subTest(kwargs=kwargs):
                response = self.client.post('/_devs_/auth', **kwargs)
                self.assertEqual((response.status_code, response.data), (403, b'ko'))

    def test_mqtt_acl_json(self):
        response = self.client.post('/_devs_/acl', json={
            'username': self.user_id, 'topic': '/appliance/test/publish',
            'acc': 2, 'clientid': 'app:test'})
        self.assertEqual((response.status_code, response.data), (200, b'ok'))

    def test_admin_json_and_cors_preflight(self):
        response = self.client.get('/_admin_/devices', headers={'Origin': 'http://localhost'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), [])
        self.assertEqual(response.headers['Access-Control-Allow-Origin'], 'http://localhost')
        response = self.client.options('/v1/Auth/signIn', headers={
            'Origin': 'http://localhost', 'Access-Control-Request-Method': 'POST',
            'Access-Control-Request-Headers': 'Content-Type'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('POST', response.headers['Access-Control-Allow-Methods'])
        self.assertIn('Content-Type', response.headers['Access-Control-Allow-Headers'])

    def test_database_reinitialization_preserves_account(self):
        self.database.db_session.remove()
        self.database.engine.dispose()
        self.database.init_db()
        self.assertEqual(self.sign_in().get_json()['apiStatus'], 0)


if __name__ == '__main__':
    unittest.main()
