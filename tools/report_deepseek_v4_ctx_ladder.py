"""What the DeepSeek threshold ladder cost, and what the rungs above it would.

Both lanes run the same rungs, so the ladder is also the only apples-to-apples
DeepSeek cost measurement this repository has. It is reported on two bases,
because they answer different questions and only one of them is trustworthy
here:

* ``retired_work`` is the executed instruction work the device reports. It is
  deterministic -- the same deployment on the same prompt retires the same work
  every time -- so it extrapolates, and a fit on it is a statement about the
  program rather than about the machine that ran it.
* ``wall_seconds`` is what it actually took. These runs were executed
  **concurrently, six at a time on 32 cores**, so wall time is an upper bound
  under contention and not a clean per-run measurement. It is reported and
  labelled, never fitted alone.

The extrapolation to the 2,052-token rung is therefore stated as work (exact,
from the closed-form growth the fit recovers) times the observed
seconds-per-unit-work (contended, and stated as such). It is `derived`, not
`measured`, and the artifact says so.
"""

from __future__ import annotations

import argparse
import json
import math
import platform
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]


def _relative(path: Path) -> str:
    try:
        return str(Path(path).resolve().relative_to(REPO))
    except ValueError:
        return str(path)


def _load(path: Path) -> dict[str, Any]:
    body = json.loads(path.read_text())
    record = body.get("record", body)
    workload = record["workload"]
    steps = record.get("notes", {}).get("per_step") or []
    prefill = next((s for s in steps if s.get("phase") == "prefill"), None)
    return {
        "artifact": _relative(path),
        "status": body.get("status"),
        "backend": record.get("target", {}).get("backend"),
        "workload_id": workload["workload_id"],
        "workload_digest": workload["workload_digest"],
        "prompt_tokens": int(workload["prompt_token_count"]),
        "generated_token_ids": list(record.get("generated_token_ids") or []),
        "gold_token_ids": list(
            record.get("notes", {}).get("reference_token_ids") or []
        ),
        "reference_agreement": record.get("notes", {}).get("reference_agreement"),
        "failure": record.get("failure"),
        "retired_work": None if prefill is None else int(prefill["retired_work"]),
        "instructions_retired": (
            None if prefill is None else int(prefill["instructions_retired"])
        ),
        "prefill_wall_seconds": (
            None if prefill is None else float(prefill["wall_seconds"])
        ),
        "attention_context_positions": int(
            record.get("counters", {}).get("attention.context_positions", -1)
        ),
        "attention_kv_bytes_read": int(
            record.get("counters", {}).get("attention.kv_bytes_read", -1)
        ),
    }


def _power_fit(points: list[tuple[int, float]]) -> dict[str, Any] | None:
    """Least-squares fit of ``y = a * n**b`` in log space.

    Two points determine it exactly; three or more make the exponent a
    measurement with a residual worth reporting. Fewer than two is not a fit
    and returns None rather than a number nobody can check.
    """
    usable = [(n, y) for n, y in points if n > 0 and y and y > 0]
    if len(usable) < 2:
        return None
    xs = [math.log(n) for n, _ in usable]
    ys = [math.log(y) for _, y in usable]
    mx = sum(xs) / len(xs)
    my = sum(ys) / len(ys)
    denom = sum((x - mx) ** 2 for x in xs)
    if denom == 0:
        return None
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / denom
    a = math.exp(my - b * mx)
    residuals = [abs(a * n**b / y - 1.0) for n, y in usable]
    return {
        "form": "y = a * prompt_tokens ** b",
        "a": a,
        "b": b,
        "points": [{"prompt_tokens": n, "y": y} for n, y in usable],
        "max_relative_residual": max(residuals),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("records", type=Path, nargs="+")
    parser.add_argument(
        "--pin",
        type=Path,
        default=REPO
        / "results"
        / "abi3"
        / "deepseek_v4_context_threshold_workload_pins.json",
    )
    parser.add_argument(
        "--target-rung",
        type=int,
        default=None,
        help="prompt length to extrapolate to; default is the pinned "
        "index_topk pruning rung",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    pin = json.loads(args.pin.read_text())
    rungs = pin.get("rungs", {})
    target = args.target_rung
    if target is None:
        pruning = [
            int(r["tokens"])
            for name, r in rungs.items()
            if "prunes" in name and r.get("tokens")
        ]
        target = max(pruning) if pruning else 2052

    loaded = [_load(p) for p in args.records]
    by_lane: dict[str, list[dict]] = {}
    for entry in loaded:
        by_lane.setdefault(entry["backend"] or "unknown", []).append(entry)

    lanes: dict[str, Any] = {}
    for lane, entries in sorted(by_lane.items()):
        entries.sort(key=lambda e: e["prompt_tokens"])
        ok = [e for e in entries if e["failure"] is None and e["retired_work"]]
        work_fit = _power_fit([(e["prompt_tokens"], e["retired_work"]) for e in ok])
        wall_fit = _power_fit(
            [(e["prompt_tokens"], e["prefill_wall_seconds"]) for e in ok]
        )
        seconds_per_work = [
            {
                "prompt_tokens": e["prompt_tokens"],
                "seconds_per_million_work": (
                    e["prefill_wall_seconds"] / e["retired_work"] * 1e6
                ),
            }
            for e in ok
            if e["retired_work"] and e["prefill_wall_seconds"]
        ]
        projected_work = (
            work_fit["a"] * target ** work_fit["b"] if work_fit else None
        )
        rate = (
            max(s["seconds_per_million_work"] for s in seconds_per_work)
            if seconds_per_work
            else None
        )
        lanes[lane] = {
            "runs": entries,
            "completed_runs": len(ok),
            "retired_work_fit": work_fit,
            "prefill_wall_seconds_fit": wall_fit,
            "seconds_per_million_work_observed": seconds_per_work,
            "projection": {
                "prompt_tokens": target,
                "projected_retired_work": projected_work,
                "seconds_per_million_work_used": rate,
                "projected_prefill_seconds": (
                    projected_work / 1e6 * rate
                    if projected_work and rate
                    else None
                ),
                "basis": (
                    "retired_work extrapolated by the fitted power law, times "
                    "the slowest observed seconds-per-work of this lane's "
                    "completed runs. The runs were concurrent, so the rate is "
                    "a contended rate and the projection inherits that."
                ),
                "evidence_grade": "derived",
            },
        }

    # Cross-lane agreement. The two lanes lower the same neutral IR with the
    # same numeric profile, so for a given rung they must emit the same token
    # and must have gathered the same KV rows. A disagreement is a defect in
    # one of them, and which one is not decidable from here -- but the
    # disagreement itself is, and nothing else in this repository looks.
    cross: dict[str, Any] = {}
    for workload_id in sorted({e["workload_id"] for e in loaded}):
        rows = [e for e in loaded if e["workload_id"] == workload_id]
        done = [e for e in rows if e["failure"] is None and e["generated_token_ids"]]
        tokens = {tuple(e["generated_token_ids"]) for e in done}
        positions = {e["attention_context_positions"] for e in done}
        kv_bytes = {e["attention_kv_bytes_read"] for e in done}
        cross[workload_id] = {
            "lanes_compared": sorted(e["backend"] for e in done),
            "lane_count": len(done),
            "tokens_agree": len(tokens) <= 1,
            "attention_context_positions_agree": len(positions) <= 1,
            "attention_kv_bytes_read_agree": len(kv_bytes) <= 1,
            "tokens_by_lane": {
                e["backend"]: e["generated_token_ids"] for e in done
            },
            "attention_context_positions_by_lane": {
                e["backend"]: e["attention_context_positions"] for e in done
            },
            "comparable": len(done) > 1,
        }
    comparable = [v for v in cross.values() if v["comparable"]]
    all_lanes_agree = bool(comparable) and all(
        v["tokens_agree"]
        and v["attention_context_positions_agree"]
        and v["attention_kv_bytes_read_agree"]
        for v in comparable
    )

    body = {
        "schema": "opentallas.deepseek_v4_ctx_ladder.v1",
        "cross_lane": cross,
        "rungs_compared_on_both_lanes": len(comparable),
        "both_lanes_agree_on_every_compared_rung": all_lanes_agree,
        "evidence_class": "functional_execution_summary",
        "model_id": pin.get("model_id", ""),
        "target_rung_prompt_tokens": target,
        "concurrency_note": (
            "Every run summarised here executed concurrently with the others, "
            "six processes on 32 cores. retired_work is unaffected by that; "
            "every wall-clock number is."
        ),
        "lanes": lanes,
        "rungs_per_lane": {
            lane: sorted({e["workload_id"] for e in entries})
            for lane, entries in sorted(by_lane.items())
        },
        "lanes_ran_identical_rungs": len(
            {
                tuple(sorted({e["workload_id"] for e in entries}))
                for entries in by_lane.values()
            }
        )
        == 1
        and len(by_lane) > 1,
        "not_a_claim": [
            "uncontended_timing",
            "rtl_execution",
            "decode_phase_execution",
            "index_score_arithmetic",
        ],
        "inputs": {
            "records": [_relative(p) for p in args.records],
            "pin": _relative(args.pin),
        },
        "environment": {"python": platform.python_version(), "platform": platform.platform()},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n")
    print(f"wrote {_relative(args.output)}")
    for lane, block in sorted(lanes.items()):
        fit = block["retired_work_fit"]
        proj = block["projection"]
        print(f"  {lane}: {block['completed_runs']} completed runs")
        for run in block["runs"]:
            print(
                f"    {run['workload_id']:<18} {run['prompt_tokens']:>5} tok "
                f"work={run['retired_work']} wall={run['prefill_wall_seconds']} "
                f"agreement={run['reference_agreement']} "
                f"tokens={run['generated_token_ids']} gold={run['gold_token_ids'][:1]}"
            )
        if fit:
            print(
                f"    work ~ n**{fit['b']:.3f} (max residual "
                f"{fit['max_relative_residual']*100:.2f}%)"
            )
        if proj["projected_prefill_seconds"]:
            print(
                f"    projected {target} tokens: "
                f"{proj['projected_prefill_seconds']/3600:.1f} h (contended)"
            )
    print(f"  rungs compared on both lanes: {len(comparable)}")
    for workload_id, block in sorted(cross.items()):
        if not block["comparable"]:
            continue
        verdict = (
            "AGREE"
            if block["tokens_agree"]
            and block["attention_context_positions_agree"]
            and block["attention_kv_bytes_read_agree"]
            else "DISAGREE"
        )
        print(
            f"    {workload_id:<18} {verdict} tokens={block['tokens_by_lane']} "
            f"positions={block['attention_context_positions_by_lane']}"
        )
    if comparable and not all_lanes_agree:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
