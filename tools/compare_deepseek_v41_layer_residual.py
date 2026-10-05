#!/usr/bin/env python3
"""The device's residual against the ORACLE's, layer by layer, paired by name.

results/abi3/deepseek_v41_device_oracle_engram_depth.json measured the two taps the
Engram makes unambiguous -- layer 1 at one BF16 ulp and layer 14 at 3.75%, 11.2x
over thirteen layers -- and said plainly what it could not settle: which layer
between them introduces it, "because the engram gives two unambiguous taps and
there is no third until layer 14, so narrowing further needs a shape-aware
per-operator comparison rather than the best-cosine matching the earlier bisection
used".

THIS NEEDS NO MATCHING. The vendor's Block does ``x = self.hc_pre(x, pre_mix)``
and then ``x = self.attn_norm(x)``, and the device's IR names a kernel
``main.layerNN.attention.norm`` whose input is
``main.layerNN.hyper_connection.attention.collapsed``. Those are the same tensor.
So a forward PRE-hook on every ``layers[n].attn_norm`` and ``layers[n].ffn_norm``
gives the oracle's side in order, the device probe gives its side in issue order,
and tap 2k pairs with layer k's attention norm by construction rather than by
similarity.

WHAT THE SHAPE OF THE ANSWER MEANS. A single operator computing the wrong function
shows as a STEP: agreement to some layer and a collapse at the next. Accumulated
rounding shows as a RAMP whose per-layer growth factor is roughly constant. The
report prints the growth factor between consecutive taps for exactly that reason,
and names the largest single jump.

THE TAP POSITION IS NOT FREE. The shipped comparator reproduces itself only at
prompt positions 0-7 (results/abi3/deepseek_v41_oracle_nondeterminism.json), so a
comparison outside that range has a noise floor larger than the effect. Default 7.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

SCHEMA = "opentallas.abi3.deepseek_v41_layer_residual_agreement.v1"
DEFAULT_SNAPSHOT = Path(
    "/home/ubuntu/.cache/huggingface/hub/models--deepseek-ai--DeepSeek-V4.1-Flash/"
    "snapshots/dba1be0a40aa45a94ad051997016db3960a90277"
)


def _stats(device_row: np.ndarray, oracle_row: np.ndarray) -> dict[str, Any]:
    difference = np.abs(device_row - oracle_row)
    peak = float(np.abs(oracle_row).max())
    denominator = float(np.linalg.norm(device_row) * np.linalg.norm(oracle_row))
    return {
        "cosine": (
            float(np.dot(device_row, oracle_row) / denominator) if denominator else None
        ),
        "max_abs_diff": float(difference.max()),
        "peak_abs_value": peak,
        "relative": float(difference.max() / peak) if peak else None,
        "elements_that_differ": int((difference > 0).sum()),
        "elements": int(device_row.size),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument(
        "--workload",
        type=Path,
        default=REPO / "build/workloads/deepseek-v4.1-flash-prefix/TA-DS41-CHAT-1-P10.json",
    )
    parser.add_argument(
        "--device-taps",
        type=Path,
        required=True,
        help="output of tools/probe_deepseek_v41_device_layer_residual.py",
    )
    parser.add_argument("--max-seq-len", type=int, default=256)
    parser.add_argument("--torch-device", default="cuda")
    parser.add_argument(
        "--tap-position",
        type=int,
        default=7,
        help="prompt position the rows are read at; the comparator reproduces "
        "itself only at 0-7",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    taps = json.loads(args.device_taps.read_text())
    device_rows = [np.asarray(t["rows"], dtype=np.float64) for t in taps["taps"]]
    if not device_rows:
        raise SystemExit("the device tap file holds no taps")

    from compiler.frontend.deepseek_v41_tokenizer import (  # noqa: PLC0415
        load_verified_deepseek_v41_tokenizer,
    )
    from runtime.reference.deepseek_v4_oracle import OracleConfig  # noqa: PLC0415
    from runtime.reference.deepseek_v41_oracle import (  # noqa: PLC0415
        StreamingDeepSeekV41,
    )
    import torch  # noqa: PLC0415

    verified = load_verified_deepseek_v41_tokenizer(args.snapshot)
    backend = getattr(verified, "backend", None) or getattr(verified, "_backend", None)
    engine = StreamingDeepSeekV41(
        OracleConfig(
            snapshot=args.snapshot,
            max_seq_len=args.max_seq_len,
            device=args.torch_device,
            verbose=False,
        ),
        tokenizer_backend=backend,
    )
    engine.load_endpoints()

    captured: dict[str, np.ndarray] = {}
    handles = []

    def pre_hook(label: str):
        def hook(_module, inputs):  # noqa: ANN001
            if not inputs or not hasattr(inputs[0], "detach"):
                return None
            rows = np.asarray(inputs[0].detach().float().cpu(), dtype=np.float64)
            captured.setdefault(label, rows.reshape(-1, rows.shape[-1]))
            return None

        return hook

    layers = list(engine.model.layers)
    for index, layer in enumerate(layers):
        for which in ("attn_norm", "ffn_norm"):
            module = getattr(layer, which, None)
            if module is None:
                continue
            handles.append(
                module.register_forward_pre_hook(pre_hook(f"L{index:02d}.{which}"))
            )

    workload = json.loads(args.workload.read_text())
    prompt = [int(t) for t in workload["token_ids"]]
    #: One forward over the prompt, exactly as tools/probe_deepseek_v41_engram_live.py
    #: drives it: the taps are prefill intermediates and no token is generated.
    with torch.inference_mode():
        engine.forward(
            torch.tensor([prompt], dtype=torch.long, device=args.torch_device), 0
        )
    for handle in handles:
        handle.remove()

    #: Tap 2k is layer k's attention norm, tap 2k+1 its FFN norm: the device
    #: issues them in that order and so does the vendor's forward.
    order = [
        f"L{index:02d}.{which}"
        for index in range(len(layers))
        for which in ("attn_norm", "ffn_norm")
    ]
    position = args.tap_position

    rows: list[dict[str, Any]] = []
    previous_relative: float | None = None
    for tap_index, device_tap in enumerate(device_rows):
        if tap_index >= len(order):
            break
        label = order[tap_index]
        oracle_tap = captured.get(label)
        entry: dict[str, Any] = {"tap": tap_index, "oracle_checkpoint": label}
        if oracle_tap is None:
            entry["matched"] = False
            rows.append(entry)
            continue
        if position >= device_tap.shape[0] or position >= oracle_tap.shape[0]:
            entry["matched"] = False
            entry["note"] = (
                f"tap position {position} outside device rows "
                f"{device_tap.shape[0]} or oracle rows {oracle_tap.shape[0]}"
            )
            rows.append(entry)
            continue
        entry["matched"] = True
        entry.update(_stats(device_tap[position], oracle_tap[position]))
        if previous_relative and entry.get("relative"):
            entry["growth_over_previous_tap"] = round(
                entry["relative"] / previous_relative, 3
            )
        previous_relative = entry.get("relative") or previous_relative
        rows.append(entry)

    graded = [r for r in rows if r.get("matched") and r.get("relative") is not None]
    jump = (
        max(graded, key=lambda r: r.get("growth_over_previous_tap") or 0)
        if graded
        else None
    )
    report = {
        "schema": SCHEMA,
        "question": (
            "the device and the comparator differ by one BF16 ulp at layer 1 and "
            "3.75% at layer 14; is there a layer between them where a single "
            "operator departs, or is the shape a ramp?"
        ),
        "tap_position": position,
        "prompt_token_count": len(prompt),
        "device_taps": str(args.device_taps),
        "device_tap_count": len(device_rows),
        "oracle_checkpoints_captured": len(captured),
        "taps": rows,
        "largest_single_jump": (
            {
                "tap": jump["tap"],
                "oracle_checkpoint": jump["oracle_checkpoint"],
                "growth_over_previous_tap": jump.get("growth_over_previous_tap"),
                "relative": jump.get("relative"),
            }
            if jump
            else None
        ),
        "not_a_claim": [
            "this is runtime.sim, not RTL",
            "a high cosine is necessary for a correct intermediate and not "
            "sufficient",
            "the comparator reproduces itself only at prompt positions 0-7, so a "
            "tap position outside that range measures its noise and not the device",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")

    print(f"{len(graded)} taps graded at prompt position {position}")
    for entry in rows:
        if not entry.get("matched"):
            print(f"  tap {entry['tap']:3d} {entry['oracle_checkpoint']:16} unmatched")
            continue
        print(
            f"  tap {entry['tap']:3d} {entry['oracle_checkpoint']:16} "
            f"cos {entry['cosine']:.10f}  rel {entry['relative']:.6%}  "
            f"max|d| {entry['max_abs_diff']:.6g}  "
            f"growth {entry.get('growth_over_previous_tap', '-')}"
        )
    print(f"-> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
