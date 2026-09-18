#!/usr/bin/env python3
"""The nine topology-model cells, and what evidence each one actually has.

The standing goal is end-to-end token generation for three models
(Qwen3-8B, DeepSeek-V4-Flash, DeepSeek-V4.1-Flash) on three weight/topology
points (HBM, ROM wafer or single chip, ROM array).  The evidence for those nine
cells accumulated across many sessions into many artifacts, and no single place
said which cells were closed -- so a reader counting them got a different number
depending on which artifacts they happened to open.

This audit reads the committed artifacts, one per cell, and states for each: the
deployment and the capability it was admitted against, whether the run was at
SHIPPED or REDUCED scale, the token ids it emitted, whether those agree with the
cell's own reference oracle, and -- for a cell that is not closed -- the blocker
with the artifact that records it.

It asserts nothing of its own.  Every field is read out of an artifact a tool
wrote, and a cell whose artifact is missing or whose fields do not parse is
reported as unknown rather than assumed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "opentallas.abi3.nine_cell_token_matrix.v1"
TOOL = "tools/audit_nine_cell_token_matrix.py"

#: One entry per cell.  ``reader`` names the shape of the artifact, because the
#: artifacts were written by different tools over months and do not share one
#: schema; unifying them retroactively would mean rewriting evidence, which is
#: worse than reading each in its own shape.
CELLS: tuple[dict[str, Any], ...] = (
    {
        "model": "qwen3-8b",
        "store": "rom_single_chip",
        "topology": "SINGLE_CHIP",
        "scale": "shipped",
        "artifact": "results/abi3/accelerator_tokens/qwen3_eos_rom_e9.json",
        "reader": "accelerator_token",
    },
    {
        "model": "qwen3-8b",
        "store": "hbm_sram",
        "topology": "SINGLE_CHIP",
        "scale": "shipped",
        "artifact": "results/abi3/accelerator_tokens/qwen3_eos_hbm_e9.json",
        "reader": "accelerator_token",
    },
    {
        "model": "qwen3-8b",
        "store": "rom_array",
        "topology": "CLUSTER_N",
        "scale": "reduced",
        "artifact": "results/abi3/qwen3_reduced_array_token_walk.json",
        "reader": "qwen3_array_walk",
    },
    {
        "model": "deepseek-v4-flash-0731",
        "store": "rom_wafer",
        "topology": "WAFER_LOGICAL_DEVICE",
        "scale": "shipped",
        "artifact": "results/abi3/accelerator_tokens/deepseek_v4_flash_rom_p32.json",
        "reader": "accelerator_token",
    },
    {
        "model": "deepseek-v4-flash-0731",
        "store": "hbm_sram",
        "topology": "CLUSTER_32",
        "scale": "shipped",
        "artifact": "results/abi3/accelerator_tokens/deepseek_v4_flash_hbm_p32.json",
        "reader": "accelerator_token",
    },
    {
        "model": "deepseek-v4-flash-0731",
        "store": "rom_array",
        "topology": "CLUSTER_32",
        "scale": "shipped",
        "artifact": (
            "results/abi3/accelerator_tokens/deepseek_v4_flash_rom_array_p32_t16.json"
        ),
        "reader": "accelerator_token",
    },
    {
        "model": "deepseek-v4.1-flash",
        "store": "rom_wafer",
        "topology": "WAFER_LOGICAL_DEVICE",
        "scale": "reduced",
        "artifact": "results/abi3/deepseek_v41_reduced_token_walk.json",
        "reader": "v41_walk",
        "case": "rom_wafer",
    },
    {
        "model": "deepseek-v4.1-flash",
        "store": "hbm_sram",
        "topology": "SINGLE_CHIP",
        "scale": "reduced",
        "artifact": "results/abi3/deepseek_v41_reduced_token_walk.json",
        "reader": "v41_walk",
        "case": "hbm_single_chip",
    },
    {
        "model": "deepseek-v4.1-flash",
        "store": "rom_array",
        "topology": "CLUSTER_N",
        "scale": "reduced",
        "artifact": "results/abi3/deepseek_v41_array_placement_refusal.json",
        "reader": "refusal",
    },
)

#: Where a cell that is not closed has its blocker recorded.
BLOCKER_EVIDENCE: dict[tuple[str, str], tuple[str, ...]] = {
    ("deepseek-v4.1-flash", "rom_wafer"): (
        "results/abi3/deepseek_v41_oracle_logit_comparison.json",
        "results/abi3/deepseek_v41_oracle_depth_bisection_deep.json",
        "results/abi3/deepseek_v41_oracle_attention_split.json",
    ),
    ("deepseek-v4.1-flash", "hbm_sram"): (
        "results/abi3/deepseek_v41_oracle_logit_comparison.json",
        "results/abi3/deepseek_v41_oracle_depth_bisection_deep.json",
    ),
    ("deepseek-v4.1-flash", "rom_array"): (
        "results/abi3/deepseek_v41_array_placement_refusal.json",
    ),
}


def _git(*args: str) -> str:
    return subprocess.run(
        ("git", *args), cwd=ROOT, capture_output=True, text=True, check=False
    ).stdout.strip()


def _sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1 << 22):
            digest.update(block)
    return digest.hexdigest()


def _read_accelerator_token(body: dict[str, Any], _cell: dict[str, Any]) -> dict[str, Any]:
    oracle = body.get("oracle") or {}
    return {
        "emitted_token_ids": list(body.get("generated_token_ids") or []),
        "agrees_with_oracle": oracle.get("agreement"),
        "oracle_artifact": oracle.get("artifact"),
        "deployment": body.get("deployment") or body.get("root"),
        "target_id": body.get("target_id"),
        "token_legitimacy_problems": body.get("token_legitimacy_problems"),
    }


def _read_qwen3_array_walk(body: dict[str, Any], _cell: dict[str, Any]) -> dict[str, Any]:
    case = (body.get("cases") or {}).get("rom_array_4") or {}
    verdict = (body.get("agreement") or {}).get("rom_array_4") or {}
    return {
        "emitted_token_ids": list(case.get("emitted_token_ids") or []),
        "agrees_with_oracle": verdict.get("agrees_with_oracle"),
        "agrees_with_single_chip": verdict.get("agrees_with_single_chip"),
        "oracle_artifact": "results/abi3/qwen3_reduced_reference_oracle.json",
        "deployment": case.get("deployment"),
        "capability": case.get("capability"),
        "retired": case.get("retired"),
        "stop_reason": case.get("stop_reason"),
        "node_count": (case.get("topology") or {}).get("node_count"),
    }


def _read_v41_walk(body: dict[str, Any], cell: dict[str, Any]) -> dict[str, Any]:
    case = (body.get("cases") or {}).get(cell["case"]) or {}
    return {
        "emitted_token_ids": list(case.get("emitted_token_ids") or []),
        "agrees_with_oracle": case.get("agrees_with_oracle"),
        "oracle_artifact": "results/abi3/deepseek_v41_reduced_reference_oracle.json",
        "oracle_token_ids": list(
            ((body.get("oracle") or {}).get("generated_token_ids"))
            or ((body.get("oracle") or {}).get("expected_token_ids"))
            or []
        ),
        "deployment": (case.get("identity") or {}).get("deployment"),
        "capability": (case.get("identity") or {}).get("capability"),
        "retired": case.get("retired_work"),
        "stop_reason": case.get("stop_reason"),
        "oracle_token_rank_in_this_distribution": (
            (case.get("distribution") or {}).get("oracle_token") or {}
        ).get("rank"),
    }


def _read_refusal(body: dict[str, Any], _cell: dict[str, Any]) -> dict[str, Any]:
    return {
        "emitted_token_ids": [],
        "agrees_with_oracle": False,
        "refusal": (
            body.get("refusal")
            or body.get("message")
            or body.get("failure")
            or "recorded in the artifact"
        ),
    }


READERS = {
    "accelerator_token": _read_accelerator_token,
    "qwen3_array_walk": _read_qwen3_array_walk,
    "v41_walk": _read_v41_walk,
    "refusal": _read_refusal,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=ROOT / "results/abi3/nine_cell_token_matrix.json"
    )
    arguments = parser.parse_args(argv)

    rows: list[dict[str, Any]] = []
    for cell in CELLS:
        path = ROOT / cell["artifact"]
        row: dict[str, Any] = {
            "model": cell["model"],
            "store": cell["store"],
            "topology": cell["topology"],
            "scale": cell["scale"],
            "artifact": cell["artifact"],
            "artifact_sha256": _sha256(path),
        }
        if not path.is_file():
            row["status"] = "unknown"
            row["why"] = "the artifact this cell's evidence lives in is not present"
            rows.append(row)
            continue
        try:
            body = json.loads(path.read_text())
        except (OSError, ValueError) as exc:
            row["status"] = "unknown"
            row["why"] = f"the artifact does not parse: {exc}"
            rows.append(row)
            continue
        row.update(READERS[cell["reader"]](body, cell))
        emitted = row.get("emitted_token_ids") or []
        agrees = row.get("agrees_with_oracle")
        if emitted and agrees is True:
            row["status"] = "closed"
        elif emitted:
            row["status"] = "executes_but_disagrees"
        else:
            row["status"] = "no_token"
        blockers = BLOCKER_EVIDENCE.get((cell["model"], cell["store"]))
        if row["status"] != "closed" and blockers:
            row["blocker_evidence"] = [
                {"artifact": name, "sha256": _sha256(ROOT / name)} for name in blockers
            ]
        rows.append(row)

    counts: dict[str, int] = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    report = {
        "schema": SCHEMA,
        "producer": {"tool": TOOL, "git": {"commit": _git("rev-parse", "HEAD")}},
        "question": (
            "which of the nine topology-model cells have an end-to-end token that "
            "agrees with their own reference oracle, and what blocks the rest?"
        ),
        "status_meanings": {
            "closed": "a token was emitted and it agrees with the cell's oracle",
            "executes_but_disagrees": (
                "the program ran end to end and emitted a token, and the token "
                "does not match the oracle -- an arithmetic fault, not a stop"
            ),
            "no_token": "no token; the blocker is recorded in blocker_evidence",
            "unknown": "the artifact is absent or does not parse",
        },
        "counts": counts,
        "cells": rows,
        "not_a_claim": [
            "not an RTL measurement: every token here is from runtime.sim unless "
            "its own artifact says otherwise",
            "a SHIPPED-scale cell and a REDUCED-scale cell are not the same "
            "evidence, and the scale field says which each is; a shipped DeepSeek "
            "token costs days of simulation at the measured rate",
        ],
    }
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    width = max(len(f"{r['model']}/{r['store']}") for r in rows)
    for row in rows:
        name = f"{row['model']}/{row['store']}"
        print(
            f"{name:<{width}}  {row['scale']:<8} {row['status']:<22} "
            f"{row.get('emitted_token_ids') or []}"
        )
    print(json.dumps(counts, sort_keys=True))
    print(f"-> {arguments.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
