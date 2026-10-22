"""KV-DOMSPLIT 10-19: no KV die word mixes the core clock ck and the HBM clock hck (OT_KV_DOMSPLIT=1).  The group <-> PC
words split per measured launch domain, the group gather lands its hck status bits in the group, relays take the launching
pin's clock.  Every check has a mutant that must FAIL (synthetic tables / netlists + the committed measured records)."""
import json
import sys
from collections import namedtuple
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import kv_pin_repair as KPR  # noqa: E402
import kv_static_die as KSD  # noqa: E402
import kv_static_params as KSP  # noqa: E402

BASE = 'results/arch/qwen_kv_domsplit_1019/base_ports'
SPLIT = 'results/arch/qwen_kv_domsplit_1019/ports'
Inst = namedtuple('Inst', 'name master')


@pytest.fixture
def records(monkeypatch):
    def use(d):
        monkeypatch.setattr(KPR, 'PORT_DOMAINS', d)
        monkeypatch.setattr(KPR, '_PD', {})
    return use


def mixed_outputs(d):
    out = []
    for k in ('grp', 'grp_h', 'pc', 'pc_h', 'hroot'):
        for p, v in json.loads((ROOT / d / f'{k}_ports.json').read_text())['ports'].items():
            ds = {x for x in v.get('domains', []) if x not in ('none', '?const')}
            if v.get('dir') == 'output' and len(ds) > 1:
                out.append(f'{k}.{p}')
    return out


def test_split_records_have_single_domain_outputs():
    assert mixed_outputs(SPLIT) == []
    # mutant: the base (unsplit) tiles -> o_pc0..3 / o_ctl / o_grp mixed
    assert sorted(mixed_outputs(BASE)) == sorted([f'{k}.{p}' for k in ('grp', 'grp_h') for p in
                                                  ('o_pc0', 'o_pc1', 'o_pc2', 'o_pc3', 'o_ctl')] + ['pc.o_grp', 'pc_h.o_grp'])


def test_relay_trunk_on_split_words(records):
    by = {'slg_WS_4': Inst('slg_WS_4', 'qkd_kvs_grp'), 'kvpc_WS_2': Inst('kvpc_WS_2', 'qkd_kvs_pc')}
    buses = [('clk_hbm_WS', 'clock_trunk', 1, [('pll', 'o'), ('slg_WS_4', 'hck'), ('kvpc_WS_2', 'hck')]),
             ('clk_core_WS', 'clock_trunk', 1, [('pll', 'o'), ('slg_WS_4', 'ck'), ('kvpc_WS_2', 'ck')]),
             ('clk_core_c', 'clock_trunk', 1, [('pll', 'o')])]
    records(SPLIT)
    got = {pa: (buses[j][0], d) for pa, pb, (j, d) in
           [(pa, pb, KPR.relay_trunk(buses, by, (s, pa), (t, pb))) for s, pa, t, pb in
            (('slg_WS_4', 'o_pc0', 'kvpc_WS_2', 'i_grp'), ('slg_WS_4', 'o_pc0_h', 'kvpc_WS_2', 'i_grp_h'),
             ('kvpc_WS_2', 'o_grp', 'slg_WS_4', 'i_pc1'), ('kvpc_WS_2', 'o_grp_h', 'slg_WS_4', 'i_pc1_h'))]}
    assert got == {'o_pc0': ('clk_core_WS', 'core'), 'o_pc0_h': ('clk_hbm_WS', 'hbm'),
                   'o_grp': ('clk_core_WS', 'core'), 'o_grp_h': ('clk_hbm_WS', 'hbm')}
    records(BASE)      # mutant: the unsplit word has no single relay clock
    assert KPR.relay_trunk(buses, by, ('slg_WS_4', 'o_pc0'), ('kvpc_WS_2', 'i_grp'))[1] == 'mixed'


def test_audit_fails_a_mixed_word_under_domsplit(tmp_path, records, monkeypatch):
    model = dict(bus_src={'ks_slg_WS_4__o_pc0': ['slg_WS_4', 'o_pc0', 'kvpc_WS_2', 'i_grp'],
                          'ks_slg_WS_4__o_pc0_h': ['slg_WS_4', 'o_pc0_h', 'kvpc_WS_2', 'i_grp_h']},
                 masters={'slg_WS_4': 'qkd_kvs_grp', 'kvpc_WS_2': 'qkd_kvs_pc'})
    f = tmp_path / 'die.v'
    f.write_text("  qkd_rlys_36 rly_ks_slg_WS_4__o_pc0_0 (.ck(n_clk_core_WS), .a(n_ks_slg_WS_4__o_pc0[32:0]), .b(n_x[32:0]));\n"
                 "  qkd_rlys_100 rly_ks_slg_WS_4__o_pc0_h_0 (.ck(n_clk_hbm_WS), .a(n_ks_slg_WS_4__o_pc0_h[94:0]), .b(n_y[94:0]));\n")
    monkeypatch.setenv('OT_KV_DOMSPLIT', '1')
    records(SPLIT)
    fails, info = KSP.relay_domains(f, model)
    assert fails == [] and info['relays_checked'] == 2 and info['mixed_domain_buses'] == {}
    # mutant 1: the hck half relayed on the core trunk
    f2 = tmp_path / 'die2.v'
    f2.write_text(f.read_text().replace('.ck(n_clk_hbm_WS)', '.ck(n_clk_core_WS)'))
    assert [x['id'] for x in KSP.relay_domains(f2, model)[0]] == ['RELAY_DOMAIN']
    # mutant 2: the unsplit (mixed) tile records -> the word is mixed -> fail closed under the flag
    records(BASE)
    assert 'RELAY_DOMAIN_MIXED' in [x['id'] for x in KSP.relay_domains(f, model)[0]]


def test_ds_parts_splits_by_measured_domain(monkeypatch):
    monkeypatch.setattr(KSD, 'DOMSPLIT', True)
    monkeypatch.setitem(KSD._G, 'ds_table', {'grp': {'phase.epoch_h[0+:16]': 'hck', 'lcal.r_epoch[0+:16]': 'ck'}, 'pc': {}})
    lst = [('pc__expected_epoch', 16, ('lcal_WS_3', 'r_epoch', 0, 16)), ('pc__cal_epoch', 16, ('phase_WS_3', 'epoch_h', 0, 16))]
    parts = KSD.ds_parts('kvpc_WS_13', 'slg_WS_3', lst)
    assert [(s, [e[0] for e in p]) for s, p in parts] == [('', ['pc__expected_epoch']), ('_h', ['pc__cal_epoch'])]
    # a pair that is not group <-> PC stays one word
    assert KSD.ds_parts('kvs_ctl', 'slg_WS_3', lst) == [('', lst)]
    # mutant: a field without a measured domain fails closed
    monkeypatch.setitem(KSD._G, 'ds_table', {'grp': {'lcal.r_epoch[0+:16]': 'ck'}, 'pc': {}})
    with pytest.raises(ValueError, match='no measured launch domain'):
        KSD.ds_parts('kvpc_WS_13', 'slg_WS_3', lst)


def test_committed_table_matches_split_records():
    """every hck field of the table sits in a '_h' port of the split tiles and every ck field in a ck port: widths add up"""
    tab = json.loads((ROOT / KSD.DOMSPLIT_TABLE).read_text())['fields']
    rec = {k: json.loads((ROOT / SPLIT / f'{k}_ports.json').read_text())['ports'] for k in ('grp', 'pc')}
    w = lambda f: int(f.rsplit('+:', 1)[1].rstrip(']'))          # noqa: E731
    pc_h = sum(w(f) for f, d in tab['pc'].items() if d == 'hck')
    assert rec['pc']['o_grp_h']['width'] == pc_h == rec['grp']['i_pc0_h']['width']
    # grp -> PC j: the hck fields of PC j's word (bcdc<j>, phase, fcal blk_go[j]) minus the gather-only status levels
    g_h = sum(w(f) for f, d in tab['grp'].items() if d == 'hck' and not f.startswith(('bcdcf.', 'fcal.'))
              and not f.split('.')[1].startswith(('applied_hbm', 'fault_hbm')) and (not f.startswith('bcdc') or f.startswith('bcdc0.')))
    assert rec['grp']['o_pc0_h']['width'] == g_h + 1 == rec['pc']['i_grp_h']['width']
