#!/usr/bin/env python3
"""Collect the near-HBM stream bench logs into rtl-bench-r1.json (canonical JSON).

Usage: qwen_hbm_sustained_bw_collect.py [r1|r2]  (r1 reads logs/, r2 logs-r2/)
Inputs: results/uarch/qwen_hbm_sustained_bw_20261003/logs*/*.log written by
tests/rtl/run_hbm_stream_bw.sh (runs named in logs/list.txt and logs/extra.txt) and
tests/rtl/run_hbm_stream_existing_models.sh (existing_*.log).
"""
import hashlib, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "results/uarch/qwen_hbm_sustained_bw_20261003"
SRC = ["rtl/model_ready_hbm_r14/ot_hbm_r14_stream_pc.sv", "rtl/model_ready_hbm_r14/ot_hbm_r14_stream_stack.sv",
       "rtl/test/model_ready_hbm_r14/tb_hbm_stream_bw.sv", "rtl/test/model_ready_hbm_r14/tb_hbm_stream_existing_models.sv",
       "rtl/hdc/kv/ot_hdc_hbm_model.sv", "rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv",
       "tests/rtl/run_hbm_stream_bw.sh", "tests/rtl/run_hbm_stream_existing_models.sh"]
NEED_PS = 1048576 / 0.9e12 * 1e12


def kv(line):
    return {k: (int(v) if re.fullmatch(r"-?\d+", v) else v) for k, v in re.findall(r"(\w+)=(\S+)", line)}


def main():
    rev = sys.argv[1] if len(sys.argv) > 1 else "r1"
    logs = D / ("logs" if rev == "r1" else f"logs-{rev}")
    runs = {}
    for f in sorted(logs.glob("*.log")):
        txt = f.read_text()
        summ = {}
        for line in txt.splitlines():
            if line.startswith("SUMMARY") or line.startswith("RESULT"):
                summ.update(kv(line))
        layers = [kv(l) for l in txt.splitlines() if l.startswith("LAYER")]
        summ["log_sha256"] = hashlib.sha256(f.read_bytes()).hexdigest()
        if layers and "data_ps" in layers[0]:
            dp = [x["data_ps"] for x in layers]
            summ["worst_data_phase_Bps"] = int(1048576 / (max(dp) * 1e-12))
        runs[f.stem] = summ
    def grp(prefix):
        r = {k: v for k, v in runs.items() if k.startswith(prefix) and "_cred" not in k}
        w = max(v["worst_stream_ps"] for v in r.values())
        return {"runs": sorted(r), "layers": sum(v.get("layers", 0) for v in r.values()),
                "worst_layer_stream_ns": w / 1000, "worst_layer_Bps": int(1048576 / (w * 1e-12)),
                "mean_Bps_min": min(v["mean_Bps"] for v in r.values()),
                "layers_over_1165ns": sum(v["layers_over_need"] for v in r.values()),
                "first_data_ns_max": max(v["first_data_ps_max"] for v in r.values()) / 1000,
                "timing_violations": sum(v["violations"] for v in r.values()),
                "data_mismatches": sum(v["sectors_bad"] for v in r.values()),
                "max_landing_sectors": max(v["max_landing"] for v in r.values()),
                "meets_0p9TBps_every_layer": w <= NEED_PS}
    out = {
        "schema": "opentallas.qwen-hbm-stream-bench.v1",
        "simulator": "Verilator 5.050 (--binary --timing)",
        "sources_sha256": {s: hashlib.sha256((ROOT / s).read_bytes()).hexdigest() for s in SRC},
        "need_layer_ns": NEED_PS / 1000,
        "groups": {
            "REFpb_aware_hint320 (primary)": grp("pb_h320_p") | {"note": "8 refresh phases x 36 layers"},
            "REFpb_aware_hint200": grp("pb_h200_"), "REFpb_aware_hint100": grp("pb_h100_"),
            "REFpb_aware_hint0": grp("pb_h0_"), "REFab_staggered_hint320": grp("ab_h320_"),
            "REFpb_aware_back_to_back": grp("pb_b2b_"),
        },
        "credit_sensitivity": {k: {x: runs[k][x] for x in ("worst_stream_ps", "worst_Bps", "max_landing", "verdict")}
                               for k in ("pb_h320_p0_cred24", "pb_h320_p0", "pb_h320_p0_cred64")},
        "negative_controls": {k: {x: runs[k][x] for x in ("violations", "sectors_bad", "verdict")}
                              for k in ("mut1", "mut2", "mut3")},
        "existing_models": {k: runs[k] for k in runs if k.startswith("existing_")},
        "runs": runs,
    }
    (D / f"rtl-bench-{rev}.json").write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(json.dumps(out["groups"], indent=1))


if __name__ == "__main__":
    main()
