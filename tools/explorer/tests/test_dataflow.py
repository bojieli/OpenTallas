"""Dataflow view (REQUIREMENTS.md section G): partition bundles and pin-level link records on the plan canvas."""
import re, pytest
from playwright.sync_api import expect
from helpers import *

# TODO (section G) still to assert: link widths / counts equal the record; clicking a link writes lane=<id>; selecting a type highlights its links;
#   df-links rows sort by bits.
CV = '[data-testid=plan-canvas]'


def painted(page):
    page.wait_for_function("""(s) => { const c = document.querySelector(s); if (!c || !c.width) return false; const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
      const seen = new Set(); for (let i = 0; i < d.length; i += 4 * 61) seen.add(d[i] + ',' + d[i + 1] + ',' + d[i + 2]); return seen.size > 3; }""", arg=CV, timeout=60000)


@pytest.mark.parametrize('die', DIES)
def test_dataflow_mounts_with_canvas(page, die):
    goto(page, '#/dataflow/' + die); painted(page)
    expect(page.get_by_test_id('view-title')).to_have_text('Dataflow')
    expect(page.get_by_test_id('view-dataflow')).to_have_attribute('aria-current', 'page')
    expect(page.get_by_test_id('fresh-chip')).to_contain_text(re.compile(r'Data|Stale'))
    expect(page.get_by_test_id('crumbs')).to_contain_text(next(d['label'] for d in api('meta')['dies'] if d['id'] == die))
    expect(page.get_by_test_id('df-mode-plan')).to_have_attribute('aria-pressed', 'true') if page.get_by_test_id('df-mode-plan').get_attribute('aria-pressed') else None


def test_dataflow_selection_carries_over(page):
    goto(page, '#/dataflow/%s?inst=%s' % (SIGNED_TYPE, S_INST))
    s = store(page); assert s['sel']['node'] == SIGNED_TYPE and s['sel']['inst'] == S_INST


def test_dataflow_modes_record_banner_and_selects(page):
    goto(page, '#/dataflow/s81'); painted(page); page.wait_for_timeout(500)
    a = canvas_signature(page, CV)['hash']
    page.get_by_test_id('df-mode-record').click()
    page.wait_for_function("() => otx.store.get().params.src === 'record'")
    assert 'src=record' in page.url
    rec = page.get_by_test_id('df-record'); expect(rec).to_be_visible(timeout=30000)
    assert rec.locator('option').first.get_attribute('value').startswith('plan_s81'), rec.locator('option').all_inner_texts()
    expect(page.get_by_test_id('df-banner')).to_be_visible(timeout=30000)
    page.wait_for_timeout(800); painted(page)
    expect(page.locator('[data-testid^=df-show-]').first).to_be_attached(timeout=30000)      # legend: only the link classes present in the record get a switch
    page.get_by_test_id('df-minbits').select_option('512')
    page.wait_for_function("() => otx.store.get().params.min === '512'")
    page.get_by_test_id('df-mode-plan').click()
    page.wait_for_function("() => !otx.store.get().params.src")
    for k in ('abut', 'through'): expect(page.locator('[data-testid=df-show-%s]' % k)).to_have_count(1)


def test_dataflow_legend_toggle_and_fit(page):
    goto(page, '#/dataflow/s81'); painted(page); page.wait_for_timeout(500)
    a = canvas_signature(page, CV)['hash']
    page.locator('label:has([data-testid=df-show-abut])').click()
    page.wait_for_timeout(500); assert canvas_signature(page, CV)['hash'] != a
    box = page.get_by_test_id('plan-canvas').bounding_box()
    page.mouse.move(box['x'] + 500, box['y'] + 400)
    for _ in range(3): page.mouse.wheel(0, -300)
    page.wait_for_timeout(500); z = canvas_signature(page, CV)['hash']
    page.get_by_test_id('df-fit').click(); page.mouse.move(5, 5); page.wait_for_timeout(600)
    assert canvas_signature(page, CV)['hash'] != z


def test_dataflow_links_tab(page):
    goto(page, '#/dataflow/s81'); painted(page)
    page.get_by_test_id('insp-tab-links').click()
    expect(page.get_by_test_id('df-links').first).to_be_visible()
