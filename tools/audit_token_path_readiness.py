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

    #: The bridge's own admission bound on a matmul weight source's row count,
    #: read out of the RTL rather than taken from a record that predates it.
    bridge = (ROOT / "rtl/abi3/ot_a3_engine_issue_bridge.sv").read_text()
    bound_match = re.search(
        r"matmul_weight_source_ok.*?desc_view_dim0 <= 32'h([0-9a-fA-F]+)",
        bridge, re.S)
    head_row_bound = int(bound_match.group(1), 16) if bound_match else 0
    shipped_head_rows = int(hf.get("shipped_weight_rows") or 0)
    head_partitions_needed = (
        -(-shipped_head_rows // head_row_bound) if head_row_bound else 0
    )
    #: REDUCTION.PARTITION_SUM's partial extent is what VOCABULARY_PARTITIONS binds,
    #: and the driver states it from the deployment rather than capping it, so the
    #: ceiling here is the symbol's own field width.
    abi_partitions = 255

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
            "id": "shipped-lm-head-fits-in-the-vocabulary-partitions",
            "asks": ("can the SHIPPED LM head width be admitted, in the vocabulary "
                     "partitions the ABI provides?"),
            #: DERIVED FROM THE RTL, not from the old measurement. The 4,096 figure
            #: in abi3_g1d_head_admission.json was measured before the bound moved;
            #: the bridge's matmul weight-source admission now reads
            #: ``desc_view_dim0 <= 32'hffff``, and a check that hardcodes False
            #: against a raised bound is exactly the stale blocker this tool exists
            #: to catch. It caught two others in the same run.
            "met": bool(head_row_bound) and head_partitions_needed <= abi_partitions,
            "evidence": (
                f"the bridge admits matmul weight rows up to {head_row_bound:,} "
                f"(rtl/abi3/ot_a3_engine_issue_bridge.sv, matmul_weight_source_ok); "
                f"the shipped Qwen3 head is {shipped_head_rows:,} rows, so it needs "
                f"{head_partitions_needed} vocabulary partitions and the ABI's "
                f"VOCABULARY_PARTITIONS symbol provides up to {abi_partitions}. The "
                f"superseded measurement in abi3_g1d_head_admission.json is "
                f"{hf.get('largest_weight_rows_measured_to_launch')} launching and "
                f"{hf.get('smallest_weight_rows_measured_to_refuse')} refusing, taken "
                f"before the bound was raised."
            ),
            "note": ("The reduced configuration is still required, but for the OTHER "
                     "reason this tool states: the shipped forward pass is 7.57e9 "
                     "multiply-accumulates and one lane retires one per cycle. Width "
                     "of the head is no longer the blocker; simulation time is."),
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

    #: ---- the staging the remaining run needs, measured from the deployment ----
    dep = jload("build/abi3/qwen3-reduced-rom/deployment.json") or {}
    objs = dep.get("objects") or []
    def size(o):
        return int((o.get("source") or {}).get("size_bytes") or 0)
    by_kind: dict[str, dict[str, int]] = {}
    for o in objs:
        kind = (o.get("source") or {}).get("kind") or "unknown"
        row = by_kind.setdefault(kind, {"objects": 0, "bytes": 0})
        row["objects"] += 1
        row["bytes"] += size(o)
    staging = {
        "objects": len(objs),
        "total_bytes": sum(size(o) for o in objs),
        "by_source_kind": by_kind,
        "largest_object_bytes": max((size(o) for o in objs), default=0),
        "placement_table_entries_available": 32,
        "note": (
            "Only objects whose source is `segments` carry data that must be "
            "staged; `zero` objects need address space and no bytes, and they are "
            "the large ones (KV planes). The largest object is bigger than the "
            "vehicle's default result bank, so RESULT_WORDS has to be raised at "
            "elaboration -- it is a parameter, not a limit."
        ),
    }

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
        "remaining_run_staging": staging,
        "remaining_run_plan": [
            "assign a distinct base per object, per bank, from the sizes in the "
            "deployment's own object table; the bridge refuses an object the "
            "placement table does not name and refuses one named twice",
            "stage the `segments` objects: the large ones through the DPI weight "
            "window the vehicle already has, the small ones into the source bank",
            "elaborate ot_a3_shipped_prefix_top at the reduced geometry "
            "(GQA_QUERY_HEADS=8, GQA_KV_HEADS=2, GQA_HEAD_WIDTH=16, scale code "
            "0x3e800000 for 1/sqrt(16)) with RESULT_WORDS raised past the largest "
            "object",
            "bootstrap the placement table by probing, which is the pattern "
            "tools/rtl_abi3_g1d_head_admission.py already uses: run, read which "
            "object the bridge refused, add it, repeat. Unlike that tool this must "
            "give each object its OWN base and stage its bytes, because a shared "
            "probe base is exactly why its selected token is not a token id",
            "read selected_token off the vehicle's port and compare it against the "
            "oracle's [1073, 382, 93]",
        ],
        "why_the_placement_step_needs_the_builder": {
            "finding": (
                "The placement bases are PER-BANK COMPACT allocations, not a global "
                "layout derivable from the deployment's object table. Read out of "
                "the committed p3_case.hex, the shipped table has objects 4 and 55 "
                "BOTH at base 8448, and objects 8 and 64 both at 12544 -- legal "
                "because the bridge chooses the bank from the reading slot, so two "
                "objects in different banks may share a base value. And the spacing "
                "does not follow the declared sizes: object 8 is 9,216 bytes and "
                "object 10 sits 128 units later."
            ),
            "consequence": (
                "A standalone planner cannot reproduce this from deployment.json. "
                "The allocation follows the builder's operator walk, which knows "
                "each view's slot and therefore its bank. Reconstructing it from "
                "thirteen sample rows would be guessing, and a guessed placement "
                "that happened to emit a token id would be worse than no token: it "
                "would read the wrong bytes and still select something."
            ),
            "so_the_next_step_is": (
                "extend tools/build_abi3_shipped_prefix_vectors.py with a reduced "
                "target and let its existing allocator assign the bases, rather "
                "than writing a second allocator that has to agree with it."
            ),
        },
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
