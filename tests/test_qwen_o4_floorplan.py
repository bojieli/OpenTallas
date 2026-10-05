"""W5 Qwen O4 floorplan records: integer placement, RTL inventory, macro-packed dies."""
import gzip
import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RP = ROOT / 'results/floorplan/qwen_o4_rom_placement.json'
INV = ROOT / 'results/floorplan/qwen_o4_die_inventory.json'
FP = ROOT / 'results/floorplan/qwen_o4/floorplan.json'


def load(p):
    if not p.exists():
        pytest.skip(f'{p} not generated')
    return json.loads(p.read_text())


def test_rom_placement_is_integer_and_closes():
    r = load(RP)
    code = r['code_rom']
    assert code['words_per_column'] == code['target_words'] + code['drafter_words']
    assert code['banks_per_column'] * code['bank_depth'] >= code['words_per_column']
    assert (code['banks_per_column'] - 1) * code['bank_depth'] < code['words_per_column']
    assert code['macros'] == code['word_columns'] * code['banks_per_column']
    assert code['word_columns'] * 2 == r['die']['groups']
    # segments tile the column's word space exactly, in order
    segs = r['code_segments']
    assert segs[0]['first_word'] == 0
    for a, b in zip(segs, segs[1:]):
        assert b['first_word'] == a['last_word'] + 1
    assert segs[-1]['last_word'] + 1 == code['words_per_column']
    s = r['scale_rom']
    assert s['rtl_compatible']['banks_per_port_group'] * 4096 >= s['words_per_die']
    assert s['result_port_groups'] == 96
    t = r['totals']
    assert t['placed_capacity_useful_bits'] >= t['stored_bits']
    for k in ('macros',):
        assert isinstance(t[k], int)


def test_inventory_fit_is_holdout_verified():
    r = load(INV)
    for k in ('inst:ot_hdc_bmul', 'inst:ot_hdc_fadd', 'inst:ot_hdc_fmul', 'inst:ot_hdc_qadd'):
        assert r['counts'][k]['holdout_ok'], k
    assert r['at_6144']['inst:ot_hdc_bmul'] == 6144 * 16
    assert r['at_6144']['inst:ot_hdc_fmul'] == 6144 * 16
    assert r['reachability']['fmul_reachable'] == 96 * 16
    assert any(g['item'].startswith('lane copies') for g in r['ledger_gaps'])


def test_floorplans_are_legal_and_account_every_macro():
    f = load(FP)
    rp = load(RP)
    for key, d in f['designs'].items():
        assert d['legality']['legal'], (key, d['legality']['errors'])
        assert d['legality']['overlaps_including_halo'] == 0
        defp = ROOT / 'results/floorplan/qwen_o4' / f"{d['design']}_{d['profile']}_macros.def.gz"
        assert hashlib.sha256(gzip.decompress(defp.read_bytes())).hexdigest() == d['def_sha256']
        assert d['macro_counts'].get('ot_hbm3e_phy') == 4
        if d['design'] == 'rom_die' and d['geometry']['fits']:
            want = (rp['code_rom']['macros'] + rp['scale_rom']['rtl_compatible']['macros']
                    + rp['embedding_rom']['macros'] + rp['embedding_rom']['scale_macros'])
            assert d['macro_counts']['ot_rom_4096x266_m8'] == want
        if 'wire_budget' not in d:
            continue
        wb = d['wire_budget']
        assert wb['reach_um_per_cycle'] > 0
        for c in wb['connections']:
            assert c['stages_needed'] >= 1 and c['added_cycles'] >= 0
