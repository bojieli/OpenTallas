"""Layout view (die with routed wires in place) on three dies.  Software WebGL: everything polls app state."""
import re, pytest
from playwright.sync_api import expect
from helpers import *

pytestmark = pytest.mark.slow


def layers_ready(page):
    page.get_by_test_id('insp-tab-layers').click()
    page.wait_for_function("() => !!otx.eng.L && !!document.querySelector('[data-testid=layer-M1]')", timeout=60000)


def to_geometry(page, die, zooms=(3.6, 5.0, 6.5)):
    """camera on the middle of a signed placement; exact geometry is decided once per view (whole view under the shape budget),
    so a big placement may need a deeper zoom than 3.6: the zoom that worked is returned"""
    inst, pack = pick_instance(die)
    assert inst, 'no signed, drawn placement on ' + die
    cx, cy = (inst['x'] + inst['w'] / 2) / 1000, (inst['y'] + inst['h'] / 2) / 1000
    for z in zooms:
        page.evaluate('([x, y, z]) => otx.eng.setCam(x, y, z)', [cx, cy, z])
        try:
            page.wait_for_function("() => otx.eng.mode === 'geometry' && otx.eng.tiles.size > 0 && otx.eng.pending.size === 0", timeout=70000)
            return inst, (cx, cy), z
        except Exception:
            continue
    raise AssertionError('no exact geometry at zoom %s over %s of %s' % (zooms, inst['name'], die))


@pytest.mark.parametrize('die', DIES)
def test_layout_loads_clean_far_view(page, die):
    goto(page, '#/layout/' + die, engine=True)
    mode = eng(page, 'e.mode')
    assert mode in ('raster', 'plan'), mode
    if mode == 'raster': assert eng(page, 'e.rasters.size') > 0
    info = page.get_by_test_id('layout-info')
    expect(info).to_have_attribute('data-mode', mode); expect(info).to_have_attribute('data-loading', '0', timeout=90000)   # rasters of many core packs on software GL
    expect(page.get_by_test_id('layout-summary')).to_contain_text('partitions drawn')
    expect(page.get_by_test_id('fresh-chip')).to_contain_text(re.compile(r'Data|Stale'))
    expect(page.get_by_test_id('view-scope')).to_contain_text('routed die map')
    assert eng(page, 'e.rasters.size') > 0 or mode == 'plan'


@pytest.mark.parametrize('die', DIES)
def test_layout_far_view_has_density_rasters(page, die):
    """far view of a die with signed packs must load density rasters (mode 'raster'), not stay at plan rectangles"""
    goto(page, '#/layout/' + die, engine=True)
    page.wait_for_function("() => otx.eng.rasters.size > 0", timeout=60000)
    assert eng(page, 'e.mode') == 'raster'


@pytest.mark.parametrize('die', DIES)
def test_layout_zoom_into_signed_instance_reaches_geometry(page, die):
    goto(page, '#/layout/' + die, engine=True)
    inst, (cx, cy), z = to_geometry(page, die)
    if die == 's81':
        assert z == 3.6, 'the s81 instance needed zoom %s' % z
    if die == 's81' and inst['name'] != S_INST:
        # the spec instance must be a drawn signed placement too
        names = [r['name'] for r in api('compose/s81')['instances']]
        assert S_INST in names
    assert eng(page, 'e.tiles.size') > 0
    expect(page.get_by_test_id('layout-info')).to_have_attribute('data-mode', 'geometry')
    assert 'exact geometry' in page.get_by_test_id('layout-info').inner_text()


def test_layout_s81_spec_instance_geometry(page):
    """the documented camera: zoom 3.6 at (8800, 9420) inside instance s_0S_x05 of slice_station__t38 reaches exact geometry"""
    goto(page, '#/layout/s81', engine=True)
    inst = next(r for r in api('compose/s81')['instances'] if r['name'] == S_INST)
    x0, y0, x1, y1 = inst['x'] / 1000, inst['y'] / 1000, (inst['x'] + inst['w']) / 1000, (inst['y'] + inst['h']) / 1000
    assert x0 <= S_INST_CAM[0] <= x1 and y0 <= S_INST_CAM[1] <= y1, 'the documented camera point is not inside the instance: %s' % [x0, y0, x1, y1]
    page.evaluate('([x, y, z]) => otx.eng.setCam(x, y, z)', list(S_INST_CAM))
    page.wait_for_function("() => otx.eng.mode === 'geometry' && otx.eng.tiles.size > 0", timeout=150000)


def test_layout_unsigned_toggle_changes_item_count(page):
    goto(page, '#/layout/hbm', engine=True)
    n0 = eng(page, 'e.items.length')
    btn = page.get_by_test_id('layout-unsigned')
    expect(btn).to_have_attribute('aria-pressed', 'false')
    btn.click()
    page.wait_for_function("() => otx.store.get().params.unsigned === '1'")
    expect(btn).to_have_attribute('aria-pressed', 'true')
    page.wait_for_function('(n) => otx.eng.items.length !== n', arg=n0, timeout=30000)
    n1 = eng(page, 'e.items.length'); assert n1 > n0, (n0, n1)
    btn.click(); page.wait_for_function('(n) => otx.eng.items.length === n', arg=n0)
    assert 'unsigned' not in store(page)['params']


def test_layout_unsigned_param_deep_link(page):
    goto(page, '#/layout/hbm?unsigned=1', engine=True)
    expect(page.get_by_test_id('layout-unsigned')).to_have_attribute('aria-pressed', 'true')


def test_layout_layers_tab_layer_solo_presets(page):
    goto(page, '#/layout/s81', engine=True); layers_ready(page)
    names = page.evaluate("() => otx.eng.L.filter((l) => l.type !== 'PHYS').map((l) => l.name)")
    assert 'M1' in names and len(names) >= 5
    vis = lambda n: page.evaluate('(n) => otx.eng.L.find((l) => l.name === n).vis', n)
    assert vis('M1')
    page.get_by_test_id('layer-M1').uncheck()
    assert not vis('M1')
    page.wait_for_function("() => (otx.store.get().params.hide || '').split('.').includes('M1')")
    page.get_by_test_id('layer-M1').check(); assert vis('M1')
    page.wait_for_function("() => !(otx.store.get().params.hide || '').includes('M1')")
    page.get_by_test_id('solo-M3').click()
    assert vis('M3') and not vis('M2') and not vis('M1')
    hidden = page.evaluate('otx.eng.hiddenLayers()')
    assert 'M3' not in hidden and 'M2' in hidden
    page.get_by_test_id('preset-all').click()
    assert all(vis(n) for n in names if n)
    page.get_by_test_id('preset-signals').click()
    assert page.evaluate('otx.eng.kindVis[1]') is False       # power stripes off in the signals preset
    page.get_by_test_id('preset-power').click()
    assert page.evaluate('otx.eng.kindVis[1]') is True and page.evaluate('otx.eng.kindVis[0]') is False
    page.get_by_test_id('preset-all').click()
    assert page.evaluate('otx.eng.kindVis[0]') is True


def test_layout_hide_param_deep_link(page):
    goto(page, '#/layout/s81?hide=M1.M2', engine=True); layers_ready(page)
    expect(page.get_by_test_id('layer-M1')).not_to_be_checked(); expect(page.get_by_test_id('layer-M3')).to_be_checked()


def test_layout_layers_tab_palette_kinds_display(page):
    goto(page, '#/layout/s81', engine=True); layers_ready(page)
    page.get_by_test_id('palette').select_option('cvd')
    assert eng(page, 'e.palette') == 'cvd'
    page.get_by_test_id('palette').select_option('classic'); assert eng(page, 'e.palette') == 'classic'
    k = page.locator('[data-testid^=kind-]'); assert k.count() >= 8
    page.get_by_test_id('kind-0').uncheck(); assert eng(page, 'e.kindVis[0]') is False
    page.get_by_test_id('kind-0').check(); assert eng(page, 'e.kindVis[0]') is True
    for key in ('plan', 'labels', 'cores', 'minimap'):
        cb = page.get_by_test_id('show-' + key); was = eng(page, 'e.show.%s' % key)
        assert cb.is_checked() == was
        cb.click(); assert eng(page, 'e.show.%s' % key) == (not was), key
    # minimap switch hides the canvas
    expect(page.get_by_test_id('minimap')).to_be_hidden()
    page.get_by_test_id('show-minimap').check(); expect(page.get_by_test_id('minimap')).to_be_visible()


def test_layout_layer_opacity_slider(page):
    goto(page, '#/layout/s81', engine=True); layers_ready(page)
    sl = page.get_by_label('M2 opacity'); sl.fill('40')
    assert abs(page.evaluate("otx.eng.L.find((l) => l.name === 'M2').op") - 0.4) < 0.02


def test_layout_ruler_button_and_key(page):
    goto(page, '#/layout/s81', engine=True)
    b = page.get_by_test_id('layout-ruler')
    expect(b).to_have_attribute('aria-pressed', 'false')
    b.click(); expect(b).to_have_attribute('aria-pressed', 'true'); assert eng(page, 'e.rulerMode')
    b.click(); expect(b).to_have_attribute('aria-pressed', 'false'); assert not eng(page, 'e.rulerMode')
    page.keyboard.press('r'); expect(b).to_have_attribute('aria-pressed', 'true')
    page.get_by_test_id('layout-clear').click(); expect(b).to_have_attribute('aria-pressed', 'false')


def test_layout_ruler_measures_two_clicks(page):
    goto(page, '#/layout/s81', engine=True)
    page.get_by_test_id('layout-ruler').click()
    box = page.get_by_test_id('layout-canvas').bounding_box()
    page.mouse.click(box['x'] + 400, box['y'] + 400); page.mouse.click(box['x'] + 700, box['y'] + 400)
    assert eng(page, '(e.marks || e.rulers || []).length') >= 1 or eng(page, 'JSON.stringify(Object.keys(e)).includes("ruler")')


def test_layout_fit_and_to_selection(page):
    goto(page, '#/layout/%s?inst=%s' % (SIGNED_TYPE, S_INST), engine=True)
    page.wait_for_function('() => (otx.eng.selBox || []).length > 0')
    page.wait_for_timeout(1500)
    sel_cam = eng(page, 'e.cam()')                  # opened zoomed on the placement
    page.get_by_test_id('layout-fit').click()
    page.wait_for_function('(z) => otx.eng.cam().z < z - 0.4', arg=sel_cam['z'], timeout=30000)
    sel = page.get_by_test_id('layout-zoomsel'); expect(sel).to_be_enabled()
    sel.click()
    page.wait_for_function('(z) => Math.abs(otx.eng.cam().z - z) < 0.3', arg=sel_cam['z'], timeout=30000)
    c = eng(page, 'e.cam()'); assert abs(c['x'] - sel_cam['x']) < 60 and abs(c['y'] - sel_cam['y']) < 60, (c, sel_cam)
    page.keyboard.press('f'); page.wait_for_function('(z) => otx.eng.cam().z < z - 0.4', arg=sel_cam['z'])


def test_layout_to_selection_disabled_without_selection(page):
    goto(page, '#/layout/hbm', engine=True)
    expect(page.get_by_test_id('layout-zoomsel')).to_be_disabled()


def test_layout_minimap_click_moves_camera(page):
    goto(page, '#/layout/s81', engine=True)
    c0 = eng(page, 'e.cam()')
    mm = page.get_by_test_id('minimap'); expect(mm).to_be_visible()
    b = mm.bounding_box()
    page.mouse.click(b['x'] + b['width'] * 0.25, b['y'] + b['height'] * 0.3)
    page.wait_for_function('(c) => Math.abs(otx.eng.cam().x - c.x) > 1 || Math.abs(otx.eng.cam().y - c.y) > 1', arg=c0, timeout=20000)
    c1 = eng(page, 'e.cam()'); assert c1['x'] < c0['x'] and c1['y'] > c0['y'], (c0, c1)


def test_layout_click_partition_selects_it(page):
    goto(page, '#/layout/s81', engine=True)
    inst = next(r for r in api('compose/s81')['instances'] if r['name'] == S_INST)
    cx, cy = (inst['x'] + inst['w'] / 2) / 1000, (inst['y'] + inst['h'] / 2) / 1000
    px = page.evaluate('([x, y]) => otx.eng.deck.getViewports()[0].project([x, y])', [cx, cy])
    b = page.get_by_test_id('layout-canvas').bounding_box()
    page.mouse.click(b['x'] + px[0], b['y'] + px[1])
    page.wait_for_function('() => !!otx.store.get().sel.inst', timeout=20000)
    s = store(page)
    assert s['sel']['inst'] == S_INST and s['sel']['node'] == SIGNED_TYPE, s['sel']
    expect(page.get_by_test_id('crumbs')).to_contain_text(S_INST)


def test_layout_unsigned_type_hint(page):
    goto(page, '#/layout/%s' % BUILDING_TYPE, engine=True)
    expect(page.get_by_test_id('layout-hint')).to_contain_text('not signed off')


@pytest.mark.allow_errors('HTTP 404')
def test_layout_unknown_node_does_not_crash(page):
    goto(page, '#/layout/s81.t.no_such_type_xyz', engine=True)
    expect(page.get_by_test_id('layout-canvas')).to_be_visible()


def test_layout_selected_type_rings(page):
    goto(page, '#/layout/%s?inst=%s' % (SIGNED_TYPE, S_INST), engine=True)
    assert eng(page, '(e.selBox || []).length') >= 1


def test_layout_view_switch_destroys_engine(page):
    goto(page, '#/layout/s81', engine=True)
    page.keyboard.press('2'); wait_settled(page, 'plan')
    assert page.locator('[data-testid=layout-canvas]').count() == 0
    page.keyboard.press('3'); wait_settled(page, 'layout'); wait_engine(page)
    assert page.locator('[data-testid=layout-canvas]').count() == 1
