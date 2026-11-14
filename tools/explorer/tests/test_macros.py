"""Owner question 2026-11-14: "in the element routed view, how can you know which macro it is?"
Macro identity: outline + label, colour by master with a legend, hover tooltip, click = select (inspector card, URL),
navigator rows (hover highlights, click zooms).  Self-contained:  pytest tests/test_macros.py -q"""
import os, time
import pytest

BASE = os.environ.get('EXPLORER_URL', 'http://127.0.0.1:8770')
ARGS = ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist']
TYPE = 's81.t.col_h10_r0_p4__t1__pvc9270d09'      # no pack of its own: 95 macros at plan placement, many masters
READY = "window.otx && window.otx.eng && window.otx.eng.marks.length > 0 && window.otx.eng.deck && window.otx.eng.deck.getViewports()[0]"
# screen position of the centre of a mark, and the largest mark that is a hard core
PICK = """() => { const e = window.otx.eng, vp = e.deck.getViewports()[0], r = document.querySelector('[data-testid=layout-canvas]').getBoundingClientRect();
  const ms = e.marks.slice().sort((a, b) => (b.bb[2] - b.bb[0]) * (b.bb[3] - b.bb[1]) - (a.bb[2] - a.bb[0]) * (a.bb[3] - a.bb[1])); const m = ms[%d];
  const p = vp.project([(m.bb[0] + m.bb[2]) / 2, (m.bb[1] + m.bb[3]) / 2]); return { key: m.key, label: m.label, sub: m.sub, ci: m.ci, x: r.left + p[0], y: r.top + p[1] }; }"""
LAYERS = "() => Object.fromEntries(window.otx.eng.deck.props.layers.filter((l) => l.id === 'marks' || l.id === 'marklabels').map((l) => [l.id, l.props.data.length]))"


# the browser fixture comes from conftest.py (one Chromium per session)


def open_page(browser, hash_):
    pg = browser.new_page(viewport={'width': 1600, 'height': 1000}); pg.errs = []
    pg.on('pageerror', lambda e: pg.errs.append(str(e)))
    pg.goto(BASE + hash_, wait_until='load'); pg.wait_for_function(READY, timeout=90000); time.sleep(1.0)
    return pg


def test_element_macros_are_outlined_labelled_and_coloured_by_master(browser):
    pg = open_page(browser, '/#/element/' + TYPE)
    marks = pg.evaluate("window.otx.eng.marks.map((m) => [m.key, m.sub, m.ci])")
    assert len(marks) >= 40
    by_master = {}
    for k, sub, ci in marks: by_master.setdefault(sub, set()).add(ci)
    assert all(len(v) == 1 for v in by_master.values()), 'one colour per master'
    assert len({ci for _, _, ci in marks if ci >= 0}) >= 4, 'repeated masters get distinct colours'
    lay = pg.evaluate(LAYERS)
    assert lay.get('marks', 0) >= 40 and lay.get('marklabels', 0) >= 5, lay            # outlines drawn, big ones labelled
    legend = pg.inner_text('[data-testid=macro-legend]')
    assert 'by master' in legend and '×' in legend
    pg.click('[data-testid=el-labels]')                                                # Labels toggle
    pg.wait_for_function("!window.otx.eng.deck.props.layers.some((l) => l.id === 'marklabels')")
    assert 'labels=0' in pg.url and pg.get_attribute('[data-testid=el-labels]', 'aria-pressed') == 'false'
    pg.click('[data-testid=el-labels]')
    pg.wait_for_function("window.otx.eng.deck.props.layers.some((l) => l.id === 'marklabels')")
    assert not pg.errs, pg.errs
    pg.close()


def test_element_macro_hover_click_select_url_and_inspector(browser):
    pg = open_page(browser, '/#/element/' + TYPE)
    m = pg.evaluate(PICK % 0)
    pg.mouse.move(m['x'] - 3, m['y'] - 3); pg.mouse.move(m['x'], m['y'])
    pg.wait_for_selector('[data-testid=tip-macro]', timeout=15000)                     # tooltip: instance, master, size, orient, state
    tip = pg.inner_text('[data-testid=tip-macro]')
    assert m['label'] in tip and 'master' in tip and '×' in tip and 'µm' in tip, tip
    pg.mouse.click(m['x'], m['y'])                                                     # click selects
    pg.wait_for_function("window.otx.store.get().sel.inst === %r" % m['key'], timeout=15000)
    assert pg.evaluate("window.otx.eng.selMark") == m['key']
    assert 'inst=' in pg.url
    pg.wait_for_selector('[data-testid=macro-card]')
    card = pg.inner_text('[data-testid=macro-card]')
    assert m['key'] in card and 'master' in card and 'size' in card, card
    if pg.query_selector('[data-testid=macro-open-core]'):                             # a hard core links to its own Element page
        href = pg.get_attribute('[data-testid=macro-open-core]', 'href'); assert '#/element/s81.c.' in href, href
    url = pg.url
    pg.reload(wait_until='load'); pg.wait_for_function(READY, timeout=90000)           # the selection is in the URL
    pg.wait_for_function("window.otx.eng.selMark === %r" % m['key'], timeout=20000)
    assert pg.url == url or 'inst=' in pg.url
    pg.wait_for_selector('[data-testid=macro-card]')
    assert not pg.errs, pg.errs
    pg.close()


def test_navigator_lists_macros_hover_highlights_click_zooms(browser):
    pg = open_page(browser, '/#/element/' + TYPE)
    rows = pg.query_selector_all('[data-testid=nav-tree] [data-macro]')
    assert len(rows) >= 40, len(rows)
    key = rows[3].get_attribute('data-macro')
    rows[3].scroll_into_view_if_needed(); rows[3].hover()
    pg.wait_for_function("window.otx.eng.hotMark === %r" % key, timeout=10000)         # hover a row = highlight on the canvas
    z0 = pg.evaluate("window.otx.eng.cam().z")
    rows[3].click()
    pg.wait_for_function("window.otx.eng.selMark === %r" % key, timeout=15000)
    pg.wait_for_function("window.otx.eng.cam().z > %f + 0.5" % z0, timeout=15000)      # click a row = select and zoom to it
    pg.wait_for_function("(k) => { const e = window.otx.eng, m = e.marks.find((x) => x.key === k), c = e.cam(); return c.x >= m.bb[0] && c.x <= m.bb[2] && c.y >= m.bb[1] && c.y <= m.bb[3]; }", arg=key, timeout=15000)   # the camera lands on it (animated)
    # the inspector list does the same
    pg.click('[data-testid=insp-tab-macros]')
    r2 = pg.query_selector_all('[data-testid=macro-list] [data-macro]')
    assert len(r2) >= 40
    k2 = r2[10].get_attribute('data-macro'); r2[10].scroll_into_view_if_needed(); r2[10].hover()
    pg.wait_for_function("window.otx.eng.hotMark === %r" % k2, timeout=10000)
    assert not pg.errs, pg.errs
    pg.close()


def test_die_layout_cores_have_identity(browser):
    pg = open_page(browser, '/#/layout/hbm?cam=14200.00,9300.00,-1.2')
    assert pg.evaluate("window.otx.eng.marks.length") > 500
    assert 'by master' in pg.inner_text('[data-testid=macro-legend]')
    m = pg.evaluate("""() => { const e = window.otx.eng, vp = e.deck.getViewports()[0], r = document.querySelector('[data-testid=layout-canvas]').getBoundingClientRect();
      for (const k of e.marks) { const p = vp.project([(k.bb[0] + k.bb[2]) / 2, (k.bb[1] + k.bb[3]) / 2]); if (p[0] > 250 && p[0] < r.width - 320 && p[1] > 200 && p[1] < r.height - 150 && (k.bb[2] - k.bb[0]) * Math.pow(2, e.cam().z) > 40) return { key: k.key, label: k.label, x: r.left + p[0], y: r.top + p[1] }; } return null; }""")
    assert m, 'a hard core large enough to click'
    pg.mouse.move(m['x'] - 2, m['y'] - 2); pg.mouse.move(m['x'], m['y'])
    pg.wait_for_selector('[data-testid=tip-macro]', timeout=15000)
    assert 'hard core' in pg.inner_text('[data-testid=tip-macro]')
    pg.mouse.click(m['x'], m['y'])
    pg.wait_for_function("window.otx.store.get().sel.inst === %r" % m['key'], timeout=15000)   # identity = <partition>/<instance>
    assert '/' in m['key'] and pg.evaluate("window.otx.eng.selMark") == m['key']
    pg.wait_for_selector('[data-testid=macro-card]')
    assert '#/element/hbm.c.' in pg.get_attribute('[data-testid=macro-open-core]', 'href')
    pg.click('[data-testid=layout-labels]')
    pg.wait_for_function("!window.otx.eng.deck.props.layers.some((l) => l.id === 'marklabels')")
    assert not pg.errs, pg.errs
    pg.close()
