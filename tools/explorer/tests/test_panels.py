"""Owner bug 2026-11-14: "when the inspector is hidden, the main area did not take the full width".
Collapsing a panel must give its width back to the stage at once, in every view, and the canvas must follow.
Self-contained (own browser) so it can run alone:  pytest tests/test_panels.py -q"""
import os, time
import pytest

BASE = os.environ.get('EXPLORER_URL', 'http://127.0.0.1:8770')
ARGS = ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist']
VW, VH = 1600, 1000
VIEWS = [('overview', 's81', None), ('plan', 's81', '[data-testid=plan-canvas]'), ('layout', 's81_head', '[data-testid=layout-canvas] canvas'),
         ('element', 's81.c.dsfd_qbank_S', '[data-testid=layout-canvas] canvas'), ('dataflow', 'hbm', '[data-testid=plan-canvas]'), ('token', 's81', None), ('closure', 'qwen_kvsys', None), ('fleet', 's81', None)]
GEOM = """(sel) => { const r = (q) => { const e = document.querySelector(q); if (!e) return null; const b = e.getBoundingClientRect(); return b.width ? [Math.round(b.left), Math.round(b.width), Math.round(b.height)] : null; };
  const app = document.querySelector('.app'); return { stage: r('.stage'), body: r('[data-testid=stage]'), nav: r('.nav'), insp: r('.insp'), rail: r('.rail'), canvas: sel ? r(sel) : null,
    navState: app.dataset.nav, inspState: app.dataset.insp, focus: app.dataset.focus, vw: innerWidth, vh: innerHeight }; }"""


# the browser fixture comes from conftest.py (one Chromium per session)


def settle(pg, sel, want_w, timeout=20):
    """wait until the stage (and the canvas, when the view has one) has the wanted width"""
    t0 = time.time(); g = None
    while time.time() - t0 < timeout:
        g = pg.evaluate(GEOM, sel)
        if g['stage'] and abs(g['stage'][1] - want_w) <= 1 and (not sel or (g['canvas'] and abs(g['canvas'][1] - g['body'][1]) <= 1)): return g
        time.sleep(0.25)
    return g


@pytest.mark.parametrize('view,node,canvas', VIEWS, ids=[v[0] for v in VIEWS])
def test_hidden_panels_give_their_width_to_the_stage(browser, view, node, canvas):
    pg = browser.new_page(viewport={'width': VW, 'height': VH}); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto('%s/#/%s/%s' % (BASE, view, node), wait_until='load')
    pg.wait_for_selector('.app'); pg.wait_for_function("window.otx && window.otx.store.get().view === '%s'" % view)
    pg.evaluate("() => { for (const k of ['nav', 'insp']) if (document.querySelector('.app').dataset[k] !== 'open') document.querySelector('[data-testid=' + k + '-show]').click(); }")
    if canvas: pg.wait_for_selector(canvas, timeout=60000)
    g0 = pg.evaluate(GEOM, canvas); rail = g0['rail'][1]
    g = settle(pg, canvas, VW - rail - g0['nav'][1] - g0['insp'][1])
    assert g['stage'][1] == VW - rail - g['nav'][1] - g['insp'][1], ('both open', g)
    navw, inspw = g['nav'][1], g['insp'][1]

    pg.click('[data-testid=insp-hide]')                                   # inspector hidden: the stage reaches the right edge
    g = settle(pg, canvas, VW - rail - navw)
    assert g['inspState'] == 'closed' and g['insp'] is None, g
    assert g['stage'][1] == VW - rail - navw and g['stage'][0] + g['stage'][1] == VW, ('inspector hidden', g)
    if canvas: assert abs(g['canvas'][1] - g['body'][1]) <= 1 and abs(g['canvas'][2] - g['body'][2]) <= 1, ('canvas after inspector hidden', g)

    pg.click('[data-testid=nav-hide]')                                    # both hidden: the stage is the viewport minus the rail
    g = settle(pg, canvas, VW - rail)
    assert g['stage'][1] == VW - rail and g['stage'][0] == rail, ('both hidden', g)
    if canvas: assert abs(g['canvas'][1] - (VW - rail)) <= 1, ('canvas after both hidden', g)

    pg.click('[data-testid=insp-show]')                                   # inspector back, navigator still hidden
    g = settle(pg, canvas, VW - rail - inspw)
    assert g['stage'][1] == VW - rail - inspw and g['stage'][0] == rail, ('navigator hidden', g)
    pg.keyboard.press('[')                                                # keys do the same
    g = settle(pg, canvas, VW - rail - navw - inspw)
    assert g['stage'][1] == VW - rail - navw - inspw, ('navigator restored by key', g)

    pg.click('[data-testid=focus]')                                       # focus mode: the stage is the whole window
    g = settle(pg, canvas, VW)
    assert g['focus'] == '1' and g['stage'][1] == VW and g['stage'][2] == VH and g['stage'][0] == 0, ('focus mode', g)
    if canvas: assert abs(g['canvas'][1] - VW) <= 1 and abs(g['canvas'][2] - VH) <= 1, ('canvas in focus mode', g)
    pg.keyboard.press('Escape')
    g = settle(pg, canvas, VW - rail - navw - inspw)
    assert g['focus'] == '0' and g['stage'][1] == VW - rail - navw - inspw, ('after focus mode', g)

    pg.click('[data-testid=fullscreen]')                                  # browser full screen (headless: the element fills the screen)
    pg.wait_for_function("document.querySelector('.app').dataset.focus === '1'")
    g = settle(pg, canvas, pg.evaluate('innerWidth'))
    assert g['stage'][1] == g['vw'] and g['stage'][2] == g['vh'], ('full screen', g)
    if canvas: assert abs(g['canvas'][1] - g['vw']) <= 1, ('canvas in full screen', g)
    pg.evaluate("document.fullscreenElement ? document.exitFullscreen() : null"); pg.keyboard.press('Escape')
    assert not errs, errs
    pg.close()


def test_hidden_panel_state_survives_reload(browser):
    cx = browser.new_context(viewport={'width': VW, 'height': VH}); pg = cx.new_page()
    pg.goto(BASE + '/#/plan/s81', wait_until='load'); pg.wait_for_selector('[data-testid=plan-canvas]')
    if pg.evaluate("document.querySelector('.app').dataset.insp") == 'open': pg.click('[data-testid=insp-hide]')
    pg.reload(wait_until='load'); pg.wait_for_selector('[data-testid=plan-canvas]')
    g = settle(pg, '[data-testid=plan-canvas]', VW - pg.evaluate(GEOM, None)['rail'][1] - (pg.evaluate(GEOM, None)['nav'] or [0, 0])[1])
    assert g['inspState'] == 'closed' and g['stage'][0] + g['stage'][1] == VW, g
    cx.close()
