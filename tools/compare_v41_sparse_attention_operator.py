#!/usr/bin/env python3
"""Run OUR sparse attention on the VENDOR's own operands, and compare.

The depth sweep put the reduced V4.1 divergence inside layer 0's attention core:
the query and latent-KV projection chain matches the oracle at cosine 1.0 and
``sparse_attn``'s output is the first departure at 0.947.  That localises the
fault to a span, not to a cause -- the span holds the query rotation, the window
KV, the sparse attention itself, the inverse rotation and the block-diagonal
output projection, and a tap cannot separate them because the KV the kernel reads
is built inside ``_window_kv`` and never exists as a module's output.

This tool separates the OPERATOR from its OPERANDS.  It wraps the vendor's
``sparse_attn`` to capture the five arguments of its first call exactly as the
kernel received them -- query, fused KV, per-head sinks, selected indices, and
the softmax scale -- and its output; then it runs
``runtime.reference.sparse_attention_bf16`` on those same numbers and compares.

The reading is binary and there is no third option:

*   the outputs AGREE -> our sparse-attention operator is right, and the fault is
    in what feeds it: the window KV, the index selection, or the rotation applied
    to the query.
*   the outputs DISAGREE -> the operator is wrong, and the comparison says by how
    much and in which heads, on inputs that are not in dispute.

The vendor kernel is BF16 in and BF16 out with an FP32 accumulator, which is what
the reference implements, so the two are comparable term for term rather than
approximately.  Exact equality is not expected: the vendor sums a block of 64 in
a GPU gemm's order and the reference sums in ascending order, and the sink and
the divide are the same operations in both.  The question is whether they agree to
the last few bits or differ structurally.
"""

from __future__ import annotations

import argparse
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
from runtime.reference.sparse_attention import (  # noqa: E402
    sparse_attention_bf16,
)
from tools.build_deepseek_v41_reduced_model import (  # noqa: E402
    DEFAULT_LOCK,
    DEFAULT_SNAPSHOT,
    WORKLOAD_ID,
    build_model,
    import_vendor,
    released_snapshot,
)
from tools.run_deepseek_v41_reduced_reference_oracle import _load_weights  # noqa: E402

SCHEMA = "opentallas.abi3.v41_sparse_attention_operator.v1"
TOOL = "tools/compare_v41_sparse_attention_operator.py"
ORACLE_RECORD = ROOT / "results/abi3/deepseek_v41_reduced_reference_oracle.json"


def _git(*args: str) -> str:
    return subprocess.run(
        ("git", *args), cwd=ROOT, capture_output=True, text=True, check=False
    ).stdout.strip()


def _bf16_codes(array: np.ndarray) -> np.ndarray:
    """BF16 code points of a float array, round-to-nearest-even."""
    import torch

    return (
        torch.from_numpy(np.ascontiguousarray(array, dtype=np.float32))
        .to(torch.bfloat16)
        .view(torch.uint16)
        .numpy()
        .astype(np.int64)
    )


def _binary32_codes(array: np.ndarray) -> np.ndarray:
    return np.ascontiguousarray(array, dtype=np.float32).view(np.uint32).astype(np.int64)


def _bf16_to_float(codes: np.ndarray) -> np.ndarray:
    raw = (np.asarray(codes, dtype=np.uint32) << 16).astype(np.uint32)
    return raw.view(np.float32).astype(np.float64)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "results/abi3/deepseek_v41_sparse_attention_operator.json",
    )
    parser.add_argument(
        "--snapshot", type=Path, default=None,
        help="the reduced snapshot the reference is built from (default v1)",
    )
    parser.add_argument(
        "--checkpoint-lock", type=Path, default=None,
        help="the lock that snapshot is verified against",
    )
    parser.add_argument(
        "--deployment", type=Path, default=None,
        help="override the device deployment for the compared store",
    )
    parser.add_argument(
        "--checkpoint-root", type=Path, default=None,
        help="the device's checkpoint root, which must match the deployment",
    )
    parser.add_argument(
        "--oracle", type=Path, default=None,
        help="the oracle record whose workload this uses",
    )
    parser.add_argument(
        "--expert-numeric-path", choices=("fp4", "fp8"), default="fp4",
        help="the routed-expert path the reference runs on",
    )
    parser.add_argument(
        "--phase", choices=("prefill", "decode"), default="prefill",
        help=(
            "which phase's device call to compare. The device issues two "
            "ATTENTION.SPARSE calls per layer -- the KV CONCAT declares "
            "phase_inputs {decode: [1, 2], prefill: [0, 2]} -- and the transaction "
            "boundary separates them. Capturing 'decode' is also the control that "
            "shows the gate is live"
        ),
    )
    parser.add_argument(
        "--call", type=int, default=1,
        help=(
            "which sparse_attn call to compare, 1-based. One per attention layer, "
            "so 3 is layer 2 -- the first layer whose compress_ratio is nonzero and "
            "the first in kv_source_layers"
        ),
    )
    parser.add_argument(
        "--with-device",
        action="store_true",
        help=(
            "also read the DEVICE's own ATTENTION.SPARSE operands and compare them "
            "against the vendor's, which is what says WHICH operand is wrong"
        ),
    )
    parser.add_argument(
        "--positions",
        type=int,
        default=2,
        help="how many query positions of the captured call to compare",
    )
    arguments = parser.parse_args(argv)

    record = json.loads(Path(arguments.oracle or ORACLE_RECORD).read_text())
    prompt = [int(t) for t in record["results"][WORKLOAD_ID]["prompt_token_ids"]]

    snapshot = Path(arguments.snapshot) if arguments.snapshot else DEFAULT_SNAPSHOT
    lock = load_checkpoint_lock(
        Path(arguments.checkpoint_lock) if arguments.checkpoint_lock else DEFAULT_LOCK
    )
    verify_checkpoint_lock(snapshot, lock)
    body = json.loads(
        (snapshot / "inference_config.json").read_text(encoding="utf-8")
    )
    import importlib

    import torch
    from transformers import AutoTokenizer

    released = released_snapshot()
    vendor, _engram = import_vendor(released)
    convert_mod = None
    if arguments.expert_numeric_path == "fp8":
        convert_mod = importlib.import_module("convert")
        body = dict(body)
        body["expert_dtype"] = None
    tokenizer = AutoTokenizer.from_pretrained(str(snapshot))
    model = build_model(vendor, body, tokenizer)
    _load_weights(model, snapshot, convert_mod=convert_mod)
    model.eval()

    captured: dict[str, Any] = {}
    original = vendor.sparse_attn

    seen = {"calls": 0}

    def spy(q, kv, attn_sink, topk_idxs, softmax_scale):
        out = original(q, kv, attn_sink, topk_idxs, softmax_scale)
        seen["calls"] += 1
        if seen["calls"] == want_call and not captured:
            captured.update(
                {
                    "q": q.detach().float().cpu().numpy(),
                    "kv": kv.detach().float().cpu().numpy(),
                    "sink": attn_sink.detach().float().cpu().numpy(),
                    "idx": topk_idxs.detach().cpu().numpy(),
                    "scale": float(softmax_scale),
                    "out": out.detach().float().cpu().numpy(),
                }
            )
        return out

    want_call = int(arguments.call)
    vendor.sparse_attn = spy
    try:
        device = next(model.parameters()).device
        with torch.inference_mode():
            model(torch.tensor([prompt], dtype=torch.long, device=device))
    finally:
        vendor.sparse_attn = original
    if not captured:
        raise SystemExit("the vendor forward pass made no sparse_attn call")

    q = captured["q"]        # [b, m, h, d]
    kv = captured["kv"]      # [b, n, d]
    sink = captured["sink"]  # [h]
    idx = captured["idx"]    # [b, m, topk]
    vendor_out = captured["out"]
    batch, positions, heads, head_dim = q.shape
    take = min(int(arguments.positions), positions)

    # The reference is exercised on the LAST ``take`` positions, because the last
    # one is where the token comes from and an earlier one is a control.
    rows = list(range(positions - take, positions))
    query_codes = [[
        [[int(c) for c in _bf16_codes(q[b, m, h])] for h in range(heads)]
        for m in rows
    ] for b in range(batch)]
    kv_codes = [
        [[int(c) for c in _bf16_codes(kv[b, n])] for n in range(kv.shape[1])]
        for b in range(batch)
    ]
    sink_codes = [int(c) for c in _binary32_codes(sink)]
    selected = [[
        [int(v) for v in idx[b, m]] for m in rows
    ] for b in range(batch)]
    scale_code = int(_binary32_codes(np.asarray([captured["scale"]]))[0])

    result = sparse_attention_bf16(
        query_codes,
        kv_codes,
        sink_codes,
        selected,
        scale_binary32=scale_code,
    )
    ours = np.asarray(
        [[[_bf16_to_float(np.asarray(head)) for head in row] for row in batch_rows]
         for batch_rows in result.values],
        dtype=np.float64,
    )
    theirs = np.asarray(
        [[[vendor_out[b, m, h] for h in range(heads)] for m in rows]
         for b in range(batch)],
        dtype=np.float64,
    )

    difference = np.abs(ours - theirs)
    flat_ours = ours.reshape(-1)
    flat_theirs = theirs.reshape(-1)
    norm = float(np.linalg.norm(flat_ours) * np.linalg.norm(flat_theirs))
    cosine = float(flat_ours @ flat_theirs / norm) if norm else None
    per_head = []
    for h in range(heads):
        a = ours[:, :, h, :].reshape(-1)
        b = theirs[:, :, h, :].reshape(-1)
        scale = float(np.linalg.norm(a) * np.linalg.norm(b))
        per_head.append({
            "head": h,
            "cosine": round(float(a @ b / scale), 6) if scale else None,
            "max_abs_diff": round(float(np.abs(a - b).max()), 8),
            "ours_norm": round(float(np.linalg.norm(a)), 8),
            "theirs_norm": round(float(np.linalg.norm(b)), 8),
        })
    worst = sorted(
        (h for h in per_head if h["cosine"] is not None), key=lambda h: h["cosine"]
    )[:8]

    agrees = bool(cosine is not None and cosine > 0.9999)
    # -- the operands themselves, from the device ---------------------------
    #
    # If the operator agrees, the fault is in what feeds it, and the three things
    # that feed it are exactly the three views ATTENTION.SPARSE reads.  So they
    # are read off the device and compared against the vendor's own, which names
    # the wrong one instead of narrowing to a span.
    operands: dict[str, Any] | None = None
    if arguments.with_device:
        from runtime.abi3.capability import Capability
        from runtime.abi3.constants import Attention, Major
        from runtime.abi3.deployment import Deployment
        from runtime.driver import GenerationDriver
        from runtime.sim import formats
        from runtime.sim.device import Device
        from runtime.sim.engine import _REGISTRY
        from runtime.sim.engines import load_engines

        load_engines()
        capability_path = ROOT / "configs/hardware/abi3_capability/rom_deepseek_v41_wafer.json"
        body_c = json.loads(capability_path.read_text())
        capability = Capability.from_dict(body_c.get("capability", body_c))
        device_obj = Device(
            Deployment.read(ROOT / "build/abi3/deepseek-v41-reduced-rom"),
            capability,
            verify=False,
            trace=False,
            root=ROOT / "build/models/deepseek-v4.1-flash-reduced-v1",
        )
        grabbed: dict[str, Any] = {}
        closed = {"prefill_done": False}
        key = (int(Major.ATTENTION), int(Attention.SPARSE))
        original_engine = _REGISTRY[key]

        device_calls = {"n": 0}
        # ADDRESSING A LAYER ON THE DEVICE BY CALL INDEX DOES NOT WORK, and the
        # probe reported three uncorrelated operands twice before that was clear:
        # the device issues attention per token block as well as per layer, so its
        # Nth call is not layer N-1.  The reliable selector is a STRUCTURAL
        # signature of the layer -- the number of live (non-padding) index slots,
        # which is the window alone at compress_ratio 0 and the window plus the
        # compressed prefix above it: 8 at layers 0 and 1 of this vehicle, 12 at
        # layer 2.  So the device call compared is the first whose live index count
        # matches the vendor's operand length.
        want_live = int(idx.shape[-1])

        def attention_spy(ctx, sub, descriptor):
            device_calls["n"] += 1
            live = None
            if not grabbed:
                try:
                    probe = ctx.input_view(descriptor, 2)
                    codes = np.ascontiguousarray(ctx.read(probe)).view(np.int32)
                    row = codes.reshape(probe.dims)
                    row = row[-1] if row.ndim > 1 else row
                    live = int((row >= 0).sum())
                except Exception:
                    live = None
            in_phase = (
                closed["prefill_done"]
                if arguments.phase == "decode"
                else not closed["prefill_done"]
            )
            if live == want_live and not grabbed and in_phase:
                for slot in range(3):
                    view = ctx.input_view(descriptor, slot)
                    codes = ctx.read(view)
                    try:
                        values = np.asarray(
                            formats.widen(view.dtype, codes), dtype=np.float64
                        )
                    except Exception:
                        # The index operand is an integer view and has no
                        # binary32 widening; its codes ARE its values, and a
                        # signed padding index has to survive the read, so it is
                        # reinterpreted as int32 rather than as unsigned.
                        values = np.asarray(
                            np.ascontiguousarray(codes).view(np.int32), dtype=np.float64
                        )
                    grabbed[f"slot{slot}"] = {
                        "dims": [int(d) for d in view.dims],
                        "dtype": int(view.dtype),
                        "values": values.reshape(-1).copy(),
                    }
            result = original_engine(ctx, sub, descriptor)
            if grabbed and "output" not in grabbed:
                # The OUTPUT of the same call, which is what settles a disagreement
                # between the operand probe and the depth sweep: if the output
                # matches while the operands appear not to, the operand slicing is
                # wrong; if the output differs too, the operands really do.
                try:
                    out_view = ctx.output_view(descriptor, 0)
                    out = np.asarray(
                        formats.widen(out_view.dtype, ctx.read(out_view)),
                        dtype=np.float64,
                    )
                    grabbed["output"] = {
                        "dims": [int(d) for d in out_view.dims],
                        "values": out.reshape(-1).copy(),
                    }
                except Exception:
                    pass
            return result

        _REGISTRY[key] = attention_spy
        # PHASE, not just position.  The device issues two ATTENTION.SPARSE calls per
        # layer -- the KV CONCAT declares phase_inputs {decode: [1, 2], prefill:
        # [0, 2]} -- and identical indices prove only that two calls are at the same
        # POSITION, since both phases of a position select the same rows.  The
        # transaction boundary is what separates them: the driver submits prefill
        # first, so capture is closed at the end of the first submission.
        driver = GenerationDriver(device_obj)
        submit = device_obj.execute_submission
        phase = {"transactions": 0}

        def phased(request):
            try:
                return submit(request)
            finally:
                phase["transactions"] += 1
                if phase["transactions"] >= 1:
                    # After prefill closes, stop accepting captures.
                    closed["prefill_done"] = True

        device_obj.execute_submission = phased
        try:
            driver.generate(prompt, max_new_tokens=1)
        finally:
            _REGISTRY[key] = original_engine
            device_obj.execute_submission = submit

        def compare(name: str, mine: np.ndarray, vendor_values: np.ndarray) -> dict[str, Any]:
            a = np.asarray(mine, dtype=np.float64).reshape(-1)
            b = np.asarray(vendor_values, dtype=np.float64).reshape(-1)
            row = {
                "operand": name,
                "device_elements": int(a.size),
                "vendor_elements": int(b.size),
            }
            if a.size != b.size:
                row["comparable"] = False
                row["why"] = "the device holds this operand in a different shape"
                return row
            scale = float(np.linalg.norm(a) * np.linalg.norm(b))
            row.update({
                "comparable": True,
                "cosine": round(float(a @ b / scale), 8) if scale else None,
                "max_abs_diff": round(float(np.abs(a - b).max()), 8),
                "mean_abs_diff": round(float(np.abs(a - b).mean()), 8),
                "identical": bool(np.array_equal(a, b)),
            })
            return row

        last = positions - 1
        rows_out = []
        if "slot0" in grabbed:
            # The device's views are the DECLARED maxima -- all prompt positions,
            # the whole window capacity, every top-k slot -- and they are padded
            # rather than shortened: the index row holds the valid rows then the
            # padding index, and the unused KV rows are zero.  So the comparison
            # slices the device's operand down to the vendor's live extent instead
            # of calling a shape difference a disagreement.
            def slot(name: str) -> np.ndarray:
                entry = grabbed[name]
                return np.asarray(entry["values"]).reshape(entry["dims"])

            device_q = slot("slot0")
            device_kv = slot("slot1")
            device_idx = slot("slot2")
            live = int(kv.shape[1])
            topk = int(idx.shape[2])
            rows_out.append(
                compare(
                    "query_after_rotation",
                    device_q[last] if device_q.ndim == 3 else device_q,
                    q[0, last],
                )
            )
            rows_out.append(
                compare("fused_kv_window", device_kv[:live], kv[0])
            )
            rows_out.append(
                compare("selected_indices", device_idx[last][:topk], idx[0, last])
            )
            padding = device_idx[last][topk:]
            rows_out.append({
                "operand": "index_padding_beyond_the_live_extent",
                "slots": int(padding.size),
                "all_padding_index": bool(np.all(padding == -1)),
                "distinct": sorted({int(v) for v in padding.tolist()})[:4],
            })
            # IS THE JOINED KV A PERMUTATION OF THE VENDOR'S?
            #
            # The indices are bit-identical while the KV values are not, and those
            # two facts together have one obvious explanation: the device's joined
            # operand holds the same rows in a different ORDER, so an identical
            # index selects a different row.  Layer 2 is the first layer that joins
            # anything -- window rows plus a compressed prefix -- so the join's row
            # order is exactly what becomes testable here.
            vendor_rows = np.asarray(kv[0], dtype=np.float64)
            # Search the WHOLE fused view, not its first ``live`` rows.  The device's
            # joined operand is a CONCAT of the window capacity and the compressed
            # prefix, so a vendor row can sit anywhere in it; restricting the search
            # to the first twelve slots reported "0 of 12 matched" when the rows may
            # simply have been further along.
            device_rows = np.asarray(device_kv, dtype=np.float64)
            permutation: list[int | None] = []
            residuals: list[float] = []
            for row in vendor_rows:
                norms = np.linalg.norm(device_rows - row, axis=1)
                best = int(np.argmin(norms))
                permutation.append(best if float(norms[best]) < 1e-6 else None)
                residuals.append(float(norms[best]))
            matched = [value for value in permutation if value is not None]
            rows_out.append({
                "operand": "joined_kv_row_order",
                "device_rows_searched": int(device_rows.shape[0]),
                "vendor_rows": int(vendor_rows.shape[0]),
                "rows_matched_exactly": len(matched),
                "is_a_permutation": len(matched) == vendor_rows.shape[0]
                and len(set(matched)) == len(matched),
                "vendor_row_to_device_row": permutation,
                "identity_order": permutation == list(range(vendor_rows.shape[0])),
                "worst_unmatched_residual": max(residuals) if residuals else None,
            })
            if "output" in grabbed:
                entry = grabbed["output"]
                device_out = np.asarray(entry["values"]).reshape(entry["dims"])
                slice_out = (
                    device_out[last] if device_out.ndim == 3 else device_out
                )
                rows_out.append(
                    compare("attention_output", slice_out, vendor_out[0, last])
                )
                rows_out.append({
                    "operand": "device_output_view_dims",
                    "dims": entry["dims"],
                })
            unused = device_kv[live:]
            rows_out.append({
                "operand": "kv_rows_beyond_the_live_extent",
                "rows": int(unused.shape[0]),
                "all_zero": bool(np.all(unused == 0.0)),
            })
        operands = {
            "what_this_settles": (
                "the operator agrees on the vendor's operands, so the wrong operand "
                "is the fault; these are the device's own three views against the "
                "vendor's own three arguments"
            ),
            "device_view_shapes": {
                name: grabbed[name]["dims"] for name in sorted(grabbed)
            },
            "comparisons": rows_out,
            "first_disagreeing_operand": next(
                (
                    r["operand"]
                    for r in rows_out
                    if r.get("comparable") and not r.get("identical")
                ),
                None,
            ),
        }

    report = {
        "schema": SCHEMA,
        "producer": {"tool": TOOL, "git": {"commit": _git("rev-parse", "HEAD")}},
        "question": (
            "given the vendor kernel's OWN operands, does our sparse-attention "
            "operator produce the vendor's output?"
        ),
        "captured_call": {
            "which": (
                f"sparse_attn call {arguments.call} of the forward pass, which is "
                f"attention layer {arguments.call - 1}"
            ),
            "query_shape": list(q.shape),
            "kv_shape": list(kv.shape),
            "sink_shape": list(sink.shape),
            "index_shape": list(idx.shape),
            "softmax_scale": captured["scale"],
            "softmax_scale_binary32": scale_code,
            "positions_compared": rows,
        },
        "verdict": "OPERATOR_AGREES" if agrees else "OPERATOR_DISAGREES",
        "reading": (
            "our operator reproduces the vendor kernel on its own operands, so the "
            "fault is upstream: the window KV, the index selection, or the query "
            "rotation"
            if agrees
            else "our operator does NOT reproduce the vendor kernel on operands "
            "that are not in dispute, so the fault is in the operator"
        ),
        "whole_tensor": {
            "cosine": round(cosine, 8) if cosine is not None else None,
            "max_abs_diff": round(float(difference.max()), 8),
            "mean_abs_diff": round(float(difference.mean()), 8),
            "elements": int(difference.size),
        },
        "worst_heads": worst,
        "operands": operands,
        "per_head": per_head,
        "not_a_claim": [
            "exact equality is not expected: the vendor sums a 64-row block in a "
            "GPU gemm's order and the reference sums in ascending order",
            "this is the reference operator, not the RTL and not the simulator's "
            "engine; they share this reference's contract",
        ],
    }
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "verdict": report["verdict"],
        "whole_tensor": report["whole_tensor"],
        "worst_heads": worst[:4],
    }, indent=1))
    print(f"-> {arguments.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
