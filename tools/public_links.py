#!/usr/bin/env python3
"""Offline public-document link gate. Never executes code from the checked repo."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

START = '<!-- aim-public-links:start -->'
END = '<!-- aim-public-links:end -->'
KEYS = ('utm_source', 'utm_medium', 'utm_campaign', 'utm_content')
STATIC = {'.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.ico', '.css',
          '.js', '.mjs', '.json', '.xml', '.pdf', '.zip', '.woff', '.woff2'}
SERVICE = {'noco.aimindset.org', 'n8n.aimindset.org', 'content.aimindset.org',
           'go.aimindset.org', 'partners.aimindset.org'}
URL = re.compile(r'(?:https?://|(?<!:)//)[^\s<>"\x27`\[\]]+', re.I)


@dataclass
class Link:
    start: int
    end: int
    url: str
    kind: str


def content(slug: str) -> str:
    name = 'org-profile' if slug == '.github' else slug
    value = 'github-' + re.sub(r'[^a-z0-9._-]', '-', name.lower())
    return value if len(value) <= 48 else value[:39] + '-' + hashlib.sha256(value.encode()).hexdigest()[:8]


def eligible(url: str) -> bool:
    try:
        p = urlsplit(html.unescape(url))
    except ValueError:
        return False
    host = (p.hostname or '').lower()
    owned = host == 'aimindset.org' or host.endswith('.aimindset.org') or host == 'ai-mindset-org.github.io'
    return (owned and host not in SERVICE and p.scheme in ('', 'http', 'https')
            and not p.path.lower().startswith(('/api/', '/.netlify/', '/auth/', '/oauth/'))
            and Path(p.path).suffix.lower() not in STATIC)


def normalized(url: str, slug: str) -> tuple[str, str | None]:
    raw = html.unescape(url)
    try:
        p = urlsplit(raw)
    except ValueError:
        return raw, 'invalid-url'
    if not eligible(raw):
        return raw, None
    if p.username or p.password:
        return raw, 'protected-url-needs-review'
    pairs = parse_qsl(p.query, keep_blank_values=True)
    params: dict[str, list[str]] = {}
    for k, v in pairs:
        params.setdefault(k, []).append(v)
    if any(k.lower() in {'token', 'code', 'signature', 'sig', 'key', 'expires'} for k in params):
        return raw, 'protected-url-needs-review'
    # Registered links retain the identity and attribution minted by the UTM service.
    if 'utm_id' in params or 'promo' in params:
        complete = all(len(params.get(k, [])) == 1 and params[k][0] for k in KEYS)
        valid_id = bool(re.fullmatch(r'[1-9][0-9]*', params.get('utm_id', [''])[0]))
        if not complete or not valid_id or 'utm_term' in params:
            return raw, 'registered-link-needs-review'
        return raw, None
    campaign = params.get('utm_campaign', ['bio' if p.hostname == 'bio.aimindset.org' else 'start'])[0]
    if not re.fullmatch(r'[a-z0-9._-]{2,48}', campaign):
        campaign = 'start'
    placement = params.get('utm_content', [content(slug)])[0]
    prefix = content(slug)
    if not re.fullmatch(r'[a-z0-9._-]{2,48}', placement) or not (placement == prefix or placement.startswith(prefix + '-')):
        placement = prefix
    tracking = dict(zip(KEYS, ('website', 'article', campaign, placement)))
    rest = [(k, v) for k, v in pairs if k not in (*KEYS, 'utm_term')]
    # Preserve meaningful query pairs, duplicates and fragments; tracking is replaced once.
    result = urlunsplit(('https', p.netloc, p.path, urlencode(rest + list(tracking.items())), p.fragment))
    return result, None


def mask_code(text: str) -> str:
    out = list(text)
    fence: tuple[str, int] | None = None
    offset = 0
    for line in text.splitlines(keepends=True):
        match = re.match(r' {0,3}(`{3,}|~{3,})', line)
        was_inside = fence is not None
        if match:
            mark = match[1]
            if fence is None:
                fence = (mark[0], len(mark))
            elif mark[0] == fence[0] and len(mark) >= fence[1] and not line[match.end():].strip():
                fence = None
        if was_inside or fence is not None or match:
            for i in range(offset, offset + len(line)):
                if out[i] != '\n':
                    out[i] = ' '
        offset += len(line)
    masked = ''.join(out)
    patterns = (r'(`+)([\s\S]*?)\1', r'<!--[\s\S]*?-->')
    for pattern in patterns:
        for m in re.finditer(pattern, masked):
            for i in range(m.start(), m.end()):
                if out[i] != '\n':
                    out[i] = ' '
        masked = ''.join(out)
    return masked


class Anchors(HTMLParser):
    def __init__(self, text: str):
        super().__init__(convert_charrefs=False)
        self.offsets = [0] + [m.end() for m in re.finditer('\n', text)]
        self.links: list[Link] = []
        self.hidden: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style', 'pre', 'code'):
            self.hidden.append(tag)
        if tag != 'a' or self.hidden:
            return
        raw = self.get_starttag_text()
        m = re.search(r'\bhref\s*=\s*(?:"([^"]*)"|\x27([^\x27]*)\x27|([^\s>]+))', raw, re.I)
        if not m:
            return
        group = next(i for i in (1, 2, 3) if m[i] is not None)
        line, col = self.getpos()
        start = self.offsets[line - 1] + col + m.start(group)
        self.links.append(Link(start, start + len(m[group]), html.unescape(m[group]), 'html'))

    def handle_endtag(self, tag):
        if tag in self.hidden:
            self.hidden.remove(tag)


def links(text: str, markdown: bool) -> list[Link]:
    masked = mask_code(text) if markdown else text
    parser = Anchors(masked)
    parser.feed(masked)
    result = parser.links
    if not markdown:
        return result
    ignore = []
    # Image destinations and visible labels are not outbound text-link destinations.
    for pattern in (r'!\[[^\]\n]*\]\([^\n]*?\)', r'\[[^\]\n]*\](?=\()',
                    r'<[a-zA-Z/!][a-zA-Z0-9/-]*(?:\s[^>]*|/?)>', r'<(script|style|pre|code)\b[\s\S]*?</\1>'):
        ignore.extend((m.start(), m.end()) for m in re.finditer(pattern, masked, re.I))
    for m in URL.finditer(masked):
        if any(a <= m.start() < b for a, b in ignore):
            continue
        url = m[0].rstrip('.,;')
        while url.endswith(')') and url.count(')') > url.count('('):
            url = url[:-1]
        if not url:
            continue
        start, end = m.start(), m.start() + len(url)
        before = masked[max(0, start - 500):start]
        if re.search(r'\]\(\s*<?$', before) or re.search(r'^ {0,3}\[[^\]]+\]:\s*<?$', before.split('\n')[-1]):
            kind = 'markdown'
        elif start and masked[start - 1] == '<' and end < len(masked) and masked[end] == '>':
            start -= 1
            end += 1
            kind = 'autolink'
        else:
            kind = 'bare'
        result.append(Link(start, end, url, kind))
    # HTML hrefs were masked from the plain Markdown pass.
    return sorted(result, key=lambda l: l.start)


def readable(url: str) -> str:
    p = urlsplit(url)
    query = urlencode([(k, v) for k, v in parse_qsl(p.query) if not k.startswith('utm_')])
    return urlunsplit(('', p.netloc, p.path.rstrip('/'), query, p.fragment)).removeprefix('//')


def inspect(text: str, slug: str, markdown: bool, fix=False):
    findings, edits = [], []
    for link in links(text, markdown):
        target, error = normalized(link.url, slug)
        if not error and not eligible(link.url):
            continue
        reasons = [error] if error else []
        if not error and target != html.unescape(link.url):
            reasons.append('utm-missing-or-invalid')
        if link.kind in ('bare', 'autolink'):
            reasons.append('use-readable-link-label')
        if reasons:
            findings.append({'line':text.count('\n', 0, link.start) + 1, 'url':link.url, 'reasons':reasons})
        if fix and not error:
            if link.kind == 'html':
                replacement = html.escape(target, quote=True)
            elif link.kind in ('bare', 'autolink'):
                replacement = '[' + readable(target) + '](' + target + ')'
            else:
                replacement = target
            if text[link.start:link.end] != replacement:
                edits.append((link.start, link.end, replacement))
    for start, end, replacement in reversed(edits):
        text = text[:start] + replacement + text[end:]
    return text, findings


def block(slug: str, english=False) -> str:
    labs, _ = normalized('https://aimindset.org/#learning', slug)
    base, _ = normalized('https://base.aimindset.org/', slug)
    labels = ('AI Mindset labs', 'Knowledge base') if english else ('Лабы AI Mindset', 'База знаний')
    return START + '\n[' + labels[0] + '](' + labs + ') · [' + labels[1] + '](' + base + ')\n' + END


def with_block(text: str, slug: str) -> str:
    english = len(re.findall('[А-Яа-яЁё]', text)) < 10
    managed = block(slug, english)
    if START in text and END in text:
        text = re.sub(re.escape(START) + r'[\s\S]*?' + re.escape(END) + r'\n*', '', text, count=1)
    # Replace the earlier two-link pilot with the standard managed placement.
    text = re.sub(r'^\[Текущие программы AI Mindset\].*?github-.*\n\n', '', text, flags=re.M)
    picture = re.search(r'^<picture>[\s\S]*?</picture>\s*\n', text)
    heading = re.search(r'^# [^\n]*\n', text, re.M)
    pos = picture.end() if picture else heading.end() if heading else 0
    prefix = text[:pos].rstrip()
    suffix = text[pos:].lstrip()
    return (prefix + '\n\n' if prefix else '') + managed + ('\n\n' + suffix if suffix else '\n')


def safe_path(root: Path, path: Path) -> bool:
    cursor = root
    for part in path.relative_to(root).parts:
        cursor = cursor / part
        if cursor.is_symlink():
            return False
    return path.resolve().is_relative_to(root.resolve())


def files(root: Path):
    output = subprocess.check_output(['git', '-C', str(root), 'ls-files', '-z'], text=True)
    for name in output.split('\0'):
        p = Path(name)
        if p.suffix.lower() not in ('.md', '.markdown', '.mdx', '.html', '.htm'):
            continue
        if any(x in ('node_modules', 'vendor', '.worktrees', '.git') for x in p.parts):
            continue
        full = root / p
        if not safe_path(root, full):
            yield name, full, 'symlink-or-out-of-root-document'
        elif full.stat().st_size > 4_000_000:
            yield name, full, 'document-exceeds-4mb'
        else:
            yield name, full, None


def run(root: Path, slug: str, fix=False):
    if not re.fullmatch(r'[a-zA-Z0-9._-]{1,100}', slug):
        raise ValueError('invalid repository slug')
    primary = root / 'README.md'
    if fix and safe_path(root, primary) and not primary.exists():
        primary.write_text('# ' + slug + '\n')
    surfaces = [primary] + ([root / 'profile/README.md'] if slug == '.github' else [])
    if fix:
        for f in surfaces:
            if safe_path(root, f) and f.exists() and f.stat().st_size <= 4_000_000:
                f.write_text(with_block(f.read_text(), slug))
    findings, scanned = [], []
    paths = {}
    for name, f, error in files(root):
        if error:
            findings.append({'file':name, 'line':1, 'reasons':[error]})
        else:
            paths[name] = f
    for f in surfaces:
        if not safe_path(root, f):
            if not any(row['file'] == str(f.relative_to(root)) for row in findings):
                findings.append({'file':str(f.relative_to(root)), 'line':1, 'reasons':['symlink-or-out-of-root-document']})
        elif f.exists() and f.stat().st_size > 4_000_000:
            if not any(row['file'] == str(f.relative_to(root)) for row in findings):
                findings.append({'file':str(f.relative_to(root)), 'line':1, 'reasons':['document-exceeds-4mb']})
        elif f.exists():
            paths[str(f.relative_to(root))] = f
    for name, f in sorted(paths.items()):
        try:
            original = f.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            findings.append({'file':name, 'line':1, 'reasons':['non-utf8-document-needs-review']})
            continue
        updated, rows = inspect(original, slug, f.suffix.lower() not in ('.html', '.htm'), fix)
        if fix and updated != original:
            f.write_text(updated, encoding='utf-8')
            _, rows = inspect(updated, slug, f.suffix.lower() not in ('.html', '.htm'))
        scanned.append(name)
        findings.extend(dict(file=name, **r) for r in rows)
    for f in surfaces:
        if not safe_path(root, f) or (f.exists() and f.stat().st_size > 4_000_000):
            continue  # Already a blocking finding; never follow it, even with --fix.
        if not f.exists() or f.read_text().count(START) != 1 or f.read_text().count(END) != 1:
            findings.append({'file':str(f.relative_to(root)), 'line':1, 'reasons':['missing-or-duplicate-labs-block']})
        elif with_block(f.read_text(), slug) != f.read_text():
            findings.append({'file':str(f.relative_to(root)), 'line':1, 'reasons':['labs-block-drift']})
    return {'repository':slug, 'scanned_files':scanned, 'findings':findings, 'pass':not findings}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path('.'))
    parser.add_argument('--slug', required=True)
    parser.add_argument('--fix', action='store_true', help='rewrite only eligible document links and standard README blocks')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()
    try:
        result = run(args.repo.resolve(), args.slug, args.fix)
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        result = {'repository':args.slug, 'pass':False, 'error':str(exc)}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        for item in result.get('findings', []):
            print(f"{item['file']}:{item['line']}: {', '.join(item['reasons'])}")
        print(('PASS' if result['pass'] else 'FAIL') + ': ' + args.slug)
    return 0 if result['pass'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
