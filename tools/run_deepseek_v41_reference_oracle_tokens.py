#!/usr/bin/env python3
"""Produce DeepSeek-V4.1-Flash gold tokens in the shape a graded run consumes.

``runtime/reference/deepseek_v41_oracle.py`` already emits shipped-scale tokens,
and ``results/abi3/deepseek_v41_shipped_reference_oracle_tokens.json`` records a
run of it.  That record cannot grade an accelerator cell, for one structural
reason: ``tools/run_accelerator_tokens.py`` selects gold by workload id **and**
requires the gold to carry the ``workload_digest`` it was produced against,
because the failure it exists to refuse is a comparison between two different
prompts.  The existing record carries a workload id and no digest, and it was
written by a session script.

So this is the committed producer.  One workload document in, one artifact out,
in the same schema ``results/abi3/deepseek_v4_reference_oracle_prefix.json``
uses, with every field a grading run checks:

* ``results[workload_id].workload_digest`` -- read out of the workload document
  itself, so a gold can never be quoted against a prompt it did not run;
* ``results[workload_id].expert_numeric_path`` -- ``fp8``, the vendor's own
  documented recast, which is what the shipped V4-Flash oracle also records and
  what V4.1's unverified FP4 GEMM makes mandatory rather than convenient;
* ``tokenizer_sha256`` -- the committed inventory's value, so the workload and
  the gold are bound to one tokenizer.

Usage::

    PATH=/usr/local/cuda/bin:$PATH PYTHONPATH=. python3 \\
        tools/run_deepseek_v41_reference_oracle_tokens.py \\
        --workload build/workloads/deepseek-v4.1-flash/TA-DS41-CHAT-1-P32.json \\
        --output results/abi3/deepseek_v41_reference_oracle_prefix.json

The CUDA prefix is not decoration: the system ``nvcc`` does not know ``sm_120a``
and the GPU is ``sm_120``, so the vendor's TileLang kernels do not compile
without CUDA 12.8 ahead of it on PATH.

NOT AN ACCELERATOR TOKEN.  This is the external comparator over the vendor's own
pinned modelling code (ADR-003 section 18).  It never supplies a value to the
device; the only values a graded run writes into the device are the workload's
own prompt token ids.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
import time
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

SCHEMA = "opentallas.abi3.deepseek_v41_reference_oracle_prefix.v1"
MODEL_ID = "deepseek-v4.1-flash"
#: The vendor's documented recast.  V4.1's ``kernel.fp8_gemm`` asserts a
#: different expert-scale shape than V4's, so the FP4 path is unverified on this
#: GPU and reporting it as verified would be the one thing ADR-003 section 14
#: forbids.
EXPERT_NUMERIC_PATH = "fp8"
DEFAULT_SNAPSHOT = Path(
    "/home/ubuntu/.cache/huggingface/hub/"
    "models--deepseek-ai--DeepSeek-V4.1-Flash/snapshots/"
    "dba1be0a40aa45a94ad051997016db3960a90277"
)


def _tokenizer_digest() -> str:
    from compiler.frontend.deepseek_v41_tokenizer import (  # noqa: PLC0415
        TOKENIZER_SHA256,
    )

    return str(TOKENIZER_SHA256)


def _environment() -> dict[str, Any]:
    import torch  # noqa: PLC0415

    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "torch": torch.__version__,
        "torch_cuda": torch.version.cuda,
        "cuda_available": bool(torch.cuda.is_available()),
        "device_name": (
            torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--workload",
        type=Path,
        action="append",
        required=True,
        help="a pinned V4.1 workload document; repeat for several",
    )
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument(
        "--max-new-tokens",
        type=int,
        default=0,
        help="override the workload's own max_new_tokens (0 = use the workload's)",
    )
    parser.add_argument("--max-seq-len", type=int, default=256)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    from compiler.frontend.deepseek_v41_tokenizer import (  # noqa: PLC0415
        load_verified_deepseek_v41_tokenizer,
    )
    from runtime.reference.deepseek_v4_oracle import OracleConfig  # noqa: PLC0415
    from runtime.reference.deepseek_v41_oracle import (  # noqa: PLC0415
        StreamingDeepSeekV41,
        verify_v41_vendor_sources,
    )

    verified = load_verified_deepseek_v41_tokenizer(args.snapshot)
    backend = getattr(verified, "backend", None) or getattr(verified, "_backend", None)
    vendor = verify_v41_vendor_sources(args.snapshot)

    started = time.time()
    config = OracleConfig(
        snapshot=args.snapshot,
        max_seq_len=args.max_seq_len,
        device=args.device,
        verbose=True,
    )
    engine = StreamingDeepSeekV41(config, tokenizer_backend=backend)
    endpoints = engine.load_endpoints()
    setup_seconds = round(time.time() - started, 3)

    results: dict[str, Any] = {}
    for path in args.workload:
        workload = json.loads(path.read_text())
        ids = workload.get("token_ids") or workload.get("prompt_token_ids")
        if not ids:
            raise SystemExit(f"workload {path} carries no prompt token ids")
        wanted = int(args.max_new_tokens or workload.get("max_new_tokens") or 1)
        eos = (workload.get("official_eos_token_ids") or [1])[0]
        started = time.time()
        out = engine.greedy_generate(
            list(ids),
            max_new_tokens=wanted,
            eos_token_id=int(eos),
            progress=lambda i, n, s: print(
                f"  token {i}/{n} {s:.1f}s", flush=True
            ),
        )
        results[str(workload["workload_id"])] = {
            # Every field below is what a grading run checks, and the digest is
            # read out of the workload document rather than restated here.
            "workload_digest": str(workload["digest"]),
            "expert_numeric_path": EXPERT_NUMERIC_PATH,
            "generated_token_ids": [int(t) for t in out["generated_token_ids"]],
            "generated_token_count": len(out["generated_token_ids"]),
            "stop_reason": out.get("stop_reason"),
            "prompt_token_count": len(ids),
            "max_new_tokens": wanted,
            "wall_seconds": round(time.time() - started, 3),
            "vendor_sample_agreements": out.get("vendor_agreements"),
            "vendor_sample_disagreements": out.get("vendor_disagreements"),
            "selection": (
                "greedy argmax over the float32 logits, ties to the lowest token id"
            ),
        }

    report = {
        "schema": SCHEMA,
        "model_id": MODEL_ID,
        "evidence_class": "external_reference_comparator",
        "expert_numeric_path": EXPERT_NUMERIC_PATH,
        "tokenizer_sha256": _tokenizer_digest(),
        "snapshot": str(args.snapshot),
        "vendor_source_sha256": vendor,
        "engine": (
            "runtime/reference/deepseek_v41_oracle.py::StreamingDeepSeekV41"
        ),
        "load_endpoints": endpoints,
        "setup_seconds": setup_seconds,
        "initial_max_seq_len": int(args.max_seq_len),
        "environment": _environment(),
        "results": results,
        "not_a_claim": [
            "not an accelerator token and not a cell: this is the external "
            "comparator over the vendor's own pinned code",
            "the expert path is the vendor's documented FP8 recast; V4.1's FP4 "
            "GEMM is unverified on this GPU and is not claimed here",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    for workload_id, row in sorted(results.items()):
        print(f"{workload_id}: {row['generated_token_ids']} ({row['stop_reason']})")
    print(f"-> {args.output}")
    print(f"   sha256 {hashlib.sha256(args.output.read_bytes()).hexdigest()[:24]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
