#!/usr/bin/env python3
"""Summary record of the DSpark MTP RTL campaign parts (results/rtl/dsrom_dspark_rtl_20261003/parts/*.json).

    python3 tools/dsrom_dspark_rtl_record.py [--dir results/rtl/dsrom_dspark_rtl_20261003]

Writes <dir>/summary.json: per part and run, pass/fail per check (tokens vs the golden's non-speculative greedy
stream, every head's logits vs the ISA model, accepted counts, final VM and KV incl. dead rows, unit activation,
mutation detected), cycles per prefill position / draft / verify+accept / step / emitted token, and the ratios
draft / AR-token and verify / AR-token against the microarchitecture model's V4.1 ROM figures.  Ratios on the
REDUCED vehicle are structural (its bottleneck is the 1-wide stream unit, not the ROM field): they are recorded
beside the model's full-shape ratios, never substituted for them.
"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_PARTS = ("rom_m1_g5_gold4", "rom_m1_g5_o8s6", "x_heme", "x_heme_guard", "x_all6",
                  "x_heme_g3", "x_heme_g1", "x_heme_guard_n24", "rom_m1_plain", "x_all6dpi")
# the model's V4.1 ROM figures (gamma 5, 6 verified positions, m = 1 time-multiplexed)
MODEL = {
    "uarch_speculation_json": {"source": "results/uarch/speculation.json v41_rom_mtp_m1",
                               "verify_over_ar": 2.298, "draft_over_ar_assumed": 3 / 40},
    "mtp_acceptance_pilot_rom_product": {
        "source": "origin/claude/v41-hbm-speculation-20261003 d2aff19ef results/speculative/"
                  "v41_hbm_speculation_methods_20261003 rom_note (T_ar 358.8 us, verify g5 768.3 us, "
                  "draft assumed 26.9 us, HBM-ratio proxy 42.1 us)",
        "t_ar_us": 358.8, "verify_us": 768.3, "draft_us_assumed": 26.9, "draft_us_proxy": 42.1,
        "verify_over_ar": round(768.3 / 358.8, 3), "draft_over_ar_assumed": round(26.9 / 358.8, 4),
        "draft_over_ar_proxy": round(42.1 / 358.8, 4)},
    "hbm_dspark_composition": {"source": "d2aff19ef: HBM design, draft 51.9 us, verify P=6 700.9 us at 1M",
                               "draft_us": 51.88, "verify_us": 700.85},
}


def checks(run):
    r, isa = run["rtl"], run["isa"]
    c = {"isa_tokens_equal_golden": isa.get("equal_golden_tokens"),
         "isa_committed_logits_bit_exact_golden": isa.get("committed_logits_bit_exact_with_golden"),
         "rtl_ran_to_summary": "iters" in r,
         "rtl_tokens_equal_golden": r.get("token_mismatches") == 0,
         "rtl_heads_bit_exact_isa": r.get("head_mismatches") == 0,
         "rtl_accept_counts_equal_isa": r.get("accept_mismatches") == 0,
         "rtl_final_vm_equal_isa": r.get("vm_mismatches") == 0,
         "rtl_final_kv_equal_isa_incl_dead_rows": r.get("kv_mismatches") == 0}
    c["rtl_exited_successfully"] = r.get("returncode") == 0
    it = r.get("per_iter", [])
    c["rtl_iteration_log_complete"] = bool(it) and len(it) == r.get("iters")
    c["rtl_iterations_fault_free"] = bool(it) and all(x.get("fault") == 0 for x in it)
    if "activation" in r:
        c["respecified_units_fired"] = r["activation"].get("pass")
    return c


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dir", type=Path, default=ROOT / "results/rtl/dsrom_dspark_rtl_20261003")
    ap.add_argument("--output", type=Path, help="new summary path; existing evidence is never overwritten")
    a = ap.parse_args()
    parts = {p.stem: json.loads(p.read_text()) for p in sorted((a.dir / "parts").glob("*.json"))}
    plain = {}
    for name, p in parts.items():
        if p.get("mode") == "plain":
            for r in p["runs"]:
                if r["rtl"].get("cycles_per_token"):
                    plain[r["prompt"]] = r["rtl"]["cycles_per_token"]
    out = {"schema": "opentallas.dsrom-dspark-rtl-summary.v1", "model": MODEL,
           "ar_token_cycles_as_built_same_bench": plain, "parts": {}}
    missing = sorted(set(EXPECTED_PARTS) - set(parts))
    out["missing_parts"] = missing
    allpass = bool(parts)
    for name, p in parts.items():
        if p.get("mode") == "plain":
            out["parts"][name] = {"pass": p["pass"], "mode": "plain (one-position baseline)",
                                  "runs": [{"prompt": r["prompt"], "pass": r["pass"],
                                            "cycles_per_token": r["rtl"].get("cycles_per_token"),
                                            "prefill_cycles": r["rtl"].get("prefill_cycles")} for r in p["runs"]]}
            allpass &= p["pass"]
            continue
        rows = []
        for r in p["runs"]:
            rt = r["rtl"]
            it = rt.get("per_iter", [])
            c = checks(r)
            row = {"prompt": r["prompt"], "drafter": r["drafter"],
                   "pass": bool(r["pass"] and all(v is True for v in c.values())), "checks": c,
                   "accepted_per_step": [x["accepted"] for x in it] or r["isa"].get("accepted"),
                   "steps": len(it), "generated": rt.get("generated")}
            if it:
                n = len(it)
                dr = sum(x["draft_cycles"] for x in it) / n
                st = sum(x["cycles"] for x in it) / n
                row["cycles"] = {"prefill_per_position": round(rt["prefill_cycles"] / rt["prompt"], 1),
                                 "draft_per_step": round(dr, 1), "verify_accept_per_step": round(st - dr, 1),
                                 "step": round(st, 1),
                                 "per_emitted_token": round(sum(x["cycles"] for x in it) /
                                                            sum(x["emitted"] for x in it), 1)}
                ar = rt["prefill_cycles"] / rt["prompt"]
                row["ratios_vs_prefill_position"] = {"draft_over_ar": round(dr / ar, 4),
                                                     "verify_accept_over_ar": round((st - dr) / ar, 3)}
            rows.append(row)
        mut = p.get("mutation_rtl_restore_slot_plus_1")
        detected = None if mut is None else bool(mut["detected"] and "iters" in mut and mut.get("returncode") == 0)
        passed = bool(p["pass"] and rows and all(r["pass"] for r in rows) and detected is not False)
        out["parts"][name] = {"pass": passed, "core": p.get("core", "ot_hdc_core_v41 (as built)"),
                              "units": p.get("respecified_units"), "accept_unit": p.get("accept_unit", "ot_hdc_accept"),
                              "gamma": p.get("gamma"), "fp": p.get("fp"), "runs": rows,
                              "mutation_engram_restore_slot_plus_1_detected": detected,
                              "isa_checks": p.get("isa_checks")}
        allpass &= passed
    out["status"] = "incomplete" if missing else "pass" if allpass else "fail"
    target = a.output or a.dir / "summary.json"
    with target.open("x") as f:
        f.write(json.dumps(out, indent=1) + "\n")
    for n, p in out["parts"].items():
        print(n, "PASS" if p["pass"] else "FAIL",
              [(r["prompt"], r.get("drafter"), r["pass"], r.get("cycles", {}).get("step", r.get("cycles_per_token")))
               for r in p["runs"]])
    return 2 if missing else 0 if allpass else 1


if __name__ == "__main__":
    raise SystemExit(main())
