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
    CONTRACT_DEEPSEEK_RMSNORM,
    CONTRACT_QWEN_RMSNORM,
    CONTRACT_SEQUENTIAL,
    BackendError,
)
from runtime.sim.engines.vector import deepseek_rms_norm_binary32  # noqa: E402
from runtime.tensor_accelerator.rmsnorm import (  # noqa: E402
    EPSILON_CODE,
    rms_norm_bf16 as qwen_rms_norm_bf16,
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
#: Elements generated per block.  A vocabulary head is 622 million elements and
#: the rounding pipeline holds several temporaries of that size, so a whole-array
#: conversion would need tens of gigabytes of host memory to produce operands
#: that are then contracted a block at a time anyway.
_GENERATION_BLOCK = 1 << 23


def _bf16_codes(values: np.ndarray) -> np.ndarray:
    """Round binary32 to the architectural BF16 codes, ties to even."""
    return backends.NumpyBackend().narrow_rne(
        np.ascontiguousarray(values, dtype=np.float32)
    ).codes


def _bf16_normal(
    shape: tuple[int, int], scale: float, seed: int
) -> np.ndarray:
    """Deterministic normal BF16 operands of ``shape``, generated in blocks."""
    rng = np.random.default_rng(seed)
    rows, cols = int(shape[0]), int(shape[1])
    out = np.empty(rows * cols, dtype=np.uint16)
    for start in range(0, out.size, _GENERATION_BLOCK):
        span = min(_GENERATION_BLOCK, out.size - start)
        block = rng.standard_normal(span, dtype=np.float32) * np.float32(scale)
        out[start : start + span] = _bf16_codes(block.reshape(1, span))[0]
    return out.reshape(rows, cols)


def _operands(rows: int, depth: int, cols: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
    """Deterministic BF16 operands at a realistic scale for this geometry.

    Weights are drawn at ``1/sqrt(K)`` so that the contraction's magnitude is
    order one, which is where a transformer's activations actually live.  A
    contrived scale would make the two contracts look either better or worse
    than they are.
    """
    activations = _bf16_normal((rows, depth), 1.0, seed)
    weights = _bf16_normal((cols, depth), 1.0 / float(np.sqrt(depth)), seed + 1)
    return activations, weights


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


def _rmsnorm_report(rows: int) -> dict[str, Any]:
    """Measure the gap between the two RMSNorm contracts (amendment A8).

    They are the same computation apart from one BF16 materialisation: the Qwen
    contract rounds the normalised value to BF16 *before* the gain multiply, the
    DeepSeek contract stays in binary32 through it and rounds once.  That is a
    double rounding, so the two disagree by at most one ulp -- but on a
    substantial fraction of elements, which is why they carry different names
    and why the engine dispatches on the contract digest rather than picking
    one.  The fraction is measured here, not quoted.
    """
    cases = []
    for label, width in (
        ("qwen3-8b hidden", 4096),
        ("qwen3-8b head_dim", 128),
        ("deepseek-v4 hidden", 4096),
        ("deepseek-v4 head_dim", 128),
    ):
        values = _bf16_normal((rows, width), 1.0, seed=5100 + width)
        gains = _bf16_normal((1, width), 0.5, seed=5200 + width)[0]
        qwen = qwen_rms_norm_bf16(values, gains, epsilon_code=EPSILON_CODE).values
        deepseek, _ = deepseek_rms_norm_binary32(
            values, gains, epsilon_bits=EPSILON_CODE
        )
        cases.append(
            {
                "label": label,
                "shape": {"rows": rows, "width": width},
                "difference": _difference(qwen, deepseek, 16),
            }
        )
    return {
        "contracts": {
            "qwen": CONTRACT_QWEN_RMSNORM,
            "deepseek": CONTRACT_DEEPSEEK_RMSNORM,
        },
        "difference_is": (
            "one BF16 materialisation of the normalised value before the gain "
            "multiply; a double rounding, so at most one ulp per element"
        ),
        "cases": cases,
    }


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


def _contraction_only(backend, activations, weights, contract: str) -> float:
    """Seconds for the contraction alone, operands already on the device.

    The end-to-end figure includes widening the weights and rounding the
    result, which at decode shapes is most of the work and none of the
    arithmetic.  Both are reported because both are true and they answer
    different questions: this one is the rate a resident-weight machine would
    see, the end-to-end one is the rate this simulator actually achieves while
    streaming weights.
    """
    left = backend.widen_bf16(activations)
    right = backend.widen_bf16(weights)
    backend.fetch(backend.matmul_binary32(left, right, contract=contract))
    started = time.perf_counter()
    result = backend.matmul_binary32(left, right, contract=contract)
    backend.fetch(result)
    return time.perf_counter() - started


def _throughput(names: Sequence[str], rows: int) -> dict[str, Any]:
    """Measured rate of both contracts on every requested backend."""
    shape = {"rows": rows, "k": 4096, "n": 4096}
    activations, weights = _operands(rows, 4096, 4096, seed=11)
    macs = rows * 4096 * 4096
    out: dict[str, Any] = {
        "shape": shape,
        "note": (
            "end_to_end times widen -> contract -> round -> fetch, which is "
            "what the engine performs; contraction_only times the contraction "
            "with both operands already resident"
        ),
        "backends": {},
    }
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
        blocked_only = _contraction_only(backend, activations, weights, CONTRACT_BLOCKED)
        sequential_only = _contraction_only(
            backend, activations, weights, CONTRACT_SEQUENTIAL
        )
        out["backends"][name] = {
            "available": True,
            "implementation_identity": backend.implementation_identity(),
            "gmac_per_second": {
                "sequential": round(_rate(macs, sequential_s), 4),
                "blocked": round(_rate(macs, blocked_s), 4),
            },
            "contraction_only_gmac_per_second": {
                "sequential": round(_rate(macs, sequential_only), 4),
                "blocked": round(_rate(macs, blocked_only), 4),
            },
            "seconds": {
                "sequential": round(sequential_s, 6),
                "blocked": round(blocked_s, 6),
                "sequential_contraction_only": round(sequential_only, 6),
                "blocked_contraction_only": round(blocked_only, 6),
            },
        }
    return out


#: One Qwen3-8B decoder layer's contractions, as ``(name, K, N)``.
QWEN_LAYER_CONTRACTIONS = (
    ("q_proj", QWEN["hidden"], QWEN["hidden"]),
    ("k_proj", QWEN["hidden"], QWEN["kv_width"]),
    ("v_proj", QWEN["hidden"], QWEN["kv_width"]),
    ("o_proj", QWEN["hidden"], QWEN["hidden"]),
    ("gate_proj", QWEN["hidden"], QWEN["intermediate"]),
    ("up_proj", QWEN["hidden"], QWEN["intermediate"]),
    ("down_proj", QWEN["intermediate"], QWEN["hidden"]),
)


def _bf16_buffer(shape: tuple[int, int], scale: float, seed: int) -> np.ndarray:
    """A BF16 code buffer of ``shape`` at a realistic magnitude, built fast.

    A vocabulary head is 622 million elements; drawing that many normal
    variates would dominate a *throughput* measurement with host random-number
    generation, which is not what is being measured.  A pool of one million
    draws is tiled instead.  The bytes moved, the shapes contracted and the
    exponent range are those of a real weight; only the values repeat, and no
    numeric claim is made from this buffer.
    """
    rng = np.random.default_rng(seed)
    pool = _bf16_codes(
        (rng.standard_normal(1 << 20, dtype=np.float32) * np.float32(scale)).reshape(
            1, 1 << 20
        )
    )[0]
    return np.resize(pool, shape[0] * shape[1]).reshape(shape)


def _forward_contractions(
    backend, *, tokens: int, row_tile: int, contract: str
) -> dict[str, Any]:
    """Time every contraction of one Qwen3-8B forward pass, for real.

    This is a measurement, not a projection.  It runs all 36 layers' seven
    projections plus the vocabulary head at the true shapes, moving a weight of
    the true size across the bus for every one of them, and reports the wall
    time.  One host buffer per weight *geometry* is reused across layers: the
    bytes streamed and the arithmetic performed are exactly those of the real
    sequence, and operand generation stays out of the timed region.

    Each weight is placed on the device once and every row tile of the
    activation is contracted against it before the next weight arrives.  That
    is the order a streaming implementation must use -- the alternative
    re-uploads the whole 15 GB per tile -- and it is why ``row_tile`` matters
    for prefill and not for decode.
    """
    geometries = sorted({(depth, cols) for _n, depth, cols in QWEN_LAYER_CONTRACTIONS})
    weights = {
        (depth, cols): _bf16_buffer((cols, depth), 1.0 / np.sqrt(depth), 7000 + index)
        for index, (depth, cols) in enumerate(geometries)
    }
    activations = {
        depth: _bf16_buffer((min(tokens, row_tile), depth), 1.0, 8000 + depth)
        for depth, _cols in geometries
    }
    head_weights = _bf16_buffer(
        (QWEN["vocabulary"], QWEN["hidden"]),
        1.0 / np.sqrt(QWEN["hidden"]),
        9001,
    )
    head_activation = _bf16_buffer((1, QWEN["hidden"]), 1.0, 9002)

    macs = 0
    weight_bytes = 0
    started = time.perf_counter()
    for _layer in range(QWEN["layers"]):
        for _name, depth, cols in QWEN_LAYER_CONTRACTIONS:
            weight = weights[(depth, cols)]
            weight_bytes += weight.nbytes
            right = backend.widen_bf16(weight)
            rows = activations[depth]
            for start_row in range(0, tokens, row_tile):
                span = min(row_tile, tokens - start_row)
                left = backend.widen_bf16(rows[:span])
                out = backend.matmul_binary32(left, right, contract=contract)
                backend.fetch(backend.narrow_rne(out).codes)
                macs += span * depth * cols
            del right
    # The vocabulary head runs on the sampled position only, which is what a
    # prefill actually needs: the logits of the token being selected.
    weight_bytes += head_weights.nbytes
    out = backend.matmul_binary32(
        backend.widen_bf16(head_activation),
        backend.widen_bf16(head_weights),
        contract=contract,
    )
    backend.fetch(backend.narrow_rne(out).codes)
    macs += QWEN["hidden"] * QWEN["vocabulary"]
    seconds = time.perf_counter() - started
    return {
        "tokens": tokens,
        "row_tile": row_tile,
        "contract": contract,
        "layers": QWEN["layers"],
        "multiply_accumulates": macs,
        "weight_bytes_streamed": weight_bytes,
        "seconds": round(seconds, 4),
        "gmac_per_second": round(_rate(macs, seconds), 4),
        "weight_stream_gigabytes_per_second": round(weight_bytes / seconds / 1e9, 4),
        "measured": True,
    }


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
    def projected(rate: float) -> dict[str, Any]:
        if not rate:
            return {"gmac_per_second": rate, "prefill_seconds": None,
                    "prefill_hours": None}
        seconds = total / (rate * 1e9)
        return {
            "gmac_per_second": rate,
            "prefill_seconds": round(seconds, 3),
            "prefill_hours": round(seconds / 3600, 4),
        }

    for name, record in throughput["backends"].items():
        if not record.get("available"):
            continue
        body["backends"][name] = {
            "end_to_end": {
                contract: projected(rate)
                for contract, rate in record["gmac_per_second"].items()
            },
            "contraction_only": {
                contract: projected(rate)
                for contract, rate in record[
                    "contraction_only_gmac_per_second"
                ].items()
            },
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
    parser.add_argument(
        "--forward-tokens",
        type=int,
        default=0,
        help=(
            "measure every contraction of a real Qwen3-8B forward pass at this "
            "token count (0 skips it; 8000 is the mandatory prefill)"
        ),
    )
    parser.add_argument(
        "--row-tile",
        type=int,
        default=1024,
        help="activation rows contracted per weight residency (default 1024)",
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
    forward: dict[str, Any] = {}
    if args.forward_tokens:
        forward["decode_one_token"] = _forward_contractions(
            backend, tokens=1, row_tile=1, contract=CONTRACT_BLOCKED
        )
        forward["prefill"] = _forward_contractions(
            backend,
            tokens=int(args.forward_tokens),
            row_tile=int(args.row_tile),
            contract=CONTRACT_BLOCKED,
        )

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
        "rmsnorm_contracts": _rmsnorm_report(max(args.rows, 8)),
        "cases": cases,
        "vocabulary_argmax_changes": changed,
        "throughput": throughput,
        "prefill_projection": _prefill_projection(throughput),
        "measured_forward_contractions": forward,
        "disclosure": (
            "The two contracts are not equal.  Every difference above was "
            "measured by running both on the same operands in this process; "
            "none is asserted to be zero.  A report that says only 'exact' "
            "does not name which contract it means and is incomplete."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_json(body))
    try:
        printable = args.output.resolve().relative_to(REPO)
    except ValueError:
        printable = args.output
    print(f"wrote {printable}")
    print(f"  backend                  {backend.name} on {backend.device}")
    print(f"  blocked determinism      {body['determinism']['bit_identical']}")
    print(f"  vocabulary argmax changes {changed}")
    for case in body["rmsnorm_contracts"]["cases"]:
        gap = case["difference"]
        print(
            f"  rmsnorm {case['label']:<22} differ {gap['differing_fraction']:.2%} "
            f"max {gap['max_ulp_diff']} ulp"
        )
    for name, record in forward.items():
        print(
            f"  {name:<24} {record['seconds']:.3f} s  "
            f"{record['gmac_per_second']:.1f} GMAC/s  "
            f"{record['weight_stream_gigabytes_per_second']:.2f} GB/s of weights"
        )
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
