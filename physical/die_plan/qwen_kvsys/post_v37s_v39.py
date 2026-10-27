#!/usr/bin/env python3
"""KV-P8-PLAN 10-23: post_v37s.py (KV-P6-SPINE L2045 E-corridor re-route) on the widened v3.9 lattice.  post_v37s keeps
L2045 at 36 stages (R8 phy_rx_flit alignment with L2048); on a wider pv type its pv_N_7 bottom-band crossing may need
one more station (span / reach), so the natural count is the smallest target >= 36 that the route meets.  The R8 table
is re-run on the final v3.9 plan (run_v39.sh), so a +1 here is padded at the L2048 landing; lat_delta_v39 lists it.
usage: post_v37s_v39.py die_plan_in.json > die_plan.json"""
import io
import os
import sys
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import post_v37s as S  # noqa: E402

base = S.ROUTES['L2045']
for target in range(base[3], base[3] + 4):
    S.ROUTES['L2045'] = base[:3] + (target,)
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            S.main()
    except AssertionError as e:
        sys.stderr.write(f'post_v37s_v39: L2045 target {target} not met ({e}); trying {target + 1}\n')
        continue
    sys.stdout.write(buf.getvalue())
    sys.stderr.write(f'post_v37s_v39: L2045 natural stages {target} (v3.7s: {base[3]})\n')
    break
else:
    raise SystemExit('post_v37s_v39: no L2045 target met')
