#!/usr/bin/env python3
"""Small interface checks for S81 opt-in planning candidates, not sign-off."""
import argparse
import json
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import dsrom_s81_fulldie as F

ap = F.die_options(argparse.ArgumentParser())
F.apply_options(ap.parse_args(['--gen', 'r8', '--die', 'layer1', '--coll-split3-cr']))
assert F.COLL_SPLIT3_CR and F.COLL_SPLIT3
manifest = json.loads((F.ROOT / F.COLL_SPLIT3_COMP).read_text())
assert 'OT_S81PH_COLL_CR' in manifest['core_rtl_defines']
assert 'OT_S81PH_LANE_CR' in manifest['lane_rtl_defines']
F.apply_options(ap.parse_args(['--gen', 'r8', '--die', 'layer1']))
assert not F.COLL_SPLIT3_CR and not F.COLL_SPLIT3
assert F.COLL_SPLIT3_COMP.endswith('composition_split3.json')

F.Q_X1B = True
F.Q_LEF = 'physical/s81_die_views/q_elem_qs5f_x1b_stub/q_elem.lef.gz'
F.REAL_FILES.clear()
rq = F.real_lef(F.Q_LEF)
left = F._q_banks('0', 4.32, 100., rq, 'frame_0')
right = F._q_banks('1', 524.45, 100., rq, 'frame_0', mirror=True)
assert F.BANK_PORTS['bx0'] == ('S', ['x1'])
assert 'x1' not in F.BANK_PORTS['bs0'][1]
xc = F._q_port_xc(rq, 'x1')
assert abs(left[0].x + 30.24 - (4.32 + xc)) < F.GX
assert abs(right[0].x + 30.24 - (524.45 + rq['w'] - xc)) < F.GX
# The old centre-pin view must not silently satisfy an east-end face plan.
with patch.object(F, '_q_port_xc', return_value=255.):
    try:
        F._q_banks('2', 4.32, 100., rq, 'frame_0')
    except AssertionError:
        pass
    else:
        raise AssertionError('legacy x1 view accepted')
print('PASS S81 candidate bindings: explicit credit manifest, defaults restored, '
      'dedicated mirrored x1 banks, legacy x1 view rejected')
