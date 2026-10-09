"""s81-gen (2026-10-09): layer1e die kind, --ctrl-rq, --path-pick candidates, --relay-tt-reach / OT_S81_HOP_R_CC options.

Light checks only (no die build): the full generator runs are remote (`dsrom_s81_fulldie.py check`, s81-gen.log)."""
import argparse
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import dsrom_s81_fulldie as F  # noqa: E402

L1 = ('--gen r8 --rev r9 --elem-h 198.72 --cc-reach-um 215 --hop-fix --pin-relay --pairs 1792 --q-elem-h 221.4 --bf-per-region 4 '
      '--pq-place --die {die}')


def _opts(extra, die='layer1'):
    return F.die_options(argparse.ArgumentParser()).parse_args((L1.format(die=die) + ' ' + extra).split())


def _ports(path, module):
    """{port: width} of a Verilog module header"""
    txt = (ROOT / path).read_text()
    hdr = txt[txt.index(f'module {module}'):]
    hdr = hdr[:hdr.index(');')]
    params = {k: int(v) for k, v in re.findall(r'parameter\s+integer\s+(\w+)\s*=\s*(\d+)', hdr)}
    params['ENG_ID_W'] = 17
    hdr = re.sub(r'//[^\n]*', '', hdr)
    out = {}
    for msb, names in re.findall(r'(?:input|output)\s+(?:wire|reg)\s*(?:\[([^\]:]+):0\])?\s*([\w\s,]+?)(?=,?\s*(?:input|output|$))',
                                 hdr + ' '):
        for name in filter(None, (n.strip() for n in names.split(','))):
            out[name] = 1 if not msb else eval(msb, {}, dict(params)) + 1   # noqa: S307 (header arithmetic only)
    return out


def test_layer1e_options():
    F.apply_options(_opts('--host', 'layer1e'))
    assert F.DIE_KIND == 'layer1e' and F.STACKS['layer1e'] == ('SW', 'SE') and F.CTRL_RQ and F.HOST_SLAB
    assert F.PAIRS == 1792
    with pytest.raises(AssertionError):
        F.apply_options(_opts('', 'layer1e'))          # Engram boot load needs the host path
    F.apply_options(_opts(''))
    assert not F.CTRL_RQ and F.RELAY_TT_REACH is None and not F.PATH_PICK


def test_reach_and_path_options(monkeypatch):
    F.apply_options(_opts('--path-pick --relay-tt-reach 600 --ctrl-rq'))
    assert F.PATH_PICK and F.RELAY_TT_REACH == 600.0 and F.CTRL_RQ and F.HOP_R_CC == 410.0
    monkeypatch.setenv('OT_S81_HOP_R_CC', '500')
    F.apply_options(_opts(''))
    assert F.HOP_R_CC == 500.0                          # 9917e9987 override was reset to 410 by apply_options


def test_hop_path_candidates():
    cor = dict(v=(100.0, 0.0, 140.0, 1000.0), h=(0.0, 480.0, 1000.0, 520.0), short=(600.0, 600.0, 640.0, 700.0))
    a, b = (900.0, 900.0), (20.0, 50.0)
    ps = F._hop_paths(a, b, cor)
    assert ps[0] == [a, (b[0], a[1]), b] and ps[1] == [a, (a[0], b[1]), b]
    assert [a, (120.0, a[1]), (120.0, b[1]), b] in ps          # Z through the spanning vertical corridor
    assert [a, (a[0], 500.0), (b[0], 500.0), b] in ps          # Z through the spanning horizontal corridor
    assert len(ps) == 4                                         # 'short' spans neither turn
    z = [a, (120.0, a[1]), (120.0, b[1]), b]
    assert F._corr_frac(z, list(cor.values())) > F._corr_frac(ps[0], list(cor.values()))


def test_engram_bus_widths_match_rtl():
    lk = _ports('rtl/dsrom_sys/engram/dsfd_engram_lkp.sv', 'dsfd_engram_lkp')
    sk = _ports('rtl/dsrom_sys/engram/dsfd_engram_sink.sv', 'dsfd_engram_sink')
    pf = _ports('rtl/dsrom_sys/engram/ot_dsrom_engram_prefetch.sv', 'ot_dsrom_engram_prefetch')
    ct = _ports('rtl/dsrom_sys/s81_ph/dsfd_ctrl.sv', 'dsfd_ctrl')
    w = {(a, pa): bits for a, pa, b, pb, bits, _ in F.ENG_BUSES}
    assert w[('collective', 't_eng')] == lk['win_v'] + lk['win_ids'] + lk['rel']
    assert w[('eng', 't_collective')] == lk['win_cred']
    assert w[('eng', 't_ag')] == sum(lk[p] for p in ('o_v', 'o_col', 'o_beat', 'o_slot', 'o_d', 'st_v', 'st_slot',
                                                     'st_bad', 'fault'))
    assert w[('collective', 't_engc')] == lk['o_cred']
    assert w[('collective', 't_engi')] == sum(sk[p] for p in ('in_v', 'in_col', 'in_beat', 'in_slot', 'in_d', 'st_v',
                                                             'st_slot', 'st_bad'))
    assert w[('eng', 't_air')] == sk['in_r']
    assert w[('eng', 't_vm')] == sum(pf[p] for p in ('out_v', 'out_data', 'out_ce', 'out_ue', 'fault')) + sk['rdy'] + sk['perr']
    assert w[('vm', 't_eng')] == pf['rd_v'] + pf['rd_addr'] + sk['rel_v'] + sk['rel_slot']
    assert w[('host', 't_eng')] == lk['cfg_layer'] + lk['cfg_rank']
    assert F.HBM_RQ_BITS == ct['rq'] and ct['rk'] == ct['wd'] == 32
    assert 35 == lk['hq_v'] + lk['hq_atom'] + lk['hq_tag']                              # eng_sw_q
    assert 265 == lk['hq_cred'] + lk['hr_v'] + lk['hr_tag'] + lk['hr_idx'] + lk['hr_d']  # eng_sw_r
