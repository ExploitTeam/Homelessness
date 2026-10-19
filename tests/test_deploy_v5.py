"""Диагностика публикации mini app и безопасность выдачи статических файлов."""
import unittest
from fastapi.testclient import TestClient
from api.http_server import app


class DeployTest(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()

    def test_version_and_no_cache(self):
        response = self.client.get('/api/version')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            'release': 'v5-20261019',
            'frontend_present': True,
            'frontend_marker': True,
        })
        self.assertIn('no-store', response.headers['cache-control'])

    def test_index_has_distinct_release_and_no_cache(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('max-miniapp-version', response.text)
        self.assertIn('v5-20261019', response.text)
        self.assertIn('no-store', response.headers['cache-control'])
        self.assertIn('releases/v5-20261019', response.text)

    def test_static_asset_real_and_unknown_404(self):
        asset = self.client.get('/releases/v5-20261019/src/main.js')
        self.assertEqual(asset.status_code, 200)
        self.assertIn('immutable', asset.headers['cache-control'])
        self.assertEqual(self.client.get('/releases/v5-20261019/src/does-not-exist.js').status_code, 404)

    def test_no_api_html_fallback(self):
        self.assertEqual(self.client.get('/api/missing.json').status_code, 404)


if __name__ == '__main__':
    unittest.main()
