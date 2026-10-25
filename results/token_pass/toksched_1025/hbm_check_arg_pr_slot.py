#!/usr/bin/env python3
"""TOK-SCHED 10-25 (a): calendar check of argmax_rows.py --arg-pr-source (Codex 2999de1eaa) against the base compile (same config).
Absolute per-edge field schedule of all P positions: every field on every edge is identical except the ARG-source
capture (capture_arg), the SU delivery sink (sink_slot bit NPT / its select nibble) and del_obase, which move exactly
+1 edge; the compiled rows also pass the compiler's own independent unroll (P-loop vs absolute schedule).
    python3 results/token_pass/toksched_1025/hbm_check_arg_pr_slot.py [--P 8 --vm-rt 81 --rows 256 --start-reg --npt 3]"""
import argparse, importlib.util, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
ap = argparse.ArgumentParser()
ap.add_argument("--P", type=int, default=8); ap.add_argument("--vm-rt", type=int, default=81)
ap.add_argument("--rows", type=int, default=256); ap.add_argument("--start-reg", action="store_true", default=True)
ap.add_argument("--npt", type=int, default=3)
ap.add_argument("--pr", type=int, default=1, help="mutant control: --pr 0 (no shift) must FAIL")
a = ap.parse_args()

def load(arg_pr):
    spec = importlib.util.spec_from_file_location(f"ar{arg_pr}", ROOT / "tools/hbm_coll_static/argmax_rows.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    m.set_rows(a.rows); m.set_npt(a.npt); m.START_O = -1 if a.start_reg else 0; m.set_arg_pr_source(arg_pr); m.set_vm_rt(a.vm_rt)
    words, meta, info = m.compile_program(0, a.P)          # runs the compiler's own unroll check
    halt = info["halt"]
    sched = [m.fields_at(c, range(a.P), 0) for c in range(halt + 4)]
    return m, info, sched

m0, i0, s0 = load(0)
m1, i1, s1 = load(a.pr)
NPT = a.npt
su_bit, su_sel = 1 << NPT, 0xf << (4 * NPT)
def split(d):
    d = dict(d); moved = {}
    for k in ("capture_arg", "del_obase"):
        if k in d: moved[k] = d.pop(k)
    if d.get("sink_slot", 0) & su_bit and (d.get("sink_select", 0) & su_sel) == (NPT + 7) << (4 * NPT):
        moved["su_sink"] = 1
        d["sink_slot"] &= ~su_bit; d["sink_select"] &= ~su_sel
        if not d["sink_slot"]: d.pop("sink_slot")
        if not d["sink_select"]: d.pop("sink_select")
    return d, moved
errs, moved_n = [], 0
for c in range(len(s0)):
    r0, m_0 = split(s0[c])
    r1, m_1 = split(s1[c])
    if r0 != r1: errs.append(("rest", c))
    prev = split(s0[c - 1])[1] if c >= 1 else {}
    if m_1 != prev: errs.append(("moved", c, m_1, prev))
    moved_n += len(m_1)
res = dict(config=vars(a), base=i0, arg_pr=i1, moved_events=moved_n, errors=errs[:10],
           verdict="PASS" if not errs and moved_n == 3 * a.P else "FAIL")
print(json.dumps(res, indent=1))
sys.exit(0 if res["verdict"] == "PASS" else 1)
