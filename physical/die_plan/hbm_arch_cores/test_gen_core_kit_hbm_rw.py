"""HBM-RF1 MEM: gen_core_kit_hbm_rw.py adds the delta's defines and swaps the macro list of the resolved recipe only."""
import importlib.util
import json
from pathlib import Path
import pytest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('coregen_rw', HERE / 'gen_core_kit_hbm_rw.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


def test_patched_recipe(tmp_path):
    d = tmp_path / 'mem_recipe_delta.json'
    d.write_text('{}')
    rec = dict(top='ot_x', defines=['A'], macros=['ot_sram_1r1w_64x512_m1_r2c2'], files=['x.sv'])
    r = m.patched_recipe(rec, dict(defines_add=['OT_HBM_RW_MACROS', 'A'], macros=['ot_sram_1r1w_64x306_m1_r0c0_g306']),
                         d, 'ot_x')
    assert r['defines'] == ['A', 'OT_HBM_RW_MACROS']
    assert r['macros'] == ['ot_sram_1r1w_64x306_m1_r0c0_g306']
    assert r['files'] == ['x.sv'] and r['rw_recipe_delta']['macros_before'] == ['ot_sram_1r1w_64x512_m1_r2c2']
    assert rec['defines'] == ['A'] and rec['macros'] == ['ot_sram_1r1w_64x512_m1_r2c2']      # input untouched


def test_entry_must_be_complete(tmp_path):
    d = tmp_path / 'mem_recipe_delta.json'
    d.write_text('{}')
    with pytest.raises(SystemExit):
        m.patched_recipe(dict(defines=[], macros=[]), dict(defines_add=['OT_HBM_RW_MACROS']), d, 'ot_x')


def test_plan_delta_entries_name_built_macros():
    repo = HERE.parents[2]
    delta = json.loads((repo / 'physical/die_plan/hbm/plan_of_record/d44v/mem_recipe_delta.json').read_text())
    for mod, e in delta.items():
        if mod.startswith('_'):
            continue
        assert e['defines_add'] == ['OT_HBM_RW_MACROS'], mod
        for mac in e['macros']:
            assert (repo / 'physical/asap7_memory_macros_v2' / mac / f'{mac}.lef').is_file(), mac
