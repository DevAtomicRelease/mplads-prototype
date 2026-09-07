"""Local service contract checks using an isolated temporary review database."""
import http.client
import json
import tempfile
import threading
import unittest
from pathlib import Path
from serve_local import make_server, CACHE

class ServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='mplads-test-')
        cls.db = Path(cls.temp.name) / 'reviews.sqlite3'
        cls.server = make_server(0, cls.db)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.key = next(key for key in cls.server.valid_keys if not key.startswith('pair:'))

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()
        cls.temp.cleanup()

    def request(self, method, path, value=None, origin=None, host=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.port, timeout=10)
        headers = {'Content-Type': 'application/json', 'Origin': origin or f'http://127.0.0.1:{self.port}'}
        if host:
            headers['Host'] = host
        connection.request(method, path, json.dumps(value) if value is not None else None, headers)
        response = connection.getresponse()
        status, body = response.status, response.read()
        connection.close()
        return status, json.loads(body)

    def value(self, **changes):
        return {'key': self.key, 'outcome': 'Needs evidence', 'note': 'Independent test only', 'version': self.server.version, **changes}

    def test_health(self):
        status, result = self.request('GET', '/api/health')
        self.assertEqual(status, 200)
        self.assertTrue(result['localOnly'])

    def test_persistent_append_only_reviews(self):
        for note in ['First review', 'Revised evidence']:
            status, result = self.request('POST', '/api/reviews', self.value(note=note))
            self.assertEqual(status, 201)
        status, result = self.request('GET', '/api/reviews')
        self.assertEqual(result['reviews'][self.key]['note'], 'Revised evidence')
        _, result = self.request('GET', '/api/reviews/history')
        self.assertEqual([r['note'] for r in result['history'] if r['record_key'] == self.key], ['First review', 'Revised evidence'])
        # A new service instance reads the same disk state after the original closes.
        replacement = make_server(0, self.db)
        from serve_local import connect_db
        with connect_db(replacement.review_db) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM reviews WHERE record_key=?', (self.key,)).fetchone()[0], 2)
        replacement.server_close()

    def test_pair_review(self):
        key = next(key for key in self.server.valid_keys if key.startswith('pair:'))
        self.assertEqual(self.request('POST', '/api/reviews', self.value(key=key))[0], 201)

    def test_invalid_inputs(self):
        for changes in [{'key': 'missing'}, {'note': ''}, {'note': 'a' * 3001}, {'outcome': 'Fraud probability'}]:
            self.assertEqual(self.request('POST', '/api/reviews', self.value(**changes))[0], 400)
        self.assertEqual(self.request('POST', '/api/reviews', self.value(version='stale'))[0], 409)

    def test_host_origin_and_payload_guards(self):
        self.assertEqual(self.request('GET', '/api/health', host='external.example')[0], 403)
        self.assertEqual(self.request('POST', '/api/reviews', self.value(), origin='https://external.example')[0], 403)
        self.assertEqual(self.request('POST', '/api/reviews', self.value(note='a'*17000))[0], 413)

    def test_allowlisted_routes(self):
        self.assertEqual(self.request('GET', '/api/reviews.sqlite3')[0], 404)
        self.assertEqual(self.request('GET', '/api/validation')[0], 200)

if __name__ == '__main__':
    unittest.main(verbosity=2)
