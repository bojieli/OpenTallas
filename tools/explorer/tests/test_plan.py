"""Plan view on three dies: canvas, selection by click, scope, colour-by, legend, overlays, fit."""
import re, pytest
from playwright.sync_api import expect
from helpers import *

CV = '[data-testid=plan-canvas]'


def type_with_pack(die): return pick_node(die, 'type', 'signed', True) or pick_node(die, 'type', 'signed', False)


def wait_painted(page):
    page.wait_for_function("""(s) => { const c = document.querySelector(s); if (!c || !c.width) return false; const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
      const seen = new Set(); for (let i = 0; i < d.length; i += 4 * 61) seen.add(d[i] + ',' + d[i + 1] + ',' + d[i + 2]); return seen.size > 4; }""", arg=CV, timeout=60000)


@pytest.mark.parametrize('die', DIES)
def test_plan_loads_clean_canvas_not_blank(page, die):
    goto(page, '#/plan/' + die)
    wait_painted(page)
    sig = canvas_signature(page, CV); assert sig['colours'] >= 5, sig
    expect(page.get_by_test_id('view-scope')).to_contain_text('partitions')
    expect(page.get_by_test_id('fresh-chip')).to_contain_text(re.compile(r'Data|Stale'))
    expect(page.get_by_test_id('plan-legend')).to_be_visible()
    expect(page.get_by_test_id('asof')).to_contain_text('data as of')


@pytest.mark.parametrize('die', DIES)
def test_plan_click_selects_partition(page, die):
    goto(page, '#/plan/' + die); wait_painted(page)
    box = page.get_by_test_id('plan-canvas').bounding_box()
    cx, cy = box['x'] + box['width'] / 2, box['y'] + box['height'] / 2
    hit = None
    pts = [(0, 0)] + [(dx * box['width'] / 12, dy * box['height'] / 12) for dy in range(-4, 5) for dx in range(-4, 5)]
    for k, (dx, dy) in enumerate(pts):
        page.mouse.click(cx + dx, cy + dy)
        s = store(page)
        if s['sel']['inst']: hit = (k, s); break
    assert hit, 'no click on the die plan selected a partition'
    s = hit[1]
    assert s['sel']['node'] and '.t.' in s['sel']['node'] and s['sel']['inst'], s
    assert ('inst=' in page.url) and (s['sel']['node'].split('.')[0] == die)
    assert hit[0] == 0, 'the canvas centre itself is not on a partition (first hit at probe #%d)' % hit[0]
    expect(page.get_by_test_id('crumbs')).to_contain_text(s['sel']['inst'])


def test_plan_double_click_opens_element(page):
    goto(page, '#/plan/s81'); wait_painted(page)
    box = page.get_by_test_id('plan-canvas').bounding_box()
    for dx in range(-4, 5):
        page.mouse.dblclick(box['x'] + box['width'] / 2 + dx * 60, box['y'] + box['height'] / 2)
        if view(page) == 'element': break
    assert view(page) == 'element' and store(page)['sel']['inst']


def view(page): return page.evaluate('otx.store.get().view')


def test_plan_tooltip_on_hover(page):
    goto(page, '#/plan/s81'); wait_painted(page)
    box = page.get_by_test_id('plan-canvas').bounding_box()
    for dx in range(-5, 6):
        page.mouse.move(box['x'] + box['width'] / 2 + dx * 50, box['y'] + box['height'] / 2)
        if page.locator('.canvas-host .tip:not([hidden])').count(): break
    expect(page.locator('.canvas-host .tip:not([hidden])')).to_contain_text('click: select')


@pytest.mark.parametrize('die', DIES)
def test_plan_scope_switch(page, die):
    nid = type_with_pack(die)
    goto(page, '#/plan/' + die)
    expect(page.get_by_test_id('plan-scope-type')).to_be_disabled()           # die-level selection has no type scope
    expect(page.get_by_test_id('plan-scope-die')).to_have_attribute('aria-pressed', 'true')
    goto(page, '#/plan/' + nid); wait_painted(page)
    expect(page.get_by_test_id('plan-scope-type')).to_be_enabled()
    a = canvas_signature(page, CV)
    page.get_by_test_id('plan-scope-type').click()
    page.wait_for_function("() => otx.store.get().params.scope === 'type'")
    expect(page.get_by_test_id('plan-scope-type')).to_have_attribute('aria-pressed', 'true')
    expect(page.get_by_test_id('view-scope')).to_contain_text('plan contents')
    expect(page.get_by_test_id('plan-colorby')).to_be_hidden()
    page.wait_for_timeout(400); b = canvas_signature(page, CV)
    assert a['hash'] != b['hash'], 'canvas unchanged after scope switch'
    page.get_by_test_id('insp-tab-overlays').click()
    expect(page.get_by_test_id('plan-ov-buses')).to_be_visible()                 # type overlays
    page.get_by_test_id('plan-scope-die').click()
    page.wait_for_function("() => !otx.store.get().params.scope")
    expect(page.get_by_test_id('plan-colorby')).to_be_visible()


@pytest.mark.parametrize('die', DIES)
def test_plan_colour_by(page, die):
    goto(page, '#/plan/' + die); wait_painted(page)
    sel = page.get_by_test_id('plan-colorby')
    leg = page.get_by_test_id('plan-legend')
    page.wait_for_timeout(300); a = canvas_signature(page, CV)
    sel.select_option('pack')
    page.wait_for_function("() => otx.store.get().params.color === 'pack'")
    expect(leg).to_contain_text('routed pack')
    page.wait_for_timeout(300); b = canvas_signature(page, CV); assert a['hash'] != b['hash']
    sel.select_option('vis'); page.wait_for_function("() => otx.store.get().params.color === 'vis'")
    expect(leg).to_contain_text('not reviewed')
    sel.select_option('state'); page.wait_for_function("() => !otx.store.get().params.color")
    page.reload(wait_until='domcontentloaded'); wait_settled(page, 'plan')
    expect(page.get_by_test_id('plan-colorby')).to_have_value('state')
    goto(page, '#/plan/%s?color=vis' % die); expect(page.get_by_test_id('plan-colorby')).to_have_value('vis')


@pytest.mark.parametrize('die', DIES)
def test_plan_state_legend_toggle(page, die):
    goto(page, '#/plan/' + die); wait_painted(page)
    boxes = page.locator('[data-testid^=plan-state-]')
    assert boxes.count() >= 1
    tid = boxes.first.get_attribute('data-testid')
    page.wait_for_timeout(300); a = canvas_signature(page, CV)
    lab = page.locator('label:has([data-testid=%s])' % tid)
    lab.click()
    expect(page.get_by_test_id(tid)).not_to_be_checked()
    page.wait_for_timeout(400); b = canvas_signature(page, CV)
    assert a['hash'] != b['hash'], 'hiding a state did not change the canvas'
    page.locator('label:has([data-testid=%s])' % tid).click()
    expect(page.get_by_test_id(tid)).to_be_checked()
    page.wait_for_timeout(400); c = canvas_signature(page, CV)
    assert c['hash'] != b['hash'], 'showing the state again did not change the canvas'


def test_plan_overlay_checkboxes(page):
    goto(page, '#/plan/s81'); wait_painted(page)
    page.get_by_test_id('insp-tab-overlays').click()
    for k in ['seams', 'cores', 'clock', 'pg', 'names']:
        cb = page.get_by_test_id('plan-ov-' + k)
        expect(cb).to_be_visible()
        before = cb.is_checked()
        cb.click()
        assert cb.is_checked() != before
        ls = page.evaluate("JSON.parse(localStorage.getItem('otx.plan.ov'))")
        assert ls[k] == (not before), (k, ls)
    page.wait_for_timeout(300); a = canvas_signature(page, CV)
    page.get_by_test_id('plan-ov-names').click()
    page.wait_for_timeout(400)
    assert canvas_signature(page, CV)['hash'] != a['hash'], 'names overlay does not change the canvas'
    reload = page.reload(wait_until='domcontentloaded'); wait_settled(page, 'plan')
    page.get_by_test_id('insp-tab-overlays').click()
    assert page.get_by_test_id('plan-ov-pg').is_checked() != (False if False else not page.evaluate("JSON.parse(localStorage.getItem('otx.plan.ov')).pg"))


def _zoom_in(page):
    box = page.get_by_test_id('plan-canvas').bounding_box()
    page.mouse.move(box['x'] + 700, box['y'] + 400)
    for _ in range(4): page.mouse.wheel(0, -300)
    page.wait_for_timeout(700); page.mouse.move(5, 5)


def _cam(page):
    page.wait_for_timeout(700)      # the camera is written to the URL after a 300 ms debounce
    return page.evaluate('otx.store.get().params.cam')


def test_plan_fit_button(page):
    goto(page, '#/plan/s81'); wait_painted(page)
    page.get_by_test_id('plan-fit').click(); fit = _cam(page)
    for _ in range(2):
        _zoom_in(page); assert _cam(page) != fit, 'wheel did not zoom the plan'
        page.get_by_test_id('plan-fit').click()
        assert _cam(page) == fit, 'Fit button did not restore the fitted camera'


def test_plan_fit_key_works_without_canvas_focus(page):
    """the help popover lists F = 'Fit the canvas' as a global key (as on Layout / Element)"""
    goto(page, '#/plan/s81'); wait_painted(page)
    page.get_by_test_id('plan-fit').click(); fit = _cam(page)
    _zoom_in(page); assert _cam(page) != fit
    page.keyboard.press('f')
    assert _cam(page) == fit, 'F did not fit the plan (the key only works while the canvas has focus)'


def test_plan_camera_saved_in_url(page):
    goto(page, '#/plan/s81'); wait_painted(page)
    box = page.get_by_test_id('plan-canvas').bounding_box()
    page.mouse.move(box['x'] + 500, box['y'] + 400); page.mouse.wheel(0, -400)
    page.wait_for_function("() => /^[-\\d.]+,[-\\d.]+,[-\\d.]+$/.test(otx.store.get().params.cam || '')")


def test_plan_core_node_highlights_users(page):
    nid = pick_node('s81', 'core', 'signed', True)
    goto(page, '#/plan/' + nid); wait_painted(page)
    expect(page.get_by_test_id('crumbs')).to_contain_text('core')
    expect(page.get_by_test_id('plan-scope-type')).to_be_enabled()


def test_plan_unknown_node_does_not_blank(page):
    pytest.importorskip('playwright')
    goto(page, '#/plan/s81.t.no_such_type_xyz'); wait_painted(page)
    expect(page.get_by_test_id('inspector')).to_contain_text('Not in the current plan')


test_plan_unknown_node_does_not_blank = pytest.mark.allow_errors('HTTP 404')(test_plan_unknown_node_does_not_blank)


def test_plan_selected_instance_ring_changes_canvas(page):
    goto(page, '#/plan/s81'); wait_painted(page); page.wait_for_timeout(300); a = canvas_signature(page, CV)
    goto(page, '#/plan/%s?inst=%s' % (SIGNED_TYPE, S_INST)); wait_painted(page); page.wait_for_timeout(400)
    assert canvas_signature(page, CV)['hash'] != a['hash']


def test_plan_and_inspector_count_earlier_signoffs_in_current_geometry(page):
    for die in ALL_DIES:
        payload = api('die/' + die)
        if any(n.get('signoff_basis') in ('deferred', 'retired') and n['status']['state'] != 'signed'
               for n in payload['nodes'].values() if n['level'] == 'type'):
            break
    else:
        pytest.skip('fixture has no historically signed active type with an unsigned current state')
    d = payload['die']
    expected = d['counts_any_plan']['type']['signed']
    assert expected == sum(n.get('signoff_display_state') == 'signed'
                           for n in payload['nodes'].values() if n['level'] == 'type')
    goto(page, '#/plan/' + die)
    expect(page.get_by_test_id('plan-legend')).to_contain_text(f'Signed off {expected}')
    expect(page.get_by_test_id('insp-signoff-types')).to_have_text(f"{expected} of {d['type_count']} partition types signed off")
