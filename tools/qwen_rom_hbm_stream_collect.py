#!/usr/bin/env python3
"""Collect the HBM_STREAM REAL_MEM runs against the frozen REAL_MEM and KV_IDEAL records.

Reads run records written by tools/qwen_rom_rt_token_stream_w12.py and the frozen REAL_MEM /
KV_IDEAL records (results/rtl/qwen_rom_real_memory_20261003/frozen_v2/runs/{real2,ideal2}_p<P>.json),
and writes a summary: per position and layer the cycles of ideal / REAL_MEM / HBM_STREAM, the
stream's MEMSTAT counters (max over dies), and the token-level estimate (36 decoder layers at the
measured L0-L2 mean, plus the embedding stage; the LM head is not in these runs and is excluded).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FROZEN = ROOT / "results/rtl/qwen_rom_real_memory_20261003/frozen_v2/runs"
LAYERS = 36


def stages(rec):
    out = {}
    for name, st in rec["stages"].items():
        mem = st.get("memory", {})
        mx = {}
        for d in mem.values():
            for k, v in d.items():
                mx[k] = max(mx.get(k, 0), v)
        out[name] = {"cycles": st["cycles"], "memory_max_over_dies": mx}
    return out


def exact(rec):
    return (rec["status"] == "pass" and rec["source_stable"]
            and all(c["mismatches"] == 0 for c in rec["layer_x_checks"].values())
            and all(c["k_mismatches"] == 0 and c["v_mismatches"] == 0 for c in rec["token_kv_writeback_checks"].values()))


def token(st):
    lay = [st[f"L{i}"]["cycles"] for i in range(3)]
    return st["E"]["cycles"] + LAYERS * sum(lay) / 3.0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run", action="append", required=True, help="name=path/to/run.json (name ends in _p<P>)")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    res = {"schema": "opentallas.qwen-rom-hbm-stream-realmem-summary.v1", "token_model":
           f"E + {LAYERS} x mean(L0,L1,L2) cycles at 1.2 GHz; LM head excluded", "runs": {}}
    for item in a.run:
        name, path = item.split("=", 1)
        rec = json.loads(Path(path).read_text())
        P = rec["position"]
        real = json.loads((FROZEN / f"real2_p{P}.json").read_text())
        ideal = json.loads((FROZEN / f"ideal2_p{P}.json").read_text())
        s, r, i = stages(rec), stages(real), stages(ideal)
        layers = {}
        for L in ("L0", "L1", "L2"):
            c_s, c_r, c_i = s[L]["cycles"], r[L]["cycles"], i[L]["cycles"]
            layers[L] = {"ideal": c_i, "real_mem": c_r, "hbm_stream": c_s,
                         "real_minus_ideal": c_r - c_i, "stream_minus_ideal": c_s - c_i,
                         "penalty_removed_fraction": round((c_r - c_s) / (c_r - c_i), 4) if c_r != c_i else None,
                         "stream_memstat": s[L]["memory_max_over_dies"], "real_memstat": r[L]["memory_max_over_dies"]}
        t_s, t_r, t_i = token(s), token(r), token(i)
        res["runs"][name] = {
            "position": P, "token": rec["token"], "bit_exact": exact(rec), "status": rec["status"],
            "source_stable": rec["source_stable"], "binary_sha256": rec["binary_sha256"],
            "design_point": rec["design_point"], "memory_services": rec["memory_services"],
            "stage_E": {"real_mem": r["E"]["cycles"], "hbm_stream": s["E"]["cycles"], "ideal": i["E"]["cycles"]},
            "layers": layers,
            "three_layer_total": {"ideal": ideal["total_cycles"], "real_mem": real["total_cycles"], "hbm_stream": rec["total_cycles"]},
            "token_estimate_cycles": {"ideal": round(t_i), "real_mem": round(t_r), "hbm_stream": round(t_s)},
            "token_rate_gain_vs_real_mem_pct": round((t_r / t_s - 1) * 100, 3),
            "token_rate_gap_to_ideal_pct": round((t_s / t_i - 1) * 100, 3),
            "frozen_real_record_sha_binary": real["binary_sha256"],
        }
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(res, indent=2, sort_keys=True) + "\n")
    for n, v in res["runs"].items():
        print(n, "exact" if v["bit_exact"] else "NOT EXACT",
              {L: (x["ideal"], x["real_mem"], x["hbm_stream"]) for L, x in v["layers"].items()},
              "token gain %", v["token_rate_gain_vs_real_mem_pct"], "gap to ideal %", v["token_rate_gap_to_ideal_pct"])


if __name__ == "__main__":
    main()
