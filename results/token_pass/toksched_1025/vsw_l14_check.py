import sys, json
from pathlib import Path
W = Path(sys.argv[1])
sys.path[:0] = [str(W/'tools/s81_dv'), str(W/'tools')]
import dv_layer_compile as dc
import layer_prog.lower_vs as lv
out = {}
for v in (0, 1):
    lv.VSW_LR_CYCLES = v
    s = dc.layer_schedule(W, 'L14', 'ar')
    out[v] = dict(span=s['span'], ops={o['op']: o['cycles'] for o in s['ops'] if 'swiglu' in o['op']})
print(json.dumps(out, indent=1))
