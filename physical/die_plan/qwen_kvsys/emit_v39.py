#!/usr/bin/env python3
"""KV-P8-PLAN 10-23: stage 2 of plan v3.9 = emit_v34 (ft stations <= 750 um apart) on the v3.9 view (import plan_v39
patches plan_v31: ctlv4 leaf moves + widened die lattice), with the face windows SPREAD over the whole shared face.

v3.1..v3.8 packed every shared face's windows from one end (MARGIN + running offset), so the N/S stack windows of the
hg / hgi columns sat in the left ~600 um of a 1279-um face and the column pass-through traffic crowded one channel
(GEOM-REVIEW8: 'one-sided traffic').  Here the same ordered windows (same order key, same lengths, same PG-band /
odd-track rule) are laid out with an equal extra gap between them: pass 1 packs as before to measure the used length,
pass 2 places them with e = OT_V39_SPREAD (0.9) x slack / (n + 1) between windows (rounded down to the 0.864 pitch).
The layout is a function of the face's ordered port list and its length only, so replicas of a type keep one pin table.
OT_V39_SPREAD=0 reproduces the packed v3.4 windows."""
import inspect
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import plan_v39  # noqa: E402,F401
import emit_v31  # noqa: E402

emit_v31.ST_MAX = 750.0
SPREAD = float(os.environ.get('OT_V39_SPREAD', '0.9'))

_src = inspect.getsource(emit_v31.main)
_old = """        cur = 0.0
        for ix in sorted(ixs, key=key):
            pr = ports[ix]
            ln = max(GAP, math.ceil((pr['width'] + 1) / PINS_PER_UM / 0.864 - 1e-9) * 0.864)
            t0 = round(tlo + MARGIN + cur, 3)
            t1 = odd_window(t0, t0 + ln, pr['width'] + 1, tuple(LAYERS['EW' if f_ref in 'EW' else 'NS']))
            ln = t1 - t0
            if t1 + MARGIN > thi + 1e-6:
                over.append(f'{x}|{y}')
            cur += ln + GAP
"""
_new = """        order = sorted(ixs, key=key)
        cur = 0.0
        for ix in order:                                     # pass 1: packed length
            pr = ports[ix]
            ln = max(GAP, math.ceil((pr['width'] + 1) / PINS_PER_UM / 0.864 - 1e-9) * 0.864)
            t0 = round(tlo + MARGIN + cur, 3)
            t1 = odd_window(t0, t0 + ln, pr['width'] + 1, tuple(LAYERS['EW' if f_ref in 'EW' else 'NS']))
            cur += t1 - t0 + GAP
        slack = (thi - tlo - 2 * MARGIN) - (cur - GAP)
        ext_gap = max(0.0, math.floor(SPREAD_ * slack / (len(order) + 1) / 0.864) * 0.864)
        cur = ext_gap
        for ix in order:                                     # pass 2: spread
            pr = ports[ix]
            ln = max(GAP, math.ceil((pr['width'] + 1) / PINS_PER_UM / 0.864 - 1e-9) * 0.864)
            t0 = round(tlo + MARGIN + cur, 3)
            t1 = odd_window(t0, t0 + ln, pr['width'] + 1, tuple(LAYERS['EW' if f_ref in 'EW' else 'NS']))
            ln = t1 - t0
            if t1 + MARGIN > thi + 1e-6:
                over.append(f'{x}|{y}')
            cur += ln + GAP + ext_gap
"""
assert _src.count(_old) == 1
emit_v31.SPREAD_ = SPREAD
exec(compile(_src.replace(_old, _new), emit_v31.__file__, 'exec'), emit_v31.__dict__)

if __name__ == '__main__':
    emit_v31.main()
