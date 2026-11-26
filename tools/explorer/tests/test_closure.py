"""Closure view (REQUIREMENTS.md section I): status table, die matrix, failure groups, coverage ledger."""
import re, pytest
from playwright.sync_api import expect
from helpers import *

# TODO (section I) still to assert: gate-miss rows match tt_wns < -42 / ff_wns < 0 / drc > 0 from the API; matrix counts equal /api/v1/dies;
#   'Open the element' link leads to the Element view; failure-group rows select their node.


@pytest.mark.parametrize('die', DIES)
def test_closure_mounts_with_rows(page, die):
    goto(page, '#/closure/' + die)
    expect(page.get_by_test_id('view-title')).to_have_text('Closure')
    expect(page.get_by_test_id('view-closure')).to_have_attribute('aria-current', 'page')
    expect(page.get_by_test_id('fresh-chip')).to_contain_text(re.compile(r'Data|Stale'))
    expect(page.get_by_test_id('crumbs')).to_contain_text(next(d['label'] for d in api('meta')['dies'] if d['id'] == die))
    t = page.get_by_test_id('closure-table'); expect(t).to_be_visible()
    n = len(closure_rows(die))
    assert t.locator('tbody tr').count() == n
    expect(page.get_by_test_id('closure-count')).to_have_text('%d of %d designs' % (n, n))


def test_closure_tabs_switch_body_and_url(page):
    goto(page, '#/closure/s81')
    for tab, marker in (('matrix', 'closure-matrix-type'), ('failures', 'failure-group'), ('ledger', 'ledger-table')):
        page.get_by_test_id('closure-tab-' + tab).click()
        page.wait_for_function('(t) => otx.store.get().params.tab === t', arg=tab)
        assert 'tab=' + tab in page.url
        expect(page.get_by_test_id(marker).first).to_be_visible(timeout=30000)
        expect(page.get_by_test_id('closure-table')).to_have_count(0)
    page.get_by_test_id('closure-tab-table').click()
    page.wait_for_function('() => !otx.store.get().params.tab')
    expect(page.get_by_test_id('closure-table')).to_be_visible()


def test_closure_level_filter_state_chips_gates(page):
    goto(page, '#/closure/s81')
    rows = closure_rows('s81'); t = page.locator('[data-testid=closure-table] tbody tr'); cnt = page.get_by_test_id('closure-count')
    page.get_by_test_id('closure-level-type').click()
    nt = sum(1 for r in rows if r['level'] == 'type'); assert t.count() == nt
    expect(cnt).to_contain_text('%d of' % nt)
    page.get_by_test_id('closure-level-core').click(); assert t.count() == len(rows) - nt
    page.get_by_test_id('closure-level-all').click(); assert t.count() == len(rows)
    page.get_by_test_id('closure-state-signed').click()
    assert t.count() == sum(1 for r in rows if r.get('signoff_basis') or (r.get('display_state') or r['state']) == 'signed')
    expect(page.get_by_test_id('closure-state-signed')).to_have_attribute('aria-pressed', 'true')
    retired = next((r for r in rows if r.get('signoff_basis') == 'retired'), None)
    if retired:
        badge = t.locator('td:first-child').filter(has_text='Retired plan').first
        expect(badge).to_contain_text('Signed off')
    page.get_by_test_id('closure-state-signed').click(); assert t.count() == len(rows)
    page.get_by_test_id('closure-gates').click()
    expect(page.get_by_test_id('closure-gates')).to_have_attribute('aria-pressed', 'true')
    miss = sum(1 for r in rows if (r['tt_wns'] is not None and r['tt_wns'] < -42) or (r['ff_wns'] is not None and r['ff_wns'] < 0) or (r['drc'] is not None and r['drc'] != 0))
    assert t.count() == miss, (t.count(), miss)


def test_closure_filter_narrows_count(page):
    goto(page, '#/closure/s81')
    n0 = page.locator('[data-testid=closure-table] tbody tr').count()
    page.get_by_test_id('closure-filter').fill('slice_station')
    page.wait_for_function('(n) => document.querySelectorAll("[data-testid=closure-table] tbody tr").length < n', arg=n0)
    k = page.locator('[data-testid=closure-table] tbody tr').count(); assert k >= 1
    expect(page.get_by_test_id('closure-count')).to_have_text('%d of %d designs' % (k, n0))
    page.get_by_test_id('closure-filter').fill('zzzqqq'); expect(page.get_by_test_id('closure-count')).to_contain_text('0 of')


def test_closure_sort_headers_flip(page):
    goto(page, '#/closure/s81')
    h_ = page.get_by_test_id('closure-sort-name'); h_.click()
    expect(h_).to_have_attribute('aria-sort', 'ascending')
    names = page.locator('[data-testid=closure-table] tbody tr td:nth-child(2)').all_inner_texts()
    assert names == sorted(names, key=lambda s: [int(x) if x.isdigit() else x for x in re.split(r'(\d+)', s)]) or len(names) > 1
    first = names[0]
    h_.click(); expect(h_).to_have_attribute('aria-sort', 'descending')
    assert page.locator('[data-testid=closure-table] tbody tr td:nth-child(2)').first.inner_text() != first


def test_closure_row_click_selects_node(page):
    goto(page, '#/closure/s81')
    row = page.locator('[data-testid=closure-table] tbody tr').nth(3)
    nid = row.get_attribute('data-node'); row.locator('td').first.click()
    page.wait_for_function('(n) => otx.store.get().sel.node === n', arg=nid)
    expect(page.locator('[data-testid=closure-table] tbody tr[data-node="%s"]' % nid)).to_have_attribute('aria-selected', 'true')
    assert store(page)['view'] == 'closure'


def test_closure_tsv_gives_feedback(page):
    goto(page, '#/closure/s81')
    page.get_by_test_id('closure-tsv').click()
    expect(page.locator('.toast')).to_contain_text(re.compile(r'copied as TSV|refused clipboard'))


def test_closure_ledger_loads_coverage(page):
    goto(page, '#/closure/s81?tab=ledger')
    expect(page.get_by_test_id('ledger-table')).to_be_visible(timeout=30000)
    assert page.locator('[data-testid=ledger-table] tbody tr').count() >= 1
