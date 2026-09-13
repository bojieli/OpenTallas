#!/usr/bin/env python3
"""What still stands between this RTL and an emitted token id?

``results/rtl/abi3_g1d_token.json`` records ``record_token_ids: []`` with the note
"the RTL emitted no token id", and that is still true. This tool checks, mechanically
and one at a time, every precondition for changing it -- because the list of
remaining work in ``abi3_g1f_reduced_end_to_end.json`` is now STALE in three places,
and a stale blocker list is worse than none: it sends the next person to fix
something that is already fixed.

Each check reads the file it is about. Nothing here is asserted.

WHY A REDUCED CONFIGURATION IS REQUIRED, since that is the whole shape of the answer.
The shipped Qwen3-8B forward pass is 7.57e9 multiply-accumulates. The single RTL
tensor lane retired one every five cycles, so the shipped-prefix campaign spent
252,057,074 simulated cycles on SIX matmuls; a whole token is about 38e9 cycles, or
roughly 49 hours. The pipelined lane cuts that to about 10 hours, which is still not a
regression test. The reduced configuration is 613 seconds at the same measured rate,
and that is the industry's ordinary answer: verify the tapeout configuration with a
pyramid of unit and composition rungs, and run the SMALL configuration whole.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def git_state() -> dict[str, Any]:
    def run(*a: str) -> str:
        return subprocess.run(["git", *a], cwd=ROOT, capture_output=True,
                              text=True, check=False).stdout.strip()
    return {"commit": run("rev-parse", "HEAD") or None,
            "worktree_dirty": bool(run("status", "--porcelain"))}


def text(rel: str) -> str:
    p = ROOT / rel
    return p.read_text() if p.exists() else ""


def jload(rel: str) -> Any:
    p = ROOT / rel
    return json.loads(p.read_text()) if p.exists() else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()

    gqa = text("rtl/abi3/ot_a3_qwen_gqa.sv")
    rms = text("rtl/abi3/ot_a3_vector_rms_norm.sv")
    veh = text("rtl/test/a3_shipped_prefix_top.sv")
    arr = text("rtl/abi3/ot_a3_engine_array.sv")
    vec = text("tools/build_abi3_shipped_prefix_vectors.py")
    head = jload("results/rtl/abi3_g1d_head_admission.json") or {}
    tok = jload("results/rtl/abi3_g1d_token.json") or {}
    fast = jload("results/rtl/abi3_shipped_prefix_campaign_pipelined_tensor.json") or {}
    base = jload("results/rtl/abi3_shipped_prefix_campaign.json") or {}

    hf = (head.get("findings") or {}).get("qwen3-8b-hbm-single-chip") or {}

    checks = [
        {
            "id": "attention-geometry-is-a-parameter",
            "asks": "does ot_a3_qwen_gqa take its head geometry at elaboration?",
            "met": all(k in gqa for k in ("QUERY_HEADS", "KV_HEADS", "HEAD_WIDTH")),
            "evidence": "rtl/abi3/ot_a3_qwen_gqa.sv parameter names",
            "was_listed_as_blocking": True,
        },
        {
            "id": "rms-norm-width-is-generic",
            "asks": ("does ot_a3_vector_rms_norm derive its mean reciprocal instead "
                     "of selecting between two hardcoded widths?"),
            "met": "exact_reciprocal_code" in rms,
            "evidence": "rtl/abi3/ot_a3_vector_rms_norm.sv derives the reciprocal",
            "was_listed_as_blocking": True,
        },
        {
            "id": "vehicle-accepts-the-reduced-geometry",
            "asks": ("can the integrated vehicle be elaborated at the reduced "
                     "geometry, rather than only at the shipped one?"),
            "met": all(k in veh for k in ("GQA_QUERY_HEADS", "GQA_KV_HEADS",
                                          "GQA_HEAD_WIDTH", "GQA_SCALE_CODE")),
            "evidence": "rtl/test/a3_shipped_prefix_top.sv parameters, forwarded to the bridge",
            "was_listed_as_blocking": False,
        },
        {
            "id": "argmax-launches-when-admitted",
            "asks": "does SELECTION.ARGMAX actually launch once the gate is on?",
            "met": bool(hf.get("argmax_launched")),
            "evidence": (f"abi3_g1d_head_admission: launches with the gate on "
                         f"{hf.get('argmax_launches_with_the_gate_on')}, off "
                         f"{hf.get('argmax_launches_with_the_gate_off')}"),
            "was_listed_as_blocking": False,
        },
        {
            "id": "shipped-lm-head-is-too-wide",
            "asks": "can the SHIPPED LM head width be admitted at all?",
            "met": False,
            "evidence": (f"largest weight rows measured to launch "
                         f"{hf.get('largest_weight_rows_measured_to_launch')}, "
                         f"smallest to refuse "
                         f"{hf.get('smallest_weight_rows_measured_to_refuse')}, "
                         f"shipped {hf.get('shipped_weight_rows')}"),
            "note": ("This is why the token must come from a REDUCED configuration "
                     "and not from the shipped one. It is a measurement, not a "
                     "limitation to be argued away."),
            "was_listed_as_blocking": False,
        },
        {
            "id": "new-tensor-datapath-runs-under-the-real-control-plane",
            "asks": ("does the redesigned tensor lane execute a real program under "
                     "the real microsequencer, bridge and engine array?"),
            "met": (fast.get("status") == "pass"
                    and "ot_a3_mac_lane_pipe" in arr),
            "evidence": (f"shipped-prefix campaign with the pipelined lane: status "
                         f"{fast.get('status')}, "
                         f"{(fast.get('cases') or [{}])[0].get('checks')} checks, "
                         f"{fast.get('simulated_cycles')} cycles against the legacy "
                         f"lane's {base.get('simulated_cycles')}"),
            "was_listed_as_blocking": False,
        },
        {
            "id": "vector-set-admits-the-six-mapped-families",
            "asks": ("does the committed vector set set MAPPED_FAMILIES_WORD, which "
                     "is what admits DMA.SCATTER, ATTENTION.GQA, VECTOR.ADD, "
                     "VECTOR.SILU_MUL, SELECTION.ARGMAX and SELECTION.TOKEN_APPEND?"),
            "met": not bool(re.search(r"words\.append\(0\)\s*#\s*MAPPED_FAMILIES_WORD", vec)),
            "evidence": ("tools/build_abi3_shipped_prefix_vectors.py emits 0 for "
                         "MAPPED_FAMILIES_WORD, because the set carries no golden "
                         "past its fail-stop boundary"),
            "note": ("THIS IS THE REMAINING BLOCKER. The gate is one word; what it "
                     "needs is a golden write stream for the reduced program past "
                     "that boundary, which is a builder bootstrap rather than a "
                     "design change: the numbers can only be what a first run "
                     "reports and are then pinned."),
            "was_listed_as_blocking": True,
        },
    ]

    met = [c for c in checks if c["met"]]
    unmet = [c for c in checks if not c["met"]]
    stale = [c for c in checks if c["met"] and c["was_listed_as_blocking"]]

    body = {
        "schema": "opentallas.audit.token_path_readiness.v1",
        "question": "What still stands between this RTL and an emitted token id?",
        "git": git_state(),
        "rtl_token_ids_today": tok.get("records", [{}])[0].get("record_token_ids")
                               if tok.get("records") else None,
        "checks": checks,
        "met_count": len(met),
        "unmet_count": len(unmet),
        "previously_listed_blockers_now_met": [c["id"] for c in stale],
        "refusals": [
            "a-met-precondition-is-not-a-token: every check here is about whether "
            "something STOPS a token. None of them is evidence that one was emitted, "
            "and record_token_ids is still empty.",
            "greps-are-not-proofs: the RTL checks test for parameter and function "
            "names in the source. They establish that the mechanism exists, not that "
            "it is correct at the reduced geometry -- the G1f probe measures that "
            "separately and reports admitted=True.",
            "the-reduced-configuration-is-not-the-shipped-one: a token from the "
            "reduced model is a regression result. It says the integrated path works "
            "end to end; it says nothing about Qwen3-8B's own output.",
        ],
    }

    print("What still stands between this RTL and an emitted token id?\n")
    for c in checks:
        mark = "MET   " if c["met"] else "UNMET "
        print(f"  [{mark}] {c['id']}")
        print(f"           {c['asks']}")
        print(f"           {c['evidence']}")
        if c.get("note"):
            print(f"           -> {c['note']}")
    print(f"\n  {len(met)} met, {len(unmet)} unmet.")
    if stale:
        print(f"\n  STALE BLOCKER LIST: {len(stale)} preconditions that "
              f"abi3_g1f_reduced_end_to_end.json still lists as blocking are met:")
        for c in stale:
            print(f"    - {c['id']}")
        print("  A stale blocker list sends the next person to fix what is already "
              "fixed.")
    print("\n  Read the refusals: a met precondition is not a token, and "
          "record_token_ids is still empty.")

    if args.output:
        args.output.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n")
        try:
            shown = args.output.relative_to(ROOT)
        except ValueError:
            shown = args.output
        print(f"wrote {shown}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
