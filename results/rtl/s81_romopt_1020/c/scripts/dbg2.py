import sys, os, time
from pathlib import Path
R = Path.cwd(); sys.path.insert(0, str(R / 'tools/s81_dv/layer_prog'))
import xs_place as X, dv_layer_compile as C
FX = '/srv/opentallas-scratch/claude/s81-calpipe/fixtures/L0'; DR = '/srv/opentallas-scratch/claude/toksim-s81b-fwoa/dieref'
die = C.Die(C.die_tree(None, DR))
t = time.time()
rec, field = X.compile_frame(die, sys.argv[1], FX, [sys.argv[2]], only={1, 2})
for ph in rec['phases'][1:3]:
    print('DBG2', sys.argv[1], sys.argv[2], 'iters x', os.environ.get('OT_XS_KSLOT_ITERS'), 'seeds', os.environ.get('OT_XS_KSLOT_SEEDS'),
          'phase', ph['phase'], 'rows', ph['rows'], 'faults', ph['faults'], 'ret', ph['ret_words'], 'time', round(time.time() - t), flush=True)
