#!/usr/bin/env python3
"""Produce and validate accelerator tokens from a committed, repeatable path.

One neutral Kernel IR v3 graph, one backend, one capability, one pinned
workload, one external reference oracle.  The tool lowers, admits, executes
prefill and decode on the functional device, compares every generated token
against the oracle's gold for the *same* workload, and writes one canonical
JSON artifact.

Why this exists rather than the ad-hoc scripts that produced the first tokens
=============================================================================

``results/abi3/accelerator_tokens/README.md`` records the first DeepSeek ROM
token as **raw, not graded**, because a session scratchpad produced it.  That is
not pedantry.  The scratchpad driver compared its token against
``TA-DS-CHAT-1``'s gold while executing ``TA-DS-CHAT-1-P32``'s prompt, wrote
``matches_gold_prefix: false`` into its own artifact, and the claim it supports
survived only because a human compared the right two lists by hand afterwards.

So this tool refuses, rather than reports, the mistakes that made that possible:

* the oracle result is selected by workload id **and** its ``workload_digest``
  must equal the workload's own digest -- comparing a run against gold produced
  for a different prompt is refused, not recorded as a mismatch;
* the oracle's ``expert_numeric_path`` must equal ``--expert-numeric-path``, so
  a gold produced through a numeric path the run does not use cannot be quoted
  as agreement (DeepSeek's shipped path is ``fp8``);
* admission is mandatory and has no override flag;
* the checkpoint root and the publish root are separate arguments (OI-18: the
  campaign tool used one path for both and wrote deployments into the user's
  Hugging Face cache);
* an empty token list never compares equal to anything.

The oracle is an external comparator only (ADR-003 section 18).  Nothing it
holds reaches the device: the only values this tool writes into the device are
the workload's own prompt token ids.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

# The blocked GEMM association is part of the numeric implementation identity.
# Establish the governed default before any runtime module imports NumPy; an
# explicit caller setting remains authoritative and is recorded in the result.
for _thread_variable in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
):
    os.environ.setdefault(_thread_variable, "8")

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from runtime.abi3.capability import Capability, canonical_json, digest_of  # noqa: E402
from runtime.abi3.deployment import Deployment  # noqa: E402
from runtime.abi3.verifier import verify_deployment  # noqa: E402
from runtime.driver import GenerationDriver, validate_token_ids  # noqa: E402
from runtime.evidence import check_token_legitimacy  # noqa: E402
from runtime.abi3.constants import DType  # noqa: E402
from runtime.sim.backend import get_backend  # noqa: E402
from runtime.sim.device import Device  # noqa: E402
from runtime.sim.engines import load_engines  # noqa: E402
from runtime.sim.formats import widen  # noqa: E402

SCHEMA = "opentallas.abi3.accelerator_tokens.v1"
EXECUTION_TIMING_SCHEMA = "opentallas.abi3.execution_token_commit_timing.v1"
TERMINAL_CONTRACTS = (
    "oracle_prefix",
    "exact_eos_or_cap",
    "exact_cap",
)

#: Storage formats whose codes are not their values.  An integer view -- a
#: token id, an index -- is already its value and must not be widened.
_WIDENABLE = frozenset(
    int(d)
    for d in (
        DType.BF16,
        DType.FP16,
        DType.FP32,
        DType.FP8_E4M3FN,
        DType.MXFP4_E2M1,
        DType.E8M0_SCALE,
    )
)

#: Backend name -> "module:function" producing a Deployment.  The same three
#: names ``tools/run_abi3_campaign.py`` uses, so a lane cannot be run here under
#: a name that means something else there.
BACKENDS = {
    "hbm_sram": "compiler.backends.hbm_sram.lower:lower_to_abi3",
    "rom_qwen3": "compiler.backends.rom.qwen3:lower_to_abi3",
    "rom_deepseek_v4": "compiler.backends.rom.deepseek_v4:lower_to_abi3",
    "rom_deepseek_v4_array": "compiler.backends.rom.deepseek_v4_array:lower_to_abi3",
}

# Sources shared by every governed token capture.  This is intentionally a
# dependency boundary, not merely the files under ``runtime/sim/engines``:
# compiler lowering, ABI decoding/admission, the host driver and the numeric
# helpers all determine the token that is eventually recorded.
FUNCTIONAL_SOURCE_PATHS = (
    "compiler/backends/numeric_contracts.py",
    "compiler/ir/v3/kernel_ir.py",
    "compiler/ir/v3/lowering.py",
    "compiler/ir/v3/numeric.py",
    "runtime/abi3/builder.py",
    "runtime/abi3/capability.py",
    "runtime/abi3/constants.py",
    "runtime/abi3/crc.py",
    "runtime/abi3/deployment.py",
    "runtime/abi3/descriptors.py",
    "runtime/abi3/layout.py",
    "runtime/abi3/records.py",
    "runtime/abi3/verifier.py",
    "runtime/driver.py",
    "runtime/evidence.py",
    "runtime/reference/compression_pool.py",
    "runtime/reference/formats.py",
    "runtime/reference/hadamard.py",
    "runtime/reference/hyper_connection.py",
    "runtime/reference/normalization.py",
    "runtime/reference/quantization.py",
    "runtime/reference/sparse_attention.py",
    "runtime/reference/sqrt_softplus.py",
    "runtime/reference/swiglu.py",
    "runtime/reference/transcendental.py",
    "runtime/sim/backend.py",
    "runtime/sim/counters.py",
    "runtime/sim/device.py",
    "runtime/sim/engine.py",
    "runtime/sim/formats.py",
    "runtime/sim/generators.py",
    "runtime/sim/memory.py",
    "runtime/sim/performance.py",
    "runtime/sim/weight_cache.py",
    "runtime/tensor_accelerator/attention.py",
    "runtime/tensor_accelerator/bf16.py",
    "runtime/tensor_accelerator/elementwise.py",
    "runtime/tensor_accelerator/rmsnorm.py",
    "runtime/tensor_accelerator/rope.py",
    "runtime/tensor_accelerator/sparse_attention.py",
)

BACKEND_FUNCTIONAL_SOURCE_PATHS = {
    "hbm_sram": (
        "compiler/backends/hbm_sram/lower.py",
        "compiler/backends/hbm_sram/plan.py",
    ),
    "rom_qwen3": (
        "compiler/backends/rom/qwen3.py",
        "compiler/backends/rom/common/image.py",
        "compiler/backends/rom/common/program.py",
    ),
    "rom_deepseek_v4": (
        "compiler/backends/rom/deepseek_v4.py",
        "compiler/backends/rom/common/image.py",
        "compiler/backends/rom/common/program.py",
    ),
    "rom_deepseek_v4_array": (
        "compiler/backends/rom/deepseek_v4_array.py",
        "compiler/backends/rom/deepseek_v4.py",
        "compiler/backends/rom/common/image.py",
        "compiler/backends/rom/common/program.py",
    ),
}


def _resolve(spec: str):
    module_name, _, attribute = spec.partition(":")
    return getattr(importlib.import_module(module_name), attribute)


class HeadTrace:
    """Summaries of every head operation's destination, per decode step.

    The head is the part of the graph after the last layer: the final
    hyper-connection, the final norm, the last-token select, the vocabulary
    projection, the temperature scale, the argmax and the token append.  It is
    where a divergence becomes a token, so when two lanes disagree this is the
    first place to look -- and it is what the ROM lane's raw capture recorded,
    so recording it here keeps the two lanes' evidence comparable.

    A summary, never the tensor: ``n``, distinct values, min, max and argmax.
    """

    def __init__(self, graph: Any) -> None:
        layered = [k.index for k in graph.kernels if k.layer is not None]
        cut = max(layered) if layered else -1
        self.head = {
            k.index: (k.kernel_id, k.kind)
            for k in graph.kernels
            if k.index > cut and k.layer is None
        }
        self.rows: list[dict[str, Any]] = []
        self._first = min(self.head) if self.head else None
        self._step = -1

    def __call__(self, pc: int, instruction: Any, family: int, ctx: Any) -> None:
        import numpy as np

        descriptor_id = instruction.descriptor_id
        try:
            operator = ctx.operator(descriptor_id)
        except Exception:  # not an operator instruction; nothing to summarise
            return
        source = int(operator.payload.get("source_kernel_id", -1))
        named = self.head.get(source)
        if named is None:
            return
        # The head runs once per transaction, so its first operation is what
        # separates one step's summaries from the next.  Counting the driver's
        # progress callback instead would mis-tag them: it fires after a decode
        # step, and never after prefill.
        if source == self._first:
            self._step += 1
        try:
            view = ctx.output_view(operator, 0)
            raw = np.asarray(ctx.read(view))
            # A BF16 or FP8 view reads back as storage *codes*, not values.
            # Summarising those directly reports a bit pattern as a magnitude
            # and, worse, an argmax that ranks by sign bit -- the most negative
            # element comes out as the largest.  Widen first, and say which
            # format was widened.
            dtype = int(view.dtype)
            values = widen(dtype, raw) if dtype in _WIDENABLE else raw
        except Exception as exc:  # a summary must never fail a run
            self.rows.append(
                {
                    "step": self._step,
                    "kernel_id": named[0],
                    "kind": named[1],
                    "unreadable": f"{type(exc).__name__}: {exc}",
                }
            )
            return
        flat = np.asarray(values).reshape(-1)
        if flat.size == 0:
            return
        numeric = flat.astype("float64", copy=False)
        self.rows.append(
            {
                "step": self._step,
                "kernel_id": named[0],
                "kind": named[1],
                "dtype": DType(dtype).name,
                "size": int(flat.size),
                "unique": int(np.unique(flat).size),
                "min": float(numeric.min()),
                "max": float(numeric.max()),
                "argmax": int(numeric.argmax()),
            }
        )


def _load_gold(path: Path, workload: dict[str, Any], expert_path: str) -> dict[str, Any]:
    """The oracle result for exactly this workload, or a refusal."""
    body = json.loads(path.read_text())
    results = body.get("results", {})
    workload_id = workload["workload_id"]
    if workload_id not in results:
        raise SystemExit(
            f"reference {path} holds no result for {workload_id!r}; it has "
            f"{sorted(results)}"
        )
    gold = results[workload_id]
    stated = gold.get("workload_digest")
    if stated != workload["digest"]:
        raise SystemExit(
            f"reference {path} produced {workload_id!r} against workload digest "
            f"{stated!r}, not {workload['digest']!r}; the comparison would be "
            "between two different prompts"
        )
    if expert_path:
        actual = gold.get("expert_numeric_path", body.get("expert_numeric_path"))
        if actual != expert_path:
            raise SystemExit(
                f"reference {path} ran {workload_id!r} through the "
                f"{actual!r} expert numeric path, not {expert_path!r}; a gold "
                "produced through a different numeric path is not this run's "
                "comparator"
            )
    return gold


def _compare(got: list[int], gold: list[int]) -> dict[str, Any]:
    """Prefix agreement, and the first index at which the two disagree.

    A run stopped by its token cap is a prefix of the oracle's sequence, so the
    comparison is against ``gold[:len(got)]``.  Both sides must be non-empty:
    two empty lists compare equal and reporting that as agreement is a vacuous
    pass this repository has produced once already.
    """
    divergence = next(
        (i for i, (a, b) in enumerate(zip(got, gold)) if a != b), None
    )
    body: dict[str, Any] = {
        "compared_tokens": min(len(got), len(gold)),
        "oracle_token_count": len(gold),
        "agreement": bool(got) and bool(gold) and got == gold[: len(got)],
        "first_divergence_index": divergence,
    }
    if divergence is not None:
        body["divergence"] = {
            "index": divergence,
            "accelerator_token_id": got[divergence],
            "oracle_token_id": gold[divergence],
        }
    return body


def _terminal_acceptance(
    *,
    contract: str,
    got: list[int],
    gold: list[int],
    stop_reason: str,
    gold_stop_reason: str,
    limit: int,
    eos_token_ids: list[int],
    per_step: list[dict[str, Any]],
) -> dict[str, Any]:
    """Assess the complete terminal sequence, not merely an oracle prefix.

    ``oracle_prefix`` preserves the short diagnostic behavior existing callers
    use.  W10 uses one of the two strict contracts: natural generation closes
    at the same first official EOS or the exact declared cap, while the stress
    fixture closes only at its separately frozen cap.
    """

    if contract not in TERMINAL_CONTRACTS:
        raise ValueError(f"unknown terminal contract {contract!r}")
    eos = {int(token) for token in eos_token_ids}
    comparison = _compare(got, gold)
    checks: dict[str, bool] = {
        "nonempty_sequences": bool(got) and bool(gold),
        "oracle_token_identity": bool(comparison["agreement"]),
    }
    if contract == "oracle_prefix":
        checks["prefix_contract_selected"] = True
        return {
            "contract": contract,
            "accepted": all(checks.values()),
            "checks": checks,
            "failed_checks": [name for name, value in checks.items() if not value],
        }

    checks.update(
        {
            "declared_limit_positive": limit > 0,
            "accelerator_within_limit": 0 < len(got) <= limit,
            "per_step_count_exact": len(per_step) == len(got),
            "per_step_tokens_exact": len(per_step) == len(got)
            and all(
                step.get("step") == index
                and step.get("produced_tokens") == [got[index]]
                and step.get("final_token_id") == got[index]
                for index, step in enumerate(per_step)
            ),
            "per_step_success": len(per_step) == len(got)
            and all(
                step.get("status") == "SUCCESS" and step.get("trap") == "NONE"
                for step in per_step
            ),
            "transaction_ids_strictly_increasing": len(per_step) == len(got)
            and all(
                isinstance(step.get("transaction_id"), int)
                for step in per_step
            )
            and all(
                per_step[index - 1]["transaction_id"]
                < per_step[index]["transaction_id"]
                for index in range(1, len(per_step))
            ),
        }
    )

    accelerator_eos = stop_reason == "eos"
    accelerator_cap = stop_reason == "max_new_tokens"
    eos_terminal = (
        contract == "exact_eos_or_cap"
        and accelerator_eos
        and bool(got)
        and got[-1] in eos
        and not any(token in eos for token in got[:-1])
        and gold_stop_reason == "eos"
        and len(gold) == len(got)
        and gold[-1] == got[-1]
    )
    cap_terminal = (
        accelerator_cap
        and len(got) == limit
        and len(gold) == limit
        and gold_stop_reason == "max_new_tokens"
        and not any(token in eos for token in got)
    )
    checks.update(
        {
            "terminal_reason_allowed": eos_terminal or cap_terminal,
            "no_post_eos_transaction": not any(token in eos for token in got[:-1])
            and (not accelerator_eos or (bool(got) and got[-1] in eos)),
            "oracle_horizon_exact": len(gold) == len(got),
        }
    )
    return {
        "contract": contract,
        "accepted": all(checks.values()),
        "terminal_kind": "eos" if eos_terminal else ("cap" if cap_terminal else None),
        "checks": checks,
        "failed_checks": [name for name, value in checks.items() if not value],
    }


def _counter_evidence(device: Device) -> dict[str, Any]:
    """Publish cluster totals beside the simulator's measured per-node split.

    ``Device.counters`` is intentionally a cluster total.  Dividing it by the
    topology size is not a per-node measurement because LINK, STATE, and host
    bookkeeping run once for the cluster.  The device already keeps the engine
    work split by ``NODE_ID``; retain that evidence so consumers can compare a
    logical model to every node without guessing from a target name or a
    capability maximum.
    """

    per_node = [
        dict(sorted(counters.snapshot().items()))
        for counters in device.node_counters
    ]
    if len(per_node) != device.node_count:
        raise RuntimeError(
            f"device exposes {len(per_node)} node counter sets for "
            f"node_count={device.node_count}"
        )
    return {
        "counter_scope": {
            "aggregate": "cluster_total",
            "per_node": "engine_work_by_node_id",
            "node_count": device.node_count,
            "node_counters_index": "NODE_ID",
            "reconciliation": (
                "cluster total equals the sum of per-node engine work plus "
                "cluster-only LINK, STATE, control, and host bookkeeping"
            ),
        },
        "node_counters": per_node,
    }


def _execution_timing_evidence(result: Any) -> dict[str, Any]:
    """Retain the ABI completion ticks from this exact token execution.

    This record intentionally makes no clock-frequency or TPOT claim.  It is
    only the raw causal event binding: the request-start device counter and the
    ``completion_timestamp`` decoded from every successful token-producing ABI
    completion.  A later timing artifact may characterize those ticks, but it
    must reproduce this exact timeline before the TPOT checker will use it.
    """

    problems: list[str] = []
    start = result.request_start_tick
    if not isinstance(start, int) or isinstance(start, bool) or start < 0:
        problems.append("fresh request-start tick is unavailable")

    commits: list[int] = []
    steps = result.per_step if isinstance(result.per_step, list) else []
    generated = list(result.generated_token_ids)
    if len(steps) != len(generated):
        problems.append("per-step count differs from the generated-token count")
    for index, step in enumerate(steps):
        tick = step.get("completion_timestamp") if isinstance(step, dict) else None
        if not isinstance(tick, int) or isinstance(tick, bool) or tick < 1:
            problems.append(f"per_step[{index}] has no positive completion tick")
            continue
        commits.append(tick)
    if len(commits) != len(generated):
        problems.append("token-commit tick count differs from generated tokens")
    if commits and isinstance(start, int) and commits[0] <= start:
        problems.append("first token commit is not after request start")
    if any(right <= left for left, right in zip(commits, commits[1:])):
        problems.append("token-commit ticks are not strictly increasing")

    return {
        "schema": EXECUTION_TIMING_SCHEMA,
        "unit": "cycles",
        "clock_domain": "abi3_device_cycle_counter",
        "request_start_tick": start,
        "request_start_source": "driver_counter_before_fresh_prefill_submission",
        "token_commit_ticks": commits,
        "token_commit_source": "decoded_abi3_completion.completion_timestamp",
        "token_commits_from_execution": not problems,
        "problems": problems,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kernel-ir", type=Path, required=True)
    parser.add_argument("--backend", choices=sorted(BACKENDS), required=True)
    parser.add_argument("--capability", type=Path, required=True)
    parser.add_argument("--workload", type=Path, required=True)
    parser.add_argument(
        "--reference",
        type=Path,
        required=True,
        help=(
            "external reference-oracle file holding this workload's gold token "
            "ids.  Required: executing without crashing is not evidence of a "
            "correct token."
        ),
    )
    parser.add_argument(
        "--checkpoint",
        type=Path,
        required=True,
        help=(
            "read-only root the deployment's relative weight paths resolve "
            "against -- the model snapshot.  Never written to."
        ),
    )
    parser.add_argument(
        "--publish",
        type=Path,
        default=None,
        help=(
            "directory to publish the deployment into and read it back from.  "
            "Separate from --checkpoint on purpose (OI-18)."
        ),
    )
    parser.add_argument(
        "--expert-numeric-path",
        default="",
        help=(
            "the model's own shipped expert format the gold must have used, "
            "e.g. fp8 for DeepSeek-V4-Flash.  Empty skips the check."
        ),
    )
    parser.add_argument("--max-new-tokens", type=int, default=None)
    parser.add_argument(
        "--decoded-weight-cache-bytes",
        type=int,
        default=0,
        help=(
            "one central host-byte ceiling across every logical node; zero "
            "keeps the required cache-off baseline"
        ),
    )
    parser.add_argument(
        "--decoded-weight-cache-working-reserve-bytes",
        type=int,
        default=64 << 20,
        help=(
            "bytes held out of the central ceiling for one uncached "
            "contraction; ignored when the cache ceiling is zero"
        ),
    )
    parser.add_argument(
        "--terminal-contract",
        choices=TERMINAL_CONTRACTS,
        default="oracle_prefix",
        help=(
            "oracle_prefix preserves diagnostic prefix comparison; W10 natural "
            "uses exact_eos_or_cap and W10 stress uses exact_cap"
        ),
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--no-head-trace",
        action="store_true",
        help="skip the per-step head-operation summaries",
    )
    args = parser.parse_args()

    if args.output.exists() and not args.force:
        print(f"refusing to overwrite {args.output}; pass --force", file=sys.stderr)
        return 1
    if (
        args.publish is not None
        and (args.publish.exists() or args.publish.is_symlink())
        and not args.force
    ):
        print(
            f"refusing to overwrite deployment root {args.publish}; pass --force",
            file=sys.stderr,
        )
        return 1
    if not args.checkpoint.is_dir():
        raise SystemExit(f"checkpoint root {args.checkpoint} is not a directory")
    if args.decoded_weight_cache_bytes < 0:
        raise SystemExit("--decoded-weight-cache-bytes must be non-negative")
    if args.decoded_weight_cache_working_reserve_bytes < 0:
        raise SystemExit(
            "--decoded-weight-cache-working-reserve-bytes must be non-negative"
        )

    # Capture the identities before the long lowering/execution phase.  These
    # are the files this process is about to load, rather than hashes collected
    # only after a multi-hour run has finished.
    functional_sources = _functional_source_sha256(args.backend)
    loaded_inputs = _loaded_input_identities(
        kernel_ir=args.kernel_ir,
        capability=args.capability,
        workload=args.workload,
        reference=args.reference,
        checkpoint=args.checkpoint,
    )

    coverage = load_engines()
    print(
        f"engines: {coverage['implemented_count']} implemented, "
        f"{coverage['missing_count']} missing {coverage['missing']}",
        flush=True,
    )

    capability = Capability.from_dict(json.loads(args.capability.read_text()))
    workload = json.loads(args.workload.read_text())
    reference_body = json.loads(args.reference.read_text())
    gold_result = _load_gold(args.reference, workload, args.expert_numeric_path)
    gold_tokens = [int(t) for t in gold_result["generated_token_ids"]]
    workload_tokenizer = str(workload.get("tokenizer_sha256", ""))
    reference_tokenizer = str(reference_body.get("tokenizer_sha256", ""))
    if workload_tokenizer and reference_tokenizer != workload_tokenizer:
        raise SystemExit(
            "workload and reference bind different tokenizer SHA-256 values: "
            f"{workload_tokenizer!r} vs {reference_tokenizer!r}"
        )
    tokenizer_sha256 = workload_tokenizer or reference_tokenizer
    if (
        len(tokenizer_sha256) != 64
        or any(character not in "0123456789abcdef" for character in tokenizer_sha256)
    ):
        raise SystemExit(
            "the workload/reference pair does not bind a valid tokenizer SHA-256"
        )
    loaded_inputs["workload"].update(
        {
            "declared_workload_digest": str(workload["digest"]),
            "prompt_token_ids_sha256": digest_of(
                [int(token) for token in workload["token_ids"]]
            ),
            "tokenizer_sha256": tokenizer_sha256,
        }
    )

    from compiler.ir.v3.kernel_ir import KernelGraph

    # KernelGraph.read re-derives graph_id, so a document edited after
    # publication is rejected here rather than silently compiled.
    graph = KernelGraph.read(args.kernel_ir)
    lower = _resolve(BACKENDS[args.backend])
    started = time.perf_counter()
    deployment = lower(graph, capability)
    lowering_seconds = time.perf_counter() - started
    print(
        f"lowered in {lowering_seconds:.1f}s: {len(deployment.table)} descriptors",
        flush=True,
    )
    if args.publish is not None:
        deployment.write(args.publish)
        deployment = Deployment.read(args.publish)
        loaded_inputs["published_deployment"] = _deployment_file_identities(
            args.publish
        )
        print(f"published deployment to {args.publish}", flush=True)
    loaded_inputs["checkpoint_root"]["deployment_digest_binding"] = (
        deployment.deployment_digest.hex()
    )

    report = verify_deployment(deployment, capability)
    print(
        f"verification: admitted={report.admitted} "
        f"instructions={report.instruction_count} "
        f"work={report.proved_retired_work}/{report.declared_retired_work}",
        flush=True,
    )
    for error in report.errors:
        print(f"  ERROR {error}", file=sys.stderr)
    if not report.admitted:
        _write(
            args.output,
            {
                "schema": SCHEMA,
                "status": "rejected_at_admission",
                "inputs": loaded_inputs,
                "source_sha256": functional_sources,
                "verification": report.to_dict(),
            },
        )
        return 2

    numeric_backend = get_backend()
    numeric_backend.reset_executed_associations()
    from runtime.sim.engines.deepseek_vector import (
        reset_ordered_product_add_observations,
    )

    reset_ordered_product_add_observations()
    device = Device(
        deployment,
        capability,
        root=args.checkpoint,
        verify=False,
        decoded_weight_cache_bytes=args.decoded_weight_cache_bytes,
        decoded_weight_cache_working_reserve_bytes=(
            args.decoded_weight_cache_working_reserve_bytes
        ),
    )
    trace = None if args.no_head_trace else HeadTrace(graph)
    if trace is not None:
        device.on_issue = trace
    driver = GenerationDriver(device)
    prompt = [int(t) for t in workload["token_ids"]]
    limit = args.max_new_tokens or int(workload["max_new_tokens"])
    print(
        f"executing {workload['workload_id']}: {len(prompt)} prompt tokens, "
        f"max_new={limit}",
        flush=True,
    )

    def progress(produced: int, budget: int) -> None:
        print(f"  {produced}/{budget} tokens", flush=True)

    result = driver.generate(prompt, max_new_tokens=limit, progress=progress)
    got = [int(t) for t in result.generated_token_ids]
    print(
        f"produced {len(got)} tokens in {result.wall_seconds:.1f}s, "
        f"stop={result.stop_reason}",
        flush=True,
    )
    if result.failure:
        print(f"  FAILURE {result.failure}", file=sys.stderr)

    legitimacy = check_token_legitimacy(
        result.generated_token_ids,
        vocabulary_size=driver.vocabulary_size,
        eos_token_ids=driver.eos_token_ids,
        stop_reason=result.stop_reason,
    )
    legitimacy += validate_token_ids(result.generated_token_ids, driver.vocabulary_size)

    comparison = _compare(got, gold_tokens)
    print(f"oracle: {json.dumps(comparison)}", flush=True)
    terminal = _terminal_acceptance(
        contract=args.terminal_contract,
        got=got,
        gold=gold_tokens,
        stop_reason=str(result.stop_reason),
        gold_stop_reason=str(gold_result.get("stop_reason", "")),
        limit=limit,
        eos_token_ids=[int(token) for token in driver.eos_token_ids],
        per_step=list(result.per_step),
    )
    print(f"terminal acceptance: {json.dumps(terminal)}", flush=True)

    if result.failure or legitimacy:
        status = "failed"
    elif not gold_tokens:
        status = "reference_empty"
    elif comparison["agreement"] and terminal["accepted"]:
        status = "pass"
    elif comparison["agreement"]:
        status = "failed_terminal_acceptance"
    else:
        status = "diverged"

    implementation_identity = _implementation_identity()
    executed_association = numeric_backend.executed_association_manifest()
    host_performance = device.host_performance_snapshot()
    ordered_calls = int(
        host_performance["ordered_executed_associations"]["blocked_call_count"]
    )
    aggregated_calls = int(executed_association["blocked_call_count"])
    host_performance["implementation_identity"] = dict(implementation_identity)
    host_performance["association_reconciliation"] = {
        "ordered_blocked_call_count": ordered_calls,
        "aggregated_blocked_call_count": aggregated_calls,
        "counts_equal": ordered_calls == aggregated_calls,
    }

    body = {
        "schema": SCHEMA,
        "status": status,
        "evidence_class": "functional_artifact_only",
        "tool": "tools/run_accelerator_tokens.py",
        "backend": args.backend,
        "target": {
            "target_id": deployment.target_id,
            "backend": deployment.backend,
            "topology_class": deployment.topology_class,
            "node_count": device.node_count,
            "capability": str(args.capability.relative_to(REPO))
            if args.capability.is_absolute()
            else str(args.capability),
            "capability_digest": capability.digest,
            "deployment_digest": deployment.deployment_digest.hex(),
            "technology_view": capability.technology_view,
        },
        "workload": {
            "workload_id": workload["workload_id"],
            "workload_digest": workload["digest"],
            "prompt_token_ids": prompt,
            "prompt_token_count": len(prompt),
            "max_new_tokens": limit,
            "rendered_text_sha256": workload.get("rendered_text_sha256", ""),
            "prompt_token_ids_sha256": digest_of(prompt),
            "tokenizer_sha256": tokenizer_sha256,
        },
        "model": {
            "model_id": graph.model_id,
            "graph_id": graph.graph_id,
            "numeric_profile": graph.to_dict().get("numeric_profile", ""),
            "checkpoint_root": str(args.checkpoint),
        },
        "generation_policy": dict(driver.policy),
        "generation_policy_digest": digest_of(driver.policy),
        "verification": report.to_dict(),
        "engine_coverage": {
            "implemented_count": coverage["implemented_count"],
            "missing_count": coverage["missing_count"],
            "missing": list(coverage["missing"]),
        },
        "implementation_identity": implementation_identity,
        "executed_association": executed_association,
        "host_performance": host_performance,
        "inputs": loaded_inputs,
        "source_sha256": functional_sources,
        "generated_token_ids": got,
        "generated_token_count": len(got),
        "stop_reason": result.stop_reason,
        "failure": result.failure,
        "token_legitimacy_problems": legitimacy,
        "oracle": {
            "artifact": str(args.reference),
            "artifact_sha256": hashlib.sha256(args.reference.read_bytes()).hexdigest(),
            "evidence_class": "external_reference_comparator",
            "expert_numeric_path": gold_result.get("expert_numeric_path"),
            "generated_token_ids": gold_tokens,
            "note": (
                "ADR-003 section 18: the oracle is an external comparator.  It "
                "supplied no activation, no weight and no token to the "
                "accelerator path; the only values written into the device are "
                "the workload's own prompt token ids."
            ),
            **comparison,
        },
        "terminal_acceptance": terminal,
        "counters": dict(sorted(result.counters.items())),
        **_counter_evidence(device),
        "per_step": result.per_step,
        "execution_timing": _execution_timing_evidence(result),
        "lowering_seconds": round(lowering_seconds, 3),
        "wall_seconds": round(result.wall_seconds, 3),
    }
    if trace is not None:
        body["head_trace"] = trace.rows
    _write(args.output, body)
    print(f"wrote {args.output} (status {status})", flush=True)
    if legitimacy:
        for problem in legitimacy:
            print(f"  TOKEN LEGITIMACY {problem}", file=sys.stderr)
        return 3
    if result.failure:
        return 4
    return 0 if status == "pass" else 5


def _implementation_identity() -> dict[str, Any]:
    try:
        from runtime.sim.backend import get_backend
        identity = dict(get_backend().implementation_identity())
    except Exception as exc:  # a missing backend must be visible, not silent
        return {"unavailable": f"{type(exc).__name__}: {exc}"}
    try:
        from runtime.sim.engines.deepseek_vector import (
            ordered_product_add_implementation_identity,
        )

        identity["deepseek_ordered_product_add"] = (
            ordered_product_add_implementation_identity()
        )
    except Exception as exc:
        # An auxiliary implementation-identity probe must not erase the
        # arithmetic backend identity that was successfully collected above.
        identity["deepseek_ordered_product_add"] = {
            "unavailable": f"{type(exc).__name__}: {exc}"
        }
    return identity


def _functional_source_sha256(backend: str | None = None) -> dict[str, str]:
    """Bind the simulator sources that produced the functional record.

    A deployment digest identifies the program being executed; it does not
    identify the engine implementation that interpreted it.  Keep that second
    identity in the record itself so a later gate can prove that an amendment
    such as A27 was present when the run happened, rather than merely hashing
    whatever source happens to be in the worktree when the gate is rebuilt.
    """

    if backend is not None and backend not in BACKEND_FUNCTIONAL_SOURCE_PATHS:
        raise ValueError(f"unknown backend source boundary {backend!r}")
    backend_paths = (
        BACKEND_FUNCTIONAL_SOURCE_PATHS[backend]
        if backend is not None
        else tuple(
            relative
            for paths in BACKEND_FUNCTIONAL_SOURCE_PATHS.values()
            for relative in paths
        )
    )
    paths = {
        Path(__file__).resolve(),
        *(REPO / relative for relative in FUNCTIONAL_SOURCE_PATHS),
        *(REPO / relative for relative in backend_paths),
        *(REPO / "runtime" / "sim" / "engines").glob("*.py"),
    }
    return {
        str(path.relative_to(REPO)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(paths)
    }


def _record_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(REPO))
    except ValueError:
        return str(resolved)


def _file_identity(path: Path) -> dict[str, Any]:
    """Identity of one exact file loaded by the token runner."""

    resolved = path.resolve()
    return {
        "path": _record_path(resolved),
        "bytes": resolved.stat().st_size,
        "sha256": hashlib.sha256(resolved.read_bytes()).hexdigest(),
    }


def _deployment_file_identities(root: Path) -> dict[str, Any]:
    """Bind the bundle that was written and then read back for execution."""

    return {
        "path": _record_path(root),
        "manifest": _file_identity(root / "deployment.json"),
        "descriptors": _file_identity(root / "descriptors.bin"),
        "program": _file_identity(root / "program.bin"),
    }


def _loaded_input_identities(
    *,
    kernel_ir: Path,
    capability: Path,
    workload: Path,
    reference: Path,
    checkpoint: Path,
) -> dict[str, Any]:
    """Record every directly loaded file and the checkpoint binding boundary.

    Hashing a multi-hundred-gigabyte checkpoint directory a second time would
    neither be cheap nor identify which byte ranges the deployment used.  The
    deployment manifest already binds those ranges and their SHA-256 values;
    the record therefore names that mechanism explicitly and, once lowering
    completes, adds the deployment digest that authenticates it.
    """

    return {
        "kernel_ir": _file_identity(kernel_ir),
        "capability": _file_identity(capability),
        "workload": _file_identity(workload),
        "reference": _file_identity(reference),
        "checkpoint_root": {
            "path": _record_path(checkpoint),
            "kind": "directory",
            "content_binding": (
                "authenticated deployment object segment SHA-256 values"
            ),
        },
    }


def _write(path: Path, body: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json(body))


if __name__ == "__main__":
    raise SystemExit(main())
