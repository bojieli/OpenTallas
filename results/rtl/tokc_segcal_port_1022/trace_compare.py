#!/usr/bin/env python3
"""TOKc-SEGCAL 10-22: per-cycle lockstep of two tb traces ("cycle hex" lines, the 2481-bit output vector of
tb_qfd_tt_ctlm_prog_hp13.sv / ref_tb_trace_patch.py).   trace_compare.py REF DUT [STAGE_LOG]
Prints TRACE_LOCKSTEP PASS|FAIL compared=N mismatches=M, the first mismatching cycles and the fields that differ."""
import sys
F = [('pobs', 76), ('csr', 1), ('lcv', 1), ('ntk', 18), ('nps', 18), ('cst', 6), ('cobs', 76), ('dobs', 69), ('cir', 1),
     ('dc', 56), ('ncmd', 380), ('hr', 453), ('cmd', 116), ('tl', 1088), ('emb_start', 1), ('emb_token', 18),
     ('emb_position', 18), ('emb_user', 2), ('cf', 1)]
W = sum(w for _, w in F)
def fields(v):
    out, sh = {}, W
    for n, w in F:
        sh -= w; out[n] = (v >> sh) & ((1 << w) - 1)
    return out
def load(p):
    return {int(c): int(h, 16) for c, h in (l.split() for l in open(p) if l.strip())}
r, d = load(sys.argv[1]), load(sys.argv[2])
cyc = sorted(set(r) & set(d))
bad = [c for c in cyc if r[c] != d[c]]
stage = {}
for c in cyc:
    stage[c] = fields(r[c])['cst']
print(f'TRACE_LOCKSTEP {"PASS" if not bad and cyc and len(r) == len(d) else "FAIL"} compared={len(cyc)} '
      f'ref_cycles={len(r)} dut_cycles={len(d)} mismatches={len(bad)}')
if bad:
    fs = {}
    for c in bad:
        a, b = fields(r[c]), fields(d[c])
        for n in a:
            if a[n] != b[n]:
                fs.setdefault(n, []).append(c)
    print('  first mismatch cycle', bad[0], 'last', bad[-1], 'command_stage at first mismatch', stage[bad[0]])
    print('  stages with mismatches', sorted({stage[c] for c in bad}))
    for n, cs in fs.items():
        print(f'  field {n}: {len(cs)} cycles, first {cs[0]}')
