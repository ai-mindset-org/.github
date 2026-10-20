import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).parents[1] / 'tools'))
import public_metadata as M
from public_links import normalized


class MetadataContract(unittest.TestCase):
    def fixture(self):
        target, _ = normalized('https://aimindset.org/#learning', 'demo')
        manifest = {'schema':1, 'repository':'demo', 'labs_url':'https://go.aimindset.org/gh-demo-labs',
                    'homepage_url':'https://go.aimindset.org/gh-demo-labs', 'homepage_target':target}
        data = {'description':'A public tool · Labs: go.aimindset.org/gh-demo-labs', 'homepage':manifest['homepage_url']}
        return manifest, data, lambda _: target

    def test_short_links_hide_utm_and_keep_exact_target(self):
        manifest, data, resolver = self.fixture()
        self.assertEqual(M.audit('demo', manifest, data, resolver), [])
        self.assertNotIn('utm_', data['description'])
        self.assertNotIn('utm_', data['homepage'])

    def test_untagged_redirect_or_changed_destination_fails(self):
        manifest, data, _ = self.fixture()
        self.assertTrue(M.audit('demo', manifest, data, lambda _: 'https://aimindset.org/'))

    def test_deleted_labs_suffix_fails(self):
        manifest, data, resolver = self.fixture()
        data['description'] = 'A public tool'
        self.assertTrue(M.audit('demo', manifest, data, resolver))

    def test_arbitrary_exemption_target_is_not_trusted(self):
        manifest, data, resolver = self.fixture()
        manifest['homepage_target'] = 'https://unrelated.example/'
        self.assertTrue(M.audit('demo', manifest, data, resolver))


if __name__ == '__main__':
    unittest.main()
