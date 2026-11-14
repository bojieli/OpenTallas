"""Fixtures: a session browser (software WebGL), a fresh context + page per test that records console errors, page errors,
failed requests and HTTP >= 400 responses and FAILS the test when any occurred (opt out with @pytest.mark.allow_errors,
optionally with substrings to tolerate: @pytest.mark.allow_errors('HTTP 404', '/api/v1/node/'))."""
import os, pytest
from playwright.sync_api import sync_playwright
import helpers

ARGS = ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist']


class _Box:
    """session browser; relaunched after a renderer / GPU crash (software WebGL on a loaded host can take the page down)"""
    def __init__(self): self.p = sync_playwright().start(); self.b = None; self.bad = False
    def get(self):
        if self.b is None or self.bad or not self.b.is_connected():
            if self.b is not None:
                try: self.b.close()
                except Exception: pass
            self.b = self.p.chromium.launch(headless=True, args=ARGS + ['--disable-dev-shm-usage']); self.bad = False
        return self.b


@pytest.fixture(scope='session')
def _box():
    bx = _Box()
    yield bx
    try:
        if bx.b: bx.b.close()
    finally: bx.p.stop()


@pytest.fixture
def browser(_box): return _box.get()


@pytest.fixture
def page(browser, request, _box):
    ctx = browser.new_context(viewport={'width': 1600, 'height': 1000}, color_scheme='light', permissions=['clipboard-read', 'clipboard-write'])
    pg = ctx.new_page()
    pg.set_default_timeout(30000)
    pg.errors = []
    pg.on('console', lambda m: pg.errors.append('console.error: %s @ %s' % (m.text, m.location.get('url', ''))) if m.type == 'error' and not m.text.startswith('Failed to load resource') else None)
    pg.on('console', lambda m: pg.errors.append('layout worker error: %s' % m.text[:240]) if m.type == 'warning' and 'layout worker' in m.text and 'error' in m.text else None)
    pg.on('pageerror', lambda e: pg.errors.append('pageerror: %s' % e))
    pg.on('requestfailed', lambda r: pg.errors.append('requestfailed: %s %s (%s)' % (r.method, r.url, r.failure)) if 'ERR_ABORTED' not in str(r.failure) else None)
    pg.on('response', lambda r: pg.errors.append('HTTP %d %s' % (r.status, r.url)) if r.status >= 400 else None)
    pg.on('crash', lambda *_: setattr(_box, 'bad', True))
    pg.errors_crashed = False
    request.node.page_ref = pg
    yield pg
    try: ctx.close()
    except Exception: _box.bad = True


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    out = yield
    rep = out.get_result()
    pg = getattr(item, 'page_ref', None)
    if rep.when != 'call' or pg is None or not rep.passed: return
    mk = item.get_closest_marker('allow_errors')
    errs = list(pg.errors)
    if mk is not None:
        errs = [e for e in errs if mk.args and not any(a in e for a in mk.args)]
    if errs:
        rep.outcome = 'failed'
        rep.longrepr = 'browser errors during the test (%d):\n  ' % len(errs) + '\n  '.join(e[:300] for e in errs[:12])
