"""Token view (REQUIREMENTS.md section H): token path records, flow graph and swimlanes."""
import re, pytest
from playwright.sync_api import expect
from helpers import *

# TODO (section H) still to assert: record contents equal /api/v1/token/record/<id>; replay clock advances; run-on links (tok-cls-*) open the right design.


@pytest.mark.parametrize('die', DIES)
def test_token_mounts(page, die):
    goto(page, '#/token/' + die)
    expect(page.get_by_test_id('view-title')).to_have_text('Token')
    expect(page.get_by_test_id('view-token')).to_have_attribute('aria-current', 'page')
    expect(page.get_by_test_id('token-page')).to_be_visible()
    expect(page.get_by_test_id('tok-banner')).to_be_visible()
    expect(page.get_by_test_id('crumbs')).to_contain_text(next(d['label'] for d in api('meta')['dies'] if d['id'] == die))
    expect(page.get_by_test_id('fresh-chip')).to_contain_text(re.compile(r'Data|Stale'))      # 'Stale data' is expected here (records from 10-20)


def test_token_selection_carries_over(page):
    goto(page, '#/token/%s?inst=%s' % (SIGNED_TYPE, S_INST))
    s = store(page); assert s['sel']['node'] == SIGNED_TYPE and s['sel']['inst'] == S_INST


def test_token_flow_and_gantt_have_svg(page):
    goto(page, '#/token/s81')
    for t in ('tok-flow', 'tok-gantt'): expect(page.get_by_test_id(t).locator('svg').first).to_be_visible(timeout=60000)


def test_token_design_select_sets_tok(page):
    goto(page, '#/token/s81')
    sel = page.get_by_test_id('tok-design'); opts = sel.locator('option').evaluate_all('(o) => o.map((x) => x.value)')
    if len(opts) < 2: pytest.skip('only one token design')
    cur = sel.input_value(); other = next(v for v in opts if v != cur)
    sel.select_option(other)
    page.wait_for_function('() => !!otx.store.get().sel.tok')
    assert 'tok=' in page.url


def test_token_mode_play_speed(page):
    goto(page, '#/token/s81')
    page.get_by_test_id('tok-mode-mtp').click(); page.wait_for_timeout(500)
    page.get_by_test_id('tok-mode-ar').click(); page.wait_for_timeout(500)
    p = page.get_by_test_id('tok-play'); t0 = p.inner_text()
    p.click(); page.wait_for_function('(t) => document.querySelector("[data-testid=tok-play]").textContent.trim() !== t', arg=t0.strip())
    p.click()
    sp = page.get_by_test_id('tok-speed'); sp.select_option(index=1)


def test_token_stage_click_and_up(page):
    goto(page, '#/token/s81')
    rows = page.get_by_test_id('tok-stages').locator('button.row'); expect(rows.first).to_be_visible(timeout=60000)
    expect(page.get_by_test_id('tok-up')).to_be_disabled()
    rows.first.click()
    page.wait_for_function('() => /:/.test(otx.store.get().sel.tok || "")')
    expect(page.get_by_test_id('tok-up')).to_be_enabled()
    page.get_by_test_id('tok-up').click()
    page.wait_for_function('() => !/:/.test(otx.store.get().sel.tok || "")')


def test_token_inspector_tabs_and_class_links(page):
    goto(page, '#/token/s81')
    page.get_by_test_id('insp-tab-runs').click()
    b = page.locator('[data-testid^=tok-cls-]').first; expect(b).to_be_visible(timeout=30000)
    b.click(); expect(page.get_by_test_id('insp-body').locator('a').first).to_be_visible()
    page.get_by_test_id('insp-tab-op').click(); expect(page.get_by_test_id('insp-body')).not_to_be_empty()
