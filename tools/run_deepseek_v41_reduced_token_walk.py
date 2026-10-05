"""Drive the reduced DeepSeek V4.1 deployment to a token and record what it is.

This is the DeepSeek analogue of ``tools/rtl_abi3_reduced_token_campaign.py``'s
golden half: it runs the admitted reduced deployment on the functional device
through ``GenerationDriver`` -- the real control plane, the real descriptor
walk, every engine operation dispatched -- and writes what the device emits
beside what the reference oracle recorded.

IT IS NOT AN RTL MEASUREMENT and says so in ``not_a_claim``.  The device here is
``runtime.sim``, so what this establishes is that the program executes to a
token and what that token is; nothing about the RTL, the schedule or the timing.

The emitted token DISAGREES with the oracle at the time of writing, and that is
the point of the artifact: the divergence is recorded with the evidence needed
to bisect it -- the oracle token's own rank and logit in the device's own
distribution, and a prompt-dependence probe that separates an arithmetic fault
from an operand that never reads its input.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from runtime.abi3.capability import Capability  # noqa: E402
from runtime.abi3.constants import Major, Selection  # noqa: E402
from runtime.abi3.deployment import Deployment  # noqa: E402
from runtime.driver import GenerationDriver  # noqa: E402
from runtime.sim.device import Device  # noqa: E402
from runtime.sim.engine import _REGISTRY  # noqa: E402
from runtime.sim.engines import load_engines  # noqa: E402
import runtime.sim.engines.selection as selection_engine  # noqa: E402

ORACLE = ROOT / "results/abi3/deepseek_v41_reduced_reference_oracle.json"
CHECKPOINT = ROOT / "build/models/deepseek-v4.1-flash-reduced-v1"
WORKLOAD = "TA-DS41-REDUCED-EOS-1"

#: Each store, with the capability record its deployment was admitted against.
STORES: dict[str, tuple[str, str]] = {
    "rom_wafer": (
        "build/abi3/deepseek-v41-reduced-rom",
        "configs/hardware/abi3_capability/rom_deepseek_v41_wafer.json",
    ),
    "hbm_single_chip": (
        "build/abi3/deepseek-v41-reduced-hbm",
        "results/abi3/deepseek_v41_hbm_comparator_capability.json",
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


def _device(store: str) -> tuple[Device, GenerationDriver, dict[str, object]]:
    deployment_dir, capability_path = STORES[store]
    body = json.loads((ROOT / capability_path).read_text())
    capability = Capability.from_dict(body.get("capability", body))
    deployment = Deployment.read(ROOT / deployment_dir)
    manifest = json.loads((ROOT / deployment_dir / "deployment.json").read_text())
    device = Device(deployment, capability, verify=False, trace=False,
                    root=CHECKPOINT)
    identity = {
        "deployment": deployment_dir,
        "deployment_sha256": manifest["deployment_sha256"],
        "capability": capability_path,
        "capability_sha256": sha256(ROOT / capability_path),
        "instruction_count": manifest["instruction_count"],
        "descriptor_count": manifest["descriptor_count"],
    }
    return device, GenerationDriver(device), identity


def _spy_argmax(captured: dict[str, object], oracle_token: int):
    """Wrap SELECTION.ARGMAX to record the distribution it chose from."""
    original = _REGISTRY[(int(Major.SELECTION), int(Selection.ARGMAX))]

    def spy(ctx, sub, descriptor):  # noqa: ANN001
        view = ctx.input_view(descriptor, 0)
        values = np.asarray(
            selection_engine._widen(ctx, view), dtype=np.float64  # noqa: SLF001
        ).reshape(-1)
        order = np.argsort(-values)
        captured["top"] = [
            {"token_id": int(index), "logit": float(values[index])}
            for index in order[:8]
        ]
        if values.size > oracle_token:
            captured["oracle_token"] = {
                "token_id": int(oracle_token),
                "logit": float(values[oracle_token]),
                "rank": int(np.where(order == oracle_token)[0][0]),
                "of": int(values.size),
            }
        return original(ctx, sub, descriptor)

    _REGISTRY[(int(Major.SELECTION), int(Selection.ARGMAX))] = spy
    return original


def run_store(store: str, prompt: list[int], oracle_token: int) -> dict[str, object]:
    device, driver, identity = _device(store)
    captured: dict[str, object] = {}
    original = _spy_argmax(captured, oracle_token)
    try:
        result = driver.generate(prompt, max_new_tokens=1).to_dict()
    finally:
        _REGISTRY[(int(Major.SELECTION), int(Selection.ARGMAX))] = original
    emitted = list(result.get("generated_token_ids") or ())
    return {
        "identity": identity,
        "emitted_token_ids": emitted,
        "stop_reason": result.get("stop_reason"),
        "failure": result.get("failure"),
        "retired_work": sum(
            int(step.get("retired_work", 0)) for step in result.get("per_step", ())
        ),
        "agrees_with_oracle": bool(emitted) and emitted[0] == oracle_token,
        "distribution": captured,
    }


def prompt_dependence(store: str, prompt: list[int]) -> dict[str, object]:
    """Does the emitted token depend on the prompt at all?

    A forward pass whose output ignores its input is a specific, known fault --
    an operand addressed by a launch counter rather than by the token id -- and
    it looks exactly like an arithmetic divergence from the outside.  Three
    prompts that produce three tokens rule it out; three that produce one do not
    merely suggest it, they establish it.
    """
    probes = {
        "oracle_prompt": list(prompt),
        "reversed": list(reversed(prompt)),
        "constant": [7] * len(prompt),
    }
    emitted: dict[str, object] = {}
    for label, ids in probes.items():
        device, driver, _identity = _device(store)
        result = driver.generate(ids, max_new_tokens=1).to_dict()
        emitted[label] = {
            "prompt_token_ids": ids,
            "emitted_token_ids": list(result.get("generated_token_ids") or ()),
            "failure": result.get("failure"),
        }
    distinct = {
        tuple(entry["emitted_token_ids"]) for entry in emitted.values()  # type: ignore[index]
    }
    return {
        "probed_store": store,
        "probes": emitted,
        "distinct_outputs": len(distinct),
        "output_depends_on_input": len(distinct) > 1,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--store", action="append", choices=sorted(STORES),
                        help="repeat to select stores; default is all of them")
    arguments = parser.parse_args()
    stores = arguments.store or sorted(STORES)

    load_engines()
    oracle = json.loads(ORACLE.read_text())
    case = oracle["results"][WORKLOAD]
    prompt = list(case["prompt_token_ids"])
    expected = list(case["generated_token_ids"])

    cases = {
        store: run_store(store, prompt, expected[0]) for store in stores
    }
    emitting = [
        store for store in stores if cases[store]["emitted_token_ids"]
    ]
    body = {
        "schema": "opentallas.abi3.reduced_token_walk.v1",
        "model_id": "deepseek-v4.1-flash-reduced-v1",
        "workload_id": WORKLOAD,
        "prompt_token_ids": prompt,
        "oracle": {
            "artifact": str(ORACLE.relative_to(ROOT)),
            "sha256": sha256(ORACLE),
            "generated_token_ids": expected,
            "checkpoint_lock_id": oracle["input_identity"]["checkpoint_lock"]["lock_id"],
        },
        "cases": cases,
        "agreement": {
            store: case["agrees_with_oracle"] for store, case in cases.items()
        },
        "stores_agree_with_each_other": len(
            {tuple(case["emitted_token_ids"]) for case in cases.values()}
        ) == 1,
        #: PROBED ON A STORE THAT ACTUALLY EMITS.  Run against a store whose
        #: prefill fails, every probe returns no token, the three agree
        #: trivially, and the field reads "the output does not depend on the
        #: input" -- which is the strongest claim this artifact can make and
        #: would be made by a store that computed nothing at all.
        "prompt_dependence": (
            prompt_dependence(emitting[0], prompt)
            if emitting
            else {"probed": None, "reason": "no store emitted a token"}
        ),
        "producer": {
            "tool": "tools/run_deepseek_v41_reduced_token_walk.py",
            "sha256": sha256(Path(__file__).resolve()),
            "git": git_state(),
        },
        "evidence_class": "functional_device_execution",
        "not_a_claim": [
            "rtl_execution",
            "timing_or_performance",
            "released_model_numerics",
            "agreement_with_the_reference_oracle",
        ],
    }
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n")
    for store, case in cases.items():
        verdict = "AGREES" if case["agrees_with_oracle"] else "DISAGREES"
        print(f"  {store:16s} emitted={case['emitted_token_ids']} "
              f"oracle={expected[:1]} {verdict}")
    print(f"wrote {arguments.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
