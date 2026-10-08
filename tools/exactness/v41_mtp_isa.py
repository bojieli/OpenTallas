#!/usr/bin/env python3
"""Exactness regression: DeepSeek-V4.1 DSpark MTP at golden + ISA level (reduced v2 vehicle).

Re-checks the claims of results/rtl/hdc_v41_mtp_isa_evidence.json on the current source:
  1. golden: Model.generate_spec (DSpark, gamma 5) == Model.generate (greedy), tokens and logits bit-equal;
  2. ISA: hdc_program_v41.mtp_run of the as-built MTP program (gamma 3 and 5, lane multiplier 1, DSpark and the
     forced drafter that exercises every accept length) == the golden greedy tokens, committed logits bit-exact;
  3. the poisoned-dead-row run (exact); the 2-entry slot-ring mutation is recorded only.

    v41_mtp_isa.py --output result.json
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden as G  # noqa: E402
import hdc_golden_v41 as V  # noqa: E402
import hdc_program_v41 as P  # noqa: E402
import rtl_hdc_v41_mtp_campaign as M  # noqa: E402


def exact_rows(a, b):
    return len(a) == len(b) and all(np.array_equal(G.bits(x), G.bits(y)) for x, y in zip(a, b))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--ngen", type=int, default=8)
    a = ap.parse_args()
    t0 = time.monotonic()
    model = V.Model()
    prompt = M.prompts()["oracle8"][:3]
    res = {"schema": "opentallas.exactness.v41-mtp-isa.v1", "prompt": prompt, "ngen": a.ngen, "runs": []}
    ref_tokens, ref_logits = model.generate(prompt, a.ngen)
    spec_tokens, spec_logits = model.generate_spec(prompt, a.ngen, gamma=5)[:2]
    res["golden"] = {"greedy_tokens": list(map(int, ref_tokens)), "spec_tokens_equal": list(spec_tokens) == list(ref_tokens),
                     "spec_logits_bit_equal": exact_rows(spec_logits, ref_logits)}
    ok = res["golden"]["spec_tokens_equal"] and res["golden"]["spec_logits_bit_equal"]
    cont = list(prompt) + list(ref_tokens)
    for gamma in (3, 5):
        lay = P.mtp_layout(model, gamma)
        prog, entry = P.build_mtp(lay, gamma, 1)
        for drafter in ("dspark", "forced"):
            forced = M.forced_drafter(cont, gamma) if drafter == "forced" else None
            toks, rows, steps = P.mtp_run(lay, prog, entry, prompt, a.ngen, gamma, forced=forced)
            r = {"gamma": gamma, "drafter": drafter, "tokens_equal": list(toks) == list(ref_tokens),
                 "logits_bit_exact": exact_rows(rows, ref_logits), "accepted": [int(s["accepted"]) for s in steps]}
            ok &= r["tokens_equal"] and r["logits_bit_exact"]
            res["runs"].append(r)
    checks = M.isa_checks(model, 3, prompt, a.ngen, (ref_tokens, ref_logits))
    res["isa_checks"] = checks
    ok &= checks["poisoned_dead_rows"]["tokens_equal_golden"] and checks["poisoned_dead_rows"]["logits_bit_exact"]
    # the 2-entry slot-ring mutation is the campaign's own negative control at gamma 5 / 16 tokens; at this short
    # run it need not alias a live entry, so it is recorded, not judged (the published evidence does not claim it)
    res["exact"] = bool(ok)
    res["wall_seconds"] = round(time.monotonic() - t0, 1)
    a.output.write_text(json.dumps(res, indent=1, default=int) + "\n")
    print(json.dumps({"exact": res["exact"], "golden": res["golden"],
                      "runs": [(r["gamma"], r["drafter"], r["tokens_equal"], r["logits_bit_exact"]) for r in res["runs"]]}))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
