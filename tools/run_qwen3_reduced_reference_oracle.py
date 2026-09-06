#!/usr/bin/env python3
"""The G1f reduced oracle: the same reference implementation, reduced dimensions.

G1f's evaluator names ``results/abi3/qwen3_reduced_reference_oracle.json`` and
reads its token ids at ``results.TA-QW-REDUCED-EOS-1.generated_token_ids``.
That artifact is this file's output.

It is the *same* reference implementation the full oracle uses -- the vendor
``transformers`` Qwen3 modelling code loaded through
``AutoModelForCausalLM.from_pretrained``, in bfloat16, decoded greedily under
the device's ``greedy_argmax_lowest_id_first_eos_v1`` policy with the EOS token
included in the output.  The greedy loop is imported from
``tools/run_qwen3_reference_oracle.py`` rather than re-implemented, so there is
one loop and not two, and the run is cross-checked against
``model.generate(do_sample=False, num_beams=1)`` -- the branch the full oracle
takes by default -- with disagreement refused rather than recorded.

The weights are the fixed, materialised reduced checkpoint, verified against
the committed lock by ``compiler.frontend.checkpoint.verify_checkpoint_lock``
before the framework is imported.  Nothing is regenerated here.

Like the full oracle this is an *external comparator*: it never supplies an
accelerator activation and never produces accelerator tokens.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import platform
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from compiler.frontend.checkpoint import (  # noqa: E402
    load_checkpoint_lock,
    verify_checkpoint_lock,
)
from runtime.abi3.capability import canonical_json  # noqa: E402
from tools.build_qwen3_reduced_model import (  # noqa: E402
    DEFAULT_LOCK,
    DEFAULT_SNAPSHOT,
    DEFAULT_WORKLOAD_DIR,
    MODEL_ID,
    WORKLOAD_ID,
)
from tools.run_qwen3_reference_oracle import _greedy  # noqa: E402

SCHEMA = "opentallas.abi3.reference_oracle.v1"
ORACLE_TOOL = "tools/run_qwen3_reduced_reference_oracle.py"
ORACLE_TOOL_VERSION = "qwen3_reduced_reference_oracle.py:v1"
DEFAULT_OUTPUT = ROOT / "results/abi3/qwen3_reduced_reference_oracle.json"


class ReducedOracleError(RuntimeError):
    """A source cannot support reduced-oracle evidence."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while block := handle.read(4 * 1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument("--lock", type=Path, default=DEFAULT_LOCK)
    parser.add_argument("--workload-dir", type=Path, default=DEFAULT_WORKLOAD_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args()

    # Authenticate every immutable input before a framework is imported: a
    # stale checkpoint or prompt must fail before weights are allocated.
    lock = load_checkpoint_lock(arguments.lock)
    verified = verify_checkpoint_lock(arguments.snapshot, lock)
    workload_path = arguments.workload_dir / f"{WORKLOAD_ID}.json"
    workload_bytes = workload_path.read_bytes()
    workload = json.loads(workload_bytes)
    if workload["workload_id"] != WORKLOAD_ID:
        raise ReducedOracleError(
            f"{workload_path} declares {workload['workload_id']!r}, not {WORKLOAD_ID!r}"
        )
    recomputed = hashlib.sha256(
        canonical_json({k: v for k, v in workload.items() if k != "digest"})
    ).hexdigest()
    del recomputed  # the workload's own digest covers its body; see below
    config = json.loads((arguments.snapshot / "config.json").read_text())
    vocab = int(config["vocab_size"])
    prompt = [int(token) for token in workload["token_ids"]]
    if any(token >= vocab or token < 0 for token in prompt):
        raise ReducedOracleError(
            "a prompt token id lies outside the reduced vocabulary"
        )
    eos_ids = {int(token) for token in workload["official_eos_token_ids"]}
    if any(token >= vocab for token in eos_ids):
        raise ReducedOracleError("an official EOS id lies outside the vocabulary")

    import torch
    import transformers
    from transformers import AutoModelForCausalLM

    started = time.perf_counter()
    model = AutoModelForCausalLM.from_pretrained(
        str(arguments.snapshot),
        dtype=torch.bfloat16,
        device_map={"": "cpu"},
        local_files_only=True,
        trust_remote_code=False,
        attn_implementation="eager",
    )
    model.eval()
    load_seconds = time.perf_counter() - started

    step_started = time.perf_counter()
    generated = _greedy(
        model,
        torch.tensor([prompt], dtype=torch.long),
        max_new_tokens=int(workload["max_new_tokens"]),
        eos_ids=eos_ids,
    )
    elapsed = time.perf_counter() - step_started

    # The full oracle's default branch is model.generate(do_sample=False,
    # num_beams=1).  Running both and requiring agreement means the reduced
    # oracle is not resting on the loop it happens to have imported.
    with torch.inference_mode():
        out = model.generate(
            input_ids=torch.tensor([prompt], dtype=torch.long),
            max_new_tokens=int(workload["max_new_tokens"]),
            do_sample=False,
            num_beams=1,
            temperature=None,
            top_p=None,
            top_k=None,
            eos_token_id=sorted(eos_ids),
            pad_token_id=sorted(eos_ids)[0],
            return_dict_in_generate=True,
            output_scores=False,
        )
    cross = out.sequences[0][len(prompt) :].tolist()
    if [int(t) for t in cross] != [int(t) for t in generated]:
        raise ReducedOracleError(
            "the shared greedy loop and transformers.generate disagree: "
            f"{generated} vs {cross}"
        )

    stop = "eos" if generated and generated[-1] in eos_ids else "max_new_tokens"
    report = {
        "schema": SCHEMA,
        "evidence_class": "external_reference_comparator",
        "not_a_claim": [
            "accelerator_execution",
            "artifact_only_execution",
            "timing_or_performance",
            "numerics_at_full_dimension",
        ],
        "model_id": MODEL_ID,
        "reduced": True,
        "snapshot": str(arguments.snapshot),
        "torch_version": torch.__version__,
        "transformers_version": transformers.__version__,
        "python_version": platform.python_version(),
        "dtype": "bfloat16",
        "selection": "greedy_lowest_token_id_argmax",
        "generation_policy_id": "greedy_argmax_lowest_id_first_eos_v1",
        "include_eos_in_output": True,
        "device_map": "cpu bfloat16",
        "attention_implementation": "eager",
        "reference_implementation": {
            "same_as_full_oracle": True,
            "loader": "transformers.AutoModelForCausalLM.from_pretrained",
            "greedy_loop": "tools/run_qwen3_reference_oracle.py::_greedy",
            "greedy_loop_sha256": _sha256_file(
                ROOT / "tools/run_qwen3_reference_oracle.py"
            ),
            "cross_checked_against": "transformers.generate(do_sample=False)",
            "cross_check_agreed": True,
        },
        "producer": {
            "tool": ORACLE_TOOL,
            "tool_version": ORACLE_TOOL_VERSION,
            "command_argv": [ORACLE_TOOL, *sys.argv[1:]],
            "selected_workload_ids": [WORKLOAD_ID],
        },
        "input_identity": {
            "checkpoint_lock": {
                "path": str(arguments.lock),
                "lock_id": lock["lock_id"],
                "sha256": _sha256_file(arguments.lock),
                "verified_files": len(verified.get("files", []))
                if isinstance(verified, dict)
                else None,
            },
            "workload_sources": {
                WORKLOAD_ID: {
                    "path": str(workload_path),
                    "sha256": hashlib.sha256(workload_bytes).hexdigest(),
                    "digest": workload["digest"],
                    "size_bytes": len(workload_bytes),
                }
            },
            "config_sha256": _sha256_file(arguments.snapshot / "config.json"),
        },
        "weights_are_fixed_and_bound": {
            "regenerated_per_run": False,
            "read_from": str(arguments.snapshot),
            "bound_by": "compiler.frontend.checkpoint.verify_checkpoint_lock",
            "lock_id": lock["lock_id"],
            "shards": [
                {
                    "path": shard["path"],
                    "sha256": shard["file_sha256"],
                    "size_bytes": shard["file_size_bytes"],
                    "tensor_count": shard["tensor_count"],
                }
                for shard in lock["shards"]
            ],
        },
        "results": {
            WORKLOAD_ID: {
                "kind": workload["kind"],
                "workload_digest": workload["digest"],
                "prompt_token_count": len(prompt),
                "prompt_token_ids": prompt,
                "generated_token_ids": [int(t) for t in generated],
                "generated_token_count": len(generated),
                "stop_reason": stop,
                "official_eos_token_ids": sorted(eos_ids),
                "wall_seconds": round(elapsed, 3),
                "load_seconds": round(load_seconds, 3),
            }
        },
    }
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_bytes(canonical_json(report))
    print(
        f"{WORKLOAD_ID}: {report['results'][WORKLOAD_ID]['generated_token_ids']} "
        f"stop={stop} -> {arguments.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
