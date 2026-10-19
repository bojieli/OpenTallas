#!/usr/bin/env python3
"""KV-CLOCK 10-18: classify every communicating tile pair of a KV die floorplan that crosses core clock REGIONS
(c, WS, WN, ES, EN; tools/die_clock/specs/kv_regions_1018.json: independent trees, not balanced against each other).

    kv_landed_pairs.py --die-v CASE/die.v.prefwd --pairs GEOM/pairs.tsv --lanes RUN/fwd_lanes.json --out OUT.json

A cross-region pair (die net between a tile on tree X and one on tree Y != X) is
  LANDED       its X-side tile is the last station of a forwarded lane (kv_fwd_lanes.py) whose receiver is the Y tile:
               after the pass that station is the landing (ring written on the lane clock, read on the Y root) -> the
               pair is timed by the die STA landing window (contract L5, one E per bundle, TT + FF), NOT by the 80-ps
               neighbour rule
  RESET_ROOT   a reset / boot net (n_rst_* / n_hboot* / n_rrs_*): the release hop into a region's station tree;
               timed by the die STA as a release window (MCP E_r) at TT and FF
  GAP          anything else: an unlanded data crossing (must be 0)
Intra-region pairs are left to die_clock_check.py (flop skew <= 80 ps at TT and FF).
"""
import argparse, json, re
from collections import Counter

CORE = re.compile(r'n_clk_core_(\w+)')
INST = re.compile(r'^\s+(\S+) (\S+) \((.*)\);\s*$')
RST = re.compile(r'^n_(rst_|hboot|rrs_)')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--die-v', required=True)
    ap.add_argument('--pairs', required=True)
    ap.add_argument('--lanes', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    reg = {}
    for ln in open(a.die_v):
        m = INST.match(ln)
        if m and m.group(1) not in ('module', 'wire'):
            reg[m.group(2)] = frozenset(CORE.findall(m.group(3)))
    lanes = json.load(open(a.lanes))['lanes']
    landed = {}
    for L in lanes:
        for d in L.get('dsts', [L['dst']]):
            landed[frozenset((L['stations'][-1], d))] = L
    cnt, gaps, seen = Counter(), [], set()
    for ln in open(a.pairs):
        f = ln.rstrip('\n').split('\t')
        if f[0] != 'P' or len(f) < 3:
            continue
        A, B, net = f[1], f[2], (f[3] if len(f) > 3 else '')
        ra, rb = reg.get(A, frozenset()), reg.get(B, frozenset())
        if not ra or not rb or ra & rb:
            continue
        key = frozenset((A, B))
        if key in seen:
            continue
        seen.add(key)
        if key in landed:
            cnt['LANDED'] += 1
        elif RST.match(net):
            cnt['RESET_ROOT'] += 1
        else:
            cnt['GAP'] += 1
            gaps.append(dict(a=A, b=B, net=net, ra=sorted(ra), rb=sorted(rb)))
    rec = dict(schema='opentallas.qwen_kv_landed_pairs.v1', die_v=a.die_v, pairs=a.pairs, lanes=a.lanes,
               cross_region_pairs=sum(cnt.values()), classes=dict(cnt), gaps=gaps[:500], gap_count=len(gaps),
               lanes_total=len(lanes), verdict='PASS' if not gaps else 'FAIL')
    json.dump(rec, open(a.out, 'w'), indent=1)
    print(f"KV LANDED PAIRS {rec['verdict']}: {dict(cnt)} (lanes {len(lanes)})")


if __name__ == '__main__':
    main()
