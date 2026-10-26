#!/usr/bin/env python3
"""KV-P3b 10-23: KV die plan v3.3 = v3.2 + the host TX FDI split-bus fix (taptree_audit_v32.json).

plan_v31.fdi_fix splits the x12 host SerDes into two x6 halves and rewrites host.fdi -> serdes_<h>.tx_flit as one edge
per half carrying 'flit half + tx_v' -- but it gave BOTH halves the source-bit range [0, n], so the plan's tap-tree
builder (union of source bits below each tree edge) saw two copies of the same bits and sized the shared trunk
hub_Wi (host) -> io_W3 at max(523, 522) = 523 b instead of the 1,044 distinct source bits (tx_v + 1,043 flit bits).
taptree_audit_v32.py (bit-exact, bind/bitcon) found exactly this one under-carrying lane: L663, deficit 521 b; the
census tap-tree credit (forward_via, widest chain) cannot see split buses (PLAN-TOOL 07:49 warning).

Fix: the real host.fdi source bits (die.v serdes_host .tx_v(fdi[1]) .tx_flit(fdi[1044:2])):
  W half = tx_v + flit[521:0]    = fdi[1] + fdi[523:2]   -> sbits [[1, 523]]            (523 b)
  E half = tx_v + flit[1042:522] = fdi[1] + fdi[1044:524] -> sbits [[1, 1], [524, 1044]] (522 b)
The receive direction is unaffected (each half is its own source bus).  Everything else is v3.2 unchanged.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import plan_v32  # noqa: E402,F401  (v3.2 patches)
import plan_v31 as pv  # noqa: E402

_orig_fdi_fix = pv.fdi_fix
SB = {'serdes_W': [[1, 523]], 'serdes_E': [[1, 1], [524, 1044]]}


def fdi_fix(asb, B):
    _orig_fdi_fix(asb, B)
    n = 0
    for e in asb['edges']:
        if e['s'] == 'host' and e['sp'] == 'fdi' and e['d'] in SB and e['dp'] == 'tx_flit':
            assert sum(b - a + 1 for a, b in SB[e['d']]) == e['bits'], (e['d'], e['bits'])
            e['sbits'] = [list(r) for r in SB[e['d']]]
            n += 1
    assert n == 2, f'host.fdi -> serdes tx_flit halves: {n}'


pv.fdi_fix = fdi_fix


if __name__ == '__main__':
    pv.main()
