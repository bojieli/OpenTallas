"""DENSE2 10-20: xs_calendar cap check (CAP cfg_d decode + GU_MERGE consumer layout vs two-matrix reference) on the
column-reduced inventory (capacity_cols env).  usage: cap_cols.py LAYERCLASS FIXDIR OUT.json"""
import json, sys
from pathlib import Path
D = Path(__file__).resolve().parent
sys.path.insert(0, str(D))
import capacity_cols as CC   # noqa: E402  (patches xs_capacity._die, prints the inventory)
import xs_calendar as XCAL   # noqa: E402
import xs_place as XP        # noqa: E402
CC.cols('dieref')            # sets xs_topo from the reduced die
cls, fixd, out = sys.argv[1:4]
fx = XP.Fix(fixd)
ops = XP.XS_OPS[cls]
rec, amap, slotc = XCAL.cap_emit(XP, fx, ops)
XP.GU_MERGE = False
_r0, ref, _s0 = XCAL.cap_emit(XP, fx, ops)
XP.GU_MERGE = True
diff = sorted(k for k in set(ref) | set(amap) if ref.get(k) != amap.get(k))
gsl = [c for c in slotc if c['op'] in ('ffn.experts_gu', 'ffn.shared_gu')]
r = dict(layer=cls, gu_prop=XP.GU_PROP, topo=XP.TP.describe()['frames_per_slice'], faults=rec['faults'], rows=len(amap),
         differing=len(diff), gu_slot_collisions=len(gsl), all_slot_collisions=len(slotc), vp_rows_used=rec['vp_rows_used'],
         reference_vp_rows_used=_r0['vp_rows_used'])
r['PASS'] = rec['faults'] == 0 and not diff and not gsl and rec['vp_rows_used'] == _r0['vp_rows_used']
Path(out).write_text(json.dumps(dict(r, phases=rec['phases']), indent=1) + '\n')
print('DENSE2_CAPCHECK', json.dumps(r))
