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
import sys
import time
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from runtime.abi3.capability import Capability, canonical_json, digest_of  # noqa: E402
from runtime.abi3.deployment import Deployment  # noqa: E402
from runtime.abi3.verifier import verify_deployment  # noqa: E402
from runtime.driver import GenerationDriver, validate_token_ids  # noqa: E402
from runtime.evidence import check_token_legitimacy  # noqa: E402
from runtime.abi3.constants import DType  # noqa: E402
from runtime.sim.device import Device  # noqa: E402
from runtime.sim.engines import load_engines  # noqa: E402
from runtime.sim.formats import widen  # noqa: E402

SCHEMA = "opentallas.abi3.accelerator_tokens.v1"

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
    if not args.checkpoint.is_dir():
        raise SystemExit(f"checkpoint root {args.checkpoint} is not a directory")

    coverage = load_engines()
    print(
        f"engines: {coverage['implemented_count']} implemented, "
        f"{coverage['missing_count']} missing {coverage['missing']}",
        flush=True,
    )

    capability = Capability.from_dict(json.loads(args.capability.read_text()))
    workload = json.loads(args.workload.read_text())
    gold_result = _load_gold(args.reference, workload, args.expert_numeric_path)
    gold_tokens = [int(t) for t in gold_result["generated_token_ids"]]

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
        print(f"published deployment to {args.publish}", flush=True)

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
                "verification": report.to_dict(),
            },
        )
        return 2

    device = Device(deployment, capability, root=args.checkpoint, verify=False)
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

    if result.failure or legitimacy:
        status = "failed"
    elif not gold_tokens:
        status = "reference_empty"
    elif comparison["agreement"]:
        status = "pass"
    else:
        status = "diverged"

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
        "implementation_identity": _implementation_identity(),
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
        "counters": dict(sorted(result.counters.items())),
        "per_step": result.per_step,
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

        return dict(get_backend().implementation_identity())
    except Exception as exc:  # a missing backend must be visible, not silent
        return {"unavailable": f"{type(exc).__name__}: {exc}"}


def _write(path: Path, body: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json(body))


if __name__ == "__main__":
    raise SystemExit(main())
