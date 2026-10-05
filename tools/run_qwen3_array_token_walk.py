#!/usr/bin/env python3
"""Drive the reduced Qwen3 ROM ARRAY to a token and record what it is.

The array is a pipelined multi-node ROM deployment of the same graph the
single-chip product lowers (:mod:`compiler.backends.rom.qwen3_array`), and its
arithmetic is the single chip's: stages exchange the residual stream by
``LINK.REMOTE_DMA``, a byte movement under no numeric contract, and no
collective reduces anything.  So this run has a stronger obligation than
agreement with the reference oracle -- it must agree with the SINGLE CHIP's own
emitted token, bit for bit, and a disagreement is a defect in the array backend
rather than a numeric difference to be explained.

Both agreements are recorded, and the single-chip run is executed here rather
than quoted from an artifact so the two tokens come from one process and one
checkpoint.

IT IS NOT AN RTL MEASUREMENT and says so in ``not_a_claim``: the device is
``runtime.sim``, so what this establishes is that the pipelined program executes
to a token under the real control plane and what that token is.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.abi3.capability import Capability  # noqa: E402
from runtime.abi3.deployment import Deployment  # noqa: E402
from runtime.driver import GenerationDriver  # noqa: E402
from runtime.sim.device import Device  # noqa: E402
from runtime.sim.engines import load_engines  # noqa: E402

SCHEMA = "opentallas.abi3.qwen3_array_token_walk.v1"
TOOL = "tools/run_qwen3_array_token_walk.py"
ORACLE = ROOT / "results/abi3/qwen3_reduced_reference_oracle.json"
WORKLOAD_ID = "TA-QW-REDUCED-EOS-1"
CHECKPOINT = ROOT / "build/models/qwen3-reduced-v1"

#: The deployments this walk compares, and the capability each was admitted
#: against.  ``rom_array_4`` is the vehicle under test; ``rom_single_chip`` is
#: the reference the array must reproduce exactly.
CASES: dict[str, tuple[str, str]] = {
    "rom_array_4": (
        "build/abi3/qwen3-reduced-rom-array-4",
        "results/abi3/qwen3_reduced_rom_array_4_capability.json",
    ),
    "rom_single_chip": (
        "build/abi3/qwen3-reduced-rom",
        "configs/hardware/abi3_capability/rom_qwen3.json",
    ),
}


def _git(*args: str) -> str:
    return subprocess.run(
        ("git", *args), cwd=ROOT, capture_output=True, text=True, check=False
    ).stdout.strip()


def run_case(name: str, prompt: list[int], budget: int) -> dict[str, Any]:
    deployment_dir, capability_path = CASES[name]
    body = json.loads((ROOT / capability_path).read_text())
    capability = Capability.from_dict(body.get("capability", body))
    deployment = Deployment.read(ROOT / deployment_dir)
    device = Device(
        deployment, capability, verify=True, trace=False, root=CHECKPOINT
    )
    started = time.perf_counter()
    failure = None
    result: dict[str, Any] = {}
    try:
        result = GenerationDriver(device).generate(prompt, max_new_tokens=budget).to_dict()
    except Exception as exc:  # a stop is evidence, not a crash to hide
        failure = f"{type(exc).__name__}: {exc}"
    elapsed = time.perf_counter() - started
    topology = None
    for descriptor in getattr(deployment, "descriptors", ()) or ():
        payload = getattr(descriptor, "payload", None)
        if isinstance(payload, dict) and "node_count" in payload:
            topology = {
                "node_count": int(payload["node_count"]),
                "topology_class": int(payload.get("topology_class", -1)),
            }
            break
    return {
        "deployment": deployment_dir,
        "capability": capability_path,
        "emitted_token_ids": [int(t) for t in result.get("generated_token_ids", [])],
        # Retirement is per transaction, so the walk's total is the sum over the
        # steps; ``result`` carries no whole-request retirement field and reading
        # one that does not exist reported zero for a run that retired 126.
        "retired": sum(
            int(step.get("instructions_retired", 0) or 0)
            for step in (result.get("per_step") or ())
        ),
        "transactions": int(result.get("transactions", 0) or 0),
        "stop_reason": result.get("stop_reason"),
        "link_counters": {
            key: value
            for key, value in sorted((result.get("counters") or {}).items())
            if key.startswith("link.") or key.startswith("engine.link")
        },
        "failure": failure,
        "seconds": round(elapsed, 3),
        "topology": topology,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", action="append", choices=sorted(CASES))
    parser.add_argument("--max-new-tokens", type=int, default=1)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "results/abi3/qwen3_reduced_array_token_walk.json",
    )
    arguments = parser.parse_args(argv)
    cases = arguments.case or sorted(CASES)

    oracle = json.loads(ORACLE.read_text())
    case = oracle["results"][WORKLOAD_ID]
    prompt = [int(t) for t in case["prompt_token_ids"]]
    expected = [int(t) for t in case["generated_token_ids"]]

    load_engines()
    results: dict[str, Any] = {}
    for name in cases:
        results[name] = run_case(name, prompt, arguments.max_new_tokens)
        emitted = results[name]["emitted_token_ids"]
        print(
            f"{name}: emitted={emitted} retired={results[name]['retired']} "
            f"failure={results[name]['failure']}",
            flush=True,
        )

    budget = int(arguments.max_new_tokens)
    oracle_prefix = expected[:budget]
    agreement = {
        name: {
            "agrees_with_oracle": results[name]["emitted_token_ids"] == oracle_prefix,
            "agrees_with_single_chip": (
                results[name]["emitted_token_ids"]
                == results.get("rom_single_chip", {}).get("emitted_token_ids")
                if "rom_single_chip" in results
                else None
            ),
        }
        for name in results
    }
    report = {
        "schema": SCHEMA,
        "producer": {"tool": TOOL, "git": {"commit": _git("rev-parse", "HEAD")}},
        "workload": {
            "workload_id": WORKLOAD_ID,
            "prompt_token_ids": prompt,
            "oracle_token_ids": expected,
            "compared_prefix": oracle_prefix,
        },
        "obligation": (
            "the array's arithmetic is the single chip's -- LINK.REMOTE_DMA moves "
            "bytes under no numeric contract and no collective reduces anything -- "
            "so the array must reproduce the single chip's token exactly, not "
            "merely land near it"
        ),
        "cases": results,
        "agreement": agreement,
        "not_a_claim": [
            "not an RTL measurement: the device is runtime.sim",
            "not a performance statement: a pipeline at batch one has one stage "
            "busy at a time, so the array's token rate is the single chip's",
        ],
    }
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    for name, verdict in sorted(agreement.items()):
        print(
            f"{name}: oracle={'AGREES' if verdict['agrees_with_oracle'] else 'DISAGREES'} "
            f"single_chip={verdict['agrees_with_single_chip']}"
        )
    print(f"-> {arguments.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
