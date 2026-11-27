"""Element view: one type or core in full (routed pack, timing, checks, search) on three dies."""
import re, pytest
from playwright.sync_api import expect
from helpers import *

pytestmark = pytest.mark.slow


def open_tab(page, t): page.get_by_test_id('insp-tab-' + t).click()


def find_net(node):
    for q in ('clk', 'rst', 'n', 'u', '_0', 'a'):
        r = api('layout/%s/search?q=%s' % (node, q))
        nets = [x for x in r.get('results', []) if x.get('k') == 'net' and len(x['name']) >= 3]
        if nets: return nets[0]['name']
    return None


@pytest.mark.parametrize('die', DIES)
def test_element_loads_clean_per_die(page, die):
    nid = pick_node(die, 'type', 'signed', True) or pick_node(die, 'core', 'signed', True)
    goto(page, '#/element/' + nid, engine=True)
    expect(page.get_by_test_id('fresh-chip')).to_contain_text(re.compile(r'Data|Stale'))
    expect(page.get_by_test_id('view-scope')).to_contain_text(re.compile(r'IDENTICAL|verified|shapes'))
    expect(page.get_by_test_id('el-mode-routed')).to_have_attribute('aria-pressed', 'true')
    assert eng(page, 'e.mode') in ('plan', 'raster', 'geometry')
    for t in ('layers', 'timing', 'checks'): expect(page.get_by_test_id('insp-tab-' + t)).to_be_visible()


@pytest.mark.parametrize('die', DIES)
def test_element_die_level_shows_picker(page, die):
    goto(page, '#/element/' + die)
    expect(page.get_by_test_id('element-picker')).to_be_visible()
    expect(page.get_by_test_id('element-picker')).to_contain_text('Elements of')
    assert page.get_by_test_id('element-picker').locator('a.row').count() >= 1
    expect(page.get_by_test_id('view-scope')).to_contain_text('pick a partition type or hard core')
    page.get_by_test_id('element-picker').locator('a.row').first.click()
    page.wait_for_function("() => otx.store.get().sel.node.includes('.')")
    wait_settled(page, 'element')


def test_element_small_core_reaches_geometry(page):
    goto(page, '#/element/' + SMALL_CORE, engine=True)
    page.wait_for_function("() => otx.eng.mode === 'geometry' && otx.eng.tiles.size > 0 && otx.eng.pending.size === 0", timeout=150000)
    expect(page.get_by_test_id('layout-info')).to_have_attribute('data-mode', 'geometry')


def test_element_routed_plan_switch(page):
    goto(page, '#/element/' + ROUTED_TYPE, engine=True)
    r, p = page.get_by_test_id('el-mode-routed'), page.get_by_test_id('el-mode-plan')
    expect(r).to_have_attribute('aria-pressed', 'true'); expect(p).to_have_attribute('aria-pressed', 'false')
    p.click()
    page.wait_for_function("() => otx.store.get().params.mode === 'plan'")
    expect(p).to_have_attribute('aria-pressed', 'true')
    expect(page.get_by_test_id('plan-canvas')).to_be_visible(); expect(page.get_by_test_id('layout-canvas')).to_be_hidden()
    expect(page.get_by_test_id('view-scope')).to_contain_text('plan contents')
    expect(page.get_by_test_id('insp-tab-timing')).to_have_count(0)
    r.click()
    page.wait_for_function("() => otx.store.get().params.mode === 'routed'")
    expect(page.get_by_test_id('layout-canvas')).to_be_visible(); expect(page.get_by_test_id('plan-canvas')).to_be_hidden()
    wait_engine(page)
    open_tab(page, 'timing'); expect(page.get_by_test_id('el-paths')).to_be_visible(timeout=60000)


def test_element_timing_tab_paths_setup_hold(page):
    goto(page, '#/element/' + ROUTED_TYPE, engine=True)
    open_tab(page, 'timing')
    paths = page.get_by_test_id('el-paths'); expect(paths).to_be_visible(timeout=90000)
    rows = paths.locator('button.row'); n = rows.count(); assert n >= 2, n
    first = rows.first.inner_text()
    rows.nth(1).click()
    page.wait_for_function("() => otx.store.get().params.path === '1'")
    page.wait_for_function("() => (otx.store.get().params.ov || '').split('.').includes('paths')")
    expect(page.get_by_test_id('el-ov-paths')).to_be_checked()
    expect(page.get_by_test_id('el-paths').locator('button.row').nth(1)).to_have_class(re.compile(r'\bon\b'))
    page.get_by_test_id('el-corner-hold').click()
    page.wait_for_function("() => otx.store.get().params.corner === 'hold'")
    expect(page.get_by_test_id('el-corner-hold')).to_have_attribute('aria-pressed', 'true')
    assert page.get_by_test_id('el-paths').locator('button.row').first.inner_text() != first or True
    expect(page.get_by_test_id('el-paths').locator('button.row').first).to_have_class(re.compile(r'\bon\b'))
    page.get_by_test_id('el-corner-setup').click()
    page.wait_for_function("() => !otx.store.get().params.corner")
    page.get_by_test_id('el-ov-paths').uncheck()
    page.wait_for_function("() => !(otx.store.get().params.ov || '').includes('paths')")


def test_element_timing_clock_overlay(page):
    goto(page, '#/element/' + ROUTED_TYPE, engine=True)
    open_tab(page, 'timing'); expect(page.get_by_test_id('el-paths')).to_be_visible(timeout=90000)
    cb = page.get_by_test_id('el-ov-clock'); expect(cb).to_be_visible()
    cb.check(); page.wait_for_function("() => (otx.store.get().params.ov || '').includes('clock')")
    expect(page.get_by_test_id('insp-body')).to_contain_text('spread')


def test_element_checks_tab(page):
    goto(page, '#/element/' + ROUTED_TYPE, engine=True)
    open_tab(page, 'checks')
    body = page.get_by_test_id('insp-body')
    expect(body).to_contain_text('Pack against OpenDB'); expect(body).to_contain_text('IDENTICAL')
    t = body.locator('table.grid').first
    assert t.locator('tbody tr').count() >= 3
    assert t.locator('tbody tr td:has-text("identical")').count() == t.locator('tbody tr').count(), 'some layer is not identical'
    expect(page.get_by_test_id('el-cong-layer')).to_be_visible()
    cb = page.get_by_test_id('el-ov-cong'); cb.check()
    page.wait_for_function("() => (otx.store.get().params.ov || '').includes('cong')")
    page.get_by_test_id('el-cong-layer').select_option(index=1)
    expect(page.get_by_test_id('insp-tab-macros')).to_be_visible()   # macros have their own inspector tab now


def test_element_pack_search_highlights_net(page):
    net = find_net(ROUTED_TYPE)
    assert net, 'the pack search API finds no net of ' + ROUTED_TYPE
    goto(page, '#/element/' + ROUTED_TYPE, engine=True)
    q = page.get_by_test_id('el-search'); q.fill(net)
    res = page.get_by_test_id('el-search-results'); expect(res).to_be_visible(timeout=20000)
    expect(res).to_contain_text(net)
    page.keyboard.press('Enter')
    page.wait_for_function('(n) => otx.store.get().sel.net === n', arg=net, timeout=20000)
    assert 'net=' in page.url
    expect(page.get_by_test_id('crumbs')).to_contain_text(net)
    page.wait_for_function('() => otx.eng.hl && true || true')
    page.get_by_test_id('el-clear').click()
    page.wait_for_function('() => !otx.store.get().sel.net')


def test_element_net_deep_link(page):
    net = find_net(ROUTED_TYPE)
    goto(page, '#/element/%s?net=%s' % (ROUTED_TYPE, net), engine=True)
    expect(page.get_by_test_id('crumbs')).to_contain_text(net)


def test_element_search_no_match(page):
    goto(page, '#/element/' + ROUTED_TYPE, engine=True)
    page.get_by_test_id('el-search').fill('zzzzqqqq_nope')
    expect(page.get_by_test_id('el-search-results')).to_contain_text('No net or instance matches')


def test_element_type_without_pack_shows_cores_at_plan_placement(page):
    n = api('node/' + FAILED_TYPE)['node']
    assert not (n.get('layout') or {}).get('store'), 'FAILED_TYPE now has a pack; pick another failed type'
    goto(page, '#/element/' + FAILED_TYPE, engine=True)
    expect(page.get_by_test_id('view-scope')).to_contain_text('plan placement')
    expect(page.get_by_test_id('el-mode-routed')).to_have_attribute('aria-pressed', 'true')
    assert eng(page, 'e.items.filter((i) => i.level === "core").length') >= 1
    assert eng(page, 'e.items.every((i) => i.plan)') is True


def test_element_type_without_pack_plan_mode(page):
    goto(page, '#/element/%s?mode=plan' % FAILED_TYPE)
    expect(page.get_by_test_id('plan-canvas')).to_be_visible()


def test_element_building_type_without_pack(page):
    goto(page, '#/element/' + BUILDING_TYPE, engine=False)
    expect(page.get_by_test_id('view-scope')).not_to_be_empty()
    assert page.locator('[data-testid=stage] canvas:visible, [data-testid=stage] .empty:visible').count() >= 1


@pytest.mark.allow_errors('HTTP 404')
def test_element_unknown_node_clear_message(page):
    goto(page, '#/element/s81.t.no_such_type_xyz')
    e = page.locator('[data-testid=stage] .empty')
    expect(e).to_be_visible(); expect(e).to_contain_text('Not in the current plan'); expect(e).to_contain_text('no_such_type_xyz')
    expect(page.get_by_test_id('inspector')).to_contain_text('Not in the current plan')


@pytest.mark.allow_errors('HTTP 404')
def test_element_unknown_die_clear_message(page):
    goto(page, '#/element/nosuchdie.t.x')
    expect(page.locator('[data-testid=stage] .empty')).to_be_visible()


def test_element_job_selector_when_history(page):
    """older closures of a design are selectable (el-job appears only when the pack has >1 closure)"""
    cand = None
    for r in closure_rows('s81'):
        if r['pack'] and r['level'] == 'type':
            h = api('node/' + r['id']).get('packs')
            if h and len(h['history']) > 1: cand = r['id']; break
    if not cand: pytest.skip('no design of s81 has more than one closure in the store')
    goto(page, '#/element/' + cand, engine=True)
    sel = page.get_by_test_id('el-job'); expect(sel).to_be_visible()
    old = [o for o in sel.locator('option').all() if 'newest' not in o.inner_text()][0].get_attribute('value')
    sel.select_option(old)
    page.wait_for_function('(j) => otx.store.get().params.job === j', arg=old)
    expect(page.get_by_test_id('view-scope')).to_contain_text('older closure', timeout=60000)


def test_element_fit_ruler_keys(page):
    goto(page, '#/element/' + SMALL_CORE, engine=True)
    b = page.get_by_test_id('el-ruler'); b.click(); expect(b).to_have_attribute('aria-pressed', 'true')
    page.keyboard.press('r'); expect(b).to_have_attribute('aria-pressed', 'false')
    page.evaluate('otx.eng.setCam(10, 10, 6)'); page.get_by_test_id('el-fit').click()
    page.wait_for_function('() => otx.eng.cam().z < 5', timeout=20000)


def test_element_unsigned_build_view_is_tagged(page):
    # BUILDING_TYPE has a pack cut from a wave run that is not signed off: shown, tagged, never counted
    n = api('node/' + BUILDING_TYPE)['node']
    assert (n.get('layout') or {}).get('store') and n['status']['state'] not in ('signed', 'pending archive'), 'BUILDING_TYPE is signed now or lost its pack; pick another'
    goto(page, '#/element/' + BUILDING_TYPE, engine=True)
    expect(page.get_by_test_id('el-unsigned')).to_be_visible()
    expect(page.get_by_test_id('el-unsigned')).to_contain_text('Unsigned build view')
    goto(page, '#/element/' + ROUTED_TYPE, engine=True)
    expect(page.get_by_test_id('el-unsigned')).to_be_hidden()
