# TOK-QK/S8 diagnostic: the exact dv_lower_bench.py --calibrate event file (no sim), + probe edges
import sys, json
from pathlib import Path
T = Path(sys.argv[1]); out = Path(sys.argv[2])
sys.path.insert(0, str(T / "rtl/test/qwen_dv")); sys.argv = sys.argv[:1]
import dv_lower_bench as LB
import numpy as np
D = LB.D
lw = D.lower(ages=dict(ssq_psum_out=[0, 100, 200], root_cfg_lead=4, source="cal placeholder"))
rng = np.random.default_rng(1); x = rng.standard_normal(4096).astype(LB.F)
ev = LB.Events(); t = LB.load_prog_and_x(ev, lw, x, LB.T0); tload = t
smap = lw["slice_map"]
for s in range(LB.N):
    ev.cmd(t + s, D.cmd_root(s, int(s == 0), 32, lw["vm"]["SSX"]["base"], fuse=int(s == 0), rx=lw["vm"]["RX"]["base"],
                             eps=lw["root"]["eps"] if s == 0 else 0, k=lw["root"]["k"] if s == 0 else 0))
t += LB.N + 40
probe = {}
for s in (LB.N - 1, 1):
    probe[s] = t; ev.cmd(t, D.cmd_su(0, s)); t += 600
ev.write(out / "cal.ev")
json.dump(dict(tload=tload, probe=probe, end=t + 100, cmd_arrival=smap["cmd_arrival"], tags={s: lw["ssq"][s]["tags"] for s in (1, 11)},
               cmds=sorted((e[0], hex(e[2])) for e in ev.ev if e[1] == 0)), open(out / "cal_meta.json", "w"), indent=1)
print("tload", tload, "probe", probe, "end", t + 100, "cmd_arrival", smap["cmd_arrival"])
