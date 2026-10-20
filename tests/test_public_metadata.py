import sys
from pathlib import Path
import unittest
import tempfile
import subprocess
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

    def test_manifest_parent_symlink_fails_before_any_network_request(self):
        with tempfile.TemporaryDirectory() as checkout, tempfile.TemporaryDirectory() as outside:
            (Path(outside) / 'public-links.json').write_text('{"private": "material"}')
            (Path(checkout) / '.github').symlink_to(outside, target_is_directory=True)
            run = subprocess.run([sys.executable, str(Path(M.__file__)), '--repo', checkout, '--slug', 'demo'], capture_output=True, text=True)
            self.assertEqual(run.returncode, 1)
            self.assertIn('cannot traverse a symlink', run.stdout)
            self.assertNotIn('material', run.stdout)

    def test_oversize_manifest_fails_before_network_request(self):
        with tempfile.TemporaryDirectory() as checkout:
            p = Path(checkout) / '.github'
            p.mkdir()
            (p / 'public-links.json').write_text('{"padding":"' + 'x' * 64_000 + '"}')
            run = subprocess.run([sys.executable, str(Path(M.__file__)), '--repo', checkout, '--slug', 'demo'], capture_output=True, text=True)
            self.assertEqual(run.returncode, 1)
            self.assertIn('exceeds 64KB limit', run.stdout)


if __name__ == '__main__':
    unittest.main()
