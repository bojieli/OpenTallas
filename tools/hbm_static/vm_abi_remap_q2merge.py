#!/usr/bin/env python3
"""Offline fixed-calendar migration for the NW (q2) VM write merge (H-SM 2026-10-16, hfd_vms_wq2_merge).

The NW banks become the exact q0C master (WG 3 -> 2).  The two wide sources that used owners 1 (SM writer smw_NW) and
2 (quantiser hb_quant_NW) now reach the bank's single wq1 port through hfd_vms_wq2_merge, which adds exactly 2 edges
(pin flop + merge flop).  Producers are UNCHANGED (their own fixed latencies stand); the VM calendar therefore
reserves the bank write slot of those writes 2 edges later, as owner 1:

  wslot owner 0            -> 0, same edge
  wslot owner 1 or 2       -> 1, edge + 2       (MERGE_EDGES; a write the merge leaf delivers)
  wslot owner k >= 3       -> k - 1, same edge  (COLL, CW, packet, CCW, DMA)

Static and exact: a moved slot that lands on an edge where that bank already has a write slot is an ERROR (the
compiler must place it elsewhere; nothing is arbitrated at run time).  In a looped programme a moved slot may not
wrap past the loop body (the final iteration would lose it): also an error.  Read slots and every other field are
unchanged.  Done visibility of moved writes is +1 edge later again (leaf output flop); producers do not wait on it.
"""
import argparse, copy, json, os
from pathlib import Path

MERGE_EDGES = int(os.environ.get('OT_Q2MERGE_EDGES', '2'))  # mutant hook: the bench proves 2 and rejects 1/3


def chunks(value, width, count):
    return [(value >> (width * k)) & ((1 << width) - 1) for k in range(count)]


def packed(values, width):
    return sum(v << (width * k) for k, v in enumerate(values))


def migrate(schedule, quadrant='NW', wb=3, edges=None):
    edges = MERGE_EDGES if edges is None else edges
    if quadrant != 'NW':
        return copy.deepcopy(schedule)
    out = copy.deepcopy(schedule)
    cyc = out['cycles']
    for c in cyc:
        for k, v in list(c.items()):
            if isinstance(v, str):
                c[k] = int(v, 0)
    n = len(cyc)
    looped = int(out.get('loops', 1)) > 1
    old = [(c.get('wslot_v', 0), chunks(c.get('wslot', 0), wb, 8)) for c in cyc]
    new_v = [0] * n
    new_s = [[0] * 8 for _ in range(n)]
    moved = []
    for t, (v, codes) in enumerate(old):
        for b in range(8):
            if not (v >> b) & 1:
                continue
            k = codes[b]
            if k in (1, 2):
                moved.append((t, b))
            else:
                new_v[t] |= 1 << b
                new_s[t][b] = k if k == 0 else k - 1
    for t, b in moved:
        u = t + edges
        if u >= n:
            if looped:
                raise ValueError(f'merged write at edge {t} bank {b} wraps past the loop body')
            for _ in range(u - n + 1):
                cyc.append({}); new_v.append(0); new_s.append([0] * 8)
            n = len(cyc)
        if (new_v[u] >> b) & 1:
            raise ValueError(f'merged write slot collides at edge {u} bank {b}')
        new_v[u] |= 1 << b
        new_s[u][b] = 1
    for t, c in enumerate(cyc):
        c['wslot_v'] = new_v[t]
        c['wslot'] = packed(new_s[t], wb)
    out['abi_migration'] = f'nw-wq2-merge: owners 1,2 -> 1 at +{edges} edges, k>=3 -> k-1; offline only'
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('input', type=Path); ap.add_argument('output', type=Path)
    a = ap.parse_args()
    a.output.write_text(json.dumps(migrate(json.loads(a.input.read_text())), indent=2) + '\n')


if __name__ == '__main__':
    main()
