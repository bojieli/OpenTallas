#!/usr/bin/env python3
"""Exact gate of the near-HBM attention RTL (rtl/hdc/nearhbm/) against the golden, and its cycle accounting.

    python3 tools/qwen_nearhbm_attn_gate.py --bin DIR_OF_Vtb --hd 128 --r 6 --cases 8192:normal,... \\
        --vectors /tmp/nhb/v --out results/.../gate_r6.json [--bin-cross DIR --cross-hd 16]

Each case's vectors come from tools/qwen_nearhbm_attn_ref.py (which asserts partitioned == golden before writing);
the bench (rtl/test/nearhbm/tb_qwen_nearhbm_attn.cpp) compares all 1,024 outputs (8 heads x 128) bit for bit and
prints cycle marks.  The phases are reported against the pricing model's per-layer budget (1,700 cycles: q in 85,
K 700, V 700, drain 76, return + hub 139; /tmp/claude-review-20261003/nearhbm/near_hbm_attention_pricing.md).
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUDGET = dict(q_in=85, K=700, V=700, drain=76, return_hub=139, total=1700)


def phases(m):
    """cycles from the layer start (the start pulse) for each phase; marks are bench cycles after start"""
    k_end = m["k_rows_served_last"]
    v_end = m["v_rows_served_last"]
    return dict(
        q_in=m["q_ready"],                                  # q over the link into the stacks (45 wire + 32 beats)
        K_stream=k_end - m["k_rows_served_first"],          # first to last K row out of HBM (all stacks)
        K_to_V_gap=m["v_rows_served_first"] - k_end,        # max exchange + exp lead not hidden by the K stream
        V_stream=v_end - m["v_rows_served_first"],          # first to last V row out of HBM
        drain=m["pv_first_beat"] - v_end,                   # last V row -> P.V partial out of the last stack
        return_hub=m["out_last"] - m["pv_first_beat"],      # serialise + link + hub levels 8-9 + x 1/Z
        total=m["out_last"],
    )


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def run_case(binary, vdir, lat, bpc, maxc):
    p = subprocess.run([str(binary), str(vdir), str(lat), str(bpc), str(maxc)], capture_output=True, text=True)
    line = p.stdout.strip().splitlines()[-1] if p.stdout.strip() else "{}"
    rec = json.loads(line)
    rec["returncode"] = p.returncode
    if p.stderr.strip():
        rec["stderr"] = p.stderr.strip()[-400:]
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bin", required=True, type=Path, help="directory holding the Vtb of the main bench")
    ap.add_argument("--hd", type=int, default=128)
    ap.add_argument("--r", type=int, required=True)
    ap.add_argument("--fp", default="dpi", choices=("dpi", "real"))
    ap.add_argument("--vectors", type=Path, required=True, help="directory of <ctx>_<kind> vector sets")
    ap.add_argument("--hbm-latency", type=int, default=16)
    ap.add_argument("--bpc", type=int, default=750)
    ap.add_argument("--max-cycles", type=int, default=400000)
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    cases = sorted(d for d in a.vectors.iterdir() if (d / "meta.json").is_file())
    with ThreadPoolExecutor(a.jobs) as ex:
        recs = list(ex.map(lambda d: run_case(a.bin / "Vtb", d, a.hbm_latency, a.bpc, a.max_cycles), cases))
    rows = []
    for d, r in zip(cases, recs):
        meta = json.loads((d / "meta.json").read_text())
        r.update(case=d.name, kind=meta["kind"], seed=meta["seed"], golden_out_sha256=meta["out_sha256"])
        if r.get("marks"):
            r["phases"] = phases(r["marks"])
        rows.append(r)
    ok = all(r.get("exact") for r in rows) and len(rows) > 0
    full = [r for r in rows if r.get("ctx") == 8192 and r.get("exact")]
    rec = dict(schema="qwen-nearhbm-attn-rtl-gate.v1", hd=a.hd, row_engines_per_stack=a.r, fp_units=a.fp,
               hbm_model=dict(latency_cycles=a.hbm_latency, bytes_per_cycle_per_stack=a.bpc,
                              note="token bucket per stack, one 128-B row per engine per cycle, in-order per engine"),
               cases=len(rows), exact_cases=sum(bool(r.get("exact")) for r in rows),
               verdict="PASS" if ok else "FAIL", budget=BUDGET,
               full_context_phases=full[0]["phases"] if full else None,
               sources_sha256={p: sha(ROOT / p) for p in (
                   "rtl/hdc/nearhbm/ot_qwen_nearhbm_attn_stack.sv", "rtl/hdc/nearhbm/ot_qwen_nearhbm_attn_hub.sv",
                   "rtl/hdc/nearhbm/ot_qwen_nearhbm_prod.sv", "rtl/test/nearhbm/ot_qwen_nearhbm_attn_die_tb.sv",
                   "rtl/test/nearhbm/tb_qwen_nearhbm_attn.cpp", "rtl/test/nearhbm/sim_nhb_fp_lat_dpi.sv",
                   "rtl/test/nearhbm/sim_nhb_fp_lat_dpi.cpp", "tools/qwen_nearhbm_attn_ref.py", "tools/hdc_golden.py")},
               rows=rows)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1))
    print(json.dumps({k: rec[k] for k in ("hd", "row_engines_per_stack", "fp_units", "cases", "exact_cases", "verdict",
                                          "full_context_phases")}))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
