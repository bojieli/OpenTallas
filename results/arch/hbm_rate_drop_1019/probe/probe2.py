"""HBM-RATE-DROP probe2: LH-REPRICE3 with the Qwen per-SM accounting made consistent with the base (TP-4 records on a
TP-8 16-SM die: rows per SM unchanged = m/32; fmt3 transport 1.25; att_qwen per TP-4 record = half a TP-8 head)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hgi_sim import d4g_reprice_1019 as R
from hgi_sim import d4g_reprice3b_1019 as R3b
from hgi_sim import d4g_quadrant_1017 as Q
import r3fix
R3b.R3 = r3fix
if os.environ.get('FIX_ATTQ') == '1':
    R.TERMS['att_qwen'][0]['nsm'] = 32
_orig_any = R.SR._any
def _any(job):
    r3fix._QW['on'] = job[0] == 'qwen'
    return _orig_any(job)
R.SR._any = _any
R3b.main()
