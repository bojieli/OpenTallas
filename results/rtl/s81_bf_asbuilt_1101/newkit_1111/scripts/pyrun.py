"""pyrun.py SCRIPT ARGS...: run a repo tool under python3 -I with the S81 tool paths and the new-kit selection env."""
import os, runpy, sys
from pathlib import Path
D = Path('/srv/opentallas-scratch2/claude/s81-bfasb-1111')
W, R = D / 'code', Path(os.environ.get('BFASB_ROOT', str(D / 'root')))
sys.path[:0] = [str(W / 'tools'), str(W / 'tools/s81_dv'), str(W / 'tools/s81_dv/layer_prog'), str(W / 'tools/s81')]
man = 'physical/die_plan/s81/bind/frame_asbuilt.json'
os.environ.update(OT_S81_SELECTED_SOURCE_ROOT=str(R), OT_S81_FRAME_SOURCE_ROOT=str(R), OT_S81_FRAME_ASBUILT_MANIFEST=man,
                  OT_S81_SELECTED_ASBUILT_MANIFEST=man, OT_XS_ASB_SCHEDULE_DIR=os.environ.get('BFASB_SCHED', str(D / 'sched')),
                  OT_S81_BF_COL_FORM='base')
script = sys.argv[1]
sys.argv = sys.argv[1:]
runpy.run_path(script, run_name='__main__')
