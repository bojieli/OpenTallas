"""Static checks of the web sources (no browser): colour tokens, accessible icon buttons, ES module imports."""
import pathlib, re
import pytest
from helpers import SRC, http

WEB = SRC / 'web'
HEX = re.compile(r'#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})\b')


def lines(p): return p.read_text().split('\n')


def allowed_ranges(p):
    """0-based line ranges where hex literals are legitimate: the PAL palette block and GLSL shader strings of the engine"""
    if p.name != 'layout-engine.js' or p.parent.name != 'engine': return []
    L = lines(p); out = []
    s = next((i for i, l in enumerate(L) if l.startswith('export const PAL')), None)
    if s is not None:
        e = next((i for i in range(s + 1, len(L)) if re.match(r'^(export const|const|function|class)\b', L[i])), len(L))
        out.append((s, e - 1))
    for i, l in enumerate(L):    # GLSL template literals: from the opening backtick line to the closing one
        if re.search(r'#version|precision (?:highp|mediump)|void main\(', l):
            lo = max(k for k in range(0, i + 1) if '`' in L[k]); hi = min((k for k in range(i, len(L)) if '`' in L[k] and k != lo), default=len(L) - 1)
            out.append((lo, hi))
    return out


def hex_hits(p):
    ok = allowed_ranges(p)
    return [(i + 1, l.strip()[:100]) for i, l in enumerate(lines(p)) if HEX.search(l) and not any(a <= i <= b for a, b in ok)]


def test_palette_block_is_found():
    p = WEB / 'js' / 'engine' / 'layout-engine.js'
    r = allowed_ranges(p)
    assert r and r[0][1] - r[0][0] < 12, 'PAL block range should be a handful of lines: %s' % r
    assert any(HEX.search(l) for l in lines(p)[r[0][0]:r[0][1] + 1])


@pytest.mark.parametrize('p', sorted((WEB / 'css').glob('*.css')), ids=lambda p: p.name)
def test_no_hex_in_css(p):
    if p.name == 'tokens.css': pytest.skip('tokens.css is where colours live')
    assert not hex_hits(p), 'hex colour literals (use a token from tokens.css): %s' % hex_hits(p)[:6]


@pytest.mark.parametrize('p', sorted((WEB / 'js').rglob('*.js')), ids=lambda p: str(p.relative_to(WEB)))
def test_no_hex_in_js(p):
    assert not hex_hits(p), 'hex colour literals (read tokens via cssv()): %s' % hex_hits(p)[:6]


def test_no_hex_in_html():
    for p in WEB.glob('*.html'): assert not HEX.search(re.sub(r'&#\d+;|href="[^"]*"', '', p.read_text())), p


def _calls(src):
    """text of every h('button...' / h('a...' call, balanced parentheses, plus its line number"""
    for m in re.finditer(r"\bh\(\s*'(button|a)\b[^']*'", src):
        i = m.start(); depth = 0; j = i; q = None
        while j < len(src):
            c = src[j]
            if q:
                if c == '\\': j += 1
                elif c == q: q = None
            elif c in '\'"`': q = c
            elif c == '(': depth += 1
            elif c == ')':
                depth -= 1
                if depth == 0: break
            j += 1
        yield src.count('\n', 0, i) + 1, src[i:j + 1]


def test_icon_only_buttons_are_labelled():
    bad = []
    for p in sorted((WEB / 'js').rglob('*.js')):
        for ln, call in _calls(p.read_text()):
            if "icon('" not in call and 'icon(' not in call: continue
            # text content = string literals / template literals that are not attribute values or the icon name
            body = re.sub(r"icon\([^)]*\)", '', call)
            body = re.sub(r"'(?:type|aria-[a-z]+|title|href|testid|class|role)'\s*:\s*(?:'[^']*'|`[^`]*`|[^,}]+)", '', body)
            body = re.sub(r"dataset:\s*\{[^}]*\}", '', body)
            body = re.sub(r"\b(?:title|testid|type|href)\s*:\s*(?:'[^']*'|`[^`]*`)", '', body)
            body = re.sub(r"^h\(\s*'[^']*'", '', body)
            visible = re.findall(r"(?<![\w$])(?:'([^']{2,})'|`([^`]{2,})`)", body)
            has_text = bool(visible)
            if not has_text and not re.search(r"title\s*:|'aria-label'\s*:|aria-label", call): bad.append('%s:%d %s' % (p.relative_to(WEB), ln, call[:90].replace('\n', ' ')))
    assert not bad, 'icon-only buttons / links without title or aria-label:\n  ' + '\n  '.join(bad)


def test_all_icon_buttons_in_dom_labelled_hint():
    """every .btn.icon built in shell.js carries both title and aria-label"""
    src = (WEB / 'js' / 'shell' / 'shell.js').read_text()
    for ln, call in _calls(src):
        if '.icon' in call.split(',')[0]: assert 'title' in call and 'aria-label' in call, (ln, call[:100])


IMPORT = re.compile(r"""(?:^|\n)\s*(?:import\s+(?:[^'"]*?\s+from\s+)?|export\s+[^'"\n]*?\s+from\s+)['"]([^'"]+)['"]""")
DYN = re.compile(r"""import\(\s*['"]([^'"]+)['"]\s*\)""")


def test_module_imports_resolve():
    js = sorted((WEB / 'js').rglob('*.js')); missing = []
    for p in js:
        src = p.read_text()
        for spec in IMPORT.findall(src) + DYN.findall(src):
            if spec.startswith('http') or not spec.startswith(('.', '/')): missing.append('%s: bare specifier %s' % (p.relative_to(WEB), spec)); continue
            if spec.startswith('/') and not (WEB / spec.lstrip('/')).is_file():     # served by the server from another tree (engine, /fv, /explorer/...)
                if http(spec)[0] != 200: missing.append('%s -> %s (HTTP %s)' % (p.relative_to(WEB), spec, http(spec)[0]))
                continue
            t = (WEB / spec.lstrip('/')) if spec.startswith('/') else (p.parent / spec)
            if not t.resolve().is_file(): missing.append('%s -> %s' % (p.relative_to(WEB), spec))
    assert not missing, missing
    assert len(js) >= 15


def test_named_imports_exist():
    """each `import { a, b } from './x.js'` names exports that x.js has"""
    bad = []
    for p in sorted((WEB / 'js').rglob('*.js')):
        for names, spec in re.findall(r"import\s*\{([^}]*)\}\s*from\s*['\"](\.[^'\"]+)['\"]", p.read_text()):
            t = (p.parent / spec).resolve()
            if not t.is_file(): continue
            ex = t.read_text()
            for n in [x.strip().split(' as ')[0].strip() for x in names.split(',') if x.strip()]:
                if not re.search(r'export\s+(?:async\s+)?(?:const|let|var|function\*?|class)\s+%s\b|export\s*\{[^}]*\b%s\b' % (re.escape(n), re.escape(n)), ex): bad.append('%s imports %s from %s' % (p.relative_to(WEB), n, spec))
    assert not bad, bad


def test_html_assets_exist():
    html = (WEB / 'index.html').read_text()
    for ref in re.findall(r'(?:href|src)="(/[^"]+)"', html): assert (WEB / ref.lstrip('/')).is_file(), ref
