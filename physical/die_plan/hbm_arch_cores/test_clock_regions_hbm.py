"""DIE-HBM-61/CLOCK: --clock-regions maps the plan's core_clock_regions.json (one entry per <= 5k sinks) onto planned
density-tap anchors: one legal lattice site per declared region, None for small / kept-signed modules, loud failure on
a stale outline, several clock ports or an over-5k region."""
import importlib.util
import json
from pathlib import Path
import pytest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('coregen_cregions', HERE / 'gen_core_kit_hbm.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


def regions(tmp_path, **mods):
    p = tmp_path / 'core_clock_regions.json'
    p.write_text(json.dumps(dict(schema=m.CLOCK_REGIONS_SCHEMA, rule='one clock entry per <= 5000 sinks', modules=mods)))
    return p


def grid(w, h, gx, gy, sinks):
    ents = []
    for j in range(gy):
        for i in range(gx):
            x0, x1, y0, y1 = w * i / gx, w * (i + 1) / gx, h * j / gy, h * (j + 1) / gy
            ents.append(dict(xy_um=[(x0 + x1) / 2, (y0 + y1) / 2], region_um=[x0, y0, x1, y1]))
    return dict(sinks=sinks, entries=gx * gy, grid=[gx, gy], outline_um=[w, h], kept_signed=False,
                sinks_per_entry=sinks / (gx * gy), regional_entries=ents)


def test_sites_one_per_region_on_lattice(tmp_path):
    p = regions(tmp_path, big=grid(427.68, 246.24, 2, 1, 9981))
    r = m.clock_region_sites(p, 'big', (427.68, 246.24), ['clk'])
    assert r['entries'] == 2 and len(r['clock_sites_um']) == 2 and len(r['sha256']) == 64
    m.planned_clock_sites_text(r['clock_sites_um'], (427.68, 246.24))   # lattice + legal band (raises otherwise)


def test_small_or_kept_unchanged(tmp_path):
    kept = dict(grid(200, 200, 2, 2, 12000), kept_signed=True)
    p = regions(tmp_path, small=grid(100, 100, 1, 1, 3000), kept=kept)
    assert m.clock_region_sites(p, 'small', (100, 100), ['clk']) is None
    assert m.clock_region_sites(p, 'kept', (200, 200), ['clk']) is None
    assert m.clock_region_sites(p, 'absent', (100, 100), ['clk']) is None


@pytest.mark.parametrize('bad', ['outline', 'clocks', 'sinks', 'schema'])
def test_refuse(tmp_path, bad):
    g = grid(345.6, 518.4, 4, 4, 79292)
    if bad == 'sinks':
        g['sinks_per_entry'] = 6000
    p = regions(tmp_path, big=g)
    if bad == 'schema':
        p.write_text(json.dumps(dict(schema='old', modules={'big': g})))
    outline = (345.6, 500.0) if bad == 'outline' else (345.6, 518.4)
    clocks = ['clk', 'clk_m0'] if bad == 'clocks' else ['clk']
    with pytest.raises(ValueError, match='CLOCK_REGIONS'):
        m.clock_region_sites(p, 'big', outline, clocks)


def test_plan_of_record_d44v_if_present():
    f = HERE.parents[2] / 'physical/die_plan/hbm/plan_of_record/d44v/core_clock_regions.json'
    if not f.is_file():
        pytest.skip('d44v not on this tree')
    doc = json.load(open(f)); n = 0
    for mod, r in doc['modules'].items():
        res = m.clock_region_sites(f, mod, tuple(r['outline_um']), ['clk'])
        if res:
            n += res['entries']; m.planned_clock_sites_text(res['clock_sites_um'], tuple(r['outline_um']))
    assert n > 0


def test_unsited_region_skipped(tmp_path):
    g = grid(400, 400, 2, 2, 16000); g['regional_entries'][3]['xy_um'] = None
    r = m.clock_region_sites(regions(tmp_path, big=g), 'big', (400, 400), ['clk'])
    assert r['entries'] == 3 and r['unsited'] == 1


def test_edge_entry_snaps_inside_band(tmp_path):
    g = grid(630.72, 1209.6, 11, 3, 162477); g['regional_entries'][-1]['xy_um'] = [630.0, 1209.0]
    r = m.clock_region_sites(regions(tmp_path, big=g), 'big', (630.72, 1209.6), ['clk'])
    m.planned_clock_sites_text(r['clock_sites_um'], (630.72, 1209.6))
