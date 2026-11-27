"""Overview view on three dies."""
import re, pytest
from collections import Counter
from playwright.sync_api import expect
from helpers import *


@pytest.mark.parametrize('die', DIES)
def test_overview_loads_clean_with_freshness(page, die):
    goto(page, '#/overview/' + die)
    expect(page.get_by_test_id('overview-page')).to_be_visible()
    card = page.get_by_test_id('card-' + die)
    expect(card).to_be_visible(); expect(card).to_have_class(re.compile(r'\bon\b'))
    d = next(x for x in api('dies')['dies'] if x['id'] == die)
    expect(card).to_contain_text(d['plan']['sha']); expect(card).to_contain_text(f"of {d['types']} partition types")
    expect(card).to_contain_text(f"{d['partitions']} partitions")
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
        rows = api('records')['records']
        levels = ('type', 'core')
        by_level = Counter(row['level'] for row in rows)
        assert census['any'] == len(rows) == sum(d['any_plan']['any'] for d in r['dies'])
        assert census['by_level'] == {level: by_level[level] for level in levels}
        chip = page.get_by_test_id('ov-signoff-any')
        expect(chip).to_contain_text(format(census['any'], ','))
        expect(chip).to_contain_text('Signed off on any plan')
        expect(chip).to_contain_text(f"{by_level['type']:,} partition types · {by_level['core']:,} hard cores")
        by_die = Counter((row['die'], row['level']) for row in rows)
        for d in r['dies']:
            expected = {level: by_die[d['id'], level] for level in levels}
            assert d['any_plan']['by_level'] == expected
            assert d['any_plan']['any'] == sum(expected.values())
            expect(page.get_by_test_id('ov-signoff-any-' + d['id'])).to_contain_text(
                f"{expected['type']:,} partition types · {expected['core']:,} hard cores")
            counts = d['counts_any_plan']
            geometry = page.get_by_test_id('ov-current-designs-' + d['id'])
            expect(geometry).to_have_text(
                f"{counts['type'].get('signed', 0)} of {d['types']} partition types, "
                f"{counts['core'].get('signed', 0)} of {d['cores']} hard cores")
            assert sum(counts['type'].values()) == sum(d['counts']['type'].values())
            assert sum(counts['core'].values()) == d['cores']
            expect(page.get_by_test_id('ov-signed-area-' + d['id'])).to_contain_text('of current die area signed on any plan')


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
    ds = api('dies')['dies']
    assert all(d['packs_unsigned']['type'] <= d['packs']['type'] and d['packs_unsigned']['core'] <= d['packs']['core'] for d in ds)
    unsigned = sum(sum(d['packs_unsigned_any_plan'].values()) for d in ds)
    signed = sum(sum(d['packs_signed_any_plan'].values()) for d in ds)
    goto(page, '#/overview')
    packs = page.get_by_test_id('ov-packs')
    expect(packs).to_contain_text('signed-off layout packs from any plan')
    expect(packs).to_contain_text(f"{unsigned:,} unsigned build views")
    expect(packs.locator('.big')).to_have_text(re.compile(r'^' + re.escape(format(signed, ','))))
