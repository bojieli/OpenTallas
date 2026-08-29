#!/usr/bin/env python3
"""Run a complete agent episode on the Qwen HBM accelerator.

The acceptance contract requires that agent actions are model-generated, parsed
fail-closed, executed in a frozen sandbox, and returned in the next rendered
context. That is a loop, not a single generation, so this tool closes it: the
accelerator produces a turn, the sandbox executes exactly what it produced, and
the observation is rendered back through the official chat template for the
next turn.

Nothing here writes a command. If the model's turn does not parse under the
frozen protocol the episode stops and says so, rather than repairing it into
something that would pass.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from compiler.backends.hbm_sram.capability import PROFILES  # noqa: E402
from compiler.backends.hbm_sram.lower import lower_to_abi3  # noqa: E402
from compiler.ir.v3.kernel_ir import KernelGraph  # noqa: E402
from compiler.workloads.qwen3 import (  # noqa: E402
    AGENT_EXPECTED_TOTAL,
    AGENT_SANDBOX_FILES,
    AGENT_SYSTEM,
    AGENT_TASK,
)
from runtime.abi3.capability import canonical_json  # noqa: E402
from runtime.agent import AgentProtocolError, Sandbox, parse_turn  # noqa: E402
from runtime.driver import GenerationDriver  # noqa: E402
from runtime.sim.backend import get_backend  # noqa: E402
from runtime.sim.device import Device  # noqa: E402
from runtime.sim.engines import load_engines  # noqa: E402

DEFAULT_SNAPSHOT = Path(
    "/home/ubuntu/.cache/huggingface/hub/models--Qwen--Qwen3-8B/snapshots/"
    "b968826d9c46dd6066d109eabc6255188de91218"
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ir", type=Path, default=REPO / "build/ir-v3/qwen3-8b/kernel_ir.v3.json")
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument("--max-turns", type=int, default=3)
    parser.add_argument("--max-new-tokens", type=int, default=48)
    parser.add_argument(
        "--output", type=Path, default=REPO / "results/abi3/qwen3_hbm_agent_episode.json"
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
    coverage = load_engines()
    capability = PROFILES["single-chip"]
    capability = capability() if callable(capability) else capability
    graph = KernelGraph.read(args.ir)
    deployment = lower_to_abi3(graph, capability)
    device = Device(deployment, capability, root=args.snapshot, verify=False)

    messages: list[dict[str, str]] = [
        {"role": "system", "content": AGENT_SYSTEM},
        {"role": "user", "content": AGENT_TASK},
    ]
    turns: list[dict[str, Any]] = []
    answer: str | None = None
    stop_reason = "max_turns"
    started = time.perf_counter()

    with Sandbox(AGENT_SANDBOX_FILES) as sandbox:
        for index in range(args.max_turns):
            rendered = tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True,
                enable_thinking=False,
            )
            prompt = tokenizer.encode(rendered, add_special_tokens=False)
            print(f"\nturn {index}: {len(prompt)} prompt tokens", flush=True)
            # A fresh session per turn: the rendered context carries the whole
            # history, which is what the pinned template contract says.
            session = device.create_session()
            driver = GenerationDriver(device)
            result = driver.generate(
                prompt, max_new_tokens=args.max_new_tokens, session=session
            )
            text = tokenizer.decode(result.generated_token_ids, skip_special_tokens=True)
            record: dict[str, Any] = {
                "turn": index,
                "prompt_token_count": len(prompt),
                "generated_token_ids": list(result.generated_token_ids),
                "generated_text": text,
                "stop_reason": result.stop_reason,
                "eos_token_id": result.eos_token_id,
                "failure": result.failure,
            }
            print(f"  {len(result.generated_token_ids)} tokens, stop={result.stop_reason}")
            print(f"  text: {text!r}")
            if result.failure:
                record["outcome"] = "device_failure"
                turns.append(record)
                stop_reason = "device_failure"
                break
            try:
                parsed = parse_turn(text)
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
            print(f"  ran {parsed.command!r} -> {observation.stdout.strip()!r}")
            turns.append(record)
            messages.append({"role": "assistant", "content": text})
            messages.append({"role": "user", "content": observation.rendered()})

    elapsed = time.perf_counter() - started
    observed = [
        t["observation"]["stdout"].strip()
        for t in turns
        if t.get("observation")
    ]
    solved = any(str(AGENT_EXPECTED_TOTAL) in o for o in observed) or (
        answer is not None and str(AGENT_EXPECTED_TOTAL) in answer
    )
    body = {
        "schema": "opentallas.abi3.agent_episode.v1",
        "evidence_class": "functional_artifact_only",
        "target": deployment.target_id,
        "backend": deployment.backend,
        "graph_id": graph.graph_id,
        "deployment_digest": deployment.deployment_digest.hex(),
        "capability_digest": capability.digest,
        "implementation_identity": dict(get_backend().implementation_identity()),
        "engine_coverage": {
            "implemented": coverage["implemented_count"],
            "missing": coverage["missing_count"],
        },
        "expected_total": AGENT_EXPECTED_TOTAL,
        "turns": turns,
        "turn_count": len(turns),
        "answer": answer,
        "stop_reason": stop_reason,
        "task_solved": solved,
        "wall_seconds": round(elapsed, 1),
        "note": (
            "Every command executed was produced by the accelerator and parsed "
            "fail-closed; the harness never writes or repairs one."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_json(body))
    print(f"\nstop={stop_reason} solved={solved} turns={len(turns)} "
          f"seconds={elapsed:.1f}")
    print(f"wrote {args.output}")
    return 0 if solved else 2


if __name__ == "__main__":
    raise SystemExit(main())
