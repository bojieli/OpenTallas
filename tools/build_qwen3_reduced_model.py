#!/usr/bin/env python3
"""Build the G1f reduced regression configuration, its weights and its workload.

G1f is the industry's small-config regression: the tapeout configuration is
verified by the pyramid (G1a-G1e), the *regression* configuration is run whole.
This tool constructs that configuration.

Nothing here is fitted to an answer after the fact.  The reduction rule, the
weight construction and the seed-selection rule are all stated below and are
applied in that order; the tool records what each of them produced.

**The reduction rule.**  Every ratio that makes the architecture Qwen3 is
preserved and only magnitudes move:

* ``num_attention_heads / num_key_value_heads == 4``  (the GQA group)
* ``num_attention_heads * head_dim == hidden_size``   (square attention block)
* ``intermediate_size / hidden_size == 3``            (the SwiGLU expansion)
* ``tie_word_embeddings`` false                       (an untied LM head)
* ``rms_norm_eps``, ``rope_theta``, ``hidden_act``, ``attention_bias``,
  ``torch_dtype`` and every other numeric contract identical

so the reduced model runs the same operator sequence under the same numeric
contracts, with fewer layers and smaller dimensions.  ``check`` mode and
``tools/build_abi3_g1f_reduced_end_to_end.py`` verify that claim rather than
restating it.

**The budget.**  The dimensions are chosen from the measured integrated rate of
39,915 MACs/s (docs/CHIP_ARCHITECTURE_DESIGN.md section 11.7) so the *whole*
workload -- prefill, every layer, every generated token -- costs minutes.  The
arithmetic is emitted in the ``budget`` block and is re-derived, not copied.

**The weights.**  Fixed, materialised once, SHA-256 bound by the same
``compiler.frontend.checkpoint.build_checkpoint_lock`` that binds the 16.4 GB
production checkpoint, and read from disk by both the oracle and anything
downstream.  They are not regenerated per run.  Each tensor's values come from
a NumPy Philox stream keyed by ``sha256(seed:tensor_name)``, so the bytes do
not depend on framework initialisation order; RMSNorm gains are ones, which is
the reference implementation's own initialisation for them.

**The seed.**  A regression fixture has to exercise the path it regresses, so
the seed is selected by a rule stated before the search runs:

    the smallest non-negative integer seed for which the reduced model's greedy
    generation from the reduced prompt reproduces the governed workload's own
    shape exactly -- three generated tokens, of which only the last is an
    official reduced EOS id.

The search is recorded (``seeds_tried``, and what seed 0 produced) so a reader
can see that it happened and what it changed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing as mp
import os
from pathlib import Path
import sys
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from compiler.frontend.checkpoint import (  # noqa: E402
    CHECKPOINT_SOURCE_SCHEMA,
    build_checkpoint_lock,
)
from runtime.abi3.capability import canonical_json  # noqa: E402

SCHEMA = "opentallas.abi3.qwen3_reduced_model.v1"
MODEL_ID = "qwen3-reduced-v1"
WORKLOAD_ID = "TA-QW-REDUCED-EOS-1"
GOVERNED_WORKLOAD_ID = "TA-QW-EOS-1"

FULL_CONFIG = ROOT / "compiler/models/qwen3-8b/config.json"
GOVERNED_WORKLOAD = ROOT / "build/workloads/qwen3-8b/TA-QW-EOS-1.json"

DEFAULT_SNAPSHOT = ROOT / "build/models/qwen3-reduced-v1"
DEFAULT_MODEL_DIR = ROOT / "compiler/models/qwen3-reduced-v1"
DEFAULT_WORKLOAD_DIR = ROOT / "build/workloads/qwen3-reduced-v1"
DEFAULT_LOCK = ROOT / "results/abi3/qwen3_reduced_checkpoint.lock.json"

#: The measured integrated rate, docs/CHIP_ARCHITECTURE_DESIGN.md section 11.7.
MEASURED_MACS_PER_SECOND = 39915
#: The full workload's cost at that rate, the figure G1's does_not_establish
#: clause carries.  Used only to state the ratio.
FULL_WORKLOAD_MACS = 143_889_104_896

#: The reduced dimensions.  Each is the full model's value divided by the
#: stated factor; the invariants above hold for both.
REDUCTION = {
    "hidden_size": (4096, 128),
    "num_attention_heads": (32, 8),
    "num_key_value_heads": (8, 2),
    "head_dim": (128, 16),
    "intermediate_size": (12288, 384),
    "num_hidden_layers": (36, 4),
    "vocab_size": (151936, 4096),
}
#: Fields that are dimensional consequences of the above rather than contracts.
DERIVED_FIELDS = ("max_window_layers", "bos_token_id", "eos_token_id")


class ReducedModelError(RuntimeError):
    """The reduced configuration cannot be built as specified."""


def _repo_relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(4 * 1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def reduced_config(full: dict[str, Any]) -> dict[str, Any]:
    """Apply the reduction rule and check every preserved invariant."""

    for field, (expected, _) in REDUCTION.items():
        if int(full[field]) != expected:
            raise ReducedModelError(
                f"the full config's {field} is {full[field]}, the reduction "
                f"rule was written against {expected}"
            )
    body = dict(full)
    for field, (_, value) in REDUCTION.items():
        body[field] = value
    body["max_window_layers"] = body["num_hidden_layers"]
    vocab = int(body["vocab_size"])
    body["bos_token_id"] = int(full["bos_token_id"]) % vocab
    body["eos_token_id"] = int(full["eos_token_id"]) % vocab

    invariants = {
        "gqa_group": (
            int(full["num_attention_heads"]) // int(full["num_key_value_heads"]),
            int(body["num_attention_heads"]) // int(body["num_key_value_heads"]),
        ),
        "heads_times_head_dim_is_hidden": (
            int(full["num_attention_heads"]) * int(full["head_dim"])
            == int(full["hidden_size"]),
            int(body["num_attention_heads"]) * int(body["head_dim"])
            == int(body["hidden_size"]),
        ),
        "swiglu_expansion": (
            int(full["intermediate_size"]) / int(full["hidden_size"]),
            int(body["intermediate_size"]) / int(body["hidden_size"]),
        ),
    }
    for name, (want, got) in invariants.items():
        if want != got:
            raise ReducedModelError(
                f"the reduction breaks invariant {name}: full {want}, reduced {got}"
            )
    return body


def budget(config: dict[str, Any], prompt_tokens: int, generated_tokens: int) -> dict:
    """The whole workload's MAC count, derived rather than asserted."""

    hidden = int(config["hidden_size"])
    heads = int(config["num_attention_heads"])
    kv_heads = int(config["num_key_value_heads"])
    head_dim = int(config["head_dim"])
    inter = int(config["intermediate_size"])
    layers = int(config["num_hidden_layers"])
    vocab = int(config["vocab_size"])

    per_layer = (
        2 * hidden * heads * head_dim
        + 2 * hidden * kv_heads * head_dim
        + 3 * hidden * inter
    )
    positions = prompt_tokens + generated_tokens
    # Two accountings, both stated.  "positions" is the convention section 11.7
    # uses for the full workload (every position through the trunk and the LM
    # head); "transactions" is what the driver actually submits -- one prefill
    # span of `prompt_tokens` rows and `generated_tokens - 1` decode rows, with
    # the LM head on one row per transaction.
    trunk_positions = positions * layers * per_layer
    head_positions = positions * hidden * vocab
    attention_positions = sum(
        2 * heads * head_dim * context for context in range(1, positions + 1)
    ) * layers

    trunk_rows = prompt_tokens + generated_tokens - 1
    contexts = list(range(1, prompt_tokens + 1)) + [
        prompt_tokens + step for step in range(1, generated_tokens)
    ]
    trunk_transactions = trunk_rows * layers * per_layer
    head_transactions = generated_tokens * hidden * vocab
    attention_transactions = (
        sum(2 * heads * head_dim * context for context in contexts) * layers
    )

    total_positions = trunk_positions + head_positions + attention_positions
    total_transactions = (
        trunk_transactions + head_transactions + attention_transactions
    )
    return {
        "measured_macs_per_second": MEASURED_MACS_PER_SECOND,
        "measured_rate_source": (
            "docs/CHIP_ARCHITECTURE_DESIGN.md section 11.7: 200,231 simulated "
            "cycles/s and 5.0164 cycles per MAC"
        ),
        "per_layer_macs_per_row": per_layer,
        "per_layer_arithmetic": (
            f"2*{hidden}*{heads * head_dim} + 2*{hidden}*{kv_heads * head_dim} "
            f"+ 3*{hidden}*{inter} = {per_layer}"
        ),
        "positions_accounting": {
            "note": (
                "one trunk row and one LM head row per position, the convention "
                "section 11.7 uses for the full workload's 143,889,104,896 MACs"
            ),
            "positions": positions,
            "trunk_macs": trunk_positions,
            "lm_head_macs": head_positions,
            "attention_macs": attention_positions,
            "total_macs": total_positions,
            "seconds_at_measured_rate": round(
                total_positions / MEASURED_MACS_PER_SECOND, 1
            ),
            "minutes_at_measured_rate": round(
                total_positions / MEASURED_MACS_PER_SECOND / 60, 2
            ),
        },
        "transactions_accounting": {
            "note": (
                "what runtime.driver.GenerationDriver actually submits: one "
                f"prefill span of {prompt_tokens} rows at context "
                f"{prompt_tokens}, then {generated_tokens - 1} decode rows, "
                "with the LM head on one row per transaction"
            ),
            "trunk_rows": trunk_rows,
            "lm_head_rows": generated_tokens,
            "trunk_macs": trunk_transactions,
            "lm_head_macs": head_transactions,
            "attention_macs": attention_transactions,
            "total_macs": total_transactions,
            "seconds_at_measured_rate": round(
                total_transactions / MEASURED_MACS_PER_SECOND, 1
            ),
            "minutes_at_measured_rate": round(
                total_transactions / MEASURED_MACS_PER_SECOND / 60, 2
            ),
        },
        "full_workload_macs": FULL_WORKLOAD_MACS,
        "reduction_factor_against_full_workload": round(
            FULL_WORKLOAD_MACS / total_positions, 1
        ),
        "full_workload_days_at_measured_rate": round(
            FULL_WORKLOAD_MACS / MEASURED_MACS_PER_SECOND / 86400, 1
        ),
    }


def tensor_shapes(config: dict[str, Any]) -> list[tuple[str, tuple[int, ...]]]:
    """Every parameter of Qwen3ForCausalLM at this configuration, in order."""

    hidden = int(config["hidden_size"])
    heads = int(config["num_attention_heads"])
    kv_heads = int(config["num_key_value_heads"])
    head_dim = int(config["head_dim"])
    inter = int(config["intermediate_size"])
    layers = int(config["num_hidden_layers"])
    vocab = int(config["vocab_size"])
    out: list[tuple[str, tuple[int, ...]]] = [
        ("model.embed_tokens.weight", (vocab, hidden))
    ]
    for layer in range(layers):
        base = f"model.layers.{layer}"
        out.extend(
            [
                (f"{base}.input_layernorm.weight", (hidden,)),
                (f"{base}.self_attn.q_proj.weight", (heads * head_dim, hidden)),
                (f"{base}.self_attn.k_proj.weight", (kv_heads * head_dim, hidden)),
                (f"{base}.self_attn.v_proj.weight", (kv_heads * head_dim, hidden)),
                (f"{base}.self_attn.o_proj.weight", (hidden, heads * head_dim)),
                (f"{base}.self_attn.q_norm.weight", (head_dim,)),
                (f"{base}.self_attn.k_norm.weight", (head_dim,)),
                (f"{base}.post_attention_layernorm.weight", (hidden,)),
                (f"{base}.mlp.gate_proj.weight", (inter, hidden)),
                (f"{base}.mlp.up_proj.weight", (inter, hidden)),
                (f"{base}.mlp.down_proj.weight", (hidden, inter)),
            ]
        )
    out.append(("model.norm.weight", (hidden,)))
    out.append(("lm_head.weight", (vocab, hidden)))
    return out


def _is_gain(name: str) -> bool:
    return name.endswith("norm.weight") or name.endswith("layernorm.weight")


def build_state(config: dict[str, Any], seed: int) -> dict[str, "np.ndarray"]:
    """The reduced weights, as bfloat16-rounded float32 arrays."""

    import torch  # local: the reference implementation's own dtype

    state: dict[str, Any] = {}
    std = float(config["initializer_range"])
    for name, shape in tensor_shapes(config):
        if _is_gain(name):
            array = np.ones(shape, dtype=np.float32)
        else:
            key = int.from_bytes(
                hashlib.sha256(f"{seed}:{name}".encode("utf-8")).digest()[:8], "big"
            )
            array = (
                np.random.default_rng(key)
                .normal(0.0, std, shape)
                .astype(np.float32)
            )
        state[name] = torch.from_numpy(array).to(torch.bfloat16)
    return state


def _build_model(config: dict[str, Any], state):
    import torch
    from transformers import Qwen3Config, Qwen3ForCausalLM

    body = {
        k: v
        for k, v in config.items()
        if k not in ("architectures", "transformers_version", "torch_dtype")
    }
    hf = Qwen3Config(**body)
    hf._attn_implementation = "eager"  # noqa: SLF001
    torch.manual_seed(0)
    model = Qwen3ForCausalLM(hf).to(torch.bfloat16).eval()
    if state is not None:
        model.load_state_dict(state)
    return model


def _greedy_ids(model, prompt: list[int], *, max_new_tokens: int, eos: set[int]):
    """The same greedy loop the full oracle uses (tools/run_qwen3_reference_oracle.py)."""

    import torch

    from tools.run_qwen3_reference_oracle import _greedy

    return _greedy(
        model,
        torch.tensor([prompt], dtype=torch.long),
        max_new_tokens=max_new_tokens,
        eos_ids=eos,
    )


def _trial(argument):
    # One thread per worker.  The search runs one process per core and torch
    # defaults to one thread per core inside each of them, which oversubscribes
    # the machine by two orders of magnitude: a 54 ms trial measured 6 s.
    import torch

    torch.set_num_threads(1)
    seed, config, prompt, max_new_tokens, eos = argument
    model = _build_model(config, build_state(config, seed))
    generated = _greedy_ids(
        model, prompt, max_new_tokens=max_new_tokens, eos=set(eos)
    )
    return seed, [int(t) for t in generated]


def _shape_matches(generated: list[int], eos: set[int], want_tokens: int) -> bool:
    return (
        len(generated) == want_tokens
        and generated[-1] in eos
        and not any(token in eos for token in generated[:-1])
    )


def select_seed(
    config: dict[str, Any],
    prompt: list[int],
    *,
    max_new_tokens: int,
    eos: set[int],
    want_tokens: int,
    limit: int,
    jobs: int,
) -> dict[str, Any]:
    """The stated seed-selection rule, applied and recorded."""

    argument = (config, prompt, max_new_tokens, sorted(eos))
    tried = 0
    seed_zero: list[int] | None = None
    chosen: tuple[int, list[int]] | None = None
    with mp.Pool(processes=jobs) as pool:
        block = max(jobs * 4, 16)
        for start in range(0, limit, block):
            batch = [
                (seed, *argument) for seed in range(start, min(start + block, limit))
            ]
            for seed, generated in sorted(pool.imap_unordered(_trial, batch)):
                tried += 1
                if seed == 0:
                    seed_zero = generated
                if chosen is None and _shape_matches(generated, eos, want_tokens):
                    chosen = (seed, generated)
            if chosen is not None:
                break
    if chosen is None:
        raise ReducedModelError(
            f"no seed below {limit} reproduces the governed workload's shape "
            f"({want_tokens} generated tokens ending in an official reduced EOS)"
        )
    return {
        "rule": (
            "the smallest non-negative integer seed for which the reduced "
            "model's greedy generation from the reduced prompt reproduces the "
            "governed workload's shape exactly: "
            f"{want_tokens} generated tokens, of which only the last is an "
            "official reduced EOS id"
        ),
        "rule_stated_before_search": True,
        "seed": chosen[0],
        "generated_token_ids": chosen[1],
        "seeds_tried": tried,
        "search_limit": limit,
        "seed_zero_generated_token_ids": seed_zero,
        "why": (
            "a regression fixture has to exercise the path it regresses; the "
            "EOS ids of an untrained model are not reachable by accident, so "
            "the seed is chosen by a rule fixed in advance rather than the "
            "config being edited after the generation was read"
        ),
    }


def write_snapshot(
    snapshot: Path, config: dict[str, Any], state, *, model_dir: Path, seed: int
) -> dict[str, Any]:
    """Materialise the reduced checkpoint in the layout the lock reads."""

    from safetensors.torch import save_file

    snapshot.mkdir(parents=True, exist_ok=True)
    config_bytes = (json.dumps(config, indent=2, sort_keys=True) + "\n").encode()
    (snapshot / "config.json").write_bytes(config_bytes)
    model_dir.mkdir(parents=True, exist_ok=True)
    (model_dir / "config.json").write_bytes(config_bytes)

    generation = {
        "bos_token_id": int(config["bos_token_id"]),
        "eos_token_id": int(config["eos_token_id"]),
        "do_sample": False,
        "transformers_version": "4.51.0",
    }
    (snapshot / "generation_config.json").write_bytes(
        (json.dumps(generation, indent=2, sort_keys=True) + "\n").encode()
    )

    shard = "model-00001-of-00001.safetensors"
    save_file(
        {name: tensor.contiguous() for name, tensor in state.items()},
        str(snapshot / shard),
        metadata={"format": "pt"},
    )
    total = sum(int(tensor.numel()) * 2 for tensor in state.values())
    index = {
        "metadata": {"total_size": total},
        "weight_map": {name: shard for name in state},
    }
    (snapshot / "model.safetensors.index.json").write_bytes(
        (json.dumps(index, indent=2, sort_keys=True) + "\n").encode()
    )

    paths = [
        "config.json",
        "generation_config.json",
        shard,
        "model.safetensors.index.json",
    ]
    # The "revision" of a constructed checkpoint is its own content: the
    # digest of the configuration and the seed that produced every byte.  It
    # names the thing it binds, which is what a commit hash does for a
    # published snapshot.
    revision = hashlib.sha256(
        config_bytes + f"|seed={seed}".encode("utf-8")
    ).hexdigest()[:40]
    source = {
        "schema": CHECKPOINT_SOURCE_SCHEMA,
        "repository": f"opentallas/{MODEL_ID}",
        "revision": revision,
        "remote_code_policy": "disabled",
        "checkpoint_index": "model.safetensors.index.json",
        "required_files": sorted(
            p
            for p in paths
            if p not in (shard, "model.safetensors.index.json")
        ),
        "expected_files": [
            {
                "path": name,
                "sha256": _sha256_file(snapshot / name),
                "size_bytes": (snapshot / name).stat().st_size,
            }
            for name in sorted(paths)
        ],
    }
    (model_dir / "checkpoint_source.json").write_bytes(
        canonical_json(source) + b"\n"
    )
    return source


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument("--model-dir", type=Path, default=DEFAULT_MODEL_DIR)
    parser.add_argument("--workload-dir", type=Path, default=DEFAULT_WORKLOAD_DIR)
    parser.add_argument("--lock", type=Path, default=DEFAULT_LOCK)
    parser.add_argument("--seed-limit", type=int, default=200000)
    parser.add_argument("--jobs", type=int, default=min(16, os.cpu_count() or 1))
    parser.add_argument("--seed", type=int, default=None, help="skip the search")
    parser.add_argument("--summary", type=Path, default=None)
    arguments = parser.parse_args()

    full = json.loads(FULL_CONFIG.read_text(encoding="utf-8"))
    governed = json.loads(GOVERNED_WORKLOAD.read_text(encoding="utf-8"))
    config = reduced_config(full)
    vocab = int(config["vocab_size"])

    prompt = [int(token) % vocab for token in governed["token_ids"]]
    eos_full = {int(full["eos_token_id"]), int(full["bos_token_id"])}
    eos = {token % vocab for token in eos_full}
    if len(eos) != len(eos_full):
        raise ReducedModelError(
            "two official EOS ids collide under the reduced vocabulary"
        )
    max_new = int(governed["max_new_tokens"])
    want_tokens = 3

    if arguments.seed is None:
        selection = select_seed(
            config,
            prompt,
            max_new_tokens=max_new,
            eos=eos,
            want_tokens=want_tokens,
            limit=arguments.seed_limit,
            jobs=arguments.jobs,
        )
    else:
        seed, generated = _trial(
            (arguments.seed, config, prompt, max_new, sorted(eos))
        )
        selection = {
            "rule": "supplied on the command line",
            "rule_stated_before_search": False,
            "seed": seed,
            "generated_token_ids": generated,
            "seeds_tried": 1,
            "search_limit": 1,
            "seed_zero_generated_token_ids": None,
        }
    seed = int(selection["seed"])
    generated = list(selection["generated_token_ids"])

    state = build_state(config, seed)
    source = write_snapshot(
        arguments.snapshot,
        config,
        state,
        model_dir=arguments.model_dir,
        seed=seed,
    )
    lock = build_checkpoint_lock(arguments.snapshot, source)
    arguments.lock.parent.mkdir(parents=True, exist_ok=True)
    arguments.lock.write_bytes(canonical_json(lock) + b"\n")

    workload = {
        "workload_id": WORKLOAD_ID,
        "kind": "chat",
        "description": (
            "G1f reduced regression workload: the governed workload "
            f"{GOVERNED_WORKLOAD_ID} at the reduced configuration.  Its prompt "
            "is that workload's own token ids reduced into the reduced "
            "vocabulary by id % vocab_size, its cap is the same, and its gold "
            "ends in an official reduced EOS after three generated tokens -- "
            "the same shape."
        ),
        "derived_from": {
            "workload_id": GOVERNED_WORKLOAD_ID,
            "path": str(GOVERNED_WORKLOAD.relative_to(ROOT)),
            "digest": governed["digest"],
            "rule": "token_id % vocab_size",
        },
        "max_new_tokens": max_new,
        "prompt_token_count": len(prompt),
        "token_ids": prompt,
        "official_eos_token_ids": sorted(eos),
        "official_eos_token_ids_full_model": sorted(eos_full),
        "model_id": MODEL_ID,
        "metadata": {
            "gate": "G1f",
            "checks": [
                "the last generated token is an official reduced EOS id",
                "generation stops before the cap; a cap stop is a failed gold",
                "exactly three generated tokens, the governed workload's shape",
            ],
        },
    }
    workload["digest"] = hashlib.sha256(canonical_json(workload)).hexdigest()
    arguments.workload_dir.mkdir(parents=True, exist_ok=True)
    workload_path = arguments.workload_dir / f"{WORKLOAD_ID}.json"
    workload_path.write_bytes(canonical_json(workload) + b"\n")
    index_body = {
        "schema": "opentallas.workload_index.v1",
        "model_id": MODEL_ID,
        "workloads": [
            {
                "workload_id": WORKLOAD_ID,
                "path": f"{WORKLOAD_ID}.json",
                "digest": workload["digest"],
                "sha256": _sha256_file(workload_path),
            }
        ],
    }
    (arguments.workload_dir / "index.json").write_bytes(
        canonical_json(index_body) + b"\n"
    )

    summary = {
        "schema": SCHEMA,
        "model_id": MODEL_ID,
        "workload_id": WORKLOAD_ID,
        "reduction": {
            field: {
                "full": full_value,
                "reduced": reduced_value,
                "factor": round(full_value / reduced_value, 4),
            }
            for field, (full_value, reduced_value) in REDUCTION.items()
        },
        "derived_fields": {field: config[field] for field in DERIVED_FIELDS},
        "preserved_contracts": {
            field: full[field]
            for field in sorted(set(full) - set(REDUCTION) - set(DERIVED_FIELDS))
        },
        "config": config,
        "budget": budget(config, len(prompt), len(generated)),
        "seed_selection": selection,
        "snapshot": {
            "path": str(arguments.snapshot),
            "files": source["expected_files"],
            "lock_id": lock["lock_id"],
            "lock_path": _repo_relative(arguments.lock),
            "parameter_tensor_count": len(state),
            "parameter_count": sum(int(t.numel()) for t in state.values()),
        },
        "workload": {
            "path": str(workload_path),
            "digest": workload["digest"],
            "sha256": _sha256_file(workload_path),
            "token_ids": prompt,
            "generated_token_ids": generated,
        },
        "not_a_claim": [
            "the reduced model is a constructed regression fixture, not a "
            "trained model; its token ids establish control flow, composition "
            "and emission, never numerics at full dimension",
        ],
    }
    if arguments.summary is not None:
        arguments.summary.parent.mkdir(parents=True, exist_ok=True)
        arguments.summary.write_bytes(
            canonical_json(summary) + b"\n"
        )
    print(json.dumps(summary["budget"], indent=2))
    print(
        f"seed={seed} tried={selection['seeds_tried']} generated={generated} "
        f"lock={lock['lock_id'][:16]} params={summary['snapshot']['parameter_count']:,}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
