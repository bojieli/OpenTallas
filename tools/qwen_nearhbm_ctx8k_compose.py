#!/usr/bin/env python3
"""Compose the Qwen3-8B ROM token at long context WITH near-HBM attention from one measured layer (+ a 3-layer chain).

Owner rule (simulate the minimum component): near-HBM attention changes only the attention block of the layer, so
  * the near-HBM subsystem (hub_p + stack_p, R = 8, layer-start fence) runs on the REAL_MEM service and four actual
    HBM timing/WR_ACK models (tools/qwen_nearhbm_realmem_ctx_gate.py) from the layer start, with the token's V and K
    written at the layer program's own points and drain barriers (T_V, GAP_K1, GAP_K2 below), bit-exact against
    the GPU ISA golden's attention output (tools/qwen_nearhbm_ctx_vectors_gpu.py);
  * the rest of the layer is the measured REAL_MEM baseline layer (realmem-ctx8k traces, baseline_points.json):
    the program up to the K writes, and SUFFIX = O projection .. layer end (2,975 cycles at P255, P4095 and P8191:
    it carries no KV term);
  * near-HBM layer = (near-HBM bench: layer start .. last attention output) + HANDOFF + SUFFIX,
    HANDOFF = 2 cycles (the baseline's P.V-end -> O-start gap; the combined top's ATT64 VM write is not simulated);
  * token = 7 + E + (L0_isolated - 1) + 35 x (chained_steady - 1) + (head - 1) + 37 stage switches, E and head from
    the P255 full-token record (no KV term), exactly as results/rtl/qwen_rom_realmem_fulltoken_20261004 composes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

CLOCK_HZ = 1.2e9
HANDOFF = 2
MODEL = {"source": "results/uarch/qwen_rom_calibrated_calendar_20261003/inputs/nearhbm/near_hbm_attention_pricing.json r2.primary",
         "per_layer": 6281, "near_hbm_attention": 1700, "token_cycles": 229158, "tokens_s": 5237}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def tok(e, head, l0, steady):
    return 7 + e + (l0 - 1) + 35 * (steady - 1) + (head - 1) + 37


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--runs", type=Path, required=True, help="runs/<config>/P<P>/<spec>_die<d>.json")
    ap.add_argument("--baseline", type=Path, required=True, help="baseline_points.json")
    ap.add_argument("--p255", type=Path, required=True, help="P255 full-token summary.json")
    ap.add_argument("--suffix", type=int, default=2975)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    base = json.loads(a.baseline.read_text())
    s255 = json.loads(a.p255.read_text())
    E, HEAD = s255["per_layer_cycles"]["E"], s255["per_layer_cycles"]["head"]
    for P, v in base.items():
        if v["suffix_o_to_end"] != a.suffix:
            raise SystemExit(f"baseline {P}: suffix {v['suffix_o_to_end']} != {a.suffix}")
    rec = {"schema": "opentallas.qwen-rom-nearhbm-ctx8k-compose.v1", "claim_boundary":
           "Near-HBM attention subsystem RTL (Verilator) on the REAL_MEM service + 4 HBM timing models, bit-exact vs the GPU "
           "ISA golden; non-attention layer cycles from the measured REAL_MEM baseline trace; composed token. Not a combined-top "
           "run, not physical sign-off; clock assumed 1.2 GHz.",
           "constants": {"handoff": HANDOFF, "suffix_o_to_layer_end": a.suffix, "E": E, "head": HEAD, "clock_hz": CLOCK_HZ},
           "inputs": {"baseline_points_sha256": sha(a.baseline), "p255_summary_sha256": sha(a.p255)},
           "model": MODEL, "runs": {}, "configs": {}}
    for f in sorted(a.runs.glob("*/P*/*.json")):
        r = json.loads(f.read_text())
        key = str(f.relative_to(a.runs))
        m = r.get("measurement") or {}
        rec["runs"][key] = {"status": r["status"], "sha256": sha(f), "layers": [
            {k: x[k] for k in ("layer", "status", "mismatches", "start", "end", "waited_for_retire", "attention_cycles",
                               "fill_sectors", "write_sectors", "rel")} for x in m.get("layers", [])],
            "HBM_bytes_mismatched": m.get("HBM_bytes_mismatched"), "token_slice_codes_mismatched": m.get("token_slice_codes_mismatched")}
    for key, r in rec["runs"].items():
        cfg, P, name = key.split("/")
        c = rec["configs"].setdefault(cfg, {}).setdefault(P, {"exact": True, "isolated": {}, "chain": None})
        c["exact"] &= r["status"] == "pass"
        if r["status"] != "pass" or not r["layers"]:
            continue
        spec, die = name[:-5].rsplit("_", 1)
        if "+" not in spec:
            x = r["layers"][0]
            c["isolated"][die if spec == "L0" else f"{spec}_{die}"] = {"layer": x["rel"]["last_output"] + HANDOFF + a.suffix,
                                  "prefix_to_near_start": x["rel"]["near_start"], "near_attention": x["attention_cycles"],
                                  "k2_write_done": x["rel"]["k2_write_done"], "kv_ok": x["rel"]["kv_ok"]}
        else:
            L = r["layers"]
            per = [L[i + 1]["start"] - L[i]["start"] for i in range(len(L) - 1)] + [L[-1]["rel"]["last_output"] + HANDOFF + a.suffix]
            c["chain"] = {"die": die, "per_layer": per, "waited_for_retire": [x["waited_for_retire"] for x in L],
                          "near_attention": [x["attention_cycles"] for x in L], "prefix_to_near_start": [x["rel"]["near_start"] for x in L]}
    for cfg, ps in rec["configs"].items():
        for P, c in ps.items():
            iso = c["isolated"].get("die0")
            if not iso:
                continue
            l0 = iso["layer"]
            steady = sum(c["chain"]["per_layer"][1:]) / len(c["chain"]["per_layer"][1:]) if c["chain"] else l0
            steady_max = max(c["chain"]["per_layer"][1:]) if c["chain"] else l0
            t = tok(E, HEAD, l0, steady)
            b = base.get(P)
            bl = b["stage"]["cycles"] if b else None
            c["composed"] = {
                "layer_isolated": l0, "layer_chained_steady": round(steady, 1), "layer_chained_max": steady_max,
                "attention_share_of_layer": round((iso["near_attention"] + HANDOFF) / l0, 4),
                "layer_breakdown": {"layer_start_to_near_start": iso["prefix_to_near_start"],
                                    "near_attention": iso["near_attention"], "handoff": HANDOFF, "suffix": a.suffix},
                "token_cycles": round(t), "token_cycles_bound_max": tok(E, HEAD, l0, steady_max),
                "tok_s_1p2GHz": round(CLOCK_HZ / t, 1),
                "vs_model_tok_s": round(CLOCK_HZ / t / MODEL["tokens_s"], 4),
                "realmem_baseline_isolated_layer": bl,
                "realmem_baseline_token_isolated_lower_bound": tok(E, HEAD, bl, bl) if bl else None,
                "realmem_baseline_tok_s_isolated_lower_bound": round(CLOCK_HZ / tok(E, HEAD, bl, bl), 1) if bl else None,
                "speedup_vs_realmem_baseline_isolated": round(tok(E, HEAD, bl, bl) / t, 4) if bl else None}
    a.out.write_text(json.dumps(rec, indent=1) + "\n")
    for cfg, ps in rec["configs"].items():
        for P, c in ps.items():
            print(cfg, P, "exact" if c["exact"] else "NOT EXACT", json.dumps(c.get("composed")))


if __name__ == "__main__":
    main()
