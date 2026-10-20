import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from urllib.parse import parse_qs, urlsplit

SPEC = importlib.util.spec_from_file_location('public_links', Path(__file__).parents[1] / 'tools/public_links.py')
P = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = P
SPEC.loader.exec_module(P)


class URLContract(unittest.TestCase):
    def test_query_fragment_and_duplicates_survive(self):
        value, error = P.normalized('https://aimindset.org/pay?product=f26_base&x=1&x=2#details', 'demo')
        self.assertIsNone(error)
        self.assertEqual(urlsplit(value).fragment, 'details')
        q = parse_qs(urlsplit(value).query)
        self.assertEqual(q['x'], ['1', '2'])
        self.assertEqual(q['product'], ['f26_base'])
        self.assertEqual(q['utm_source'], ['website'])
        self.assertEqual(q['utm_medium'], ['article'])
        self.assertEqual(q['utm_content'], ['github-demo'])

    def test_registered_partner_identity_is_never_overwritten(self):
        url = 'https://aimindset.org/?utm_source=partner&utm_medium=post&utm_campaign=f26&utm_content=author&utm_id=123&promo=DEMO'
        self.assertEqual(P.normalized(url, 'demo'), (url, None))

    def test_partial_registered_link_fails_instead_of_retagging(self):
        url = 'https://aimindset.org/?utm_id=123'
        self.assertEqual(P.normalized(url, 'demo'), (url, 'registered-link-needs-review'))

    def test_protected_link_fails_instead_of_changing_signature(self):
        self.assertEqual(P.normalized('https://learn.aimindset.org/?token=example', 'demo')[1], 'protected-url-needs-review')

    def test_hostname_boundaries_and_technical_targets(self):
        for url in ('https://aimindset.org.evil.example/', 'https://evilaimindset.org/',
                    'https://aimindset.org/image.svg', 'https://learn.aimindset.org/api/user',
                    'https://noco.aimindset.org/', 'https://go.aimindset.org/example',
                    'https://github.com/ai-mindset-org/demo', 'https://t.me/aimindset_lab_bot?start=123'):
            with self.subTest(url=url):
                self.assertFalse(P.eligible(url))
        self.assertTrue(P.eligible('https://apps.aimindset.org/canvas-ui-anywhere/'))
        self.assertTrue(P.eligible('https://ai-mindset-org.github.io/demo/'))

    def test_raw_pilot_placements_and_product_campaign_survive(self):
        url = 'https://base.aimindset.org/?utm_source=website&utm_medium=article&utm_campaign=f26&utm_content=github-demo-base'
        self.assertEqual(P.normalized(url, 'demo'), (url, None))

    def test_duplicate_and_forbidden_utm_are_repaired_once(self):
        result, _ = P.normalized('https://aimindset.org/?utm_source=x&utm_source=y&utm_term=no&utm_content=other', 'demo')
        q = parse_qs(urlsplit(result).query)
        self.assertEqual(q['utm_source'], ['website'])
        self.assertNotIn('utm_term', q)
        self.assertEqual(P.normalized(result, 'demo'), (result, None))


class DocumentContract(unittest.TestCase):
    def test_markdown_visible_label_unchanged(self):
        original = '[Открыть инструмент](https://apps.aimindset.org/tool/?mode=demo#start)'
        fixed, _ = P.inspect(original, 'demo', True, True)
        self.assertTrue(fixed.startswith('[Открыть инструмент]('))
        self.assertIn('mode=demo&', fixed)
        self.assertTrue(fixed.endswith('#start)'))
        self.assertFalse(P.inspect(fixed, 'demo', True)[1])

    def test_bare_and_autolinks_have_clean_visible_labels(self):
        for original in ('https://aimindset.org/', '<https://aimindset.org/>'):
            fixed, _ = P.inspect(original, 'demo', True, True)
            self.assertTrue(fixed.startswith('[aimindset.org]('), fixed)
            self.assertNotIn('utm_', fixed.split('](')[0])
            self.assertFalse(P.inspect(fixed, 'demo', True)[1])

    def test_code_images_comments_and_scripts_are_ignored(self):
        original = '''`https://aimindset.org/`
~~~text
https://aimindset.org/
~~~
![banner](https://aimindset.org/banner)
<!-- https://aimindset.org/ -->
<script>const template = 'https://aimindset.org/';</script>
'''
        self.assertEqual(P.inspect(original, 'demo', True, True), (original, []))

    def test_html_labels_attributes_and_entity_escaping(self):
        original = '<a class="button" href="https://aimindset.org/?mode=demo&amp;x=1#start">Начать</a>'
        fixed, _ = P.inspect(original, 'demo', False, True)
        self.assertIn('class="button"', fixed)
        self.assertTrue(fixed.endswith('>Начать</a>'))
        self.assertIn('&amp;utm_source=website', fixed)
        self.assertEqual(len(P.links(fixed, False)), 1)
        self.assertFalse(P.inspect(fixed, 'demo', False)[1])

    def test_html_anchor_inside_markdown_not_counted_twice(self):
        original = '<a href="https://aimindset.org/">Lab</a>'
        fixed, _ = P.inspect(original, 'demo', True, True)
        self.assertEqual(fixed.count('utm_source'), 1)
        self.assertFalse(P.inspect(fixed, 'demo', True)[1])

    def test_protocol_relative_html_link_is_tracked(self):
        fixed, findings = P.inspect('<a href="//aimindset.org/">Lab</a>', 'demo', False, True)
        self.assertIn('href="https://aimindset.org/?utm_source=website', fixed)
        self.assertTrue(findings)
        self.assertFalse(P.inspect(fixed, 'demo', False)[1])

    def test_reference_balanced_parentheses_and_image_link(self):
        cases = ('[Lab][lab]\n\n[lab]: https://aimindset.org/labs/f26',
                 '[Lab](https://aimindset.org/demo_(one))',
                 '[![badge](https://other.example/badge.svg)](https://aimindset.org/)')
        for original in cases:
            with self.subTest(original=original):
                fixed, _ = P.inspect(original, 'demo', True, True)
                self.assertIn('utm_source=website', fixed)
                self.assertEqual(P.inspect(fixed, 'demo', True, True)[0], fixed)
        self.assertIn('demo_(one)?', P.inspect(cases[1], 'demo', True, True)[0])

    def test_standard_block_at_top_and_idempotent(self):
        text = '# Demo\n\nA useful project.\n\n## Setup\n'
        fixed = P.with_block(text, 'demo')
        self.assertEqual(P.with_block(fixed, 'demo'), fixed)
        self.assertLess(fixed.index(P.START), fixed.index('A useful project.'))
        self.assertIn('#learning)', fixed)
        self.assertEqual(fixed.count(P.START), 1)

    def test_profile_banner_retained(self):
        text = '<picture>\n<img src="banner.svg">\n</picture>\n\nWe run labs.\n'
        fixed = P.with_block(text, '.github')
        self.assertTrue(fixed.startswith('<picture>'))
        self.assertLess(fixed.index('</picture>'), fixed.index(P.START))
        self.assertIn('github-org-profile', fixed)

    def test_new_minimal_readme_has_no_blank_eof_line(self):
        fixed = P.with_block('# Demo\n', 'demo')
        self.assertTrue(fixed.endswith('\n'))
        self.assertFalse(fixed.endswith('\n\n'))
        self.assertEqual(P.with_block(fixed, 'demo'), fixed)

    def test_labs_block_cannot_drift_to_bottom(self):
        text = '# Demo\n\nIntroduction.\n\n## Setup\n\n' + P.block('demo', True) + '\n'
        fixed = P.with_block(text, 'demo')
        self.assertLess(fixed.index(P.START), fixed.index('Introduction.'))
        self.assertEqual(P.with_block(fixed, 'demo'), fixed)

    def test_username_in_destination_is_not_rewritten(self):
        url = 'https://example@aimindset.org/'
        self.assertEqual(P.normalized(url, 'demo'), (url, 'protected-url-needs-review'))


class LiveGateContract(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True)

    def tearDown(self):
        self.tmp.cleanup()

    def stage(self):
        subprocess.run(['git', '-C', str(self.root), 'add', '.'], check=True)

    def test_real_cli_fails_then_passes_and_mutated_utm_fails(self):
        f = self.root / 'README.md'
        f.write_text('# Example\n\n[Lab](https://aimindset.org/)\n')
        self.stage()
        cli = [sys.executable, str(Path(P.__file__)), '--repo', str(self.root), '--slug', 'demo', '--json']
        self.assertEqual(subprocess.run(cli, capture_output=True).returncode, 1)
        self.assertEqual(subprocess.run(cli + ['--fix'], capture_output=True).returncode, 0)
        self.assertEqual(subprocess.run(cli, capture_output=True).returncode, 0)
        f.write_text(f.read_text().replace('utm_medium=article', 'utm_medium=wrong'))
        self.assertEqual(subprocess.run(cli, capture_output=True).returncode, 1)

    def test_tracked_document_symlink_fails_closed(self):
        outside = self.root.parent / (self.root.name + '-outside.md')
        outside.write_text('private')
        try:
            (self.root / 'README.md').symlink_to(outside)
            self.stage()
            result = P.run(self.root, 'demo')
            self.assertFalse(result['pass'])
            self.assertIn('symlink-or-out-of-root-document', result['findings'][0]['reasons'])
            self.assertFalse(P.run(self.root, 'demo', True)['pass'])
            self.assertEqual(outside.read_text(), 'private')
        finally:
            outside.unlink()


if __name__ == '__main__':
    unittest.main()
