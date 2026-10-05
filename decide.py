#!/usr/bin/env python3
"""Turn analytical evidence into explicit technical gates, never an implied tapeout decision."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("result", type=Path)
    parser.add_argument("--sensitivity", type=Path, default=Path("results/sensitivity/claim-audit.json"))
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/standard/DECISION_LEGACY.md"),
    )
    args = parser.parse_args()
    data = json.loads(args.result.read_text(encoding="utf-8"))
    all_comparisons = data["comparisons"]
    comparisons = [
        row for row in all_comparisons if row["scenario"] == "no_speculation"
    ]
    primary = [row for row in comparisons if "DeepSeek-V4" in row["model"]]
    speed_wins = [row for row in primary if row.get("speed_ratio") is not None and row["speed_ratio"] > 1]
    cost_wins = [
        row for row in primary
        if row.get("partial_tco_ratio_vs_cheapest_gpu") is not None
        and row["partial_tco_ratio_vs_cheapest_gpu"] > 1
    ]
    speculative_primary = [
        row
        for row in all_comparisons
        if row["scenario"] == "speculative_midpoint"
        and "DeepSeek-V4" in row["model"]
    ]
    speculative_speed_wins = [
        row
        for row in speculative_primary
        if row.get("speed_ratio") is not None and row["speed_ratio"] > 1
    ]

    def ratio(model_fragment: str, context: int, batch: int) -> float | None:
        row = next(
            row
            for row in primary
            if model_fragment in row["model"]
            and row["context_tokens"] == context
            and row["batch_size"] == batch
        )
        return row.get("speed_ratio")

    def ratio_text(value: float | None) -> str:
        return "infeasible" if value is None else f"{value:.2f}×"

    deepseek_b64 = [row for row in primary if row["batch_size"] == 64]
    deepseek_b64_losses = [
        row
        for row in deepseek_b64
        if row.get("speed_ratio") is not None and row["speed_ratio"] < 1
    ]
    claim_audit = []
    if args.sensitivity.exists():
        claim_audit = json.loads(args.sensitivity.read_text(encoding="utf-8"))
    lines = [
        "# Legacy single-midpoint technical gate decision",
        "",
        "> **Superseded.** This generator consumes `results/standard/` and cannot",
        "> overwrite the current iso-node decision in `results/DECISION.md`.",
        "",
        "**Decision: CONDITIONAL CONTINUE for simulation/test-chip work; no evidence-based",
        "authorization for product silicon.**",
        "",
        "The released-format midpoint has some DeepSeek low-batch speed and cost wins, but",
        "the result changes sign by batch and depends on unmeasured ROM bandwidth, compute",
        "density, HBM beachfront, and physical collective timing. It therefore supports the",
        "next measurement phase, not the brief's product-level performance claims.",
        "",
        "## Evidence currently passed",
        "",
        f"- Without speculation, {len(speed_wins)} of {len(primary)} required DeepSeek points beat the fastest same-batch GPU configuration under midpoint assumptions.",
        f"- With the assumed five-candidate/70%-acceptance speculative midpoint enabled on both sides, only {len(speculative_speed_wins)} of {len(speculative_primary)} required DeepSeek points retain a same-batch speed win; acceptance and draft cost are not measured.",
        f"- {len(cost_wins)} of {len(primary)} required DeepSeek points beat the cheapest feasible same-batch GPU on modeled partial TCO (hardware/NRE amortization plus active electricity).",
        "- Flash B8 no-speculation ROM/GPU ratios are "
        f"{ratio_text(ratio('Flash', 200_000, 8))} at 200K and "
        f"{ratio_text(ratio('Flash', 1_000_000, 8))} at 1M; Pro B8 ratios are "
        f"{ratio_text(ratio('Pro', 200_000, 8))} and "
        f"{ratio_text(ratio('Pro', 1_000_000, 8))}, respectively.",
        f"- {len(deepseek_b64_losses)} of {len(deepseek_b64)} DeepSeek B64 points are feasible and lose on same-batch speed; no DeepSeek B64 speed case survives the midpoint.",
        "- Exact checkpoint manifests/configs are pinned and fully accounted without full payload downloads; main-decode, draft-only, and resident-only bytes are separated.",
        "- DeepSeek numeric formats are now explicit: MXFP4 expert storage is modeled as MXFP4-weight × FP8-activation compute, so neither GPU nor ROM receives an incompatible pure-FP4 roof.",
        "- Closed-form MoE coverage matches uniform trace simulation; correlated stress traces expose the load-balance tail.",
        "- Hierarchical collective and placement sweeps execute on CPU and report their own lower bounds.",
        "- Pipeline capacity charges batch × stages resident sessions, so infeasible high-context points are no longer reported as throughput wins.",
        "",
        "## Gates not passed",
        "",
        "- No foundry measurement establishes ROM bit density or PB/s-class full-array read bandwidth.",
        "- No synthesis result establishes the multi-POP/s per-wafer compute density needed by the provisional ultra tiers.",
        "- No production router or GPU profiler trace establishes engaged bandwidth, tail imbalance, or actual KV HBM reads.",
        "- The 2 × active-parameter compute proxy still lacks an operator-level inventory for context-dependent indexer/attention work and vector operations.",
        "- The present B200/B300 report is a contemporary-market challenge, not an N7/HBM2e iso-technology comparison; the A100/N7 scenario remains to be built.",
        "- The model owner/checkpoint-freeze commitment has not occurred.",
        "- Packaging, beachfront HBM, yield/repair, clock/power delivery, cooling, NRE, and unit cost remain assumptions.",
        "- Partial TCO excludes staffing, financing, networking, floor space, maintenance, replacement inventory, and idle-period electricity.",
        "",
        "## Target ordering",
        "",
        "1. **DeepSeek V4 Flash** as the primary proof target: smallest measured image and strongest low-batch margin, while the speculative result makes clear that the margin still needs trace validation.",
        "2. **DeepSeek V4 Pro** as a stretch architecture target, not a current product-performance claim: it requires six released-format midpoint stages, loses at B8, and loses even at B1 under the assumed speculative midpoint.",
        "3. **Qwen3-8B** as a small dense control, not a mask-ROM product target: it checks single-stage dense/GQA behavior and x1/x2 GPU normalization at 8K without importing an unsupported draft model.",
        "4. **Kimi K3** as a negative/stress control: its dense MLA traffic makes 1M context beachfront-bound and it does not show a robust speed case here.",
        "",
        "## Next pass criteria",
        "",
        "Continue only if circuit simulation/test macro and synthesis put the required read/compute point inside a power/cooling envelope, an operator-level V4 trace replaces the current compute proxy, and measured router/KV traces leave ROM viable in both the N7/A100 attribution case and the leading-node/B300 market case at the intended batch. A checkpoint-freeze commitment remains an independent mandatory gate.",
        "",
    ]
    if claim_audit:
        lines.extend(["## Provisional tier audit", ""])
        for claim in claim_audit:
            lines.append(
                f"- B={claim['batch_size']}: brief target {claim['brief_target_per_user_tokens_s']:,.0f} tok/s; "
                f"collective/pipeline-only ceiling {claim['collective_and_pipeline_ceiling_tokens_s']:,.0f} tok/s; "
                f"grid maximum {claim.get('maximum_achieved_per_user_tokens_s_on_grid', 0):,.0f} tok/s "
                f"({claim.get('binding_constraint_at_grid_maximum', 'unknown')})."
            )
        lines.append("")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
