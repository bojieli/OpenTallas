"""Overview view on three dies."""
import re, pytest
from playwright.sync_api import expect
from helpers import *


@pytest.mark.parametrize('die', DIES)
def test_overview_loads_clean_with_freshness(page, die):
    goto(page, '#/overview/' + die)
    expect(page.get_by_test_id('overview-page')).to_be_visible()
    card = page.get_by_test_id('card-' + die)
    expect(card).to_be_visible(); expect(card).to_have_class(re.compile(r'\bon\b'))
    d = next(x for x in api('dies')['dies'] if x['id'] == die)
    expect(card).to_contain_text(d['plan']['sha']); expect(card).to_contain_text('of %d types' % d['types'])
    expect(page.get_by_test_id('fresh-chip')).to_contain_text(re.compile(r'Data|Stale'))
    expect(page.get_by_test_id('asof')).to_contain_text('data as of')
    t = page.get_by_test_id('fresh-table')
    assert t.locator('tbody tr').count() >= 6
    expect(t).to_contain_text('Design index')


def test_overview_five_cards_and_totals(page):
    goto(page, '#/overview')
    for d in ALL_DIES: expect(page.get_by_test_id('card-' + d)).to_be_visible()
    r = api('dies')
    n = sum(d['types'] for d in r['dies'])
    expect(page.get_by_test_id('overview-page')).to_contain_text('%s current partition types' % format(n, ','))
    census = r.get('signoff_census')
    if census:
        assert census['any'] == census['current'] + census['deferred'] + census['retired']
        assert census['any'] == sum(d['any_plan']['any'] for d in r['dies'])
        expect(page.get_by_test_id('ov-signoff-any')).to_contain_text(format(census['any'], ','))
        expect(page.get_by_test_id('ov-signoff-any')).to_contain_text('Signed off on any plan')


@pytest.mark.parametrize('die', DIES)
def test_overview_thumbnail_painted(page, die):
    goto(page, '#/overview')
    sel = '[data-testid=thumb-%s] canvas' % die
    page.wait_for_function("""(s) => { const c = document.querySelector(s); if (!c || !c.width) return false; const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
      const seen = new Set(); for (let i = 0; i < d.length; i += 4 * 97) seen.add(d[i] + ',' + d[i + 1] + ',' + d[i + 2] + ',' + d[i + 3]); return seen.size > 3; }""", arg=sel, timeout=60000)


@pytest.mark.parametrize('die', DIES)
def test_overview_links_open_views(page, die):
    goto(page, '#/overview')
    page.get_by_test_id('open-plan-' + die).click(); wait_settled(page, 'plan')
    assert store(page)['sel']['node'] == die
    page.go_back(); wait_settled(page, 'overview')
    page.get_by_test_id('thumb-' + die).click(); wait_settled(page, 'plan')
    page.go_back(); wait_settled(page, 'overview')
    page.get_by_test_id('open-closure-' + die).click(); wait_settled(page, 'closure')
    assert store(page)['sel']['node'] == die


def test_overview_theme_repaints_thumbs(page):
    goto(page, '#/overview')
    sel = '[data-testid=thumb-s81] canvas'
    page.wait_for_function("(s) => { const c = document.querySelector(s); return c && c.width > 0; }", arg=sel)
    page.wait_for_timeout(500)
    a = canvas_signature(page, sel)
    page.get_by_test_id('theme').click(); page.wait_for_timeout(500)
    b = canvas_signature(page, sel)
    assert a['hash'] != b['hash'], 'thumbnail did not repaint on theme change'


def test_overview_counts_signed_packs_apart_from_unsigned_views(page):
    ds = api('dies')['dies']; idx = {d['id']: d for d in ds}
    uns = sum(d['packs_unsigned']['type'] + d['packs_unsigned']['core'] for d in ds); allp = sum(d['packs']['type'] + d['packs']['core'] for d in ds)
    assert all(d['packs_unsigned']['type'] <= d['packs']['type'] and d['packs_unsigned']['core'] <= d['packs']['core'] for d in ds)
    goto(page, '#/overview')
    expect(page.get_by_test_id('ov-packs')).to_contain_text('signed-off layout packs')
    expect(page.get_by_test_id('ov-packs')).to_contain_text('%d unsigned build views' % uns if uns < 1000 else 'unsigned build views')
    assert str(allp - uns) in page.get_by_test_id('ov-packs').inner_text().replace(',', '')
