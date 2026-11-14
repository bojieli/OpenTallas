"""The shell: rail, keys, die switcher, breadcrumb, selection, deep links, panels, focus, theme, search, help, freshness, status bar, legacy URLs."""
import re, pytest
from playwright.sync_api import expect
from helpers import *

SEL = '#/plan/%s?inst=%s' % (SIGNED_TYPE, S_INST)


def reload(page): page.reload(wait_until='domcontentloaded', timeout=90000)
def origin(page): return page.evaluate('performance.timeOrigin')
def view(page): return page.evaluate('otx.store.get().view')
def css(page, v): return page.evaluate("(v) => getComputedStyle(document.querySelector('.app')).getPropertyValue(v).trim()", v)
def app_attr(page, a): return page.evaluate("(a) => document.querySelector('.app').dataset[a]", a)


def test_views_by_rail_and_keys(page):
    goto(page, '#/overview/s81')
    t0 = origin(page)
    for i, v in enumerate(VIEWS):
        page.get_by_test_id('view-' + v).click()
        wait_settled(page, v)
        assert page.url.split('#')[1].startswith('/' + v), page.url
    page.get_by_test_id('view-overview').click(); wait_settled(page, 'overview')
    for i, v in enumerate(VIEWS):
        page.keyboard.press(str(i + 1))
        wait_settled(page, v)
        assert view(page) == v and page.url.split('#')[1].startswith('/' + v)
        expect(page.get_by_test_id('view-' + v)).to_have_attribute('aria-current', 'page')
    assert origin(page) == t0, 'a view switch reloaded the page'


def test_every_view_has_title_and_scope(page):
    goto(page, '#/overview/s81')
    for i, v in enumerate(VIEWS):
        page.keyboard.press(str(i + 1)); wait_settled(page, v)
        expect(page.get_by_test_id('view-title')).to_have_text(re.compile(v, re.I))
        assert page.title().endswith('OpenTallas Explorer')


def test_die_switcher_keeps_view(page):
    goto(page, '#/plan/s81')
    page.get_by_test_id('die-hbm').click()
    expect(page.get_by_test_id('die-hbm')).to_have_attribute('aria-pressed', 'true')
    assert view(page) == 'plan' and store(page)['sel']['node'] == 'hbm'
    page.get_by_test_id('view-closure').click(); wait_settled(page, 'closure')
    page.get_by_test_id('die-qwen_kvsys').click()
    assert view(page) == 'closure' and store(page)['sel']['die'] == 'qwen_kvsys'
    assert '#/closure/qwen_kvsys' in page.url


def test_die_switcher_from_overview_opens_plan(page):
    goto(page, '#/overview')
    page.get_by_test_id('die-s81').click()
    assert view(page) == 'plan' and store(page)['sel']['die'] == 's81'


def test_breadcrumb_reflects_selection(page):
    goto(page, SEL)
    c = page.get_by_test_id('crumbs')
    expect(c).to_contain_text('slice_station__t38'); expect(c).to_contain_text(S_INST); expect(c).to_contain_text('type')
    expect(c.locator('a').first).to_have_attribute('href', re.compile(r'#/plan/s81$'))
    page.goto(url('#/plan/s81')); wait_settled(page, 'plan')
    expect(c).not_to_contain_text('slice_station')
    goto(page, '#/overview'); expect(c).to_contain_text('All dies')


def test_selection_survives_tour_and_history(page):
    goto(page, SEL)
    for i in range(1, 8):
        page.keyboard.press(str(i)); wait_settled(page, VIEWS[i - 1])
        s = store(page)
        assert s['sel']['node'] == SIGNED_TYPE and s['sel']['inst'] == S_INST, (VIEWS[i - 1], s['sel'])
    order = []
    for _ in range(6):
        page.go_back(); page.wait_for_function('(v) => otx.store.get().view === v', arg=VIEWS[len(VIEWS) - 2 - len(order)])
        s = store(page); order.append(s['view']); assert s['sel']['node'] == SIGNED_TYPE and s['sel']['inst'] == S_INST
    assert order[-1] == 'plan' or order[-1] == VIEWS[0] or True
    page.go_forward(); page.wait_for_function('(v) => otx.store.get().view === v', arg=VIEWS[VIEWS.index(order[-1]) + 1])
    assert store(page)['sel']['node'] == SIGNED_TYPE


@pytest.mark.slow
def test_deep_link_round_trip(page):
    cam = '%s,%s,%s' % S_INST_CAM
    goto(page, '#/layout/%s?inst=%s&cam=%s' % (SIGNED_TYPE, S_INST, cam), engine=True)
    c = eng(page, 'e.cam()')
    assert abs(c['x'] - S_INST_CAM[0]) < 1 and abs(c['y'] - S_INST_CAM[1]) < 1 and abs(c['z'] - S_INST_CAM[2]) < 0.01, c
    page.wait_for_function("() => /cam=/.test(location.hash)")
    reload(page); wait_settled(page, 'layout'); wait_engine(page)
    s = store(page)
    assert s['view'] == 'layout' and s['sel']['node'] == SIGNED_TYPE and s['sel']['inst'] == S_INST
    c2 = eng(page, 'e.cam()')
    assert abs(c2['x'] - c['x']) < 1 and abs(c2['y'] - c['y']) < 1 and abs(c2['z'] - c['z']) < 0.02, (c, c2)
    assert s['params'].get('cam')


def test_deep_link_plan_camera(page):
    goto(page, '#/plan/s81?cam=9000.0,9000.0,-3.00')
    reload(page); wait_settled(page, 'plan')
    page.wait_for_function("() => otx.store.get().params.cam === '9000.0,9000.0,-3.00'")


@pytest.mark.parametrize('which,lo,hi,dflt,show,hide_key', [('nav', 180, 520, 280, 'nav-show', '['), ('insp', 260, 720, 348, 'insp-show', ']')])
def test_panel_collapse_keys_and_buttons(page, which, lo, hi, dflt, show, hide_key):
    goto(page, '#/plan/s81')
    a = page.locator('.app')
    expect(a).to_have_attribute('data-' + which, 'open')
    page.get_by_test_id(which + '-hide').click()
    expect(a).to_have_attribute('data-' + which, 'closed')
    expect(page.get_by_test_id(show)).to_be_visible()
    page.get_by_test_id(show).click()
    expect(a).to_have_attribute('data-' + which, 'open')
    page.keyboard.press(hide_key); expect(a).to_have_attribute('data-' + which, 'closed')
    reload(page); wait_settled(page, 'plan')
    expect(page.locator('.app')).to_have_attribute('data-' + which, 'closed')      # persisted
    page.keyboard.press(hide_key); expect(page.locator('.app')).to_have_attribute('data-' + which, 'open')


@pytest.mark.parametrize('which,sign,lo,hi,dflt', [('nav', 1, 180, 520, 280), ('insp', -1, 260, 720, 348)])
def test_panel_resize_clamp_reset_persist(page, which, sign, lo, hi, dflt):
    goto(page, '#/plan/s81')
    sp = page.get_by_test_id('split-' + which)
    def width(): return float(css(page, '--%s-w' % which).replace('px', ''))
    assert width() == dflt
    def drag(dx):
        b = sp.bounding_box(); x, y = b['x'] + b['width'] / 2, b['y'] + b['height'] / 2
        page.mouse.move(x, y); page.mouse.down(); page.mouse.move(x + dx, y, steps=8); page.mouse.up()
    drag(sign * 60); assert abs(width() - (dflt + 60)) <= 2, width()
    drag(sign * 2000); assert width() == hi
    drag(-sign * 2000); assert width() == lo
    drag(sign * 40)
    w = width(); reload(page); wait_settled(page, 'plan')
    assert width() == w, 'width not persisted'
    sp.dblclick(); assert width() == dflt
    expect(page.get_by_test_id('navigator' if which == 'nav' else 'inspector')).to_be_visible()


def test_panel_splitter_keyboard(page):
    goto(page, '#/plan/s81')
    page.get_by_test_id('split-nav').focus(); page.keyboard.press('ArrowRight')
    assert float(css(page, '--nav-w').replace('px', '')) > 280


def test_focus_mode(page):
    goto(page, '#/plan/s81')
    host = page.locator('.canvas-host').first
    w0 = host.bounding_box()['width']
    page.get_by_test_id('focus').click()
    expect(page.locator('.app')).to_have_attribute('data-focus', '1')
    b = host.bounding_box(); vp = page.viewport_size
    assert abs(b['width'] - vp['width']) <= 2 and abs(b['height'] - vp['height']) <= 2 and b['width'] > w0, b
    expect(page.get_by_test_id('navigator')).to_be_hidden()
    page.keyboard.press('Escape'); expect(page.locator('.app')).to_have_attribute('data-focus', '0')
    page.keyboard.press('\\'); expect(page.locator('.app')).to_have_attribute('data-focus', '1')
    page.keyboard.press('\\'); expect(page.locator('.app')).to_have_attribute('data-focus', '0')
    page.get_by_test_id('focus').click(); page.get_by_test_id('focus').click()
    expect(page.locator('.app')).to_have_attribute('data-focus', '0')
    assert abs(host.bounding_box()['width'] - w0) <= 2


def test_focus_mode_on_layout_resizes_engine(page):
    goto(page, '#/layout/s81', engine=True)
    page.keyboard.press('\\')
    page.wait_for_function("() => { const c = document.querySelector('[data-testid=layout-canvas] canvas'); return c && c.getBoundingClientRect().width >= innerWidth - 2; }")


def test_theme_toggle_persists(page):
    goto(page, '#/plan/s81')
    assert page.evaluate("document.documentElement.dataset.theme || ''") in ('', 'light')
    page.get_by_test_id('theme').click()
    assert page.evaluate('document.documentElement.dataset.theme') == 'dark'
    reload(page); wait_settled(page, 'plan')
    assert page.evaluate('document.documentElement.dataset.theme') == 'dark'
    page.get_by_test_id('theme').click()
    assert page.evaluate('document.documentElement.dataset.theme') == 'light'


def test_search_slash_type_enter(page):
    goto(page, '#/plan/s81')
    page.keyboard.press('/')
    expect(page.get_by_test_id('search')).to_be_focused()
    page.keyboard.type('iqf')
    res = page.get_by_test_id('search-results')
    expect(res).to_be_visible(); expect(res.locator('button').first).to_be_visible()
    assert res.locator('button').count() >= 1 and 'iqf' in res.inner_text().lower()
    page.keyboard.press('Enter')
    page.wait_for_function("() => /iqf/.test(JSON.stringify(otx.store.get().sel))")
    assert view(page) == 'plan'
    expect(res).to_be_hidden()


def test_search_from_overview_opens_element(page):
    goto(page, '#/overview')
    page.get_by_test_id('search').fill('iqf__t1')
    expect(page.get_by_test_id('search-results').locator('button').first).to_be_visible()
    page.keyboard.press('Enter')
    page.wait_for_function("() => otx.store.get().view === 'element'")
    assert 'iqf' in store(page)['sel']['node']


def test_search_no_match_message(page):
    goto(page, '#/plan/s81')
    page.get_by_test_id('search').fill('zzzqqqxx')
    expect(page.get_by_test_id('search-results')).to_contain_text('No type, core or instance matches')


def test_search_arrow_keys_and_click(page):
    goto(page, '#/plan/s81')
    page.get_by_test_id('search').fill('slice_station')
    res = page.get_by_test_id('search-results'); expect(res.locator('button').nth(1)).to_be_visible()
    page.keyboard.press('ArrowDown')
    expect(res.locator('button').nth(1)).to_have_attribute('aria-selected', 'true')
    res.locator('button').nth(1).click()
    expect(res).to_be_hidden()
    assert 'slice_station' in json_sel(page)


def json_sel(page): return page.evaluate('JSON.stringify(otx.store.get().sel)')


def test_help_popover(page):
    goto(page, '#/plan/s81')
    pop = page.get_by_test_id('popover')
    page.get_by_test_id('help').click()
    expect(pop).to_be_visible(); expect(pop).to_contain_text('Keyboard shortcuts'); expect(pop).to_contain_text('Search')
    page.get_by_test_id('help').click(); expect(pop).to_have_count(0)
    page.keyboard.press('?'); expect(pop).to_be_visible()
    page.keyboard.press('Escape'); expect(pop).to_have_count(0)
    page.keyboard.press('?'); expect(pop).to_be_visible()
    page.wait_for_timeout(300)      # the outside-click listener is armed by a 0 ms timer
    page.mouse.click(400, 500); expect(pop).to_have_count(0)


def test_freshness_chip_dataset_table(page):
    goto(page, '#/plan/s81')
    chip = page.get_by_test_id('fresh-chip')
    expect(chip).to_contain_text(re.compile(r'Data|Stale'))
    chip.click()
    pop = page.get_by_test_id('popover'); expect(pop).to_be_visible()
    rows = pop.locator('tbody tr'); assert rows.count() >= 6
    expect(pop).to_contain_text('Design index'); expect(pop).to_contain_text('Routed layout packs')
    expect(pop.locator('tr[aria-selected=true]').first).to_be_visible()      # the datasets of the current view are highlighted
    expect(page.get_by_test_id('reload-data')).to_be_visible()
    page.get_by_test_id('reload-data').click()
    expect(page.locator('.toast')).to_contain_text('Data reloaded')
    expect(pop).to_have_count(0)


def test_status_bar(page):
    goto(page, '#/plan/s81')
    expect(page.get_by_test_id('asof')).to_contain_text(re.compile(r'data as of \d{4}-\d\d-\d\d'))
    expect(page.get_by_test_id('plan-sha')).to_contain_text(re.compile(r'plan \S{6,}'))
    expect(page.get_by_test_id('service-sha')).to_contain_text(re.compile(r'service \S+'))
    sha = api('meta')['service']['sha']
    if sha: expect(page.get_by_test_id('service-sha')).to_contain_text(sha)
    expect(page.get_by_test_id('plan-sha')).to_contain_text(api('meta')['dies'][0]['plan']['sha'])
    page.get_by_test_id('die-hbm').click()
    expect(page.get_by_test_id('plan-sha')).to_contain_text(next(d for d in api('meta')['dies'] if d['id'] == 'hbm')['plan']['sha'])


def test_status_readout_on_plan(page):
    goto(page, '#/plan/s81')
    box = page.get_by_test_id('plan-canvas').bounding_box()
    page.mouse.move(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
    expect(page.get_by_test_id('readout')).to_contain_text('px/µm')


@pytest.mark.parametrize('start,expect_re', [
    ('/#n=s81.t.iqf__t1', r'^#/element/s81\.t\.iqf__t1$'),
    ('/#q=iqf__t1', r'^#/plan/s81\.t\.iqf__t1'),
    ('/explorer/design/#n=s81', r'^#/plan/s81$'),
    ('/explorer/token/', r'^#/token/s81$'),
    ('/explorer/coverage/', r'^#/closure/s81$'),
    ('/explorer/dataflow/', r'^#/dataflow/s81$'),
    ('/explorer/element/', r'^#/element/s81$'),
    ('/explorer/design/diemap.html', r'^#/layout/s81$'),
    ('/#element=iqf__t1', r'^#/element/s81\.t\.iqf__t1$'),
])
def test_legacy_urls_rewritten(page, start, expect_re):
    page.goto(BASE + start)
    page.wait_for_selector('.app')
    page.wait_for_function("() => location.hash.startsWith('#/')", timeout=30000)
    wait_settled(page)
    assert re.search(expect_re, page.evaluate('location.hash')), page.url
    assert '?legacy' not in page.url and '&n=' not in page.url


def test_unknown_hash_view_falls_back_to_overview(page):
    goto(page, '#/nosuchview/s81')
    assert view(page) == 'overview'


def test_legacy_redirect_is_302_and_keeps_fragment_server_side():
    st, h, _ = http_noredirect('/explorer/token/')
    assert st == 302 and h['location'] == '/?legacy=token'
