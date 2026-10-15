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
    F.apply_options(_opts('--host --wfc-hard', 'layer1e'))
    assert F.WFC_HARD
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
    F.apply_options(_opts('--hop-r-cc 480'))
    assert F.HOP_R_CC == 480.0


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


def test_hop_path_candidates_reject_far_detours():
    # a 140-um hop must not try a corridor 13.6 mm away (GEN18p/c18 hop stage ran for hours)
    a, b = (14244.492, 17141.856), (14369.224, 17120.16)
    cor = dict(far=(27800.0, 0.0, 27930.0, 26000.0), near=(14500.0, 0.0, 14600.0, 26000.0),
               hfar=(0.0, 9000.0, 33000.0, 9100.0))
    ps = F._hop_paths(a, b, cor)
    xs = {p[1][0] for p in ps if len(p) == 4}
    assert 14550.0 in xs and not any(x > 20000 for x in xs)
    assert not any(len(p) == 4 and p[1][1] == 9050.0 for p in ps)
    # a long nearly-horizontal hop keeps a corridor a few mm off its line (the 20.2 mm host chain case)
    a2, b2 = (2000.0, 14724.7), (22200.0, 14800.0)
    ps2 = F._hop_paths(a2, b2, dict(h=(0.0, 16400.0, 33000.0, 16500.0)))
    assert any(len(p) == 4 and p[1][1] == 16450.0 for p in ps2)


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


def test_stn70_split_remaps_lanes():
    it = F.Inst('g_cr_0', 'dsfd_stnh_70x3', 1000.08, 2000.16, 30.0, 30.0, kind='stn', region='link', domain='fwd')
    drv = F.Inst('drv', 'dsfd_stnh_70x1', 900.0, 2000.16, 17.256, 17.256, kind='stn')
    m = {'insts': [drv, it], 'buses': [('b0', 'lane', 70, [('drv', 'do0'), ('g_cr_0', 'di2')]),
                                        ('b1', 'fclk', 1, [('g_cr_0', 'fo1'), ('drv', 'fi0')])],
         'chain_tail': {'c': ('g_cr_0', 'fo2', 'do2')}}
    F._split_multi_lane_stations(m)
    names = {i.name: i for i in m['insts']}
    assert 'g_cr_0' not in names and {'g_cr_0_k0', 'g_cr_0_k1', 'g_cr_0_k2'} <= set(names)
    assert all(names[f'g_cr_0_k{k}'].master == 'dsfd_stnh_70x1' for k in range(3))
    assert m['buses'][0][3][1] == ('g_cr_0_k2', 'di0') and m['buses'][1][3][0] == ('g_cr_0_k1', 'fo0')
    assert m['chain_tail']['c'] == ('g_cr_0_k2', 'fo0', 'do0')
    boxes = [names[f'g_cr_0_k{k}'].box() for k in range(3)]
    assert all(a[3] <= b[1] or b[3] <= a[1] or a[2] <= b[0] or b[2] <= a[0] for i, a in enumerate(boxes) for b in boxes[i + 1:])


def test_station_pin_alternation_halves_density():
    Mx = F.Q.Master('dsfd_hstnh_1024', 36.288, 53.976, 3, 't')
    F._lay(Mx, 'W', [('di', 1024)], 'M4', gap=0.0)
    F._lay(Mx, 'E', [('dq', 1024)], 'M4', gap=0.0)
    before = {r[0]: r for r in F.pin_rects(Mx, 1, {})}
    out = F._station_pin_layers({'dsfd_hstnh_1024': Mx})
    assert out['dsfd_hstnh_1024'] > 12.0
    after = F.pin_rects(Mx, 1, {})
    assert {r[0] for r in after} == set(before) and all(r[2] == before[r[0]][2] for r in after)   # same coordinates
    for face_x in (0.0,):
        lys = [r[1] for r in after if r[2][0] <= 1e-6]
        assert lys.count('M4') == lys.count('M6') == 512


def test_station_footprint_grant_depth_only(monkeypatch):
    monkeypatch.setattr(F, 'STN_FOOTPRINTS', {'dsfd_hstnh_1024': (36.288, 53.976)})
    a = F.Inst('s1', 'dsfd_hstnh_1024', 1000.08, 2000.16, 17.256, 53.976, kind='stn')
    blk = F.Inst('blk', 'x', 1018.0, 2000.16, 30.0, 60.0)          # output side taken -> grows toward the input
    m = {'insts': [a, blk], 'buses': []}
    F._apply_station_footprints(m)
    assert (a.w, a.h) == (36.288, 53.976) and a.x + a.w <= 1000.08 + 17.256 + 1e-6
    assert m['stn_footprints']['flipped'] == 1
