#!/usr/bin/env python3
"""Measure the gap between the two ABI 3.0 contraction contracts.

Amendment A7 of ``docs/TENSOR_ACCELERATOR_ABI_3_OPERATOR_CONVENTIONS.md``
declares two contracts and says the difference between them is *measured, not
assumed*.  This tool is that measurement, and the file it writes --
``results/abi3/numeric_contract_qualification.json`` -- is the honest-disclosure
artifact any report citing "exact" execution must point at.

``bf16_bf16_fp32_sequential_rne_v1``
    Exact products, strictly ascending-K binary32 accumulation, one RNE output
    rounding.  Reproducible on any machine.  The oracle.

``bf16_bf16_fp32_blocked_rne_v1``
    Exact products, binary32 accumulation in the executing implementation's
    declared deterministic blocked association, one RNE output rounding.  The
    association is fixed by an implementation identity -- library, version,
    device and shape -- which this report records for every case.

For each representative Qwen3-8B and DeepSeek-V4-Flash contraction shape it
reports, on the binary32 accumulator and on the BF16 output separately:

* maximum absolute difference,
* maximum ULP difference,
* the fraction of elements that differ,

and, at the vocabulary head, whether the greedy argmax -- the value that
actually decides a token -- changes.  It also measures the rate of both
contracts on every available backend, because the rate is why the blocked
contract exists at all: the sequential kernel is about 112 hours per
8,000-token Qwen prefill and cannot run the mandatory workloads.

Nothing here is asserted.  Every number in the output was produced by running
both contracts on the same operands in the same process.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Any, Sequence

import numpy as np

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from runtime.abi3.capability import canonical_json  # noqa: E402
from runtime.sim import backend as backends  # noqa: E402
from runtime.sim.backend import (  # noqa: E402
    CONTRACT_BLOCKED,
    CONTRACT_SEQUENTIAL,
    BackendError,
)

DEFAULT_OUTPUT = REPO / "results/abi3/numeric_contract_qualification.json"

SCHEMA = "opentallas.abi3.numeric_contract_qualification.v1"

#: Qwen3-8B, from ``configs/models/qwen3-8b.json`` and the frozen adapter:
#: hidden 4096, intermediate 12288, 32 query heads and 8 key/value heads of
#: width 128, vocabulary 151,936, 36 layers, 8,000-token target context.
QWEN = {
    "hidden": 4096,
    "intermediate": 12288,
    "kv_width": 1024,
    "vocabulary": 151936,
    "layers": 36,
    "context": 8000,
}

#: DeepSeek-V4-Flash-0731: hidden 4096, MoE expert width 2048, vocabulary
#: 129,280, 43 layers, six routed experts per token.
DEEPSEEK = {
    "hidden": 4096,
    "expert": 2048,
    "vocabulary": 129280,
    "layers": 43,
    "experts_per_token": 6,
}


def _cases(rows: int) -> list[dict[str, Any]]:
    """Representative contraction shapes, one per distinct weight geometry."""
    return [
        {"model": "qwen3-8b", "operation": "q_proj",
         "rows": rows, "k": QWEN["hidden"], "n": QWEN["hidden"]},
        {"model": "qwen3-8b", "operation": "kv_proj",
         "rows": rows, "k": QWEN["hidden"], "n": QWEN["kv_width"]},
        {"model": "qwen3-8b", "operation": "mlp_gate_up",
         "rows": rows, "k": QWEN["hidden"], "n": QWEN["intermediate"]},
        {"model": "qwen3-8b", "operation": "mlp_down",
         "rows": rows, "k": QWEN["intermediate"], "n": QWEN["hidden"]},
        {"model": "deepseek-v4-flash-0731", "operation": "attention_project",
         "rows": rows, "k": DEEPSEEK["hidden"], "n": DEEPSEEK["hidden"]},
        {"model": "deepseek-v4-flash-0731", "operation": "expert_gate_up",
         "rows": rows, "k": DEEPSEEK["hidden"], "n": DEEPSEEK["expert"]},
        {"model": "deepseek-v4-flash-0731", "operation": "expert_down",
         "rows": rows, "k": DEEPSEEK["expert"], "n": DEEPSEEK["hidden"]},
    ]


def _vocabulary_cases() -> list[dict[str, Any]]:
    """The two vocabulary heads, where a difference can change a token."""
    return [
        {"model": "qwen3-8b", "operation": "lm_head",
         "rows": 1, "k": QWEN["hidden"], "n": QWEN["vocabulary"]},
        {"model": "deepseek-v4-flash-0731", "operation": "vocabulary_head",
         "rows": 1, "k": DEEPSEEK["hidden"], "n": DEEPSEEK["vocabulary"]},
    ]


# ---------------------------------------------------------------------------
# Operands
# ---------------------------------------------------------------------------
def _bf16_codes(values: np.ndarray) -> np.ndarray:
    """Round binary32 to the architectural BF16 codes, ties to even."""
    return backends.NumpyBackend().narrow_rne(
        np.ascontiguousarray(values, dtype=np.float32)
    ).codes


def _operands(rows: int, depth: int, cols: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
    """Deterministic BF16 operands at a realistic scale for this geometry.

    Weights are drawn at ``1/sqrt(K)`` so that the contraction's magnitude is
    order one, which is where a transformer's activations actually live.  A
    contrived scale would make the two contracts look either better or worse
    than they are.
    """
    rng = np.random.default_rng(seed)
    activations = rng.standard_normal((rows, depth)).astype(np.float32)
    weights = (
        rng.standard_normal((cols, depth)) / np.sqrt(depth)
    ).astype(np.float32)
    return _bf16_codes(activations), _bf16_codes(weights)


# ---------------------------------------------------------------------------
# Difference measures
# ---------------------------------------------------------------------------
def _monotonic(bits: np.ndarray, width: int) -> np.ndarray:
    """Map IEEE bit patterns onto a sign-monotonic integer axis.

    Adjacent representable values are then adjacent integers, so the absolute
    difference of two mapped values *is* the ULP distance -- including across
    zero and through the subnormals.
    """
    sign_bit = np.int64(1) << (width - 1)
    ordered = bits.astype(np.int64)
    return np.where(ordered & sign_bit, sign_bit - ordered, ordered)


def _difference(left: np.ndarray, right: np.ndarray, width: int) -> dict[str, Any]:
    """Compare two arrays of IEEE values of the same format."""
    if width == 32:
        bits_left = np.ascontiguousarray(left, dtype=np.float32).view(np.uint32)
        bits_right = np.ascontiguousarray(right, dtype=np.float32).view(np.uint32)
        values_left = np.ascontiguousarray(left, dtype=np.float32)
        values_right = np.ascontiguousarray(right, dtype=np.float32)
    else:
        bits_left = np.ascontiguousarray(left, dtype=np.uint16)
        bits_right = np.ascontiguousarray(right, dtype=np.uint16)
        values_left = (bits_left.astype(np.uint32) << 16).view(np.float32)
        values_right = (bits_right.astype(np.uint32) << 16).view(np.float32)
    differing = bits_left != bits_right
    count = int(np.count_nonzero(differing))
    ulp = np.abs(
        _monotonic(bits_left, width) - _monotonic(bits_right, width)
    )
    absolute = np.abs(values_left.astype(np.float64) - values_right.astype(np.float64))
    magnitude = np.maximum(
        np.abs(values_left.astype(np.float64)), np.abs(values_right.astype(np.float64))
    )
    with np.errstate(divide="ignore", invalid="ignore"):
        relative = np.where(magnitude > 0, absolute / magnitude, 0.0)
    return {
        "elements": int(bits_left.size),
        "differing_elements": count,
        "differing_fraction": count / max(int(bits_left.size), 1),
        "max_abs_diff": float(absolute.max()) if absolute.size else 0.0,
        "max_relative_diff": float(relative.max()) if relative.size else 0.0,
        "max_ulp_diff": int(ulp.max()) if ulp.size else 0,
        "mean_ulp_diff": float(ulp.mean()) if ulp.size else 0.0,
    }


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------
def _run(backend, activations: np.ndarray, weights: np.ndarray, contract: str):
    """One contraction: BF16 codes in, binary32 accumulator and BF16 out."""
    started = time.perf_counter()
    left = backend.widen_bf16(activations)
    right = backend.widen_bf16(weights)
    accumulator = backend.matmul_binary32(left, right, contract=contract)
    narrowed = backend.narrow_rne(accumulator)
    codes = np.ascontiguousarray(backend.fetch(narrowed.codes), dtype=np.uint16)
    seconds = time.perf_counter() - started
    return (
        np.ascontiguousarray(backend.fetch(accumulator), dtype=np.float32),
        codes,
        int(narrowed.saturations),
        seconds,
    )


def _rate(macs: int, seconds: float) -> float:
    return (macs / seconds) / 1e9 if seconds > 0 else 0.0


def _case_report(
    backend, case: dict[str, Any], *, seed: int, argmax: bool
) -> dict[str, Any]:
    rows, depth, cols = int(case["rows"]), int(case["k"]), int(case["n"])
    activations, weights = _operands(rows, depth, cols, seed)
    macs = rows * depth * cols

    sequential_acc, sequential_codes, sequential_sat, sequential_s = _run(
        backend, activations, weights, CONTRACT_SEQUENTIAL
    )
    blocked_acc, blocked_codes, blocked_sat, blocked_s = _run(
        backend, activations, weights, CONTRACT_BLOCKED
    )

    body: dict[str, Any] = {
        "model": case["model"],
        "operation": case["operation"],
        "shape": {"rows": rows, "k": depth, "n": cols},
        "multiply_accumulates": macs,
        "accumulator_binary32": _difference(sequential_acc, blocked_acc, 32),
        "output_bf16": _difference(sequential_codes, blocked_codes, 16),
        "output_saturations": {
            "sequential": sequential_sat,
            "blocked": blocked_sat,
        },
        "seconds": {
            "sequential": round(sequential_s, 6),
            "blocked": round(blocked_s, 6),
        },
        "gmac_per_second": {
            "sequential": round(_rate(macs, sequential_s), 4),
            "blocked": round(_rate(macs, blocked_s), 4),
        },
    }
    if argmax:
        body["argmax"] = _argmax_report(sequential_acc, blocked_acc, sequential_codes, blocked_codes)
    return body


def _argmax_report(
    sequential_acc: np.ndarray,
    blocked_acc: np.ndarray,
    sequential_codes: np.ndarray,
    blocked_codes: np.ndarray,
) -> dict[str, Any]:
    """Whether the greedy selection changes over a vocabulary-sized row.

    ``GREEDY_ARGMAX_LOWEST_ID`` breaks a tie by the lowest token ID, which is
    what ``numpy.argmax`` does, so this is the selection the device performs.
    Both the binary32 logits and the BF16 logits are checked: which one the
    selection engine sees depends on the head's output format, and a difference
    that survives the BF16 rounding is the one that can change a token.
    """
    out: dict[str, Any] = {}
    for name, left, right in (
        ("binary32_logits", sequential_acc, blocked_acc),
        (
            "bf16_logits",
            (sequential_codes.astype(np.uint32) << 16).view(np.float32),
            (blocked_codes.astype(np.uint32) << 16).view(np.float32),
        ),
    ):
        left_rows = left.reshape(left.shape[0], -1)
        right_rows = right.reshape(right.shape[0], -1)
        sequential_ids = [int(np.argmax(row)) for row in left_rows]
        blocked_ids = [int(np.argmax(row)) for row in right_rows]
        changed = [
            index
            for index, (a, b) in enumerate(zip(sequential_ids, blocked_ids))
            if a != b
        ]
        margins = []
        for row in left_rows:
            ordered = np.sort(row)[::-1]
            margins.append(float(ordered[0] - ordered[1]) if ordered.size > 1 else 0.0)
        out[name] = {
            "sequential_argmax": sequential_ids,
            "blocked_argmax": blocked_ids,
            "rows_with_changed_argmax": len(changed),
            "changed_rows": changed,
            "top_two_margin": [round(m, 8) for m in margins],
        }
    return out


def _determinism(backend, repeats: int) -> dict[str, Any]:
    """Whether repeating the blocked contract reproduces itself bit for bit."""
    activations, weights = _operands(8, 4096, 4096, seed=99)
    reference = None
    identical = True
    for _ in range(max(repeats, 2)):
        _, codes, _, _ = _run(backend, activations, weights, CONTRACT_BLOCKED)
        if reference is None:
            reference = codes
        elif not np.array_equal(reference, codes):
            identical = False
    return {
        "shape": {"rows": 8, "k": 4096, "n": 4096},
        "repeats": max(repeats, 2),
        "bit_identical": bool(identical),
        "claim": (
            "two runs of one implementation identity are bit-identical; the "
            "blocked contract makes no claim across implementations"
        ),
    }


def _throughput(names: Sequence[str], rows: int) -> dict[str, Any]:
    """Measured rate of both contracts on every requested backend."""
    shape = {"rows": rows, "k": 4096, "n": 4096}
    activations, weights = _operands(rows, 4096, 4096, seed=11)
    macs = rows * 4096 * 4096
    out: dict[str, Any] = {"shape": shape, "backends": {}}
    for name in names:
        try:
            backend = backends.get_backend(name)
        except BackendError as exc:
            out["backends"][name] = {"available": False, "reason": str(exc)}
            continue
        # One untimed pass: the first call on a device pays for its context.
        _run(backend, activations, weights, CONTRACT_BLOCKED)
        _, _, _, blocked_s = _run(backend, activations, weights, CONTRACT_BLOCKED)
        _, _, _, sequential_s = _run(backend, activations, weights, CONTRACT_SEQUENTIAL)
        out["backends"][name] = {
            "available": True,
            "implementation_identity": backend.implementation_identity(),
            "gmac_per_second": {
                "sequential": round(_rate(macs, sequential_s), 4),
                "blocked": round(_rate(macs, blocked_s), 4),
            },
            "seconds": {
                "sequential": round(sequential_s, 6),
                "blocked": round(blocked_s, 6),
            },
        }
    return out


def _prefill_projection(throughput: dict[str, Any]) -> dict[str, Any]:
    """Hours per 8,000-token Qwen prefill at each measured rate.

    Per-token contraction work is the model's active parameter count -- one
    multiply-accumulate per weight -- which for Qwen3-8B is 7.568e9, so an
    8,000-token prefill contracts 6.055e13 times.
    """
    per_token = (
        QWEN["layers"]
        * (
            QWEN["hidden"] * (2 * QWEN["hidden"] + 2 * QWEN["kv_width"])
            + 3 * QWEN["hidden"] * QWEN["intermediate"]
        )
        + QWEN["hidden"] * QWEN["vocabulary"]
    )
    total = per_token * QWEN["context"]
    body: dict[str, Any] = {
        "multiply_accumulates_per_token": per_token,
        "prefill_tokens": QWEN["context"],
        "prefill_multiply_accumulates": total,
        "backends": {},
    }
    for name, record in throughput["backends"].items():
        if not record.get("available"):
            continue
        rates = record["gmac_per_second"]
        body["backends"][name] = {
            contract: {
                "gmac_per_second": rate,
                "prefill_seconds": round(total / (rate * 1e9), 3) if rate else None,
                "prefill_hours": round(total / (rate * 1e9) / 3600, 4) if rate else None,
            }
            for contract, rate in rates.items()
        }
    return body


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--backend",
        default=None,
        help="backend to qualify on (default: the selected or default backend)",
    )
    parser.add_argument(
        "--rows",
        type=int,
        default=8,
        help="activation rows per representative case (default 8)",
    )
    parser.add_argument(
        "--repeats", type=int, default=3, help="determinism repeats (default 3)"
    )
    parser.add_argument(
        "--skip-vocabulary",
        action="store_true",
        help="skip the vocabulary heads, which dominate the runtime",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)

    backend = backends.get_backend(args.backend)
    cases = [
        _case_report(backend, case, seed=1000 + index, argmax=False)
        for index, case in enumerate(_cases(args.rows))
    ]
    if not args.skip_vocabulary:
        cases += [
            _case_report(backend, case, seed=2000 + index, argmax=True)
            for index, case in enumerate(_vocabulary_cases())
        ]
    throughput = _throughput(backends.available_backends(), args.rows)

    changed = sum(
        case.get("argmax", {}).get("bf16_logits", {}).get(
            "rows_with_changed_argmax", 0
        )
        for case in cases
    )
    body = {
        "schema": SCHEMA,
        "contract": "TA-ABI3-OPCONV-1 amendment A7",
        "generated_by": "tools/qualify_numeric_contracts.py",
        "contracts": {
            "sequential": CONTRACT_SEQUENTIAL,
            "blocked": CONTRACT_BLOCKED,
        },
        "backend": backend.name,
        "implementation_identity": backend.implementation_identity(),
        "backend_availability": backends.backend_availability(),
        "determinism": _determinism(backend, args.repeats),
        "cases": cases,
        "vocabulary_argmax_changes": changed,
        "throughput": throughput,
        "prefill_projection": _prefill_projection(throughput),
        "disclosure": (
            "The two contracts are not equal.  Every difference above was "
            "measured by running both on the same operands in this process; "
            "none is asserted to be zero.  A report that says only 'exact' "
            "does not name which contract it means and is incomplete."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_json(body))
    print(f"wrote {args.output.relative_to(REPO)}")
    print(f"  backend                  {backend.name} on {backend.device}")
    print(f"  blocked determinism      {body['determinism']['bit_identical']}")
    print(f"  vocabulary argmax changes {changed}")
    for case in cases:
        out = case["output_bf16"]
        print(
            f"  {case['model']:<26} {case['operation']:<18} "
            f"bf16 differ {out['differing_fraction']:.4%} "
            f"max {out['max_ulp_diff']} ulp  "
            f"acc max abs {case['accumulator_binary32']['max_abs_diff']:.3e}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
