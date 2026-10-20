import sys, os, collections
from pathlib import Path
R = Path.cwd(); sys.path.insert(0, str(R / 'tools/s81_dv/layer_prog'))
import xs_place as X, dv_layer_compile as C
FX = '/srv/opentallas-scratch/claude/s81-calpipe/fixtures/L0'; DR = '/srv/opentallas-scratch/claude/toksim-s81b-fwoa/dieref'
die = C.Die(C.die_tree(None, DR))
rec, field = X.compile_frame(die, sys.argv[1], FX, [sys.argv[2]], only={1})
ph = rec['phases'][1]; pl = ph['plan']
print('PHASE', ph['phase'], 'rows', ph['rows'], 'faults', ph['faults'], 'ret', ph['ret_words'])
root = pl['topology']['root']
for n, r in sorted(pl['nodes'].items(), key=lambda x: int(x[0][1:])):
    print('  node', n, 'ROOT' if n == root else '', r['a'], r['b'], 'in', len(r['arrive_a']), len(r['arrive_b']), 'merges', r['merges'], 'fwd', r['forwards'], 'faults', [f[0] for f in r['faults']])
print('RET edges', sorted(w[0] for w in pl['ret']))
