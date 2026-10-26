#!/usr/bin/env python3
"""Compare two tb_q3prog_trace traces (legacy vs __q3sync assembly) cycle by cycle outside reset windows.
A diff is don't-care only when it sits on a data field whose own valid is 0 in BOTH traces (per lane where the bus is
laned); every other diff is a FAIL.  Usage: trace_compare.py legacy/trace.txt sync/trace.txt [--json out.json]"""
import sys, json, re
from collections import Counter

def load(p):
    fields, rows = None, []
    for ln in open(p):
        if ln.startswith('# TRACE_FIELDS'):
            fields = [(f.split(':')[0], int(f.split(':')[1])) for f in ln.split()[2:] if ':' in f]
            continue
        c, r, h = ln.split()
        rows.append((int(c), int(r), int(h, 16)))
    return fields, rows

def expand(rows):
    out, cur, i = {}, None, 0
    last = rows[-1][0]
    for c in range(rows[0][0], last + 1):
        while i < len(rows) and rows[i][0] == c:
            cur = rows[i]; i += 1
        out[c] = (cur[1], cur[2])
    return out

fl, rl = load(sys.argv[1]); fs, rs = load(sys.argv[2])
assert fl == fs, 'field lists differ'
off, pos = {}, sum(w for _, w in fl)
for n, w in fl:                       # first field = MSB of the concat
    pos -= w; off[n] = (pos, w)
get = lambda v, n: (v >> off[n][0]) & ((1 << off[n][1]) - 1)
# data field -> (valid field, lane width of data, lane count) ; lane k of data valid = bit k of valid
LANED = {'del_d': ('del_v', 545), 'del_a': ('del_v', 40), 'txf': ('txv', 612), 'tkx_del_flit': ('tkx_del_valid', 545),
         'ag_d': ('ag_v', 256), 'ag_src': ('ag_v', 2), 'ag_tag': ('ag_v', 3)}
SCALAR = {'rrd': 'rrv', 'rrt': 'rrv', 'inj_idx': 'inj_rd', 'inj_addr': 'inj_rd'}
L, S = expand(rl), expand(rs)
cyc = sorted(set(L) & set(S))
cmp_n, dc, fail = 0, Counter(), Counter()
first_fail = []
for c in cyc:
    (rL, vL), (rS, vS) = L[c], S[c]
    if not (rL and rS):
        continue
    cmp_n += 1
    if vL == vS:
        continue
    for n, (o, w) in off.items():
        a, b = get(vL, n), get(vS, n)
        if a == b:
            continue
        ok = False
        if n in LANED:
            vn, lw = LANED[n]; va, vb = get(vL, vn), get(vS, vn)
            ok = True
            for k in range(w // lw):
                if ((a ^ b) >> (k * lw)) & ((1 << lw) - 1) and ((va >> k) & 1 or (vb >> k) & 1):
                    ok = False
        elif n in SCALAR:
            ok = get(vL, SCALAR[n]) == 0 and get(vS, SCALAR[n]) == 0
        elif n == 'vm_rq':            # 8 banks x {valid, sector[15:0]}
            ok = True
            for k in range(8):
                if ((a ^ b) >> (17 * k)) & 0x1ffff and ((a >> (17 * k + 16)) & 1 or (b >> (17 * k + 16)) & 1):
                    ok = False
        (dc if ok else fail)[n] += 1
        if not ok and len(first_fail) < 20:
            first_fail.append('cyc %d %s' % (c, n))
res = dict(compared_cycles=cmp_n, legacy_cycles=len(L), sync_cycles=len(S), dontcare=dict(dc), fail=dict(fail),
           first_fail=first_fail, verdict='PASS' if not fail and cmp_n > 0 else 'FAIL')
print(json.dumps(res))
if len(sys.argv) > 4 and sys.argv[3] == '--json':
    json.dump(res, open(sys.argv[4], 'w'), indent=1)
sys.exit(0 if res['verdict'] == 'PASS' else 1)
