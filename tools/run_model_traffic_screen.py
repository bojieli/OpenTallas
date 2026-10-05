#!/usr/bin/env python3
"""Generate the hardware-independent weight/KV traffic screen."""

from __future__ import annotations

import argparse
import csv
import io
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from opentallas.schema import ModelProfile  # noqa: E402
from opentallas.workload import kv_traffic, weight_traffic  # noqa: E402


MODEL_PATHS = (
    ROOT / "configs/models/deepseek-v4-flash-0731.json",
    ROOT / "configs/models/deepseek-v4-pro-0813.json",
    ROOT / "configs/models/kimi-k3.json",
    # Candidate, profiled 2026-09-13 from the official checkpoint headers;
    # both Engram placements carry identical traffic, so only one is screened.
    ROOT / "configs/models/candidates/deepseek-v4.1-flash.json",
)
CONTEXTS = (8_192, 32_768, 200_000, 1_000_000)
BATCHES = (1, 8, 32, 64)
OUTPUT_ROOT = ROOT / "results/model-traffic"


def build() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for path in MODEL_PATHS:
        model = ModelProfile.load(path)
        for context in CONTEXTS:
            kv = kv_traffic(model, context)
            for batch in BATCHES:
                weights = weight_traffic(model, batch)
                kv_read_step = batch * kv.read_bytes
                kv_total_step = batch * kv.total_transfer_bytes
                rows.append(
                    {
                        "model": model.name,
                        "source_revision": model.source_revision,
                        "context_tokens": context,
                        "batch_size": batch,
                        "active_weight_read_bytes_per_step": weights.total_bytes,
                        "routed_expert_coverage": weights.routed_expert_coverage,
                        "kv_read_bytes_per_user_token": kv.read_bytes,
                        "kv_write_bytes_per_user_token": kv.write_bytes,
                        "kv_read_bytes_per_step": kv_read_step,
                        "kv_total_bytes_per_step": kv_total_step,
                        "weight_to_kv_read_ratio": (
                            weights.total_bytes / kv_read_step
                        ),
                        "weight_to_kv_read_write_ratio": (
                            weights.total_bytes / kv_total_step
                        ),
                    }
                )
    return {
        "schema_version": 1,
        "definition": {
            "weight_to_kv_read_ratio": "active weight bytes per step / (batch * KV read bytes per user token)",
            "weight_to_kv_read_write_ratio": "active weight bytes per step / (batch * (KV read + KV write bytes per user token))",
            "scope": "ordinary one-position decode traffic before any hardware bandwidth, compute, communication, capacity, or thermal model",
        },
        "contexts": list(CONTEXTS),
        "batches": list(BATCHES),
        "rows": rows,
        "evidence_boundary": [
            "DeepSeek cache layout/precision and tensor topology follow pinned official artifacts; packing overhead is derived.",
            "Kimi topology is pinned, while KDA retained-state precision and optimized gated-MLA cache representation remain explicit assumptions in the model profile.",
            "Uniform independent expert routing determines expected expert coverage; production router traces are unavailable.",
            "Ratios are traffic screens, not speedup predictions.",
        ],
    }


def _fmt_ratio(value: float) -> str:
    return f"{value:,.2f}×"


def render_report(result: dict[str, Any]) -> str:
    lines = [
        "# Model weight/KV traffic screen",
        "",
        "This is a hardware-independent ordinary-decode traffic calculation. It",
        "answers how many active weight bytes are read for each mutable KV byte at",
        "a given context and batch; it does **not** predict ROM/GPU speedup.",
        "",
        "```text",
        "R_read(B,L)  = active_weight_bytes(B) / (B × KV_read_bytes(L))",
        "R_total(B,L) = active_weight_bytes(B) / (B × (KV_read_bytes(L) + KV_write_bytes))",
        "```",
        "",
        "## Raw traffic inputs",
        "",
        "B1 weight traffic reflects expected routed-expert coverage. KV values are",
        "per user and per generated token. Decimal GB/MB are used.",
        "",
        "| Model | Context | B1 active weight | KV read/user/token | KV write/user/token |",
        "|---|---:|---:|---:|---:|",
    ]
    for model in sorted({row["model"] for row in result["rows"]}):
        for context in result["contexts"]:
            row = next(
                item
                for item in result["rows"]
                if item["model"] == model
                and item["context_tokens"] == context
                and item["batch_size"] == 1
            )
            lines.append(
                f"| {model} | {context:,} | "
                f"{row['active_weight_read_bytes_per_step']/1e9:,.3f} GB | "
                f"{row['kv_read_bytes_per_user_token']/1e6:,.3f} MB | "
                f"{row['kv_write_bytes_per_user_token']/1e6:,.3f} MB |"
            )

    for key, title in (
        ("weight_to_kv_read_ratio", "Weight / KV-read ratio"),
        ("weight_to_kv_read_write_ratio", "Weight / (KV-read + write) ratio"),
    ):
        lines.extend(
            [
                "",
                f"## {title}",
                "",
                "| Model | Context | B1 | B8 | B32 | B64 |",
                "|---|---:|---:|---:|---:|---:|",
            ]
        )
        for model in sorted({row["model"] for row in result["rows"]}):
            for context in result["contexts"]:
                values = []
                for batch in result["batches"]:
                    row = next(
                        item
                        for item in result["rows"]
                        if item["model"] == model
                        and item["context_tokens"] == context
                        and item["batch_size"] == batch
                    )
                    values.append(_fmt_ratio(row[key]))
                lines.append(
                    f"| {model} | {context:,} | {' | '.join(values)} |"
                )

    lines.extend(
        [
            "",
            "## Interpretation boundary",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in result["evidence_boundary"])
    lines.extend(
        [
            "- The ratio falls with context because mutable attention/state traffic",
            "  grows, and falls with batch because GPU weight reads are amortized",
            "  while KV traffic scales per user.",
            "- ROM can exploit a large ratio only if its array, compute, NoC, power,",
            "  and package can service the corresponding bytes; those are separate",
            "  constraints in the iso-node reports.",
            "",
        ]
    )
    return "\n".join(lines)


CSV_FIELDS = (
    "model",
    "source_revision",
    "context_tokens",
    "batch_size",
    "active_weight_read_bytes_per_step",
    "routed_expert_coverage",
    "kv_read_bytes_per_user_token",
    "kv_write_bytes_per_user_token",
    "kv_read_bytes_per_step",
    "kv_total_bytes_per_step",
    "weight_to_kv_read_ratio",
    "weight_to_kv_read_write_ratio",
)


def render_csv(result: dict[str, Any]) -> str:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=CSV_FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(result["rows"])
    return output.getvalue()


def run(output_root: Path = OUTPUT_ROOT) -> dict[str, Any]:
    result = build()
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "analytical.json").write_text(
        json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    (output_root / "sweep.csv").write_text(
        render_csv(result), encoding="utf-8", newline=""
    )
    (output_root / "REPORT.md").write_text(
        render_report(result).rstrip() + "\n", encoding="utf-8"
    )
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT_ROOT)
    args = parser.parse_args(argv)
    run(args.output)
    print((args.output / "REPORT.md").resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
