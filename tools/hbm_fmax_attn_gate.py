#!/usr/bin/env python3
"""Exactness / cycle gate of the streaming attention engine ot_hdc_v41x_attn_s (rtl/hdc/v41x/ot_hdc_v41x_attn_s.sv)
on the as-built campaign benches (tools/rtl_hdc_v41x_attn_campaign.py run_engine: bit-exact against
tools/hdc_golden_v41.py, per-job issue windows).

  equiv  FPL = FML = 3, NBANKP = 0: _s against the as-built ot_hdc_v41x_attn, per job every issue/retire cycle
         (qk_first/last, pv_first/last, last_score/p/pv) equal, both bit-exact -- for each controller config
  lat    _s at --lat FPL,FML over --banks (NBANKP; 0 = as built): bit-exact + q.k / p.v bubbles per job

    python3 tools/hbm_fmax_attn_gate.py equiv --work W --out R.json
    python3 tools/hbm_fmax_attn_gate.py lat --lat 7,6 --banks 0,5,6,7 --work W --out R.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import rtl_hdc_v41x_attn_campaign as C  # noqa: E402

V, T = ROOT / "rtl/hdc/v41x", ROOT / "rtl/test"
FPLIB = [ROOT / "rtl/hdc/ot_hdc_fp32_add_lat.sv", ROOT / "rtl/hdc/ot_hdc_prefix.sv"]
AS_BUILT = dict(RTL_TILE=C.RTL_TILE, RTL_ENG=C.RTL_ENG, TB_ENG=C.TB_ENG, lib=C.lib)
JOBF = ("T", "qk_first", "qk_last", "qk_beats", "pv_first", "pv_last", "pv_beats", "last_score", "last_p", "last_pv",
        "qk_beat_bubbles", "pv_beat_bubbles")
# controller configs: the baseline-cited engine (ILV 0, PWORDS 1) and the physical (verify) controller
CONFIGS = {"ilv0_pw1": {"PWORDS": 1},
           "ilv0_pw2": {"PWORDS": 2},
           "ilv1_repl2_ns2_pw2": {"PWORDS": 2, "ILV": 1, "REPL": 2, "NSTAGE": 2}}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def use(streaming: bool):
    if streaming:
        C.RTL_TILE, C.RTL_ENG, C.TB_ENG = V / "ot_hdc_v41x_attn_tile_lat.sv", V / "ot_hdc_v41x_attn_s.sv", \
            T / "tb_hdc_v41x_attn_s.sv"
        base = [V / "ot_hdc_v41x_attn_tile.sv", V / "ot_hdc_v41x_attn.sv", *C.LIB, *FPLIB]
        C.lib = lambda f=3: list(base)
    else:
        for k, v in AS_BUILT.items():
            setattr(C, k, v)


def jobsets():
    rng = np.random.default_rng(9)
    small = [C.random_job(rng, 4, 64, t, min(t, 40)) for t in (72, 1, 33)]
    rng = np.random.default_rng(5)
    dpt8 = [C.random_job(rng, 16, 64, t, min(t, 128)) for t in (256, 97, 128)]
    return [("small", dict(H=4, D=64, TD=16, NL=1, TROWS=72), small),
            ("dpt8", dict(H=16, D=64, TD=32, NL=4, TROWS=256), dpt8)]


def run(work, name, cfg, jobs, extra):
    r = C.run_engine(work, name, cfg, jobs, extra=extra)
    return dict(name=name, config=cfg, extra=extra, bit_exact=r["bit_exact"], latency=r["latency"],
                per_job=[{k: j[k] for k in JOBF} for j in r["per_job"]])


def gate_equiv(a):
    work = Path(a.work)
    rows, ok = [], True
    for jname, cfg, jobs in jobsets():
        for cname, ex in CONFIGS.items():
            if ex.get("PWORDS", 1) == 2 and (cfg["H"] % 2):
                continue
            ex = dict(ex)
            use(False)
            ref = run(work, f"ref_{jname}_{cname}", cfg, jobs, ex)
            use(True)
            new = run(work, f"s3_{jname}_{cname}", cfg, jobs, dict(ex, FPL=3, FML=3))
            same = ref["per_job"] == new["per_job"]
            row = dict(case=f"{jname}/{cname}", as_built_bit_exact=ref["bit_exact"], s_bit_exact=new["bit_exact"],
                       cycle_identical=same, per_job=new["per_job"], as_built_per_job=ref["per_job"])
            ok &= ref["bit_exact"] and new["bit_exact"] and same
            print(json.dumps({k: row[k] for k in ("case", "as_built_bit_exact", "s_bit_exact", "cycle_identical")}),
                  flush=True)
            rows.append(row)
    return dict(gate="equiv", rows=rows, status="pass" if ok else "fail")


def gate_lat(a):
    work = Path(a.work)
    fpl, fml = map(int, a.lat.split(","))
    use(True)
    rows, ok = [], True
    for jname, cfg, jobs in jobsets():
        if a.only and jname not in a.only.split(","):
            continue
        for cname, ex in CONFIGS.items():
            for nb in a.banks:
                e = dict(ex, FPL=fpl, FML=fml, NBANKP=nb)
                r = run(work, f"s{fpl}{fml}_{jname}_{cname}_b{nb}", cfg, jobs, e)
                ok &= r["bit_exact"]
                print(json.dumps(dict(case=f"{jname}/{cname}/b{nb}", bit_exact=r["bit_exact"],
                                      jobs=[{k: j[k] for k in ("T", "qk_beat_bubbles", "pv_beat_bubbles", "last_pv")}
                                            for j in r["per_job"]])), flush=True)
                rows.append(dict(case=f"{jname}/{cname}/b{nb}", **r))
    return dict(gate="lat", latencies=dict(FPL=fpl, FML=fml), rows=rows, status="pass" if ok else "fail")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("gate", choices=("equiv", "lat"))
    ap.add_argument("--lat", default="7,6")
    ap.add_argument("--banks", type=lambda s: [int(x) for x in s.split(",")], default=[0])
    ap.add_argument("--only", default="")
    ap.add_argument("--work", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    Path(a.work).mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    rec = gate_equiv(a) if a.gate == "equiv" else gate_lat(a)
    rec.update(tool="tools/hbm_fmax_attn_gate.py " + " ".join(sys.argv[1:]), wall_s=round(time.time() - t0, 1),
               sources={str(p.relative_to(ROOT)): sha(p) for p in
                        [V / "ot_hdc_v41x_attn_s.sv", V / "ot_hdc_v41x_attn_tile_lat.sv", V / "ot_hdc_v41x_attn.sv",
                         V / "ot_hdc_v41x_attn_tile.sv", V / "ot_hdc_v41x_attn_staging.sv",
                         T / "tb_hdc_v41x_attn_s.sv", T / "tb_hdc_v41x_attn.sv", *C.LIB, *FPLIB,
                         ROOT / "tools/rtl_hdc_v41x_attn_campaign.py", ROOT / "tools/hdc_golden_v41.py",
                         Path(__file__).resolve()]})
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(rec, indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o))
                           + "\n")
    print("status", rec["status"])


if __name__ == "__main__":
    main()
