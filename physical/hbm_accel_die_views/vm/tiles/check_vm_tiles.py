#!/usr/bin/env python3
"""check_vm_tiles.py trace_ref.hex trace_dut.hex: every output bit of the joined r19 tiles must equal the monolithic
hfd_vm's at ONE constant latency (dut cycle = ref cycle + L, L in -6..24) over the whole trace (tb_vm_tiles.sv MODE 2).
Forwarded-clock bits (q[581:580], x[2067:2063]) are clocks, not data, and are skipped.  Exit 1 on any unmatched bit.
Prints, per port, the contiguous bit ranges and their latency difference (the cycle cost of the split on that path)."""
import sys
PORTS = [('t_su_SW', 2048), ('t_su_NW', 2048), ('t_su_SE', 2048), ('t_su_NE', 2048), ('qSW', 582), ('qNW', 582),
         ('qSE', 582), ('qNE', 582), ('xSW', 2068), ('xNW', 2068), ('xSE', 2068), ('xNE', 2068), ('t_quant', 1024),
         ('t_router', 512)]
SKIP = {p: ((1 << 580) | (1 << 581)) if p[0] == 'q' else (31 << 2063) if p[0] == 'x' else 0 for p, _ in PORTS}
def load(f):
    return [[int(x, 16) for x in l.split()] for l in open(f) if l.strip()]
ref, dut = load(sys.argv[1]), load(sys.argv[2])
n = min(len(ref), len(dut)); LAGS = range(-6, 25); WARM = 30
bad = 0; out = []
for i, (p, w) in enumerate(PORTS):
    full = (1 << w) - 1
    ok = {}
    for L in LAGS:
        m = 0
        for c in range(WARM, n - 30):
            if 0 <= c + L < n:
                m |= ref[c][i] ^ dut[c + L][i]
        ok[L] = ~m & full
    lag = []
    for b in range(w):
        if (SKIP[p] >> b) & 1:
            lag.append('clk'); continue
        good = [L for L in LAGS if (ok[L] >> b) & 1]
        # prefer the smallest |L| among the matching lags (constant bits match every lag)
        lag.append(min(good, key=abs) if good else None)
        if not good:
            bad += 1
    seg, s0 = [], 0
    for b in range(1, w + 1):
        if b == w or lag[b] != lag[s0]:
            seg.append(f'[{b-1}:{s0}]={lag[s0]}'); s0 = b
    out.append(f'{p}: ' + ' '.join(seg))
print('\n'.join(out))
print(f'VM_TILES_STRUCT cycles={n} unmatched_bits={bad}')
sys.exit(1 if bad else 0)
