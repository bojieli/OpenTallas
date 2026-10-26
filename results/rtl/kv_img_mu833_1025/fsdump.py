# run a kv_boot_v36 compile and dump the MU frame-search inputs (rows, F, phase profile) for recheck.py; no behaviour change
import os, pickle, runpy, sys
sys.path.insert(0, os.getcwd())
from tools.qwen_static_schedule import mu_calendar as MC
OUT = os.environ["FS_OUT"]; _fs = MC.kv_frame_search
def fs(rows, F=MC.KV_FRAME_F, seed=1, tries=400, spread=3000, filler_tokens=None):
    pickle.dump(dict(rows=rows, F=F, filler_tokens=filler_tokens, ATT_END=MC.KV_ATT_END, PHASE=dict(MC.KV_PHASE)), open(OUT, "wb"))
    return _fs(rows, F, seed, tries, spread, filler_tokens)
MC.kv_frame_search = fs
sys.argv = sys.argv[1:]
runpy.run_path(sys.argv[0], run_name="__main__")
