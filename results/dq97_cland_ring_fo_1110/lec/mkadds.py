#!/usr/bin/env python3
"""adds.ys: register-correspondence $equiv cells for the same-D copies the gate adds (DIE-QC-97 ring LEC).
gate wen copy (slot i, 32-bit chunk c) == gold wen (slot i, chunk 0); gate select copy r of chunk c == gold di of chunk c."""
import sys
DEPTH, WNC_GOLD, WNC_GATE, NCH, SREP = 4, 9, 18, 9, 2
L = []
for i in range(DEPTH):
    for c in range(WNC_GATE):
        L.append(f"equiv_add -try \\u.u_ring.g_wreg.sl[{i}].ch[0].u_wen.q_gold \\u.u_ring.g_wreg.sl[{i}].ch[{c}].u_wen.q_gate")
    for c in range(WNC_GOLD):
        L.append(f"equiv_add -try \\u.u_ring.g_wreg.sl[{i}].ch[0].u_wen.q_gold \\u.u_ring.g_wreg.sl[{i}].ch[{c}].u_wen.q_gold")
for c in range(NCH):
    for r in range(SREP):
        L.append(f"equiv_add -try \\u.u_ring.dch[{c}].u_dsel.di_gold \\u.u_ring.dch[{c}].u_dsel.g_srep.sr[{r}].u_sel.di_gate")
print("\n".join(L))
