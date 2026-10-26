import sys, json, collections, os
from pathlib import Path
R = Path.cwd(); sys.path.insert(0, str(R / 'tools/s81_dv/layer_prog'))
import xs_place as X, dv_layer_compile as C, frame_return_plan as P
FX = '/srv/opentallas-scratch/claude/s81-calpipe/fixtures/L0'; DR = '/srv/opentallas-scratch/claude/toksim-s81b-fwoa/dieref'
die = C.Die(C.die_tree(None, DR))
rec, field = X.compile_frame(die, 'u_f_0L00', FX, ['ffn.experts_gu'], only={1, 2})
for ph in rec['phases'][1:3]:
    pl = ph['plan']
    print('PHASE', ph['phase'], 'rows', ph['rows'], 'faults', ph['faults'], 'ret', ph['ret_words'])
    print(' edges', pl['emission']['edges'])
    print(' placement', [(d['pair'], d['super_row'], d['seg'], d.get('slot')) for d in pl['placement']])
    for n, r in sorted(pl['nodes'].items()):
        if r['faults']:
            print('  node', n, r['a'], r['b'], 'arr_a', r['arrive_a'], 'arr_b', r['arrive_b'], 'faults', r['faults'][:4])
