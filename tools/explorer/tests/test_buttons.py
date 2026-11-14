"""Generic 'no dead control' sweep.

For each view (with a sensible selection) and each inspector tab, every visible, enabled element with a data-testid that is a
button, link, checkbox, select or [role=tab] is activated (click; select: another option).  Each activation must change at least one of:
URL, the DOM of .app (minus canvases, plus form state), otx.store state, localStorage, engine switches, a canvas pixel hash (stage screenshot),
a popover / toast, fullscreen / focus mode, theme.  Controls that change nothing, or that raise a console / network error, are
collected and reported in one failure per scenario (and written to <shots>/dead-controls.json).

The shell controls (top bar, rail, panel heads, stage bar) are swept once, in the 'shell' scenario; view scenarios sweep the view's own tools and tabs.
"""
import json, re, pytest
from helpers import *

pytestmark = pytest.mark.slow

CONTROLS = """() => {
  const out = [];
  document.querySelectorAll('[data-testid]').forEach((e) => {
    const t = e.tagName, ty = (e.getAttribute('type') || '').toLowerCase(), role = e.getAttribute('role');
    const ok = t === 'BUTTON' || t === 'A' || t === 'SELECT' || (t === 'INPUT' && ty === 'checkbox') || role === 'tab';
    if (!ok || e.disabled || e.closest('[hidden]') || e.getAttribute('aria-disabled') === 'true') return;
    const r = e.getBoundingClientRect(); const lab = ty === 'checkbox' && e.closest('label');
    const vis = (r.width > 0 && r.height > 0 && getComputedStyle(e).visibility !== 'hidden' && getComputedStyle(e).display !== 'none');
    const labVis = lab && lab.getBoundingClientRect().width > 0;
    if (!vis && !labVis) return;
    out.push({id: e.dataset.testid, tag: t, type: ty, seg: !!e.closest('.seg,.presets'), n: out.filter((o) => o.id === e.dataset.testid).length});
  });
  return out;
}"""

SHELL_IDS = re.compile(r'^(die-|view-|fresh-chip|theme|help|nav-|insp-hide|insp-show|copy-link|focus|fullscreen|reload-data|split-)')
SCENARIOS = [
    # name, hash, tabs, shell?
    ('shell', '#/overview/s81', [None], True),
    ('overview', '#/overview/s81', [None], False),
    ('plan-die', '#/plan/s81', [None, 'overlays'], False),
    ('plan-type', '#/plan/%s?inst=%s' % (SIGNED_TYPE, S_INST), [None, 'overlays'], False),
    ('layout', '#/layout/%s?inst=%s' % (SIGNED_TYPE, S_INST), [None, 'layers'], False),
    ('element-routed', '#/element/' + ROUTED_TYPE, [None, 'layers', 'timing', 'checks'], False),
    ('element-core', '#/element/' + SMALL_CORE, [None, 'layers'], False),
    ('element-plan', '#/element/%s?mode=plan' % FAILED_TYPE, [None], False),
    ('element-picker', '#/element/s81', [None], False),
    ('dataflow', '#/dataflow/s81', [None], False),
    ('token', '#/token/s81', [None], False),
    ('closure', '#/closure/s81', [None], False),
]


def open_panel(page, tab):
    if tab:
        page.get_by_test_id('insp-tab-' + tab).click()


def restore(page, base, base_view):
    """back to the scenario's page state after one activation"""
    page.evaluate("""() => { document.querySelectorAll('[data-testid=popover]').forEach((p) => p.remove());
      if (document.fullscreenElement) document.exitFullscreen(); otx.shell.setFocus(false);
      if (document.querySelector('.app').dataset.nav !== 'open') otx.shell.setPanel('nav', true);
      if (document.querySelector('.app').dataset.insp !== 'open') otx.shell.setPanel('insp', true); }""")
    cur = re.sub(r'([?&])cam=[^&]*&?', r'\1', page.evaluate('location.hash')).rstrip('?&')
    if cur != base:
        nav_hash(page, base)
        wait_settled(page, base_view, timeout=120000)
        page.wait_for_timeout(300)
    if page.evaluate("otx.eng && otx.eng.rulerMode"): page.evaluate('otx.eng.setRuler(false)')


def stage_shot(page):
    return md5(page.screenshot(clip={'x': 60, 'y': 40, 'width': 900, 'height': 700}, timeout=60000))


def activate(page, c):
    loc = page.locator('[data-testid="%s"]' % c['id']).nth(c['n'])
    if c['tag'] == 'SELECT':
        vals = loc.evaluate('(s) => [...s.options].map((o) => o.value)'); cur = loc.input_value()
        other = next((v for v in vals if v != cur), None)
        if other is None: return 'single-option select'
        loc.select_option(other)
    elif c['type'] == 'checkbox':
        if loc.is_visible(): loc.click()
        else: loc.evaluate('(e) => e.closest("label").click()')
    else:
        loc.scroll_into_view_if_needed(); loc.click()
    return None


def sweep(page, name, hash_, tabs, shell):
    dead, errs, notes, count = [], [], [], 0
    page.set_default_timeout(8000)
    goto(page, hash_, engine=name.startswith(('layout', 'element-routed', 'element-core')))
    base_view = hash_.split('/')[1].split('?')[0]
    page.wait_for_timeout(1500)
    for tab in tabs:
        restore(page, hash_, base_view)
        open_panel(page, tab)
        page.wait_for_timeout(300)
        todo = [c for c in page.evaluate(CONTROLS) if bool(SHELL_IDS.match(c['id'])) == shell and not c['id'].startswith('insp-tab-') and c['id'] != 'view-' + base_view]
        for c in todo:
            try:
                restore(page, hash_, base_view); open_panel(page, tab)
            except Exception as e:
                notes.append('%s: restore failed (%s)' % (c['id'], str(e).splitlines()[0][:100])); continue
            if page.locator('[data-testid="%s"]' % c['id']).count() <= c['n']: notes.append('%s vanished' % c['id']); continue
            before_err = len(page.errors)
            page.mouse.move(5, 5)
            snap0, px0, url0 = snap_state(page), stage_shot(page), page.url
            try: why = activate(page, c)
            except Exception as e:
                notes.append('%s: could not activate (%s)' % (c['id'], str(e).splitlines()[0][:120])); continue
            page.wait_for_timeout(350)
            page.mouse.move(5, 5)
            try: snap1 = snap_state(page)
            except Exception: snap1 = 'navigated'
            count += 1
            new_err = page.errors[before_err:]
            if new_err: errs.append((c['id'], new_err[:3]))
            if snap1 != snap0 or why: continue
            try: px1 = stage_shot(page)
            except Exception: px1 = px0
            if px1 != px0 or page.url != url0: continue
            if c['seg']:     # the current choice of a segmented control: a click on it is a no-op by design; click a sibling first, then retry
                try:
                    loc = page.locator('[data-testid="%s"]' % c['id']).nth(c['n'])
                    loc.evaluate("(e) => { const o = [...e.closest('.seg,.presets').querySelectorAll('button')].find((b) => b !== e && !b.disabled); if (o) o.click(); }")
                    page.wait_for_timeout(2500); page.mouse.move(5, 5)
                    s2, p2 = snap_state(page), stage_shot(page)
                    activate(page, c); page.wait_for_timeout(2500); page.mouse.move(5, 5)
                    if snap_state(page) != s2 or stage_shot(page) != p2: continue
                except Exception as e: notes.append('%s: seg retry failed (%s)' % (c['id'], str(e).splitlines()[0][:80]))
            dead.append(c['id'])
    return count, dead, errs, notes


@pytest.mark.parametrize('name,hash_,tabs,shell', SCENARIOS, ids=[s[0] for s in SCENARIOS])
def test_no_dead_controls(page, name, hash_, tabs, shell):
    count, dead, errs, notes = sweep(page, name, hash_, tabs, shell)
    SHOTS.mkdir(parents=True, exist_ok=True)
    (SHOTS / ('dead-controls-%s.json' % name)).write_text(json.dumps(dict(scenario=name, hash=hash_, activated=count, dead=dead, errors=errs, notes=notes), indent=1))
    page.errors.clear()      # reported below, per control, instead of at the end of the test
    assert count > 0 or name in ('dataflow', 'token', 'closure', 'element-picker', 'element-plan', 'overview'), 'no control found in scenario ' + name
    assert not dead, 'controls that did nothing (%d of %d activated): %s' % (len(dead), count, dead)
    assert not errs, 'controls that raised errors: %s' % errs
