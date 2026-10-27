#!/usr/bin/env python3
"""LEC-ICG-2 diagnosis: rebuild the miter of a finished lec.py run from its saved AIGs + hyp.json, optionally add
candidate hypotheses, and for named outputs (hypotheses / compare points) find a counterexample with pycryptosat
and print the non-default inputs of its cone (matched registers / gold-only registers / X sources).
usage: diag_hyp.py LEC_PY_DIR LECDIR OUTNAME... [--add side|key|eq|oside|okey|inv ...] [--show N]"""
import json, sys, collections
args = sys.argv[1:]
lecdir_py, lecdir = args[0], args[1]
names, adds, show = [], [], 60
i = 2
while i < len(args):
    if args[i] == '--add':
        adds.append(args[i + 1].split('|')); i += 2
    elif args[i] == '--show':
        show = int(args[i + 1]); i += 2
    else:
        names.append(args[i]); i += 1
sys.path.insert(0, lecdir_py)
import lec as LC
import os
sys.path.append(os.environ.get('LEC_SOLVER_PATH', '/lecsolver'))
import pycryptosat
from pathlib import Path
out = Path(lecdir)
L = LC.Lec(LC.read_aig(out / 'gold.aig'), LC.read_map(out / 'gold.map'),
           LC.read_aig(out / 'gate.aig'), LC.read_map(out / 'gate.map'))
log = []
LC.normalize_gold_elements(L, LC.slang_elements(out / 'gold.aliases.json'), log)
LC.json_alias_keys(L, log, work=out)
LC.slang_element_keys(L, log, work=out)
LC.alias_arrays(L, log, work=out)
LC.relayout(L, log)
LC.renamed(L, log)
L.hyp = {}
for sd, k, h in json.load(open(out / 'hyp.json')):
    L.hyp[(sd, k)] = tuple(h)
for a in adds:
    sd, k, kind, osd, ok, inv = a
    L.hyp[(sd, k)] = (kind, osd, ok, int(inv))
    print('ADD', sd, k, '=', osd, ok, inv)
m, kind = L.build(with_compare=True, with_hyp=True)
idx = {n: j for j, n in enumerate(m.onames)}
for n in names:
    if n not in idx:
        print('NO OUTPUT', n, [x for x in m.onames if n.split(':')[-1] in x][:5]); continue
    lit = m.outs[idx[n]]
    need, stack = set(), [lit >> 1]
    while stack:
        v = stack.pop()
        if not v or v in need:
            continue
        need.add(v)
        if v > m.ni:
            kk = v - m.ni - 1
            stack += [m.ands[2 * kk] >> 1, m.ands[2 * kk + 1] >> 1]
    s = pycryptosat.Solver(threads=1)
    def cl(lits):
        if 1 in lits:
            return
        s.add_clause([-(x >> 1) if x & 1 else x >> 1 for x in lits if x > 1])
    for kk in range(len(m.ands) // 2):
        nn = 2 * (m.ni + kk + 1)
        if nn >> 1 not in need:
            continue
        x, y = m.ands[2 * kk:2 * kk + 2]
        cl([nn ^ 1, x]); cl([nn ^ 1, y]); cl([nn, x ^ 1, y ^ 1])
    s.add_clause([max(need), -max(need)])
    if lit <= 1:
        print(n, 'CONST', lit); continue
    sat, model = s.solve(assumptions=[-(lit >> 1) if lit & 1 else lit >> 1])
    ins = sorted(v for v in need if v <= m.ni)
    print(f'== {n}: {"DIFFERS (cex)" if sat else "PROVED"}; cone inputs {len(ins)}')
    if not sat:
        continue
    byk = collections.Counter(kind.get(v, ('?',))[0] for v in ins)
    print('   cone input kinds', dict(byk))
    rows = []
    for v in ins:
        kd = kind.get(v, ('?', '?'))
        val = model[v] if v < len(model) else None
        rows.append((kd[0], kd[1], int(bool(val))))
    # print the non-matched inputs first, then matched ones (all values)
    rows.sort(key=lambda r: (r[0] in ('matched', 'paired'), r[1]))
    for r in rows[:show]:
        print('   ', r[0], r[1], '=', r[2])
