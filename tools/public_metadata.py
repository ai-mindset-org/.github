#!/usr/bin/env python3
"""Read-only audit of GitHub About fields and first-party short-link targets."""
import argparse
import json
import os
from pathlib import Path
import re
import urllib.error
import urllib.request
from urllib.parse import parse_qs, urlsplit

from public_links import eligible, normalized, safe_path


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def github(path):
    headers = {'Accept':'application/vnd.github+json', 'User-Agent':'AIM-public-repository-audit'}
    token = os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
    if token:
        headers['Authorization'] = 'Bearer ' + token
    request = urllib.request.Request('https://api.github.com/' + path, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def short_target(url):
    if not re.fullmatch(r'https://go\.aimindset\.org/[a-z0-9-]{1,40}', url):
        raise ValueError('short link must use the first-party go host and one slug')
    request = urllib.request.Request(url, method='HEAD', headers={'User-Agent':'AIM-public-repository-audit'})
    try:
        urllib.request.build_opener(NoRedirect()).open(request, timeout=30)
    except urllib.error.HTTPError as response:
        if response.code == 302:
            return response.headers.get('Location', '')
        raise
    raise ValueError('expected a non-permanent 302 redirect')


def audit(slug, manifest, metadata, resolver, org=None):
    failures = []
    if manifest.get('schema') != 1 or manifest.get('repository') != slug:
        return ['invalid metadata manifest identity']
    labs_url = manifest.get('labs_url', '')
    expected_labs, _ = normalized('https://aimindset.org/#learning', slug)
    if resolver(labs_url) != expected_labs:
        failures.append('labs short-link target differs from the standard labs URL')
    suffix = ' · Labs: ' + labs_url.removeprefix('https://')
    if not (metadata.get('description') or '').endswith(suffix):
        failures.append('About description is missing the standard labs suffix')
    homepage = manifest.get('homepage_url', '')
    target = manifest.get('homepage_target', '')
    if not eligible(target) or normalized(target, slug) != (target, None):
        failures.append('homepage target is not an eligible correctly tracked AIM URL')
    if metadata.get('homepage') != homepage:
        failures.append('About website differs from the manifest')
    if resolver(homepage) != target:
        failures.append('About website redirect differs from its recorded target')
    if slug == '.github':
        expected, _ = normalized('https://aimindset.org/', slug)
        if not org or org.get('blog') != manifest.get('organization_url'):
            failures.append('organization website differs from the manifest')
        elif resolver(org['blog']) != expected:
            failures.append('organization website target differs from the tracked main site')
    return failures


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path('.'))
    parser.add_argument('--slug', required=True)
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()
    try:
        if not re.fullmatch(r'[a-zA-Z0-9._-]{1,100}', args.slug):
            raise ValueError('invalid repository slug')
        root = args.repo.resolve()
        f = root / '.github/public-links.json'
        if not safe_path(root, f):
            raise ValueError('metadata manifest cannot traverse a symlink or leave the repository')
        if f.stat().st_size > 64_000:
            raise ValueError('metadata manifest exceeds 64KB limit')
        manifest = json.loads(f.read_text())
        metadata = github('repos/ai-mindset-org/' + args.slug)
        org = github('orgs/ai-mindset-org') if args.slug == '.github' else None
        failures = audit(args.slug, manifest, metadata, short_target, org)
        result = {'repository':args.slug, 'pass':not failures, 'findings':failures}
    except (OSError, ValueError, urllib.error.URLError) as exc:
        result = {'repository':args.slug, 'pass':False, 'error':str(exc)}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['pass'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
