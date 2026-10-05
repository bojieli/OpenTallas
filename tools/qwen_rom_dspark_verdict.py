#!/usr/bin/env python3
"""Qwen ROM 8K operating-mode verdict on the STREAM4 path: AR_MODE or DSPARK_PAYS.

Inputs (all records in the repository):
  * AR token on STREAM4: results/rtl/qwen_rom_kv_fullbw_20261004/compose_P8191_token.json (measured composition);
  * verify layers on STREAM4, measured exact at P8187 (np = 2, 3, 4; baseline and MERGE_SU programs): --verify NAME:NP:CYCLES:RESULT
  * draft terms: the DSpark ctx8k record (drafter layers 5 x D0 at S = 3, draft heads) + the measured ingest/Markov
    (fac4b889e, 75,000 at S = 3);
  * tau: third-party published (results/speculative/third_party_acceptance_20261004/acceptance.json), taken per
    draft length; lengths 1 and 2 by the same published derivation (per benchmark constant conditional acceptance
    r from the gamma-7 Table 1 values, tau_k = 1 + sum_{i<=k} r^i, equal weight; it reproduces the published
    3 and 4 values);
  * the single-pass area estimate: dspark_breakeven.json.
step(np) = 36 x verify(np) + verify head + draft(S = np - 1) + commit; per-user = tau(S) x clock / step.
DSpark pays iff some np gives tau(S) x AR token > step.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import third_party_tau as T  # noqa: E402

HZ = 1.2e9


def tau_by_draft():
    acc = json.loads((ROOT / "results/speculative/third_party_acceptance_20261004/acceptance.json").read_text())
    q = acc["models"]["qwen3_8b"]["by_draft_tokens"]
    pb = q["3"]["per_benchmark"]

    def r_of(t3):
        lo, hi = 0.0, 1.0
        for _ in range(200):
            m = (lo + hi) / 2
            lo, hi = (m, hi) if 1 + m + m * m + m ** 3 < t3 else (lo, m)
        return lo

    rs = [r_of(v) for v in pb.values()]
    out = {k: sum(1 + sum(r ** i for i in range(1, k + 1)) for r in rs) / len(rs) for k in (1, 2, 3, 4)}
    assert abs(out[3] - T.tau_qwen3_8b()) < 1e-3 and abs(out[4] - q["4"]["tau"]) < 1e-3
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--verify", action="append", default=[], help="NAME:NP:CYCLES:RESULT_JSON (measured, exact)")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    R = ROOT / "results/rtl"
    rec = json.loads((R / "qwen_dspark_system_20261004/ctx8k/step_composed_ctx8k.json").read_text())
    tok = json.loads((R / "qwen_rom_kv_fullbw_20261004/compose_P8191_token.json").read_text())
    be = json.loads((R / "qwen_rom_kv_fullbw_20261004/dspark_breakeven.json").read_text())
    ar = tok["stream4"]["token_cycles"]
    ar_wire = tok["wire_bound"]["bound_cycles"]
    taus = tau_by_draft()
    dt = rec["composed"]["draft_terms"]
    head = rec["components_cycles"]["verify_head_p4_step1"]
    commit = rec["composed"]["commit_cycles"]
    layers_s3, heads_s3 = dt["drafter_layers_rtl"], dt["drafter_lm_head_S_slots_from_measured_heads"]
    ingest, markov_s3 = 70032, 4968

    def draft(S, bound):
        # S-dependent terms: draft heads and Markov scale with the slots (measured per slot); the drafter layers were
        # measured at S = 3 only: 'upper' keeps the S = 3 value, 'lower' scales it by S / 3 (both unvalidated for S < 3)
        lay = layers_s3 if (S == 3 or bound == "upper") else layers_s3 * S / 3
        return lay + heads_s3 * S / 3 + ingest + markov_s3 * S / 3

    rows = {}
    for v in a.verify:
        name, np_, cyc, res = v.split(":")
        np_, cyc = int(np_), int(cyc)
        r = json.loads(Path(res).read_text())
        S = np_ - 1
        tau = taus[S]
        row = {"np": np_, "draft_tokens": S, "tau": round(tau, 4), "verify_layer": cyc, "exact": r["status"] == "pass",
               "result": str(Path(res).relative_to(ROOT)) if Path(res).is_relative_to(ROOT) else res}
        for bound in ("upper", "lower"):
            d = draft(S, bound)
            step = 36 * cyc + head + d + commit
            row[f"draft_{bound}"] = round(d)
            row[f"step_{bound}"] = round(step)
            row[f"tok_s_{bound}"] = round(tau * HZ / step, 1)
            row[f"speedup_vs_ar_{bound}"] = round(tau * ar / step, 3)
        row["break_even_verify_layer_draft_upper"] = round((tau * ar - draft(S, "upper") - commit - head) / 36, 1)
        row["break_even_verify_layer_draft_lower"] = round((tau * ar - draft(S, "lower") - commit - head) / 36, 1)
        row["break_even_verify_layer_free_draft"] = round((tau * ar - commit - head) / 36, 1)
        rows[name] = row
    best = max(rows.values(), key=lambda x: x["speedup_vs_ar_lower"])
    verdict = "DSPARK_PAYS" if any(x["exact"] and x["speedup_vs_ar_upper"] > 1.0 for x in rows.values()) else "AR_MODE"
    out = {
        "schema": "opentallas.qwen-rom-dspark-verdict.v1",
        "verdict": verdict,
        "context": "Qwen3-8B ROM TP4, 8K (P8187..8191), 4-stack STREAM4 KV path, 1.2 GHz",
        "method": __doc__.split("\n\n", 1)[1].strip(),
        "ar": {"token_cycles": ar, "tok_s": round(HZ / ar, 1), "wire_bound_cycles": ar_wire,
               "wire_bound_tok_s": round(HZ / ar_wire, 1), "record": "results/rtl/qwen_rom_kv_fullbw_20261004/compose_P8191_token.json"},
        "tau_by_draft_tokens": {str(k): round(v, 4) for k, v in taus.items()},
        "tau_source": T.tau_src("qwen3_8b"),
        "draft_terms_s3": {"drafter_layers_5xD0_realmem": layers_s3, "draft_heads": heads_s3, "ingest_measured": ingest,
                           "markov_measured_plus_priced_argmax": markov_s3, "source": "step_composed_ctx8k.json + ingest_markov_rtl/README.md (fac4b889e)"},
        "verify_head": head, "commit": commit,
        "variants": rows,
        "best": best,
        "single_pass_area": be.get("single_pass_4pos_area_estimate"),
        "levers": json.loads((R / "qwen_rom_kv_fullbw_20261004/dspark_levers.json").read_text()),
        "unvalidated": ["drafter layers at S < 3 (bounded: S = 3 value upper, x S/3 lower)",
                        "drafter layers measured on REAL_MEM, not STREAM4",
                        "draft argmax + gather priced (3 x 736 at S = 3)",
                        "verify head for np < 4 taken at the np = 4 value (upper)"],
    }
    a.out.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: out[k] for k in ("verdict", "ar", "tau_by_draft_tokens")}, indent=1))
    for n, x in rows.items():
        print(n, {k: x[k] for k in ("np", "tau", "verify_layer", "exact", "speedup_vs_ar_upper", "speedup_vs_ar_lower",
                                     "break_even_verify_layer_draft_lower")})


if __name__ == "__main__":
    main()
