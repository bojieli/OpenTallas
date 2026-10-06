#!/usr/bin/env python3
"""DSpark step on the Qwen ROM STREAM4 path: composition, break-even and gap (owner: measured terms only).

step = 36 x verify_layer + verify_head + draft + commit;  per-user = tau x clock / step.
draft = drafter layers (5 x D0, REAL_MEM record) + draft heads + ingest/Markov MEASURED (fac4b889e, 75,000).
AR = the STREAM4 8K token (compose_P8191_token.json).  Break-even verify layer: step = tau x AR token.
"""
import argparse, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import third_party_tau as T


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--verify-layer", action="append", default=[], help="NAME=cycles (measured verify layers)")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    R = ROOT / "results/rtl"
    rec = json.loads((R / "qwen_dspark_system_20261004/ctx8k/step_composed_ctx8k.json").read_text())
    im = json.loads((R / "qwen_dspark_system_20261004/ctx8k/ingest_markov_rtl/record.json").read_text())
    tok = json.loads((R / "qwen_rom_kv_fullbw_20261004/compose_P8191_token.json").read_text())
    HZ, tau = 1.2e9, T.tau_qwen3_8b()
    dt = rec["composed"]["draft_terms"]
    ingest_markov = 75000
    draft = dt["drafter_layers_rtl"] + dt["drafter_lm_head_S_slots_from_measured_heads"] + ingest_markov
    head = rec["components_cycles"]["verify_head_p4_step1"]; commit = rec["composed"]["commit_cycles"]
    ar = tok["stream4"]["token_cycles"]
    out = {"tau": tau, "tau_source": T.tau_src("qwen3_8b"), "ar_token_cycles_stream4": ar, "ar_tok_s": round(HZ / ar, 1),
           "draft_cycles": draft, "draft_terms": {"drafter_layers_rtl_realmem": dt["drafter_layers_rtl"],
           "draft_heads": dt["drafter_lm_head_S_slots_from_measured_heads"], "ingest_markov_measured_fac4b889e": ingest_markov},
           "verify_head": head, "commit": commit,
           "break_even_verify_layer": (tau * ar - draft - commit - head) / 36,
           "break_even_verify_layer_free_draft": (tau * ar - commit - head) / 36, "variants": {}}
    for s in a.verify_layer:
        n, c = s.split("="); c = int(c)
        step = 36 * c + head + draft + commit
        out["variants"][n] = {"verify_layer": c, "step": step, "tok_s": round(tau * HZ / step, 1),
                              "speedup_vs_ar": round(tau * ar / step, 3),
                              "gap_to_break_even": round(c - out["break_even_verify_layer"], 1)}
    out["unvalidated"] = ["drafter layers measured on REAL_MEM (STREAM4 would be faster)", "draft argmax+gather 3 x 736 priced inside the 75,000"]
    a.out.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
