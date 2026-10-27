#!/usr/bin/env python3
"""LEC-ICG-2 fast check: saved AIGs + saved converged hyp.json of the base run, then the fixed lec.py's
unwritten-X build and late_pairs, then prove every compare point.  usage: diag_full.py LEC_PY_DIR LECDIR WORK"""
import json, sys, collections
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import lec as LC
out, work = Path(sys.argv[2]), Path(sys.argv[3])
work.mkdir(parents=True, exist_ok=True)
L = LC.Lec(LC.read_aig(out / 'gold.aig'), LC.read_map(out / 'gold.map'),
           LC.read_aig(out / 'gate.aig'), LC.read_map(out / 'gate.map'))
log = []
LC.normalize_gold_elements(L, LC.slang_elements(out / 'gold.aliases.json'), log)
LC.json_alias_keys(L, log, work=out)
LC.slang_element_keys(L, log, work=out)
LC.alias_arrays(L, log, work=out)
LC.relayout(L, log)
LC.renamed(L, log)
L.hyp = {(sd, k): tuple(h) for sd, k, h in json.load(open(out / 'hyp.json'))}
L.build(with_compare=False, with_hyp=False)
print('unwritten', len(L.unwritten), L.unwritten[:12], flush=True)
lp = LC.late_pairs(L, work, 1000, log)
print('late_pairs', lp, flush=True)
m, kind = L.build(with_compare=True, with_hyp=True)
st = LC.prove(m, work, 1000, log, tag='full')
c = collections.Counter(st.values())
cmp_bad = sorted(n for n, s in st.items() if s != 'proved' and not n.startswith(('hyp:', 'cons:')))
hyp_bad = sorted(n for n, s in st.items() if s != 'proved' and n.startswith(('hyp:', 'cons:')))
print('statuses', dict(c), 'compare not proved', len(cmp_bad), 'hyp not proved', len(hyp_bad))
for n in cmp_bad[:80]:
    print('  CMP', st[n], n)
for n in hyp_bad[:40]:
    print('  HYP', st[n], n)
(work / 'diag_full.log').write_text('\n'.join(log)[-200000:])
