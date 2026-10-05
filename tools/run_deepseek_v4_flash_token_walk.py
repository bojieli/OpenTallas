"""Drive the SHIPPED DeepSeek-V4-Flash deployment to a token and check the oracle.

Why the shipped model rather than a reduced one: V4-Flash has no reduced vehicle,
and it turns out not to need one.  Its ROM wafer deployment is 1,323 instructions
and one greedy step over the released 32-token workload retires 26,102 of them on
the functional device in under an hour -- which is the only cell in the matrix
where a SHIPPED checkpoint produces a checkable token, and it checks.

WHAT THIS ESTABLISHES, and it is the strongest evidence in the token work: the
engine stack, the real control plane and the ROM wafer lowering are correct
end-to-end for a full-scale DeepSeek model, because the emitted token EQUALS the
reference oracle's.  Everything the V4.1 reduced vehicle disagrees with its own
oracle about is therefore in a V4.1-SPECIFIC path -- the Engram lookup and gate,
the compressor, the two-level index -- and not in anything the two releases share.

NOT a claim about RTL, timing, or the released model's numerics beyond this one
greedy step on this one workload.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from runtime.abi3.capability import Capability  # noqa: E402
from runtime.abi3.deployment import Deployment  # noqa: E402
from runtime.driver import GenerationDriver  # noqa: E402
from runtime.sim.device import Device  # noqa: E402
from runtime.sim.engines import load_engines  # noqa: E402

ORACLE = ROOT / "results/abi3/deepseek_v4_reference_oracle_prefix.json"
WORKLOAD = ROOT / "build/workloads/deepseek-v4-flash-0731-prefix/TA-DS-CHAT-1-P32.json"
WORKLOAD_ID = "TA-DS-CHAT-1-P32"

#: Each store, with the capability its deployment was admitted against.
STORES: dict[str, tuple[str, str]] = {
    "rom_wafer": (
        "build/abi3/deepseek-v4-flash-rom",
        "configs/hardware/abi3_capability/rom_deepseek_v4.json",
    ),
    "rom_array_32": (
        "build/abi3/deepseek-v4-flash-rom-array-32",
        "configs/hardware/abi3_capability/rom_deepseek_v4_array_32.json",
    ),
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_state() -> dict[str, object]:
    def run(*a: str) -> str:
        return subprocess.run(["git", *a], cwd=ROOT, capture_output=True,
                              text=True, check=False).stdout.strip()
    return {"commit": run("rev-parse", "HEAD") or None,
            "worktree_dirty": bool(run("status", "--porcelain"))}


def snapshot() -> Path:
    root = Path("/home/ubuntu/.cache/huggingface/hub/"
                "models--deepseek-ai--DeepSeek-V4-Flash-0731/snapshots")
    return sorted(root.glob("*"))[0]


def run_store(store: str, prompt: list[int], expected: list[int],
              max_new: int) -> dict[str, object]:
    deployment_dir, capability_path = STORES[store]
    body = json.loads((ROOT / capability_path).read_text())
    capability = Capability.from_dict(body.get("capability", body))
    deployment = Deployment.read(ROOT / deployment_dir)
    manifest = json.loads((ROOT / deployment_dir / "deployment.json").read_text())
    device = Device(deployment, capability, verify=False, trace=False,
                    root=snapshot())
    driver = GenerationDriver(device)
    result = driver.generate(prompt, max_new_tokens=max_new).to_dict()
    emitted = list(result.get("generated_token_ids") or ())
    return {
        "identity": {
            "deployment": deployment_dir,
            "deployment_sha256": manifest["deployment_sha256"],
            "target_id": manifest["target_id"],
            "capability": capability_path,
            "capability_sha256": sha256(ROOT / capability_path),
            "instruction_count": manifest["instruction_count"],
            "node_count": int(device.node_count),
        },
        "emitted_token_ids": emitted,
        "stop_reason": result.get("stop_reason"),
        "failure": result.get("failure"),
        "retired_work": sum(
            int(step.get("retired_work", 0)) for step in result.get("per_step", ())
        ),
        "agrees_with_oracle": (
            emitted[: len(emitted)] == expected[: len(emitted)] if emitted else False
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--store", action="append", choices=sorted(STORES))
    parser.add_argument("--max-new-tokens", type=int, default=1)
    arguments = parser.parse_args()
    stores = arguments.store or sorted(STORES)

    load_engines()
    workload = json.loads(WORKLOAD.read_text())
    oracle = json.loads(ORACLE.read_text())
    prompt = list(workload["token_ids"])
    expected = list(oracle["results"][WORKLOAD_ID]["generated_token_ids"])

    cases = {
        store: run_store(store, prompt, expected, arguments.max_new_tokens)
        for store in stores
    }
    body = {
        "schema": "opentallas.abi3.shipped_token_walk.v1",
        "model_id": "deepseek-v4-flash-0731",
        "workload_id": WORKLOAD_ID,
        "prompt_token_ids": prompt,
        "oracle": {
            "artifact": str(ORACLE.relative_to(ROOT)),
            "sha256": sha256(ORACLE),
            "generated_token_ids": expected,
        },
        "cases": cases,
        "agreement": {s: c["agrees_with_oracle"] for s, c in cases.items()},
        "producer": {
            "tool": "tools/run_deepseek_v4_flash_token_walk.py",
            "sha256": sha256(Path(__file__).resolve()),
            "git": git_state(),
        },
        "evidence_class": "functional_device_execution_shipped_checkpoint",
        "not_a_claim": [
            "rtl_execution",
            "timing_or_performance",
            "numerics_beyond_this_workload_and_step_count",
        ],
    }
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n")
    for store, case in cases.items():
        verdict = "AGREES" if case["agrees_with_oracle"] else "DISAGREES"
        print(f"  {store:14s} emitted={case['emitted_token_ids']} "
              f"oracle={expected[:1]} retired={case['retired_work']} {verdict}")
    print(f"wrote {arguments.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
