"""Private canary: preserve a failing GRT instead of detailed-routing it."""
from pathlib import Path
import re
import sys

s = Path('/work/run/logs/asap7/dp_hd_mesh_e/base/5_1_grt.log').read_text()
rows = re.findall(r'OT_HOLD_MM after repair: SS setup ws ([-.0-9]+) / FF hold ws ([-.0-9]+)', s)
if not rows:
    raise SystemExit('missing actual coupled timing; no private canary route')
t, h = map(float, rows[-1])
print('HEAD_R6_PRE_ROUTE_ACTUAL_TT_FF', t, h)
sys.exit(0 if t >= 0 and h >= 0 else 42)
