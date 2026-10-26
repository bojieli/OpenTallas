# TOK-QK/S8A: 2-slice s8_flat vehicle (tb_s8dbg, calibrate stimulus diag/gen_cal.py, seed 1) functional check.
# PASS = slice 1 (the probed slice of the 2-slice chain) emits exactly its 3 SSQ PSUM words (tags = lowering ssq[1].tags),
# each value bit-exact to the golden block partial reduce_chunked(x_b * x_b) (hdc_golden), no SU / VM fault, SU returns idle.
import sys, re, json
from pathlib import Path
T, log = Path(sys.argv[1]), Path(sys.argv[2])
sys.path.insert(0, str(T / "rtl/test/qwen_dv")); sys.argv = sys.argv[:1]
import dv_lower_bench as LB
import numpy as np
D, G, F = LB.D, LB.G, LB.F
lw = D.lower(ages=dict(ssq_psum_out=[0, 100, 200], root_cfg_lead=4, source="cal placeholder"))
x = np.random.default_rng(1).standard_normal(4096).astype(F)
tags = list(lw["ssq"][1]["tags"])
ps, stat = [], []
for line in log.read_text().splitlines():
    f = line.split()
    if len(f) == 3 and f[1] == "S1SD":
        w = int(f[2].replace("x", "0").replace("X", "0").replace("z", "0"), 16)
        if (w >> 44) & 7 == 1: ps.append((int(f[0]), (w >> 32) & 0xFFF, w & 0xFFFFFFFF))
    if len(f) > 2 and f[1] == "D" and f[2] == "stat":
        stat.append(line)
def gold(t):
    xb = x[D.BLOCK * t:D.BLOCK * (t + 1)]
    return int(np.array([G.reduce_chunked(G.mul(xb, xb))], dtype=F).view(np.uint32)[0])
errs = []
got = [(c, t, v) for c, t, v in ps if t in tags]
if [t for _, t, _ in got] != tags: errs.append(f"PSUM tags {[t for _, t, _ in got]} want {tags}")
for c, t, v in got:
    if v != gold(t): errs.append(f"tag {t} edge {c}: {v:#010x} want {gold(t):#010x}")
last = stat[-1] if stat else ""
m = dict(re.findall(r"(\w+) (\w+)", last.split(" stat ", 1)[-1])) if last else {}
if m.get("fault") != "0" or m.get("vm_fault") != "0" or m.get("nr") != "0": errs.append(f"fault status: {last}")
if m.get("idle") != "1": errs.append(f"SU not idle at end: {last}")
v = "PASS" if not errs else "FAIL"
print(json.dumps(dict(verdict=v, psums=[dict(edge=c, tag=t, value=hex(v_), golden=hex(gold(t))) for c, t, v_ in got],
                      final_stat=last, errors=errs)))
