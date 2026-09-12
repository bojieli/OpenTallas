#!/usr/bin/env python3
"""Run a complete agent episode on the Qwen HBM accelerator, against an oracle.

The acceptance contract requires that agent actions are model-generated, parsed
fail-closed, executed in a frozen sandbox, and returned in the next rendered
context. That is a loop, not a single generation, so this tool closes it: the
accelerator produces a turn, the sandbox executes exactly what it produced, and
the observation is rendered back through the official chat template for the
next turn.

Nothing here writes a command. If the model's turn does not parse under the
frozen protocol the episode stops and says so, rather than repairing it into
something that would pass.

What the earlier version of this tool could not say is whether the tokens were
*right*. It reported ``task_solved`` from the sandbox's own output, which is a
property of the command, not of the decode: a wrong command that happens to
print the right number would have passed, and so would a right command decoded
from a broken accelerator if the harness had repaired it. This version compares
every turn against an external oracle episode -- the prompt the loop rendered
and the tokens decoded from it -- and reserves ``pass`` for a full match.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from compiler.backends.hbm_sram.lower import lower_to_abi3  # noqa: E402
from compiler.ir.v3.kernel_ir import KernelGraph  # noqa: E402
from runtime.abi3.capability import Capability, canonical_json  # noqa: E402
from runtime.abi3.deployment import Deployment  # noqa: E402
from runtime.abi3.verifier import verify_deployment  # noqa: E402
from runtime.agent import (  # noqa: E402
    AgentProtocolError,
    Sandbox,
    parse_turn,
    render_agent_context,
    split_thinking,
)
from runtime.driver import GenerationDriver, validate_token_ids  # noqa: E402
from runtime.evidence import check_token_legitimacy  # noqa: E402
from runtime.sim.backend import get_backend  # noqa: E402
from runtime.sim.device import Device  # noqa: E402
from runtime.sim.engines import load_engines  # noqa: E402

DEFAULT_SNAPSHOT = (
    Path.home()
    / ".cache/huggingface/hub/models--Qwen--Qwen3-8B/snapshots"
    / "b968826d9c46dd6066d109eabc6255188de91218"
)


def _compare_turn(
    got_prompt: list[int],
    got_generated: list[int],
    gold: dict[str, Any] | None,
) -> dict[str, Any]:
    """Compare one accelerator turn against the oracle's turn.

    Both halves matter.  The generated ids are the decode under test; the
    prompt ids are what the loop *built* from the previous turn, so comparing
    them is what makes this a test of the closed loop rather than of four
    unrelated generations.  A run stopped by its token cap is a prefix of the
    oracle's sequence, so the generated comparison is against the oracle prefix
    of the same length -- but two empty lists are never an agreement.
    """
    if gold is None:
        return {"compared": False, "reason": "oracle episode has no such turn"}
    gold_prompt = [int(t) for t in gold["prompt_token_ids"]]
    gold_generated = [int(t) for t in gold["generated_token_ids"]]
    prompt_divergence = next(
        (i for i, (a, b) in enumerate(zip(got_prompt, gold_prompt)) if a != b), None
    )
    generated_divergence = next(
        (i for i, (a, b) in enumerate(zip(got_generated, gold_generated)) if a != b),
        None,
    )
    prompt_match = bool(got_prompt) and got_prompt == gold_prompt
    generated_match = (
        bool(got_generated)
        and bool(gold_generated)
        and got_generated == gold_generated[: len(got_generated)]
    )
    body: dict[str, Any] = {
        "compared": True,
        "prompt_match": prompt_match,
        "generated_match": generated_match,
        "oracle_prompt_token_count": len(gold_prompt),
        "oracle_generated_token_count": len(gold_generated),
        "first_prompt_divergence_index": prompt_divergence,
        "first_generated_divergence_index": generated_divergence,
    }
    if prompt_divergence is not None:
        body["prompt_divergence"] = {
            "index": prompt_divergence,
            "accelerator_token_id": got_prompt[prompt_divergence],
            "oracle_token_id": gold_prompt[prompt_divergence],
        }
    elif len(got_prompt) != len(gold_prompt):
        body["prompt_divergence"] = {
            "index": min(len(got_prompt), len(gold_prompt)),
            "reason": "one prompt is a strict prefix of the other",
            "accelerator_token_count": len(got_prompt),
            "oracle_token_count": len(gold_prompt),
        }
    if generated_divergence is not None:
        body["generated_divergence"] = {
            "index": generated_divergence,
            "accelerator_token_id": got_generated[generated_divergence],
            "oracle_token_id": gold_generated[generated_divergence],
        }
    return body


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--ir", type=Path, default=REPO / "build/ir-v3/qwen3-8b/kernel_ir.v3.json"
    )
    parser.add_argument(
        "--capability",
        type=Path,
        default=REPO / "configs/hardware/abi3_capability/hbm_sram_single_chip.json",
    )
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument(
        "--workload",
        type=Path,
        default=REPO / "build/workloads/qwen3-8b/TA-QW-AGENT-2.json",
        help="the pinned opening context, sandbox contents and protocol",
    )
    parser.add_argument(
        "--reference",
        type=Path,
        default=None,
        help=(
            "reference-oracle file holding this workload's gold episode.  "
            "Without it the run is recorded as executed_unverified: a closed "
            "loop that ran is not evidence that it decoded the right tokens."
        ),
    )
    parser.add_argument("--max-turns", type=int, default=None)
    parser.add_argument("--max-new-tokens", type=int, default=None)
    parser.add_argument("--context-capacity", type=int, default=8192)
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO / "results/abi3/qwen3_hbm_agent_episode.json",
    )
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if args.output.exists() and not args.force:
        print(f"refusing to overwrite {args.output}; pass --force", file=sys.stderr)
        return 1

    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(
        str(args.snapshot), local_files_only=True, trust_remote_code=False
    )
    workload = json.loads(args.workload.read_text())
    metadata = workload.get("metadata", {})
    enable_thinking = bool(metadata.get("enable_thinking", False))
    sandbox_files = metadata["sandbox_files"]
    max_turns = args.max_turns or int(metadata.get("max_turns", 4))
    max_new_tokens = args.max_new_tokens or int(workload["max_new_tokens"])

    gold_turns: list[dict[str, Any]] = []
    gold_episode: dict[str, Any] | None = None
    if args.reference is not None:
        body = json.loads(args.reference.read_text())
        results = body.get("results", {})
        wid = workload["workload_id"]
        if wid not in results:
            raise SystemExit(
                f"reference {args.reference} holds no result for {wid!r}; "
                f"it has {sorted(results)}"
            )
        if results[wid].get("workload_digest") != workload["digest"]:
            raise SystemExit(
                f"reference {args.reference} was produced against workload "
                f"digest {results[wid].get('workload_digest')!r}, not "
                f"{workload['digest']!r}; the comparison would be between two "
                f"different prompts"
            )
        gold_episode = results[wid].get("episode")
        if not gold_episode:
            raise SystemExit(
                f"reference {args.reference} holds a single generation for "
                f"{wid!r}, not an episode; regenerate it with --agent-episode"
            )
        gold_turns = gold_episode["turns"]

    coverage = load_engines()
    print(
        f"engines: {coverage['implemented_count']} implemented, "
        f"{coverage['missing_count']} missing"
    )
    capability = Capability.from_dict(json.loads(args.capability.read_text()))
    graph = KernelGraph.read(args.ir)
    deployment = lower_to_abi3(graph, capability)
    deployment.write(args.snapshot)
    deployment = Deployment.read(args.snapshot)
    report = verify_deployment(deployment, capability)
    print(
        f"verification: admitted={report.admitted} "
        f"instructions={report.instruction_count} "
        f"work={report.proved_retired_work}/{report.declared_retired_work} "
        f"loop_depth={report.loop_depth}"
    )
    if not report.admitted:
        raise SystemExit(f"deployment not admitted: {report.errors}")
    device = Device(deployment, capability, verify=False)

    from compiler.workloads.qwen3 import AGENT_SYSTEM, AGENT_TASK

    messages: list[dict[str, str]] = [
        {"role": "system", "content": AGENT_SYSTEM},
        {"role": "user", "content": AGENT_TASK},
    ]
    turns: list[dict[str, Any]] = []
    answer: str | None = None
    stop_reason = "max_turns"
    legitimacy_problems: list[Any] = []
    started = time.perf_counter()

    with Sandbox(sandbox_files) as sandbox:
        for index in range(max_turns):
            rendered, prompt = render_agent_context(
                tokenizer, messages, enable_thinking=enable_thinking
            )
            if index == 0 and prompt != list(workload["token_ids"]):
                raise SystemExit(
                    "the loop's turn-0 prompt does not match the pinned "
                    "workload prompt; the workload and the loop disagree "
                    "about the opening context"
                )
            budget = args.context_capacity - len(prompt)
            if budget <= 0:
                stop_reason = "context_exhausted"
                break
            limit = min(max_new_tokens, budget)
            print(
                f"\nturn {index}: {len(prompt)} prompt tokens, max_new={limit}",
                flush=True,
            )
            # A fresh session per turn: the rendered context carries the whole
            # history, which is what the pinned template contract says.
            session = device.create_session()
            driver = GenerationDriver(device)
            result = driver.generate(
                prompt, max_new_tokens=limit, session=session
            )
            generated = list(result.generated_token_ids)
            text = tokenizer.decode(generated, skip_special_tokens=True)
            thinking, visible = split_thinking(text)
            problems = check_token_legitimacy(
                generated,
                vocabulary_size=driver.vocabulary_size,
                eos_token_ids=driver.eos_token_ids,
                stop_reason=result.stop_reason,
            )
            problems += validate_token_ids(generated, driver.vocabulary_size)
            legitimacy_problems += problems
            gold = gold_turns[index] if index < len(gold_turns) else None
            record: dict[str, Any] = {
                "turn": index,
                "prompt_token_ids": prompt,
                "prompt_token_count": len(prompt),
                "rendered_prompt_sha256": hashlib.sha256(
                    rendered.encode()
                ).hexdigest(),
                "max_new_tokens": limit,
                "generated_token_ids": generated,
                "generated_token_count": len(generated),
                "generated_text": text,
                "thinking_text": thinking,
                "visible_text": visible,
                "stop_reason": result.stop_reason,
                "eos_token_id": result.eos_token_id,
                "wall_seconds": round(result.wall_seconds, 3),
                "token_legitimacy_problems": problems,
                "failure": result.failure,
                "oracle_comparison": _compare_turn(prompt, generated, gold),
            }
            print(
                f"  {len(generated)} tokens in {result.wall_seconds:.1f}s, "
                f"stop={result.stop_reason}, "
                f"oracle={record['oracle_comparison']}",
                flush=True,
            )
            if thinking:
                print(f"  thinking ({len(thinking)} chars): {thinking[:200]!r}")
            print(f"  visible: {visible[:300]!r}", flush=True)
            if result.failure:
                record["outcome"] = "device_failure"
                turns.append(record)
                stop_reason = "device_failure"
                break
            try:
                parsed = parse_turn(visible)
            except AgentProtocolError as exc:
                record["outcome"] = "protocol_violation"
                record["protocol_violation"] = str(exc)
                turns.append(record)
                stop_reason = "protocol_violation"
                break
            record["parsed"] = parsed.to_dict()
            if parsed.kind == "answer":
                answer = parsed.answer
                record["outcome"] = "answered"
                turns.append(record)
                stop_reason = "answered"
                break
            if parsed.kind == "neither":
                record["outcome"] = "no_action"
                turns.append(record)
                stop_reason = "no_action"
                break
            assert parsed.command is not None
            observation = sandbox.run(parsed.command)
            record["outcome"] = "executed"
            record["observation"] = observation.to_dict()
            print(
                f"  ran {parsed.command!r} -> exit {observation.exit_code}, "
                f"stdout {observation.stdout.strip()!r}",
                flush=True,
            )
            turns.append(record)
            messages.append({"role": "assistant", "content": text})
            messages.append({"role": "user", "content": observation.rendered()})

    elapsed = time.perf_counter() - started
    expected_total = metadata.get("expected_total")
    observed = [
        t["observation"]["stdout"].strip() for t in turns if t.get("observation")
    ]
    solved = bool(expected_total is not None) and (
        any(str(expected_total) in o for o in observed)
        or (answer is not None and str(expected_total) in answer)
    )

    executed_turns = sum(1 for t in turns if t.get("outcome") == "executed")
    comparisons = [t["oracle_comparison"] for t in turns]
    compared = [c for c in comparisons if c.get("compared")]
    oracle_agreement = (
        bool(compared)
        and len(compared) == len(turns)
        and all(c["prompt_match"] and c["generated_match"] for c in compared)
        and gold_episode is not None
        and len(turns) == int(gold_episode["turn_count"])
    )
    if gold_episode is None:
        status = "executed_unverified"
    elif any(t.get("failure") for t in turns) or legitimacy_problems:
        status = "failed"
    elif not gold_turns:
        status = "reference_empty"
    elif not oracle_agreement:
        status = "diverged"
    elif executed_turns < 1:
        # A single decoded tool call that is never executed is not an agentic
        # episode; neither is an episode whose only turn is the answer.
        status = "not_closed_loop"
    else:
        status = "pass"

    body = {
        "schema": "opentallas.abi3.agent_episode.v2",
        "status": status,
        "evidence_class": "functional_artifact_only",
        "workload_id": workload["workload_id"],
        "workload_digest": workload["digest"],
        "enable_thinking": enable_thinking,
        "target": deployment.target_id,
        "backend": deployment.backend,
        "graph_id": graph.graph_id,
        "deployment_digest": deployment.deployment_digest.hex(),
        "capability_digest": capability.digest,
        "verification": report.to_dict(),
        "implementation_identity": dict(get_backend().implementation_identity()),
        "engine_coverage": {
            "implemented": coverage["implemented_count"],
            "missing": coverage["missing_count"],
        },
        "reference": str(args.reference) if args.reference else None,
        "oracle_agreement": oracle_agreement if gold_episode else None,
        "oracle_episode": gold_episode,
        "expected_total": expected_total,
        "turns": turns,
        "turn_count": len(turns),
        "executed_command_count": executed_turns,
        "answer": answer,
        "stop_reason": stop_reason,
        "task_solved": solved,
        "token_legitimacy_problems": legitimacy_problems,
        "wall_seconds": round(elapsed, 1),
        "note": (
            "Every command executed was produced by the accelerator and parsed "
            "fail-closed; the harness never writes or repairs one.  'pass' "
            "additionally requires that every turn's prompt and generated "
            "token ids matched the external oracle episode and that at least "
            "one command was actually executed in the sandbox."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_json(body))
    print(
        f"\nstatus={status} stop={stop_reason} solved={solved} "
        f"turns={len(turns)} executed={executed_turns} seconds={elapsed:.1f}"
    )
    print(f"wrote {args.output}")
    return 0 if status == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
