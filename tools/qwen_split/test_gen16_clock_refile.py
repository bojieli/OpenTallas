#!/usr/bin/env python3
"""DIE-QWEN-GEN16: region re-file of forwarded-lane clock pins (landing -> receiver root, hop 0 -> sender root), reset
repeater column split, and the opt-in co-root group, on the GEN's own _regions_from_placement."""
import os
import sys
from pathlib import Path
from types import SimpleNamespace as N

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ['OT_SPLIT_CK_COROOT'] = 'a,b'
import qwen_rom_fulldie_b3r2 as G  # noqa: E402


def I(n, x, y, master='blk', w=10.0, h=10.0):
    return N(name=n, master=master, x=x, y=y, w=w, h=h)


def model():
    regs = [dict(name='W', kind='k', rect=[0, 0, 5000, 20000]), dict(name='E', kind='k', rect=[5000, 0, 10000, 20000])]
    insts = [I('hub', 0, 0), I('a', 100, 100), I('b', 5100, 100), I('src', 1000, 1000), I('dst', 9000, 1000),
             I('land', 4990, 1000), I('h0', 5010, 1000)]
    reps = [I(f'r{j}', 2000 + (3000 if j >= 6 else 0), 500 + 400 * (j % 6), master='qfd_rst_rep') for j in range(12)]
    insts += reps
    buses = [('clk_r0', 'clock_trunk', 1, [('hub', 'pll_r0'), ('a', 'ck'), ('src', 'ck'), ('land', 'ck')] +
              [(r.name, 'clk') for r in reps]),
             ('clk_r1', 'clock_trunk', 1, [('hub', 'pll_r1'), ('b', 'ck'), ('dst', 'ck'), ('h0', 'ck_s')])]
    return dict(clock_regions=regs, insts=insts, buses=buses, b3r2={},
                ck_follow={('land', 'ck'): 'dst', ('h0', 'ck_s'): 'src'},
                fwd_lanes=dict(lanes=[dict(bid='x', stations=[], landing='land', src_ck='stale', dst_ck='stale')]))


def net_of(m):
    return {(i, p): b for b, c, n, e in m['buses'] for i, p in e if not p.startswith('pll_')}


m = model()
G._regions_from_placement(m)
n = net_of(m)
assert n[('land', 'ck')] == n[('dst', 'ck')], n           # landing on the receiver's root
assert n[('h0', 'ck_s')] == n[('src', 'ck')], n           # hop 0 on the sender's root
assert n[('b', 'ck')] == n[('a', 'ck')], n                # co-root group
cols = {}
for j in range(12):
    cols.setdefault(n[(f'r{j}', 'clk')], set()).add(j // 6)
assert all(len(v) == 1 for v in cols.values()), cols       # never two repeater columns on one root
assert all(n[(f'r{j}', 'clk')] != n[('a', 'ck')] for j in range(12)), n   # the field column left the block region
spans = {}
for j in range(12):
    spans.setdefault(n[(f'r{j}', 'clk')], []).append(500 + 400 * (j % 6))
assert all(max(v) - min(v) <= G.REP_SEG_MM * 1000 for v in spans.values()), spans
r = m['b3r2']['gen16_clock_refile']
assert r['follow_moved'] == 2 and r['rep_regions_split'] >= 1 and not r['follow_missing_owner'], r
m['fwd_lanes']['lanes'][0]['stations'] = []
G._gen16_fwd_ck_names(m)
assert m['fwd_lanes']['lanes'][0]['dst_ck'] == n[('dst', 'ck')], m['fwd_lanes']
# mutant: without the follow map the landing stays on the region its own cell centre is in (the dv2f14bi GAP bug)
m2 = model(); m2['ck_follow'] = {}
G._regions_from_placement(m2)
n2 = net_of(m2)
assert n2[('land', 'ck')] != n2[('dst', 'ck')], 'mutant must reproduce the GAP'
# scattered lane repeaters (no stacked column) stay in their block region (dv2f16 first GEN: 1,340 one-repeater roots)
m3 = model()
for j in range(12):
    r_ = next(i for i in m3['insts'] if i.name == f'r{j}')
    r_.x = 200 + 300 * j if j < 6 else 5200 + 300 * (j - 6)
G._regions_from_placement(m3)
n3 = net_of(m3)
assert all(n3[(f'r{j}', 'clk')] == n3[('a', 'ck')] for j in range(6)), n3
print('GEN16_CLOCK_REFILE PASS: landing->receiver, hop0->sender, co-root, rep columns split <=', G.REP_SEG_MM, 'mm; '
      'no-follow mutant reproduces the GAP')
