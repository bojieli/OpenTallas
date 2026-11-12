"""qualify.py RECORDS.json: xs_bf.qualify_asbuilt_measurement + meas_for on every record, against
OT_S81_SELECTED_SOURCE_ROOT (pyrun.py BFASB_ROOT).  Prints one line per record and op."""
import json, os, sys
from layer_prog import xs_bf as B
recs = json.load(open(sys.argv[1]))
print('ROOT', os.environ['OT_S81_SELECTED_SOURCE_ROOT'])
for k, r in recs.items():
    master, frame = k.split('|')[0].split('_asb_')[0], 'asb_' + k.split('|')[0].split('_asb_')[1]
    land_e = int(k.split('|')[1][1:])
    try:
        print('QUALIFY', k, B.qualify_asbuilt_measurement(r, master, land_e, frame))
        for op in ('attn.wo_a', 'ffn.router', 'attn.cmp.wk'):
            rec, how = B.meas_for(recs, master, land_e, frame, op=op)
            print('  MEAS_FOR', op, how)
    except Exception as e:
        print('REFUSED', k, type(e).__name__, e)
