#!/usr/bin/env python3
"""Compare the reduced V4.1 devices' logit row against the ORACLE's own row.

Two lanes emit tokens that disagree with the reference oracle, and the
disagreement had been read as one fault.  It cannot be read at all without the
oracle's own distribution, because the oracle is not an exact computation: it is
the vendor's ``inference/model.py`` Transformer in **bfloat16 on a GPU**, and
the device runs FP32-accumulate numeric contracts.  Forty layers of that
difference produce a logit perturbation of some size, and whether it can move
the argmax depends entirely on the oracle's own top-1 margin -- a number nobody
had looked at.

So this tool taps three rows at one place (the SELECTION.ARGMAX input, the last
tensor before the token is chosen, which is where the oracle's ``row`` is taken
too) and asks the only question that separates a fault from a conditioning
artifact:

*   how decisive is the oracle's own argmax -- the top-1 to top-2 gap, and how
    many of the 4,040 logits lie within the device-vs-device disagreement of
    the top?
*   how well do the rows agree AS DISTRIBUTIONS -- Pearson correlation, mean
    and max absolute difference, and the rank each side's winner holds in the
    other's order?

A large shared error with an uncorrelated row is a fault in the V4.1 graph.  A
row that tracks the oracle closely while the oracle's own margin is smaller than
the tracking error is a conditioning artifact of the reduced fixture, and the
argmax is then not a usable comparison instrument at this scale no matter how
correct the implementation is.  This tool does not decide which; it measures
both so the artifact can say.

The oracle half needs a GPU and torch; the device half is ``runtime.sim``.
Neither is an RTL measurement.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from compiler.frontend.checkpoint import (  # noqa: E402
    load_checkpoint_lock,
    verify_checkpoint_lock,
)
from runtime.abi3.capability import Capability  # noqa: E402
from runtime.abi3.constants import Major, Selection  # noqa: E402
from runtime.abi3.deployment import Deployment  # noqa: E402
from runtime.driver import GenerationDriver  # noqa: E402
from runtime.sim.device import Device  # noqa: E402
from runtime.sim.engine import _REGISTRY  # noqa: E402
from runtime.sim.engines import load_engines  # noqa: E402
import runtime.sim.engines.selection as selection_engine  # noqa: E402
from tools.build_deepseek_v41_reduced_model import (  # noqa: E402
    DEFAULT_LOCK,
    DEFAULT_SNAPSHOT,
    MODEL_ID,
    WORKLOAD_ID,
    build_model,
    import_vendor,
    released_snapshot,
)
from tools.run_deepseek_v41_reduced_reference_oracle import _load_weights  # noqa: E402

SCHEMA = "opentallas.abi3.v41_oracle_logit_comparison.v1"
TOOL = "tools/compare_deepseek_v41_oracle_logits.py"
ORACLE_RECORD = ROOT / "results/abi3/deepseek_v41_reduced_reference_oracle.json"
CHECKPOINT = ROOT / "build/models/deepseek-v4.1-flash-reduced-v1"

STORES = {
    "rom": (
        "build/abi3/deepseek-v41-reduced-rom",
        "configs/hardware/abi3_capability/rom_deepseek_v41_wafer.json",
    ),
    "hbm": (
        "build/abi3/deepseek-v41-reduced-hbm",
        "results/abi3/deepseek_v41_hbm_comparator_capability.json",
    ),
}


def _git(*args: str) -> str:
    return subprocess.run(
        ("git", *args), cwd=ROOT, capture_output=True, text=True, check=False
    ).stdout.strip()


def oracle_row(prompt: list[int]) -> np.ndarray:
    """The vendor module's step-0 logit row, in float64, from the locked bytes."""
    lock = load_checkpoint_lock(DEFAULT_LOCK)
    verify_checkpoint_lock(DEFAULT_SNAPSHOT, lock)
    body = json.loads(
        (DEFAULT_SNAPSHOT / "inference_config.json").read_text(encoding="utf-8")
    )
    import torch
    from transformers import AutoTokenizer

    released = released_snapshot()
    vendor, _engram = import_vendor(released)
    # The fixture's OWN tokenizer, not the release's.  build_deepseek_v41_reduced_model
    # writes a reduced tokenizer into the snapshot and builds the model against it,
    # because the Engram n-gram state asserts the tokenizer's vocabulary equals the
    # body's ``engram_compressed_vocab_size``; the released tokenizer describes a
    # vocabulary this vehicle does not have (99,092 against 3,402).
    tokenizer = AutoTokenizer.from_pretrained(str(DEFAULT_SNAPSHOT))
    model = build_model(vendor, body, tokenizer)
    _load_weights(model, DEFAULT_SNAPSHOT)
    model.eval()
    device = next(model.parameters()).device
    ids = torch.tensor([prompt], dtype=torch.long, device=device)
    with torch.inference_mode():
        _, logits, _ = model(ids)
    return np.asarray(logits[0].float().cpu(), dtype=np.float64).reshape(-1)


def device_row(store: str, prompt: list[int]) -> tuple[np.ndarray, list[int]]:
    """The device's step-0 SELECTION.ARGMAX input row and the token it picked."""
    deployment_dir, capability_path = STORES[store]
    body = json.loads(Path(ROOT / capability_path).read_text())
    capability = Capability.from_dict(body.get("capability", body))
    device = Device(
        Deployment.read(ROOT / deployment_dir),
        capability,
        verify=False,
        trace=False,
        root=CHECKPOINT,
    )
    grabbed: dict[str, np.ndarray] = {}
    key = (int(Major.SELECTION), int(Selection.ARGMAX))
    original = _REGISTRY[key]

    def spy(ctx, sub, descriptor):
        view = ctx.input_view(descriptor, 0)
        values = np.asarray(
            selection_engine._widen(ctx, view), dtype=np.float64
        ).reshape(-1)
        grabbed.setdefault("logits", values.copy())
        return original(ctx, sub, descriptor)

    _REGISTRY[key] = spy
    try:
        result = GenerationDriver(device).generate(prompt, max_new_tokens=1).to_dict()
    finally:
        _REGISTRY[key] = original
    return grabbed.get("logits"), [int(t) for t in result.get("generated_token_ids", [])]


def _top(row: np.ndarray, count: int = 10) -> list[dict[str, Any]]:
    order = np.argsort(-row, kind="stable")[:count]
    return [{"token_id": int(t), "logit": round(float(row[t]), 6)} for t in order]


def _pair(name: str, a: np.ndarray, b: np.ndarray) -> dict[str, Any]:
    """How two rows agree as distributions, and how each winner fares in the other."""
    difference = np.abs(a - b)
    order_a = np.argsort(-a, kind="stable")
    order_b = np.argsort(-b, kind="stable")
    win_a, win_b = int(order_a[0]), int(order_b[0])
    return {
        "pair": name,
        "pearson_r": round(float(np.corrcoef(a, b)[0, 1]), 6),
        "mean_abs_diff": round(float(difference.mean()), 6),
        "max_abs_diff": round(float(difference.max()), 6),
        "rms_diff": round(float(np.sqrt((difference**2).mean())), 6),
        "first_winner": win_a,
        "second_winner": win_b,
        "first_winner_rank_in_second": int(np.where(order_b == win_a)[0][0]),
        "second_winner_rank_in_first": int(np.where(order_a == win_b)[0][0]),
        "first_logit_at_second_winner": round(float(a[win_b]), 6),
        "second_logit_at_first_winner": round(float(b[win_a]), 6),
    }


def _decisiveness(row: np.ndarray, perturbation: float) -> dict[str, Any]:
    """Whether this row's argmax can survive a perturbation of that size."""
    order = np.argsort(-row, kind="stable")
    top, second = float(row[order[0]]), float(row[order[1]])
    margin = top - second
    within = int(np.count_nonzero(row >= top - perturbation))
    return {
        "argmax": int(order[0]),
        "top1_logit": round(top, 6),
        "top2_logit": round(second, 6),
        "top1_to_top2_margin": round(margin, 6),
        "perturbation_compared_against": round(perturbation, 6),
        "margin_over_perturbation": round(margin / perturbation, 4) if perturbation else None,
        "logits_within_perturbation_of_the_top": within,
        "argmax_survives_a_perturbation_of_that_size": bool(margin > perturbation),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "results/abi3/deepseek_v41_oracle_logit_comparison.json",
    )
    parser.add_argument("--skip-oracle", action="store_true", help="devices only")
    arguments = parser.parse_args(argv)

    record = json.loads(ORACLE_RECORD.read_text())
    case = record["results"][WORKLOAD_ID]
    prompt = [int(t) for t in case["prompt_token_ids"]]
    oracle_token = int(case["generated_token_ids"][0])

    load_engines()
    rows: dict[str, np.ndarray] = {}
    tokens: dict[str, list[int]] = {}
    for store in ("rom", "hbm"):
        row, emitted = device_row(store, prompt)
        if row is None:
            raise RuntimeError(f"the {store} store reached no SELECTION.ARGMAX")
        rows[store] = row
        tokens[store] = emitted
        print(f"{store}: token {emitted} argmax {int(np.argmax(row))}", flush=True)

    if not arguments.skip_oracle:
        rows["oracle"] = oracle_row(prompt)
        print(f"oracle: argmax {int(np.argmax(rows['oracle']))}", flush=True)
        if int(np.argmax(rows["oracle"])) != oracle_token:
            raise RuntimeError(
                f"the re-run oracle picks {int(np.argmax(rows['oracle']))} but the "
                f"record says {oracle_token}; the fixture is not reproducible"
            )

    # The device-vs-device difference is the perturbation two CORRECT lowerings
    # of one graph already produce, so it is the natural yardstick for asking
    # whether the oracle's margin is meaningful.
    store_gap = float(np.abs(rows["rom"] - rows["hbm"]).mean())
    pairs = [_pair("rom_vs_hbm", rows["rom"], rows["hbm"])]
    decisive: dict[str, Any] = {}
    for store in ("rom", "hbm"):
        decisive[store] = _decisiveness(rows[store], store_gap)
    if "oracle" in rows:
        pairs.append(_pair("oracle_vs_rom", rows["oracle"], rows["rom"]))
        pairs.append(_pair("oracle_vs_hbm", rows["oracle"], rows["hbm"]))
        oracle_gap = float(
            np.abs(rows["oracle"] - rows["rom"]).mean()
            + np.abs(rows["oracle"] - rows["hbm"]).mean()
        ) / 2.0
        decisive["oracle_against_store_gap"] = _decisiveness(rows["oracle"], store_gap)
        decisive["oracle_against_oracle_gap"] = _decisiveness(
            rows["oracle"], oracle_gap
        )

    report = {
        "schema": SCHEMA,
        "producer": {
            "tool": TOOL,
            "git": {"commit": _git("rev-parse", "HEAD")},
        },
        "question": (
            "the devices disagree with the oracle; is that a fault in the V4.1 graph "
            "or is the reduced fixture's argmax not decisive enough to be an "
            "instrument?"
        ),
        "workload": {
            "workload_id": WORKLOAD_ID,
            "model_id": MODEL_ID,
            "prompt_token_ids": prompt,
            "oracle_token_id": oracle_token,
            "vocabulary": int(rows["rom"].size),
        },
        "oracle_is_not_exact": (
            "the reference is the vendor inference/model.py Transformer in bfloat16 "
            "on a GPU; the device runs FP32-accumulate numeric contracts. The rows "
            "are not required to be equal, so the comparison that matters is "
            "distributional agreement against the oracle's own margin."
        ),
        "emitted": tokens,
        "decisiveness": decisive,
        "pairs": pairs,
        "top_10": {name: _top(row) for name, row in rows.items()},
        "logit_at_every_winner": {
            name: {
                "at_oracle_token": round(float(row[oracle_token]), 6),
                "at_rom_winner": round(float(row[int(np.argmax(rows["rom"]))]), 6),
                "at_hbm_winner": round(float(row[int(np.argmax(rows["hbm"]))]), 6),
            }
            for name, row in rows.items()
        },
        "not_a_claim": [
            "not an RTL measurement: the device here is runtime.sim",
            "correlation is not proof of correctness; it bounds how large a shared "
            "error could be, and a small margin means the argmax cannot resolve it",
        ],
    }
    body = json.dumps(report, indent=2, sort_keys=True) + "\n"
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(body, encoding="utf-8")
    print(json.dumps({"decisiveness": decisive, "pairs": pairs}, indent=2))
    print(f"-> {arguments.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
