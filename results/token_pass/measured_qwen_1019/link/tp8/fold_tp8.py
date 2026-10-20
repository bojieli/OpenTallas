#!/usr/bin/env python3
"""TOKSIM-QW/LINK: fold per-case TP8 bench records (back/tp8/<case>/record.json) -> tp8 summary (same E/span law as tools/xdie_qtp8/record.py)."""
import json, sys
from pathlib import Path
B = Path(sys.argv[1]); LAYERS = 36
def terms(c):
    p = c["program"]
    for m in p:
        m["last_in"] = m["first_slot"] + (8 if m["mode"] else 1) * (m["words"] - 1)
    return dict(span=c["compiled_span_cycles"], E_meas_first=p[0]["first_out"] - p[0]["last_in"],
                latency_first_in_to_first_out=p[0]["first_out"] - p[0]["first_slot"])
runs = {}
for d in sorted(B.glob("*/record.json")):
    r = json.loads(d.read_text())
    cs = {c["name"]: dict(passed=c["passed"], words_out=(c.get("result") or {}).get("words_out"),
                          mismatches=(c.get("result") or {}).get("mismatches"), **terms(c)) for c in r["cases"]}
    ok = (not any(c["passed"] for c in r["cases"])) if r["expect_fail"] else all(c["passed"] for c in r["cases"])
    runs[d.parent.name] = dict(expect_fail=r["expect_fail"], ok=ok, lats=r["lats"], latu=r["latu"], mutant=r["mutant"],
                               verilator=r.get("verilator_version"), real_lanes_source=r.get("real_lanes_source"),
                               source_sha256=r.get("source_sha256"), cases=cs)
c = runs["g3_cal"]["cases"]; ar, am = c["qwen_ar_256w"], c["qwen_argmax_1w"]
mu = runs["g3_mu"]["cases"]
meas = dict(AR256=dict(span=ar["span"], E_meas=ar["E_meas_first"], first_in_to_first_out=ar["latency_first_in_to_first_out"]),
            AR256x2_back_to_back_span=c["qwen_layer_2x256w"]["span"],
            argmax_gather_1w=dict(span=am["span"], E_meas=am["E_meas_first"]),
            layer_2xAR_plus_argmax_span=c["qwen_layer_2x256w_argmax"]["span"],
            token_tp_allreduce_cycles_E=LAYERS * 2 * ar["E_meas_first"],
            token_E_exposed_cycles_incl_argmax=LAYERS * 2 * ar["E_meas_first"] + am["E_meas_first"],
            token_span_cycles=LAYERS * 2 * ar["span"] + am["span"],
            multi_user_4=dict(span=mu["mu_window"]["span"], E_meas=mu["mu_window"]["E_meas_first"], words_out=mu["mu_window"]["words_out"],
                              user0_alone_span=mu["mu_window_ref_user0"]["span"], user0_alone_E=mu["mu_window_ref_user0"]["E_meas_first"]),
            calendar=dict(LS=runs["g3_cal"]["lats"], LU=runs["g3_cal"]["latu"]))
print(json.dumps(dict(measured=meas, verdicts={k: ("OK" if v["ok"] else "UNEXPECTED") for k, v in runs.items()}, runs=runs), indent=1))
