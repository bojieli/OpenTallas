"""First generated kit is preflightable; a hardened child never counts as glue."""
import json
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cells
import cap_estimate
import gen_phys


def plan(t):
    return SimpleNamespace(types={'t': t}, raw={'partition_types': {'t': t}, 'partitions': []}, path=None)


def budget(tmp_path):
    (tmp_path / 'budget.json').write_text(json.dumps(dict(outline_um=[100, 100], pins=100)))


def test_explicit_cells_is_available_before_synthesis(tmp_path):
    budget(tmp_path)
    rec = gen_phys.write_cap_budget(plan(dict(cells=410000)), 't', tmp_path)
    assert rec['cells'] == 410000 and rec['basis'] == 'type.cells'
    errors, projection = cap_estimate.check_kit(tmp_path)
    assert errors and projection['verdict'] == 'OVER'


def test_cored_flat_estimate_is_not_a_movable_count(tmp_path, monkeypatch):
    budget(tmp_path)
    monkeypatch.setattr(cells, 'estimate', lambda *a: (_ for _ in ()).throw(AssertionError('flat lookup')))
    # Re-generation must also retire an old, unsound flat cap receipt.
    (tmp_path / 'cap_budget.json').write_text('{"cells": 7000000}')
    t = dict(hard_cores=[dict(inst='u_c')], contents=[dict(inst='u_c', cells=7000000)])
    rec = gen_phys.write_cap_budget(plan(t), 't', tmp_path)
    assert 'cells' not in rec and rec['macros'] == 1 and rec['basis'].startswith('CORED')
    assert cap_estimate.check_kit(tmp_path) == ([], None)


def test_cored_explicit_glue_and_macro_instance_count(tmp_path):
    t = dict(cells=1000, hard_cores=[dict(inst='a'), dict(inst='b')],
             contents=[dict(inst='a', lef='same.lef'), dict(inst='m0', lef='same.lef'),
                       dict(inst='m1', lef='same.lef')])
    rec = gen_phys.write_cap_budget(plan(t), 't', tmp_path)
    assert rec['cells'] == 1000 and rec['macros'] == 4


def test_measured_synthesis_supersedes_plan(tmp_path):
    budget(tmp_path)
    gen_phys.write_cap_budget(plan(dict(cells=7000000)), 't', tmp_path)
    (tmp_path / 'native_cell_count.json').write_text('{"stdcells": 1000, "macros": 0}')
    errors, projection = cap_estimate.check_kit(tmp_path)
    assert not errors and projection['synth'] == 1000 and 'measured' in projection['synth_basis']


def test_noncore_estimate_is_cached_without_gating_unknown(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(cells, 'estimate', lambda *a: (calls.append(a) or {'t': (2000, 'contents')}, []))
    p = plan(dict(contents=[dict(cells=2000)]))
    assert gen_phys.write_cap_budget(p, 't', tmp_path)['cells'] == 2000
    assert gen_phys.write_cap_budget(p, 't', tmp_path)['cells'] == 2000
    assert len(calls) == 1
    unknown = plan({})
    monkeypatch.setattr(cells, 'estimate', lambda *a: ({}, []))
    assert 'cells' not in gen_phys.write_cap_budget(unknown, 't', tmp_path)

