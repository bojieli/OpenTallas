#!/usr/bin/env python3
"""Build the V4.1 G1f reduced regression configuration, its weights and its workload.

This is the DeepSeek-V4.1-Flash counterpart of
``tools/build_qwen3_reduced_model.py``, written to plan section 10.2 of
``docs/DEEPSEEK_V41_FLASH_ROM_IMPLEMENTATION_PLAN.md`` (WP-L): *"hidden, expert
width and expert count reduced, 40 layers and the CSA2 mode sequence kept
exactly, because the mode sequence is what is under test."*

Nothing here is fitted to an answer after the fact.  The reduction rule, the
weight construction and the seed-selection rule are stated below, applied in
that order, and each of them records what it produced.

**The reduction rule.**  Two classes of field, and the class decides the
treatment:

*Kept exactly* -- everything that makes the architecture V4.1 rather than a
generic MoE transformer: ``n_layers`` 40 and ``n_mtp_layers`` 3; the 43-entry
``compress_ratios`` sequence and the ``kv_source_layers`` /
``index_source_layers`` / ``candidate_source_layer`` / ``engram_layer_ids`` /
``dspark_target_layer_ids`` index sets that give it its CSA2 mode sequence;
every arity (``n_heads``, ``index_n_heads``, ``engram_n_heads``, ``o_groups``,
``n_shared_experts``, ``n_activated_experts``, ``candidate_block_size``,
``hc_mult``, ``hc_sinkhorn_iters``, ``engram_max_ngram_size``, ``window_size``);
and every numeric contract (``norm_eps``, ``score_func``, ``route_scale``,
``swiglu_limit``, ``norm_topk_prob``, the two RoPE thetas and the YaRN
parameters, ``hc_eps``, ``dtype`` fp8 and ``expert_dtype`` fp4).

*Reduced* -- magnitudes only, by ``--width-factor`` (default 32).  Widths are
reduced to a multiple of the release's own 32-element quantization block, and
never below one block, because the release's own kernel refuses anything else::

    assert N % block_size == 0

(``inference/kernel.py`` ``act_quant``, line 108, at the pinned revision).  A
width of 72 -- which is what 2,304 / 32 would give ``moe_inter_dim`` -- fails
that assertion inside the first expert GEMM, so the block, not the factor, is
what sets the floor.  ``rope_head_dim`` is then *derived* from the reduced
``head_dim`` so that the released ``head_dim / rope_head_dim`` ratio of 8 is
preserved exactly rather than rounded.

**The Engram tables.**  ``engram_num_embeddings`` is not scaled: it is
*derived*, by handing the reduced arguments to the release's own
``engram.EngramLayout.from_args`` and summing the prime bucket ranges it draws.
That derivation is checked, on every run, by re-deriving at the RELEASED bucket
size and requiring the released pair ``[384006168, 384016682]`` back.  The
bucket size itself is reduced by the smallest power of two for which the two
tables keep no more than their released share of the fixture's bytes, and both
shares are recorded.

**The weights.**  Fixed, materialised once, SHA-256 bound by the same
``compiler.frontend.checkpoint.build_checkpoint_lock`` that binds the 510 GB
production checkpoint.  Each tensor's values come from a NumPy Philox stream
keyed by ``sha256(seed:tensor_name)``, so the bytes do not depend on framework
initialisation order.  The construction is by storage format, because this model
has five of them:

* ``float8_e8m0fnu`` block scales are the byte ``0x7F``, exactly 2**0.  A scale
  is not a weight: the codes it scales are drawn in range already, so the
  fixture's scale is the identity and the dequantised weight is the stored code.
* ``float4_e2m1fn_x2`` routed-expert weights are raw stream bytes.  E2M1 has no
  NaN and no infinity, so every byte is a valid pair of finite weights.
* ``float8_e4m3fn`` weights are ``N(0, initializer_range)`` cast to the format.
* RMSNorm gains and the Engram gate's ``q_weight`` / ``k_weight`` are ones,
  which is the reference implementation's own initialisation for them.
* every other parameter is ``N(0, initializer_range)``, with
  ``initializer_range`` read from the released ``text_config``.

**The seed.**  A regression fixture has to exercise the path it regresses, so
the seed is selected by a rule stated before the search runs:

    the smallest non-negative integer seed for which the reduced model's greedy
    generation from the reduced prompt terminates in an official reduced EOS id
    strictly before the cap, with no official EOS id before the last token.

``TA-DS41-EOS-1`` carries no gold of its own -- its ``gold_status`` is
"unverified" -- so, unlike the Qwen predecessor, there is no governed token
count to reproduce.  The rule therefore fixes the *shape* (stops on EOS, not on
the cap) and records the count the search found rather than requiring one.

**What this is not.**  The reduced model is a constructed regression fixture,
not a trained model, and it is not a V4.1 reference oracle: it establishes
control flow, composition and emission at reduced dimension.  No number it
produces is a TPOT and none of its token ids says anything about the shipped
checkpoint's answers.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import importlib
import json
import os
from pathlib import Path
import re
import sys
import time
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from compiler.frontend.checkpoint import (  # noqa: E402
    CHECKPOINT_SOURCE_SCHEMA,
    build_checkpoint_lock,
)
from compiler.frontend.deepseek_v4_releases import V41_FLASH  # noqa: E402
from runtime.abi3.capability import canonical_json  # noqa: E402

SCHEMA = "opentallas.abi3.deepseek_v41_reduced_model.v1"
MODEL_ID = "deepseek-v4.1-flash-reduced-v1"
WORKLOAD_ID = "TA-DS41-REDUCED-EOS-1"
GOVERNED_WORKLOAD_ID = "TA-DS41-EOS-1"
PLAN = "docs/DEEPSEEK_V41_FLASH_ROM_IMPLEMENTATION_PLAN.md"
WORK_PACKAGE = "WP-L"

MODEL_DIR_FULL = ROOT / "compiler/models/deepseek-v4.1-flash"
FULL_ROOT_CONFIG = MODEL_DIR_FULL / "config.json"
FULL_INFERENCE_CONFIG = MODEL_DIR_FULL / "inference_config.json"
GOVERNED_WORKLOAD = (
    ROOT / "build/workloads/deepseek-v4.1-flash" / f"{GOVERNED_WORKLOAD_ID}.json"
)

DEFAULT_SNAPSHOT = ROOT / "build/models/deepseek-v4.1-flash-reduced-v1"
DEFAULT_MODEL_DIR = ROOT / "compiler/models/deepseek-v4.1-flash-reduced-v1"
DEFAULT_WORKLOAD_DIR = ROOT / "build/workloads/deepseek-v4.1-flash-reduced-v1"
DEFAULT_LOCK = ROOT / "results/abi3/deepseek_v41_reduced_checkpoint.lock.json"
DEFAULT_SUMMARY = ROOT / "results/abi3/deepseek_v41_reduced_model.json"

#: The measured integrated rate, docs/CHIP_ARCHITECTURE_DESIGN.md section 11.7 --
#: the same figure and the same citation the Qwen reduced builder uses, so the two
#: ladders' budgets are comparable.
MEASURED_MACS_PER_SECOND = 39915

#: Fields whose value is the architecture rather than its size.  Reducing any of
#: them would change what the G1f run is a witness to.
KEPT_EXACTLY = (
    "n_layers", "n_mtp_layers", "n_heads", "index_n_heads", "engram_n_heads",
    "o_groups", "n_shared_experts", "n_activated_experts",
    "dspark_n_activated_experts", "dspark_block_size", "candidate_block_size",
    "hc_mult", "hc_sinkhorn_iters", "hc_eps", "engram_max_ngram_size",
    "engram_pad_id", "window_size",
    "norm_eps", "score_func", "route_scale", "swiglu_limit",
    "rope_theta", "compress_rope_theta", "rope_factor", "beta_fast",
    "beta_slow", "original_seq_len", "dtype", "expert_dtype",
    "compress_ratios", "kv_source_layers", "index_source_layers",
    "candidate_source_layer", "engram_layer_ids", "dspark_target_layer_ids",
    "dspark_noise_token_id", "image_token_id",
)
#: Widths that carry a per-block quantization scale, so the release's own block
#: size is their floor and their granularity.
BLOCK_WIDTHS = (
    "dim", "moe_inter_dim", "head_dim", "q_lora_rank", "o_lora_rank",
    "index_head_dim", "engram_head_dim", "dspark_markov_rank",
)
#: Counts reduced by the width factor and nothing else -- no block applies to a
#: number of experts, a vocabulary or a top-k.
COUNT_FIELDS = (
    "vocab_size", "n_routed_experts", "dspark_n_routed_experts",
    "index_topk", "candidate_topk_blocks",
)
#: Fields this builder derives rather than either keeping or scaling, each with
#: the rule that derives it.
DERIVED_FIELDS = {
    "rope_head_dim": "head_dim // (released head_dim // released rope_head_dim)",
    "engram_vocab_size": "released bucket size // the engram share factor below",
    "engram_compressed_vocab_size": (
        "engram.build_compressed_token_map of the REDUCED tokenizer, which the "
        "release itself asserts this field against; a reduced vocabulary "
        "normalises onto a smaller compressed space, so the released 99,092 is "
        "not a fact about this vehicle"
    ),
    "engram_num_embeddings": (
        "engram.EngramLayout.from_args of the reduced arguments, bucket primes "
        "summed per engram layer"
    ),
    "max_seq_len": (
        "the workload's prompt length plus its cap, rounded up to the largest "
        "compress ratio so every compressed KV plane holds a whole number of "
        "latents"
    ),
    "max_batch_size": "1; the G1f ladder runs one session",
    "vision_n_layers": "0; see vision_excluded below",
    "temperature": "0; greedy selection, so the vendor sample() is argmax",
}
#: Parameters the reference implementation itself initialises to ones.
GAIN_PARAMETER = re.compile(r"(^|\.)(\w*norm)\.weight$|(^|\.)(q_weight|k_weight)$")

#: The routed experts' own E8M0 block scales, which are the only lever this
#: construction has over the magnitude of an expert projection.
EXPERT_SCALE_PARAMETER = re.compile(r"\.experts\.\d+\.w[123]\.scale$")

#: Exponent written into a routed expert's E8M0 block scale, as a power of two.
#:
#: ZERO WAS A FIDELITY BUG, not a neutral default.  The expert weights are
#: uniform random FP4 nibbles, so they span the whole E2M1 range up to 6.0, and a
#: scale of 2**0 leaves them there.  Measured on the v1 fixture by an independent
#: dequantisation -- numpy, the vendor's own FP4_TABLE, the fixture's own stored
#: bytes -- a 160-wide expert projection then reaches absmax 119.3 with mean 32.6
#: against the architecture's own ``swiglu_limit`` of 10.0, so 99.8% to 100.0% of
#: routed gate and up values saturate the clamp while the SHARED expert (whose
#: weights are FP8 and trained-shaped) sits at absmax 1.008 with none saturating.
#: A fixture whose routed experts are permanently clamped is not a reduction of
#: the architecture: the clamp makes the expert output a function of the SIGNS of
#: its operands, so no two implementations can be compared through it, and
#: ``results/abi3/deepseek_v41_reduced_fixture_saturates.json`` records that in
#: full.
#:
#: The scale is what the format provides for exactly this: it sets the magnitude
#: of a block.  -5 divides the projection by 32, which puts absmax near 3.7 and
#: mean near 1.0 -- inside the limit, and the same order as the shared expert the
#: fixture already builds correctly.  The default stays 0 so the v1 fixture and
#: every artifact pinned to its digest reproduce byte for byte.
EXPERT_SCALE_EXPONENT = 0


def install_cache_view(source: dict[str, Any], snapshot: Path) -> Path:
    """Publish the constructed checkpoint where a hub consumer resolves it.

    ``runtime/sim/generators.py`` derives the Engram compressed token map by
    calling ``huggingface_hub.try_to_load_from_cache(repository, "tokenizer.json",
    revision=...)`` and then checking the bytes against the digest the graph
    declares.  The digest check is the guarantee; the cache is only the lookup.
    This repository does not exist on the Hub -- it is a constructed fixture
    whose "revision" is the digest of its own content -- so the lookup has to be
    satisfied locally or a deployment cannot be built at all:

        opentallas/deepseek-v4.1-flash-reduced-v1 tokenizer.json at revision
        ... is not in the local cache

    Real files are written, never symlinks into ``blobs/``.  A hub cache names
    blobs by the file's git SHA-1, which is shared across repositories, so
    writing a fixture's bytes through a blob symlink can overwrite a *released*
    file that happens to hash the same -- a trap this fixture has already hit
    once from the other direction.  The revision is content-addressed, so a
    rebuild installs a new directory rather than mutating this one.
    """
    root = Path(
        os.environ.get("OPENTALLAS_HF_HOME", Path.home() / ".cache/huggingface/hub")
    )
    view = (
        root
        / f"models--{source['repository'].replace('/', '--')}"
        / "snapshots"
        / str(source["revision"])
    )
    view.mkdir(parents=True, exist_ok=True)
    for record in source["expected_files"]:
        name = record["path"]
        payload = (snapshot / name).read_bytes()
        if hashlib.sha256(payload).hexdigest() != record["sha256"]:
            raise ReducedModelError(
                f"{name} does not match the digest the source contract declares"
            )
        (view / name).write_bytes(payload)
    return view


def write_reduced_tokenizer(snapshot: Path, model_dir: Path, vocab_size: int) -> None:
    """Materialise the reduced tokenizer into the fixture directory."""
    from tools.build_deepseek_v41_reduced_tokenizer import reduce_tokenizer

    released = json.loads((snapshot / "tokenizer.json").read_text(encoding="utf-8"))
    reduced = reduce_tokenizer(released, vocab_size)
    (model_dir / "tokenizer.json").write_text(
        json.dumps(reduced, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (model_dir / "tokenizer_config.json").write_text(
        (snapshot / "tokenizer_config.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )


class ReducedModelError(RuntimeError):
    """The reduced configuration cannot be built as specified."""


# ---------------------------------------------------------------------------
# The release, and the vendor modules the fixture is built out of
# ---------------------------------------------------------------------------
def released_snapshot() -> Path:
    """The pinned V4.1 snapshot directory, from the checkpoint lock's own source."""

    base = Path(
        os.environ.get(
            "OPENTALLAS_HF_HOME", Path.home() / ".cache/huggingface/hub"
        )
    )
    path = (
        base
        / "models--deepseek-ai--DeepSeek-V4.1-Flash/snapshots"
        / V41_FLASH.revision
    )
    if not path.is_dir():
        raise ReducedModelError(
            f"the pinned V4.1 snapshot is not at {path}; this builder runs the "
            "release's own inference/model.py, so the snapshot is required"
        )
    return path


def import_vendor(snapshot: Path) -> tuple[Any, Any]:
    """Import the release's ``model`` and ``engram`` modules.

    ``model.py`` does ``from kernel import ...`` and ``from engram import ...``,
    so ``inference/`` goes on ``sys.path`` rather than the modules being loaded
    by file path -- the same mechanism
    ``runtime/reference/deepseek_v4_oracle.import_vendor`` uses for V4.
    """
    inference = str(snapshot / "inference")
    if inference not in sys.path:
        sys.path.insert(0, inference)
    return (
        importlib.import_module("model"),
        importlib.import_module("engram"),
    )


def quantization_block(root_config: dict[str, Any]) -> int:
    """The release's weight scale block, read off its own quantization_config."""

    block = root_config["quantization_config"]["weight_block_size"]
    if len(set(block)) != 1:
        raise ReducedModelError(
            f"the release's weight_block_size is {block}; this builder's width "
            "rule assumes one block size in both dimensions"
        )
    return int(block[0])


# ---------------------------------------------------------------------------
# The reduction rule
# ---------------------------------------------------------------------------
def reduce_width(value: int, factor: int, block: int) -> int:
    """A reduced width: a whole number of blocks, and never fewer than one."""

    return max(block, ((int(value) // factor) // block) * block)


def reduced_body(
    full: dict[str, Any],
    *,
    factor: int,
    block: int,
    engram_factor: int,
    compressed_vocab_size: int,
) -> dict[str, Any]:
    """Apply the reduction rule to the released flat inference config."""

    unclassified = sorted(
        set(full)
        - set(KEPT_EXACTLY)
        - set(BLOCK_WIDTHS)
        - set(COUNT_FIELDS)
        - set(DERIVED_FIELDS)
        - {
            "vision_dim", "vision_n_heads", "vision_inter_dim",
            "vision_patch_size", "vision_rope_theta", "vision_downsample_ratio",
            "vision_max_n_token", "vision_min_pixels", "vision_max_wh_ratio",
        }
    )
    if unclassified:
        raise ReducedModelError(
            "the released inference config carries fields this reduction rule "
            f"does not classify: {unclassified}.  Classify each one as kept, "
            "block-scaled, counted or derived before building a fixture from it"
        )

    body = dict(full)
    for field in KEPT_EXACTLY:
        value = full[field]
        body[field] = tuple(value) if isinstance(value, list) else value
    for field in BLOCK_WIDTHS:
        body[field] = reduce_width(full[field], factor, block)
    for field in COUNT_FIELDS:
        reduced = int(full[field]) // factor
        if reduced < 1:
            raise ReducedModelError(
                f"{field} reduces to {reduced} at factor {factor}"
            )
        body[field] = reduced

    rope_ratio, remainder = divmod(int(full["head_dim"]), int(full["rope_head_dim"]))
    if remainder:
        raise ReducedModelError(
            f"the release's head_dim {full['head_dim']} is not a whole multiple "
            f"of its rope_head_dim {full['rope_head_dim']}"
        )
    body["rope_head_dim"] = body["head_dim"] // rope_ratio
    if body["rope_head_dim"] % 2:
        raise ReducedModelError(
            f"the reduced rope_head_dim {body['rope_head_dim']} is odd; the "
            "rotation pairs channels, so it has to be even"
        )
    body["engram_vocab_size"] = int(full["engram_vocab_size"]) // engram_factor
    body["engram_compressed_vocab_size"] = int(compressed_vocab_size)
    body["vision_n_layers"] = 0
    body["max_batch_size"] = 1
    body["temperature"] = 0
    if body["index_topk"] > body["candidate_topk_blocks"] * body["candidate_block_size"]:
        raise ReducedModelError(
            "the reduced indexer would select more entries than the candidate "
            "pool offers it"
        )
    return body


def sequence_context(body: dict[str, Any], prompt_tokens: int, cap: int) -> int:
    """``max_seq_len``: the whole run, aligned to every structure that tiles it.

    Two alignments, and the second was missing.

    The compress ratio, so every compressed KV plane holds a whole number of
    latents -- the rule this function was written to.

    AND THE SLIDING WINDOW, because the window tiles the context too. The
    reduction keeps ``window_size`` at 128 exactly, the window being part of the
    mode structure under test, so a capacity that is not a whole number of
    windows is a capacity no deployment can use: the V4.1 export refuses a
    context that is not a whole number of sliding windows, and the RTL's own
    ``ROUTE.WINDOW_INDEX`` admission requires ``window <= slots``. Rounding to
    the compress ratio alone gave 24 against a window of 128, which satisfies
    neither, and the reduced model could be built but not deployed.

    The cost is capacity, not work: the run still touches its own
    prompt_tokens + cap positions, and the KV planes are merely sized for a
    whole window.
    """

    ratios = [int(r) for r in body["compress_ratios"] if int(r) > 0]
    step = max(ratios) if ratios else 1
    window = int(body.get("window_size") or 0)
    if window > 0:
        #: lcm would be the general answer; every shipped window is a multiple
        #: of every shipped ratio, so the window alone is the binding alignment
        #: and a mismatch is worth refusing rather than silently rounding.
        if window % step:
            raise ReducedModelError(
                f"the reduced window {window} is not a multiple of the largest "
                f"compress ratio {step}, so no capacity tiles both"
            )
        step = window
    needed = prompt_tokens + cap
    return ((needed + step - 1) // step) * step


def derive_engram_rows(vendor: Any, engram_mod: Any, body: dict[str, Any]) -> tuple:
    """The bucket-summed table rows, from the release's own EngramLayout."""

    probe = dict(body)
    probe["engram_num_embeddings"] = tuple(1 for _ in body["engram_layer_ids"])
    layout = engram_mod.EngramLayout.from_args(vendor.ModelArgs(**probe))
    if layout is None:
        raise ReducedModelError("the reduced configuration has no engram layers")
    return tuple(
        sum(prime for per_ngram in layer for prime in per_ngram)
        for layer in layout.primes
    )


def check_engram_derivation(
    vendor: Any, engram_mod: Any, body: dict[str, Any], full: dict[str, Any]
) -> dict[str, Any]:
    """Re-derive at the RELEASED bucket size and require the released rows back.

    This is the whole warrant for deriving ``engram_num_embeddings`` instead of
    scaling it: run the same derivation at the released
    ``engram_vocab_size`` and ``engram_n_heads`` and it has to reproduce the
    released ``[384006168, 384016682]`` exactly.  If it does not, the derivation
    is wrong and the reduced rows are not to be trusted either.
    """
    at_release = dict(body)
    at_release["engram_vocab_size"] = int(full["engram_vocab_size"])
    at_release["engram_n_heads"] = int(full["engram_n_heads"])
    at_release["engram_max_ngram_size"] = int(full["engram_max_ngram_size"])
    at_release["engram_layer_ids"] = tuple(full["engram_layer_ids"])
    derived = derive_engram_rows(vendor, engram_mod, at_release)
    released = tuple(int(v) for v in full["engram_num_embeddings"])
    if derived != released:
        raise ReducedModelError(
            "the engram row derivation does not reproduce the release: derived "
            f"{derived}, released {released}"
        )
    return {
        "claim": (
            "engram_num_embeddings is the sum of the release's own prime bucket "
            "ranges, not a scaled magnitude"
        ),
        "at_released_bucket_size": int(full["engram_vocab_size"]),
        "derived": list(derived),
        "released": list(released),
        "agrees": True,
    }


# ---------------------------------------------------------------------------
# The fixture's weights
# ---------------------------------------------------------------------------
def parameter_bytes(model: Any) -> dict[str, int]:
    """Bytes per parameter group, used by the engram share rule and the summary."""

    total = 0
    engram = 0
    for name, parameter in model.named_parameters():
        size = int(parameter.numel()) * int(parameter.element_size())
        total += size
        if ".engram." in name:
            engram += size
    return {"total": total, "engram": engram}


def fill_parameters(model: Any, seed: int, initializer_range: float) -> None:
    """The stated construction, applied by storage format."""

    import torch

    with torch.no_grad():
        for name, parameter in model.named_parameters():
            key = int.from_bytes(
                hashlib.sha256(f"{seed}:{name}".encode("utf-8")).digest()[:8], "big"
            )
            rng = np.random.default_rng(key)
            shape = tuple(parameter.shape)
            if parameter.dtype == torch.float8_e8m0fnu:
                # 0x7F is E8M0's zero exponent: a scale of exactly 2**0.  A
                # routed expert's scale takes EXPERT_SCALE_EXPONENT instead, for
                # the reason recorded beside that constant; the code for exponent
                # ``e`` is ``127 + e``.
                code = 0x7F
                if EXPERT_SCALE_PARAMETER.search(name):
                    code = 0x7F + int(EXPERT_SCALE_EXPONENT)
                    if not 0 <= code <= 0xFE:
                        raise ReducedModelError(
                            f"expert scale exponent {EXPERT_SCALE_EXPONENT} "
                            f"encodes as E8M0 code {code}, outside 0..254"
                        )
                parameter.view(torch.uint8).copy_(
                    torch.full(
                        shape, code, dtype=torch.uint8, device=parameter.device
                    )
                )
            elif parameter.dtype == torch.float4_e2m1fn_x2:
                raw = torch.from_numpy(
                    rng.integers(0, 256, size=shape, dtype=np.uint8)
                ).to(parameter.device)
                parameter.view(torch.uint8).copy_(raw)
            elif GAIN_PARAMETER.search(name):
                parameter.copy_(
                    torch.ones(shape, dtype=parameter.dtype, device=parameter.device)
                )
            else:
                values = rng.normal(0.0, initializer_range, shape).astype(np.float32)
                parameter.copy_(
                    torch.from_numpy(values).to(parameter.device).to(parameter.dtype)
                )


def build_model(vendor: Any, body: dict[str, Any], tokenizer: Any) -> Any:
    """One reduced ``Transformer`` on the default device, uninitialised."""

    import torch

    torch.set_default_dtype(torch.bfloat16)
    torch.set_default_device(
        "cuda" if torch.cuda.is_available() else "cpu"
    )
    torch.manual_seed(0)
    return vendor.Transformer(vendor.ModelArgs(**body), tokenizer)



#: Parameters whose STORAGE dtype in the released checkpoint differs from the
#: dtype the vendor module holds at runtime, by suffix.  Every entry was read
#: off the released checkpoint's own shard headers:
#:
#:   head.weight                            BF16
#:   layers.N.attn.compressor.wkv.weight    BF16   (module says float32)
#:   layers.N.attn.compressor.wgate.weight  BF16   (module says float32)
#:   layers.N.attn.compressor.norm.weight   BF16
#:   mtp.N.markov_head.head.weight          BF16
#:   mtp.N.markov_head.embed.weight         BF16
#:   mtp.N.confidence_head.proj.weight      BF16
#:
#: ``layers.N.attn.attn_sink`` is NOT here: the release stores it F32 and the
#: module declares float32, so storage and runtime agree and there is nothing to
#: round trip.  That is why it never appeared in the derivation's dtype
#: disagreement while its neighbours did.
STORAGE_BF16_SUFFIXES = (
    "head.weight",
    "attn.compressor.wkv.weight",
    "attn.compressor.wgate.weight",
    "attn.compressor.norm.weight",
    "markov_head.head.weight",
    "markov_head.embed.weight",
    "confidence_head.proj.weight",
)


def storage_dtype_for(name: str, torch: Any) -> Any | None:
    """The dtype the released checkpoint stores this parameter in, or None."""

    for suffix in STORAGE_BF16_SUFFIXES:
        if name.endswith(suffix):
            return torch.bfloat16
    return None


def round_trip_storage_dtypes(model: Any) -> int:
    """Put every narrowed parameter through its storage round trip, in place.

    The same reason ``round_trip_wo_a`` exists: a fixture's recorded tokens have
    to be the tokens loading it reproduces, and a parameter the checkpoint stores
    in BF16 while the module holds F32 loses bits on the way out. Generating from
    the F32 values records tokens from precision no loader can reconstruct.
    """

    import torch

    touched = 0
    with torch.no_grad():
        for name, parameter in model.named_parameters():
            storage = storage_dtype_for(name, torch)
            if storage is None or parameter.dtype == storage:
                continue
            parameter.copy_(parameter.detach().to(storage).to(parameter.dtype))
            touched += 1
    return touched


def round_trip_wo_a(model: Any) -> int:
    """Put wo_a through the release's storage round trip, in place.

    THE FIXTURE'S RECORDED TOKENS MUST BE THE TOKENS LOADING IT REPRODUCES, and
    without this they are not. The vendor module holds wo_a as bf16 -- the
    RUNTIME shape -- while the checkpoint stores fp8 with a 32x32-blocked E8M0
    scale, and ``convert.py`` dequantizes between them. Generating from the
    freshly initialised bf16 weights therefore records tokens from values that
    are strictly more precise than any loader can reconstruct, and the reduced
    oracle caught exactly that: the builder recorded
    [2794, 2794, 2794, 2794, 3929 x 9, 1] and loading the same fixture produced
    [3929 x 14, 1].

    So the round trip is applied to the in-memory model before anything reads
    it -- generation, the seed search, and the writer alike. Every one of them
    then sees the values the release's own pipeline would deliver.
    """

    import torch

    touched = 0
    with torch.no_grad():
        for name, parameter in model.named_parameters():
            if not name.endswith("attn.wo_a.weight"):
                continue
            state, _ = _store_wo_a_quantized(
                {name: parameter.detach().to("cpu")}, {name: "bfloat16"}, torch
            )
            stored = state[name]
            scale = state[name.replace(".weight", ".scale")]
            out_block = stored.size(0) // scale.size(0)
            in_block = stored.size(1) // scale.size(1)
            wide = (
                stored.unflatten(0, (-1, out_block))
                .unflatten(-1, (-1, in_block))
                .float()
                * scale[:, None, :, None].float()
            )
            parameter.copy_(
                wide.flatten(2, 3).flatten(0, 1).bfloat16().to(parameter.device)
            )
            touched += 1
    return touched


def greedy(model: Any, prompt: list[int], *, cap: int, eos: set[int]) -> list[int]:
    """Greedy generation, argmax with ties to the lowest id, stopping on EOS.

    The vendor's ``sample()`` is Gumbel-max above temperature 0 and argmax at 0,
    and ``temperature`` is 0 in the reduced arguments; the argmax is taken here
    from the logits anyway so that the tie rule is this tool's, not the
    kernel's.
    """
    import torch

    device = next(model.parameters()).device
    generated: list[int] = []
    ids = torch.tensor([prompt], dtype=torch.long, device=device)
    _, logits, _ = model(ids)
    position = len(prompt)
    for _ in range(cap):
        row = logits[0].float()
        if not bool(torch.isfinite(row).all()):
            raise ReducedModelError(
                f"the reduced model produced a non-finite logit at position "
                f"{position}"
            )
        token = int(row.argmax())
        generated.append(token)
        if token in eos:
            break
        _, logits, _ = model(
            torch.tensor([[token]], dtype=torch.long, device=device), position
        )
        position += 1
    return generated


def shape_matches(generated: list[int], eos: set[int], cap: int) -> bool:
    """Stops on an official EOS, before the cap, and only at the last token."""

    return (
        1 < len(generated) <= cap
        and generated[-1] in eos
        and not any(token in eos for token in generated[:-1])
    )


def search_seeds(
    vendor: Any,
    body: dict[str, Any],
    tokenizer: Any,
    prompt: list[int],
    *,
    cap: int,
    eos: set[int],
    start: int,
    stride: int,
    limit: int,
    initializer_range: float,
    report: Path,
) -> int:
    """Search one residue class of the seed space and write what it found.

    The rule is "the smallest non-negative seed", and one process evaluates one
    seed at a time because each seed is a different set of weights and cannot be
    batched with another.  A trial is one prefill plus up to ``cap`` decode
    steps through 40 layers, which measures at seconds rather than the Qwen
    predecessor's 54 ms, so a single-process scan of thousands of seeds is not
    affordable.  Splitting the space by residue class keeps the rule intact:
    the smallest matching seed over all classes IS the smallest matching seed,
    PROVIDED every class has been scanned past it.  That proviso is not assumed
    -- ``--search-report`` re-checks it from these files before a seed is used.
    """
    model = build_model(vendor, body, tokenizer)
    tried: list[int] = []
    match: int | None = None
    generated: list[int] = []
    zero: list[int] | None = None
    resumed_from: int | None = None
    # RESUME.  A trial costs seconds and the hit rate is low, so a scan that
    # restarted from its class start on every interruption would repeat hours of
    # settled negative results.  An existing report for the same class, prompt,
    # cap and EOS set is continued from its highest tried seed; anything else is
    # refused rather than merged, because a report built against a different
    # question is not this scan's history.
    if report.exists():
        prior = json.loads(report.read_text(encoding="utf-8"))
        same = (
            int(prior.get("start", -1)) == start
            and int(prior.get("stride", -1)) == stride
            and int(prior.get("cap", -1)) == cap
            and sorted(prior.get("official_eos_token_ids", [])) == sorted(eos)
            and list(prior.get("prompt_token_ids", [])) == list(prompt)
        )
        if not same:
            raise ReducedModelError(
                f"{report} is a scan of a different class, prompt, cap or EOS "
                "set; move it aside rather than resuming into it"
            )
        if prior.get("match") is not None:
            print(f"{report} already found seed {prior['match']}")
            return 0
        tried = [int(v) for v in prior.get("seeds_tried", [])]
        zero = prior.get("seed_zero_generated_token_ids")
        if tried:
            resumed_from = tried[-1] + stride
    resumed_count = len(tried)
    started = time.time()
    report.parent.mkdir(parents=True, exist_ok=True)

    def write_report() -> None:
        """Checkpoint the scan so an interrupted search is still evidence.

        A trial measures at seconds and the hit rate is low -- the Qwen
        predecessor's equivalent search took 6,912 trials -- so a scan that only
        recorded itself on completion would throw away hours of real negative
        results every time it was stopped.
        """
        report.write_bytes(
            canonical_json(
                {
                    "schema": (
                        "opentallas.abi3.deepseek_v41_reduced_seed_search.v1"
                    ),
                    "start": start,
                    "stride": stride,
                    "limit": limit,
                    "cap": cap,
                    "official_eos_token_ids": sorted(eos),
                    "prompt_token_ids": prompt,
                    "seeds_tried": tried,
                    "highest_seed_tried": tried[-1] if tried else None,
                    "match": match,
                    "generated_token_ids": generated,
                    "seed_zero_generated_token_ids": zero,
                    "resumed_from": resumed_from,
                    "complete": match is not None
                    or (bool(tried) and tried[-1] + stride >= limit),
                    "wall_seconds": round(time.time() - started, 1),
                    "seconds_per_trial": (
                        round(
                            (time.time() - started)
                            / max(1, len(tried) - resumed_count),
                            2,
                        )
                        if len(tried) > resumed_count
                        else None
                    ),
                }
            )
            + b"\n"
        )

    for seed in range(resumed_from if resumed_from is not None else start,
                      limit, stride):
        fill_parameters(model, seed, initializer_range)
        round_trip_storage_dtypes(model)
        round_trip_wo_a(model)
        produced = greedy(model, prompt, cap=cap, eos=eos)
        tried.append(seed)
        if seed == 0:
            zero = list(produced)
        print(f"seed {seed}: {produced}", file=sys.stderr, flush=True)
        if shape_matches(produced, eos, cap):
            match = seed
            generated = list(produced)
            break
        if len(tried) % 25 == 0:
            write_report()
    write_report()
    print(
        f"class {start}/{stride}: tried {len(tried)} seed(s), match={match} "
        f"in {time.time() - started:.1f}s -> {report}"
    )
    return 0


def aggregate_search(
    reports: list[Path], *, cap: int, eos: set[int], prompt: list[int]
) -> dict[str, Any]:
    """The smallest matching seed over a set of search reports, and its warrant.

    Refuses unless the reports partition a prefix of the seed space that covers
    the winning seed: every residue class must have been scanned to at least the
    winner, or have found a match of its own at or below it.  Without that the
    winner is only "a seed that works", not "the smallest", and the rule would
    be a claim the search does not support.
    """
    bodies = []
    for path in reports:
        body = json.loads(path.read_text(encoding="utf-8"))
        if body.get("schema") != "opentallas.abi3.deepseek_v41_reduced_seed_search.v1":
            raise ReducedModelError(f"{path} is not a seed-search report")
        if int(body["cap"]) != cap:
            raise ReducedModelError(
                f"{path} searched at cap {body['cap']}, this run's cap is {cap}"
            )
        if sorted(body["official_eos_token_ids"]) != sorted(eos):
            raise ReducedModelError(f"{path} searched against a different EOS set")
        if list(body["prompt_token_ids"]) != list(prompt):
            raise ReducedModelError(f"{path} searched against a different prompt")
        bodies.append({"path": _repo_relative(path), **body})
    strides = {int(b["stride"]) for b in bodies}
    if len(strides) != 1:
        raise ReducedModelError(f"the reports mix strides {sorted(strides)}")
    stride = strides.pop()
    starts = sorted(int(b["start"]) for b in bodies)
    if starts != list(range(stride)):
        raise ReducedModelError(
            f"the reports cover residues {starts}, not every class of stride "
            f"{stride}; the smallest matching seed cannot be established"
        )
    matches = [int(b["match"]) for b in bodies if b["match"] is not None]
    if not matches:
        raise ReducedModelError(
            "no report found a seed that stops on an official reduced EOS before "
            f"the cap of {cap}; searched "
            f"{sum(len(b['seeds_tried']) for b in bodies)} seed(s)"
        )
    winner = min(matches)
    uncovered = [
        int(b["start"])
        for b in bodies
        if b["match"] is None
        and (b["highest_seed_tried"] is None or int(b["highest_seed_tried"]) < winner)
    ]
    if uncovered:
        raise ReducedModelError(
            f"seed {winner} matches, but residue class(es) {uncovered} were not "
            "scanned past it, so it is not established as the SMALLEST matching "
            "seed. Extend those classes and re-aggregate"
        )
    chosen = next(b for b in bodies if b["match"] == winner)
    return {
        "seed": winner,
        "generated_token_ids": list(chosen["generated_token_ids"]),
        "seeds_tried": sum(len(b["seeds_tried"]) for b in bodies),
        "stride": stride,
        "search_limit": max(int(b["limit"]) for b in bodies),
        "seed_zero_generated_token_ids": next(
            (
                b["seed_zero_generated_token_ids"]
                for b in bodies
                if b["seed_zero_generated_token_ids"] is not None
            ),
            None,
        ),
        "coverage": [
            {
                "report": b["path"],
                "residue": int(b["start"]),
                "seeds_tried": len(b["seeds_tried"]),
                "highest_seed_tried": b["highest_seed_tried"],
                "match": b["match"],
            }
            for b in sorted(bodies, key=lambda b: int(b["start"]))
        ],
        "minimality_established": True,
        "minimality_argument": (
            f"every residue class of stride {stride} was scanned either to a "
            f"match of its own or past seed {winner}, so no seed below "
            f"{winner} satisfies the rule"
        ),
        "search_wall_seconds": round(
            max(float(b["wall_seconds"]) for b in bodies), 1
        ),
    }


def select_seed(
    vendor: Any,
    body: dict[str, Any],
    tokenizer: Any,
    prompt: list[int],
    *,
    cap: int,
    eos: set[int],
    limit: int,
    initializer_range: float,
) -> dict[str, Any]:
    """The stated seed-selection rule, applied and recorded."""

    model = build_model(vendor, body, tokenizer)
    tried = 0
    seed_zero: list[int] | None = None
    chosen: tuple[int, list[int]] | None = None
    started = time.time()
    for seed in range(limit):
        fill_parameters(model, seed, initializer_range)
        round_trip_storage_dtypes(model)
        round_trip_wo_a(model)
        generated = greedy(model, prompt, cap=cap, eos=eos)
        tried += 1
        if seed == 0:
            seed_zero = list(generated)
        print(f"seed {seed}: {generated}", file=sys.stderr, flush=True)
        if shape_matches(generated, eos, cap):
            chosen = (seed, list(generated))
            break
    if chosen is None:
        raise ReducedModelError(
            f"no seed below {limit} stops on an official reduced EOS before the "
            f"cap of {cap}"
        )
    return {
        "rule": (
            "the smallest non-negative integer seed for which the reduced "
            "model's greedy generation from the reduced prompt terminates in an "
            "official reduced EOS id strictly before the cap, with no official "
            "EOS id before the last token"
        ),
        "rule_stated_before_search": True,
        "why_not_a_token_count": (
            f"{GOVERNED_WORKLOAD_ID} carries no gold of its own -- its "
            "gold_status is unverified -- so there is no governed token count "
            "to reproduce, unlike the Qwen predecessor's three. The rule fixes "
            "the shape and the count is recorded, not required"
        ),
        "seed": chosen[0],
        "generated_token_ids": chosen[1],
        "generated_token_count": len(chosen[1]),
        "seeds_tried": tried,
        "search_limit": limit,
        "seed_zero_generated_token_ids": seed_zero,
        "search_wall_seconds": round(time.time() - started, 1),
        "selection_is_argmax": True,
        #: This path scans upward from zero and breaks at the first seed that
        #: satisfies the rule, so minimality holds by construction and
        #: ``seeds_tried == seed + 1`` is the check. The sharded path states a
        #: residue-class argument instead because it does not scan in order;
        #: this one needs no argument beyond the loop. The field was absent here
        #: while the sharded path set it, which read as a regression in the
        #: record when a serial search replaced a sharded one.
        "minimality_established": True,
        "minimality_argument": (
            f"the search scanned every seed from 0 upward and stopped at the "
            f"first that satisfied the rule, so no seed below {chosen[0]} "
            f"satisfies it; seeds_tried {tried} is {chosen[0]} + 1"
        ),
        "searched_in_parallel": False,
    }, model


# ---------------------------------------------------------------------------
# The budget
# ---------------------------------------------------------------------------
def budget(body: dict[str, Any], prompt_tokens: int, generated: int) -> dict[str, Any]:
    """The whole workload's MAC count, derived term by term rather than asserted."""

    dim = int(body["dim"])
    heads = int(body["n_heads"])
    head_dim = int(body["head_dim"])
    q_rank = int(body["q_lora_rank"])
    o_rank = int(body["o_lora_rank"])
    o_groups = int(body["o_groups"])
    inter = int(body["moe_inter_dim"])
    shared = int(body["n_shared_experts"])
    active = int(body["n_activated_experts"])
    routed = int(body["n_routed_experts"])
    layers = int(body["n_layers"])
    vocab = int(body["vocab_size"])
    index_heads = int(body["index_n_heads"])
    index_dim = int(body["index_head_dim"])
    hc_mult = int(body["hc_mult"])
    engram_layers = len(body["engram_layer_ids"])
    engram_cols = (int(body["engram_max_ngram_size"]) - 1) * int(
        body["engram_n_heads"]
    )
    engram_dim = int(body["engram_head_dim"])
    window = int(body["window_size"])

    attention_projection = (
        dim * q_rank                      # wq_a
        + q_rank * heads * head_dim       # wq_b
        + dim * head_dim                  # wkv, one latent plane
        + heads * head_dim * o_rank       # wo_a, block diagonal over o_groups
        + o_groups * o_rank * dim         # wo_b
    )
    indexer = q_rank * index_heads * index_dim + dim * index_dim
    hyper_connection = 2 * hc_mult * dim * (hc_mult + 2)
    moe = routed * dim + (active + shared) * 3 * dim * inter
    per_layer = attention_projection + indexer + hyper_connection + moe
    per_engram_layer = engram_cols * engram_dim * dim * (hc_mult + 1)
    lm_head = dim * vocab

    positions = prompt_tokens + generated
    rows = prompt_tokens + generated - 1
    contexts = list(range(1, prompt_tokens + 1)) + [
        prompt_tokens + step for step in range(1, generated)
    ]
    # Attention itself reads the sliding window plus whatever compressed KV the
    # layer owns, so it is bounded by the window, not by the context.
    attention_scores = sum(
        2 * heads * head_dim * min(context, window) for context in contexts
    ) * layers

    trunk = rows * layers * per_layer
    engram = rows * engram_layers * per_engram_layer
    head = generated * lm_head
    total = trunk + engram + head + attention_scores
    return {
        "measured_macs_per_second": MEASURED_MACS_PER_SECOND,
        "measured_rate_source": (
            "docs/CHIP_ARCHITECTURE_DESIGN.md section 11.7: 200,231 simulated "
            "cycles/s and 5.0164 cycles per MAC"
        ),
        "terms_per_row": {
            "attention_projection": attention_projection,
            "attention_projection_arithmetic": (
                f"{dim}*{q_rank} + {q_rank}*{heads * head_dim} + {dim}*{head_dim}"
                f" + {heads * head_dim}*{o_rank} + {o_groups}*{o_rank}*{dim}"
                f" = {attention_projection}"
            ),
            "indexer": indexer,
            "hyper_connection": hyper_connection,
            "mixture_of_experts": moe,
            "mixture_of_experts_arithmetic": (
                f"{routed}*{dim} + ({active}+{shared})*3*{dim}*{inter} = {moe}"
            ),
            "per_layer": per_layer,
            "per_engram_layer": per_engram_layer,
            "lm_head": lm_head,
        },
        "transactions_accounting": {
            "note": (
                f"one prefill span of {prompt_tokens} rows, then "
                f"{generated - 1} decode rows, with the LM head on one row per "
                "generated token"
            ),
            "positions": positions,
            "trunk_rows": rows,
            "trunk_macs": trunk,
            "engram_macs": engram,
            "lm_head_macs": head,
            "attention_macs": attention_scores,
            "total_macs": total,
            "seconds_at_measured_rate": round(total / MEASURED_MACS_PER_SECOND, 1),
            "hours_at_measured_rate": round(
                total / MEASURED_MACS_PER_SECOND / 3600, 2
            ),
        },
        "does_not_establish": (
            "this is the arithmetic cost of the fixture at a rate measured on a "
            "different workload, not a measured G1f runtime and not a TPOT"
        ),
    }


# ---------------------------------------------------------------------------
# Materialisation
# ---------------------------------------------------------------------------
def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(4 * 1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def _repo_relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)



def _store_wo_a_quantized(
    state: dict[str, Any], logical: dict[str, str], torch: Any
) -> tuple[dict[str, Any], dict[str, str]]:
    """Rewrite every ``attn.wo_a.weight`` into the release's storage shape.

    The inverse of ``convert.py``'s dequantization: that reads a 32x32-blocked
    E8M0 scale and multiplies, so this divides by a power-of-two scale chosen
    per block and stores the quotient as F8_E4M3.  E8M0 carries an exponent
    only, and the reduced builder's own format record states its convention --
    "byte 0x7F, a scale of exactly 2**0" -- so the byte is 127 + exponent.
    """

    block = 32
    #: float8_e4m3fn's largest finite magnitude.
    fp8_max = 448.0
    out: dict[str, Any] = {}
    for name, tensor in state.items():
        if not name.endswith("attn.wo_a.weight"):
            out[name] = tensor
            continue
        rows, columns = int(tensor.shape[0]), int(tensor.shape[1])
        if rows % block or columns % block:
            raise ReducedModelError(
                f"{name} is {rows}x{columns}, which the release's {block}-wide "
                "weight scale block does not divide; the reduced widths are "
                "chosen to be divisible by it, so this is a configuration error"
            )
        blocked = (
            tensor.float()
            .unflatten(0, (rows // block, block))
            .unflatten(-1, (columns // block, block))
        )
        magnitude = blocked.abs().amax(dim=(1, 3))
        #: A power-of-two scale that brings each block inside fp8's range, and
        #: exactly 2**0 for an all-zero block.
        exponent = torch.where(
            magnitude > 0,
            torch.ceil(torch.log2(magnitude / fp8_max)),
            torch.zeros_like(magnitude),
        )
        exponent = exponent.clamp(-127.0, 127.0)
        #: exp2 rather than pow(tensor(2.0), ...): this builder runs under a
        #: default-device context, so a freshly constructed scalar lands on the
        #: accelerator while the state dict has already been moved to the host,
        #: and the multiply then refuses with "found at least two devices".
        scale = torch.exp2(exponent)
        quotient = blocked / scale[:, None, :, None]
        weight = (
            quotient.flatten(2, 3).flatten(0, 1).to(torch.float8_e4m3fn).contiguous()
        )
        out[name] = weight
        logical[name] = "float8_e4m3fn"
        scale_name = name.replace(".weight", ".scale")
        #: THE SCALE'S VALUE, not its exponent. E8M0 carries no mantissa and
        #: its byte is 127 + exponent, so 2**0 stores as 0x7F -- which is the
        #: convention this builder's own format record states. Casting the
        #: exponent itself put -6 where 2**-6 belonged and the round trip came
        #: back four orders of magnitude out.
        out[scale_name] = scale.to(torch.float8_e8m0fnu).contiguous()
        logical[scale_name] = "float8_e8m0fnu"
    return out, logical


def write_snapshot(
    model: Any,
    snapshot: Path,
    body: dict[str, Any],
    *,
    model_dir: Path,
    seed: int,
) -> dict[str, Any]:
    """Materialise the reduced checkpoint in the layout the lock reads."""

    import torch
    from safetensors.torch import save_file

    snapshot.mkdir(parents=True, exist_ok=True)
    model_dir.mkdir(parents=True, exist_ok=True)
    serialisable = {
        key: (list(value) if isinstance(value, tuple) else value)
        for key, value in body.items()
    }
    config_bytes = (
        json.dumps(serialisable, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    (snapshot / "inference_config.json").write_bytes(config_bytes)
    (model_dir / "inference_config.json").write_bytes(config_bytes)
    # The tokenizer is part of the checkpoint, not a side artifact: the Engram
    # compressed token map is derived from it, so a consumer that resolved a
    # different tokenizer would build different hash tables for the same weights.
    # It is written into both trees and registered in the source contract below
    # for the same reason ``inference_config.json`` is.
    for name in ("tokenizer.json", "tokenizer_config.json"):
        (snapshot / name).write_bytes((model_dir / name).read_bytes())

    # STORAGE FORMAT.  The packed FP4 expert weights are written as I8, which is
    # how the RELEASED checkpoint represents them -- compiler/frontend/checkpoint
    # says so in as many words ("DeepSeek's packed FP4 payload is represented as
    # I8 by the released checkpoint; this reader does not invent a nibble
    # format") and refuses an F4 header outright.  Writing torch's
    # float4_e2m1fn_x2 dtype straight out produced exactly that refusal:
    #
    #   CheckpointError: tensor 'layers.0.ffn.experts.0.w1.weight' uses
    #   unsupported dtype 'F4'
    #
    # so the fixture follows the release's convention instead of widening the
    # reader.  Every byte is identical either way -- the view is a
    # reinterpretation, not a conversion -- and parameter_formats.json below
    # records the logical format of each tensor so a loader restores it.
    logical: dict[str, str] = {}
    state: dict[str, Any] = {}
    for name, parameter in model.named_parameters():
        tensor = parameter.detach().cpu().contiguous()
        logical[name] = str(tensor.dtype).removeprefix("torch.")
        if tensor.dtype == torch.float4_e2m1fn_x2:
            tensor = tensor.view(torch.int8)
        state[name] = tensor

    # EVERY NARROWED PARAMETER IS WRITTEN IN ITS STORAGE DTYPE. The released
    # checkpoint stores head.weight, the compressor's projections and the MTP
    # heads in BF16 where the vendor module holds F32 -- its own shard headers
    # say so -- and a fixture that writes the runtime dtype instead disagrees
    # with the front end's derivation on nine tensor groups and 1,613,184
    # payload bytes.
    for name in list(state):
        storage = storage_dtype_for(name, torch)
        if storage is None or state[name].dtype == storage:
            continue
        state[name] = state[name].to(storage).contiguous()
        logical[name] = str(storage).removeprefix("torch.")

    # wo_a IS WRITTEN IN THE RELEASE'S STORAGE SHAPE, not its runtime one.
    #
    # The vendor module declares it ``ColumnParallelLinear(..., dtype=
    # torch.bfloat16)`` while every sibling projection takes the default fp8,
    # and it says why beside the einsum that consumes it: "wo_a is
    # block-diagonal over groups (each projects only its own heads), hence
    # einsum not Linear.  convert.py dequantizes it to bf16; an fp8 grouped
    # GEMM would halve the memory."  So bf16 is what the RUNTIME holds after
    # conversion -- the released CHECKPOINT stores fp8 with a scale, which its
    # own shard header confirms: layers.0.attn.wo_a.weight is F8_E4M3
    # [8192, 4096] beside wo_a.scale F8_E8M0 [256, 128].
    #
    # Writing named_parameters() straight out therefore produced a fixture in
    # the runtime shape, missing 43 ``attn.wo_a.scale`` tensors that this
    # release's storage shape has -- which
    # tools/audit_deepseek_v41_reduced_tensor_structure.py measures, and which
    # kept the model from being pinnable by a front end that models storage.
    #
    # This is the inverse of convert.py's own dequantization, block sizes and
    # all: per 32x32 block a power-of-two scale, E8M0 as the release's
    # ``scale_fmt: ue8m0`` asks, with the weight stored as F8_E4M3.  The
    # round trip is lossy, exactly as it is for the release, so the fixture's
    # numerics now match what the release actually computes rather than being
    # more precise than it.
    state, logical = _store_wo_a_quantized(state, logical, torch)
    shard = "model-00001-of-00001.safetensors"
    save_file(state, str(snapshot / shard), metadata={"format": "pt"})
    total = sum(
        int(tensor.numel()) * int(tensor.element_size()) for tensor in state.values()
    )
    index = {
        "metadata": {"total_size": total},
        "weight_map": {name: shard for name in state},
    }
    (snapshot / "model.safetensors.index.json").write_bytes(
        (json.dumps(index, indent=2, sort_keys=True) + "\n").encode("utf-8")
    )
    (snapshot / "parameter_formats.json").write_bytes(
        canonical_json(
            {
                "note": (
                    "the LOGICAL format of every parameter, so a reader does not "
                    "have to reconstruct it from the vendor module. Where it "
                    "differs from the shard's stored format the shard follows the "
                    "released checkpoint's convention: packed FP4 is stored as I8 "
                    "and reinterpreted, byte for byte, as float4_e2m1fn_x2"
                ),
                "logical": logical,
                "stored": {
                    name: str(tensor.dtype).removeprefix("torch.")
                    for name, tensor in state.items()
                },
                "reinterpreted": sorted(
                    name
                    for name, tensor in state.items()
                    if logical[name] != str(tensor.dtype).removeprefix("torch.")
                ),
            }
        )
        + b"\n"
    )

    paths = [
        "inference_config.json",
        "model.safetensors.index.json",
        "parameter_formats.json",
        "tokenizer.json",
        "tokenizer_config.json",
        shard,
    ]
    # The "revision" of a constructed checkpoint is its own content: the digest
    # of the configuration and the seed that produced every byte.
    revision = hashlib.sha256(
        config_bytes
        + f"|seed={seed}".encode("utf-8")
        + b"|tokenizer="
        + _sha256_file(model_dir / "tokenizer.json").encode("utf-8")
    ).hexdigest()[:40]
    source = {
        "schema": CHECKPOINT_SOURCE_SCHEMA,
        "repository": f"opentallas/{MODEL_ID}",
        "revision": revision,
        "remote_code_policy": "disabled",
        "checkpoint_index": "model.safetensors.index.json",
        "required_files": sorted(
            path
            for path in paths
            if path not in (shard, "model.safetensors.index.json")
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
    (model_dir / "checkpoint_source.json").write_bytes(canonical_json(source) + b"\n")
    del torch
    return source


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument("--model-dir", type=Path, default=DEFAULT_MODEL_DIR)
    parser.add_argument("--workload-dir", type=Path, default=DEFAULT_WORKLOAD_DIR)
    parser.add_argument("--lock", type=Path, default=DEFAULT_LOCK)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--width-factor", type=int, default=32)
    parser.add_argument("--seed-limit", type=int, default=4096)
    parser.add_argument("--seed", type=int, default=None, help="skip the search")
    parser.add_argument(
        "--expert-scale-exponent",
        type=int,
        default=0,
        help=(
            "power of two written into every routed expert's E8M0 block scale. "
            "0 reproduces the v1 fixture, whose expert projection reaches 119.3 "
            "against a swiglu_limit of 10 and therefore saturates the clamp on "
            "99.8%% of values; -5 divides it by 32 and puts it inside the limit, "
            "the same order as the shared expert. See EXPERT_SCALE_EXPONENT"
        ),
    )
    parser.add_argument(
        "--engram-share-limit",
        type=int,
        default=1 << 20,
        help="largest engram bucket factor the share rule may consider",
    )
    parser.add_argument(
        "--search-only",
        type=Path,
        default=None,
        help=(
            "scan one residue class of the seed space and write a search report "
            "there instead of building anything. Use with --seed-start and "
            "--seed-stride to split the scan over several processes"
        ),
    )
    parser.add_argument("--seed-start", type=int, default=0)
    parser.add_argument("--seed-stride", type=int, default=1)
    parser.add_argument(
        "--search-report",
        type=Path,
        nargs="+",
        default=None,
        help=(
            "aggregate these search reports, take the smallest matching seed and "
            "build with it. Refuses unless the reports establish minimality"
        ),
    )
    arguments = parser.parse_args(argv)

    # Before ANY weight is constructed, and once: the seed search and the final
    # build must use one construction or the search selects a seed for a fixture
    # that is never built.
    global EXPERT_SCALE_EXPONENT
    EXPERT_SCALE_EXPONENT = int(arguments.expert_scale_exponent)

    root_config = json.loads(FULL_ROOT_CONFIG.read_text(encoding="utf-8"))
    full = json.loads(FULL_INFERENCE_CONFIG.read_text(encoding="utf-8"))
    governed = json.loads(GOVERNED_WORKLOAD.read_text(encoding="utf-8"))
    text_config = root_config["text_config"]
    initializer_range = float(text_config["initializer_range"])
    block = quantization_block(root_config)
    factor = int(arguments.width_factor)

    snapshot_dir = released_snapshot()
    vendor, engram_mod = import_vendor(snapshot_dir)
    from transformers import AutoTokenizer

    # The fixture is built against its OWN tokenizer, not the release's.  The
    # released tokenizer emits ids up to 129,279 while this vehicle's embedding
    # has ``vocab_size`` rows, so building the model against it would produce a
    # fixture that tokenises text it cannot embed -- and would leave the Engram
    # compressed token map, which ``build_compressed_token_map`` derives FROM the
    # tokenizer, describing a vocabulary the checkpoint does not have.  The
    # release's own assertion in ``engram.py`` is what forces the pair to agree.
    reduced_vocab_size = int(full["vocab_size"]) // factor
    arguments.model_dir.mkdir(parents=True, exist_ok=True)
    write_reduced_tokenizer(snapshot_dir, arguments.model_dir, reduced_vocab_size)
    tokenizer = AutoTokenizer.from_pretrained(str(arguments.model_dir))
    if len(tokenizer) != reduced_vocab_size:
        raise ReducedModelError(
            f"the reduced tokenizer holds {len(tokenizer)} tokens for a "
            f"{reduced_vocab_size}-row embedding"
        )
    _, compressed_vocab_size = engram_mod.build_compressed_token_map(tokenizer)
    compressed_vocab_size = int(compressed_vocab_size)

    prompt_tokens = int(governed["prompt_token_count"])
    cap = int(governed["max_new_tokens"])

    # The engram bucket factor: the smallest power of two whose tables keep no
    # more than their released share of the fixture's bytes.  The non-engram
    # bytes do not depend on it, so one probe build settles the search.
    inventory = json.loads(
        (ROOT / "data/inventory/deepseek-v4.1-flash.json").read_text(encoding="utf-8")
    )
    released_share = (
        float(inventory["lookup_table_bytes"]["engram_table_packed"])
        / float(inventory["checkpoint_bytes"])
    )
    # The share rule needs the fixture's NON-engram bytes, which do not depend on
    # the engram bucket factor at all, so it is measured once from a probe build.
    # That probe is built at the SMALLEST tables the rule may consider, never at
    # factor 1: at factor 1 the tables are the released 384,006,168 rows, which
    # is 24.6 GB of device memory for a number this loop is about to reject, and
    # allocating it was what made a parallel seed search fail to start.
    probe_body = reduced_body(
        full,
        factor=factor,
        block=block,
        engram_factor=int(arguments.engram_share_limit),
        compressed_vocab_size=compressed_vocab_size,
    )
    probe_body["max_seq_len"] = sequence_context(probe_body, prompt_tokens, cap)
    probe_body["engram_num_embeddings"] = derive_engram_rows(
        vendor, engram_mod, probe_body
    )
    probe_model = build_model(vendor, probe_body, tokenizer)
    probe_bytes = parameter_bytes(probe_model)
    del probe_model
    other_bytes = probe_bytes["total"] - probe_bytes["engram"]

    search: list[dict[str, Any]] = []
    chosen_factor: int | None = None
    engram_factor = 1
    while engram_factor <= int(arguments.engram_share_limit):
        body = reduced_body(
            full,
            factor=factor,
            block=block,
            engram_factor=engram_factor,
            compressed_vocab_size=compressed_vocab_size,
        )
        body["max_seq_len"] = sequence_context(body, prompt_tokens, cap)
        body["engram_num_embeddings"] = derive_engram_rows(vendor, engram_mod, body)
        rows = sum(body["engram_num_embeddings"])
        engram_bytes = rows * int(body["engram_head_dim"])  # fp8 e4m3, one byte
        share = engram_bytes / (engram_bytes + other_bytes)
        search.append(
            {
                "factor": engram_factor,
                "engram_vocab_size": int(body["engram_vocab_size"]),
                "engram_table_rows": list(body["engram_num_embeddings"]),
                "engram_bytes": engram_bytes,
                "share": round(share, 6),
            }
        )
        if share <= released_share:
            chosen_factor = engram_factor
            break
        engram_factor *= 2
    if chosen_factor is None:
        raise ReducedModelError(
            "no engram bucket factor below the limit brings the tables to their "
            "released share of the fixture"
        )

    body = reduced_body(
        full,
        factor=factor,
        block=block,
        engram_factor=chosen_factor,
        compressed_vocab_size=compressed_vocab_size,
    )
    body["max_seq_len"] = sequence_context(body, prompt_tokens, cap)
    body["engram_num_embeddings"] = derive_engram_rows(vendor, engram_mod, body)
    engram_check = check_engram_derivation(vendor, engram_mod, body, full)

    vocab = int(body["vocab_size"])
    prompt = [int(token) % vocab for token in governed["token_ids"]]
    if len(prompt) != prompt_tokens:
        raise ReducedModelError(
            f"{GOVERNED_WORKLOAD_ID} declares {prompt_tokens} prompt tokens and "
            f"carries {len(prompt)}"
        )
    eos_released = {
        int(text_config.get("eos_token_id", root_config["eos_token_id"])),
        int(root_config["bos_token_id"]),
    }
    eos = {token % vocab for token in eos_released}
    if len(eos) != len(eos_released):
        raise ReducedModelError(
            "two official EOS ids collide under the reduced vocabulary"
        )

    if arguments.search_only is not None:
        return search_seeds(
            vendor,
            body,
            tokenizer,
            prompt,
            cap=cap,
            eos=eos,
            start=int(arguments.seed_start),
            stride=int(arguments.seed_stride),
            limit=int(arguments.seed_limit),
            initializer_range=initializer_range,
            report=arguments.search_only,
        )

    if arguments.search_report:
        aggregated = aggregate_search(
            [Path(path) for path in arguments.search_report],
            cap=cap,
            eos=eos,
            prompt=prompt,
        )
        model = build_model(vendor, body, tokenizer)
        fill_parameters(model, int(aggregated["seed"]), initializer_range)
        round_trip_storage_dtypes(model)
        round_trip_wo_a(model)
        replayed = greedy(model, prompt, cap=cap, eos=eos)
        if replayed != list(aggregated["generated_token_ids"]):
            raise ReducedModelError(
                "replaying the winning seed does not reproduce the search's "
                f"token ids: {replayed} vs {aggregated['generated_token_ids']}"
            )
        selection = {
            "rule": (
                "the smallest non-negative integer seed for which the reduced "
                "model's greedy generation from the reduced prompt terminates in "
                "an official reduced EOS id strictly before the cap, with no "
                "official EOS id before the last token"
            ),
            "rule_stated_before_search": True,
            "why_not_a_token_count": (
                f"{GOVERNED_WORKLOAD_ID} carries no gold of its own -- its "
                "gold_status is unverified -- so there is no governed token "
                "count to reproduce, unlike the Qwen predecessor's three. The "
                "rule fixes the shape and the count is recorded, not required"
            ),
            "searched_in_parallel": True,
            "why_in_parallel": (
                "a trial is one prefill plus up to the cap in decode steps "
                "through 40 layers and cannot be batched with another seed's "
                "weights, so the seed space is split by residue class; "
                "minimality is then re-established from the reports rather "
                "than assumed"
            ),
            "replayed_in_this_process": True,
            "generated_token_count": len(replayed),
            "selection_is_argmax": True,
            **aggregated,
        }
    elif arguments.seed is None:
        selection, model = select_seed(
            vendor,
            body,
            tokenizer,
            prompt,
            cap=cap,
            eos=eos,
            limit=int(arguments.seed_limit),
            initializer_range=initializer_range,
        )
        fill_parameters(model, int(selection["seed"]), initializer_range)
        round_trip_storage_dtypes(model)
        round_trip_wo_a(model)
    else:
        model = build_model(vendor, body, tokenizer)
        fill_parameters(model, int(arguments.seed), initializer_range)
        round_trip_storage_dtypes(model)
        round_trip_wo_a(model)
        generated = greedy(model, prompt, cap=cap, eos=eos)
        selection = {
            "rule": "supplied on the command line",
            "rule_stated_before_search": False,
            "seed": int(arguments.seed),
            "generated_token_ids": generated,
            "generated_token_count": len(generated),
            "seeds_tried": 1,
            "search_limit": 1,
            "seed_zero_generated_token_ids": None,
            "shape_matches": shape_matches(generated, eos, cap),
        }
    seed = int(selection["seed"])
    generated = list(selection["generated_token_ids"])

    source = write_snapshot(
        model, arguments.snapshot, body, model_dir=arguments.model_dir, seed=seed
    )
    lock = build_checkpoint_lock(arguments.snapshot, source)
    arguments.lock.parent.mkdir(parents=True, exist_ok=True)
    arguments.lock.write_bytes(canonical_json(lock) + b"\n")
    cache_view = install_cache_view(source, arguments.snapshot)

    workload = {
        "workload_id": WORKLOAD_ID,
        "kind": "chat",
        "description": (
            f"G1f reduced regression workload: the governed workload "
            f"{GOVERNED_WORKLOAD_ID} at the reduced V4.1 configuration.  Its "
            "prompt is that workload's own token ids reduced into the reduced "
            "vocabulary by id % vocab_size, its cap is the same, and its gold "
            "stops on an official reduced EOS before the cap.  40 layers and "
            "the CSA2 mode sequence are the shipped ones."
        ),
        "derived_from": {
            "workload_id": GOVERNED_WORKLOAD_ID,
            "path": str(GOVERNED_WORKLOAD.relative_to(ROOT)),
            "digest": governed["digest"],
            "rule": "token_id % vocab_size",
        },
        "max_new_tokens": cap,
        "prompt_token_count": len(prompt),
        "token_ids": prompt,
        "gold_token_ids": generated,
        "official_eos_token_ids": sorted(eos),
        "official_eos_token_ids_full_model": sorted(eos_released),
        "model_id": MODEL_ID,
        "metadata": {
            "gate": "G1f",
            "plan": PLAN,
            "plan_section": "10.2",
            "work_package": WORK_PACKAGE,
            "checks": [
                "the last generated token is an official reduced EOS id",
                "generation stops before the cap; a cap stop is a failed gold",
                "40 layers and the 43-entry CSA2 mode sequence are the release's",
            ],
            "gold_status": (
                "executed: produced by the release's own inference/model.py at "
                "the reduced configuration on this machine"
            ),
        },
    }
    workload["digest"] = hashlib.sha256(canonical_json(workload)).hexdigest()
    arguments.workload_dir.mkdir(parents=True, exist_ok=True)
    workload_path = arguments.workload_dir / f"{WORKLOAD_ID}.json"
    workload_path.write_bytes(canonical_json(workload) + b"\n")
    (arguments.workload_dir / "index.json").write_bytes(
        canonical_json(
            {
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
        )
        + b"\n"
    )

    bytes_now = parameter_bytes(model)
    parameter_count = sum(int(p.numel()) for p in model.parameters())
    summary = {
        "schema": SCHEMA,
        "model_id": MODEL_ID,
        "workload_id": WORKLOAD_ID,
        "plan": PLAN,
        "plan_section": "10.2",
        "work_package": WORK_PACKAGE,
        "release": {
            "model_id": V41_FLASH.model_id,
            "repository": V41_FLASH.repository,
            "revision": V41_FLASH.revision,
            "config_sha256": V41_FLASH.config_sha256,
            "inference_config_sha256": V41_FLASH.inference_config_sha256,
            "vendor_modules": ["inference/model.py", "inference/engram.py"],
        },
        "reduction": {
            "width_factor": factor,
            "quantization_block": block,
            "quantization_block_source": (
                "config.json quantization_config.weight_block_size; the "
                "release's own act_quant asserts N % block_size == 0, so it is "
                "the floor and the granularity of every reduced width"
            ),
            "kept_exactly": {
                field: (
                    list(full[field]) if isinstance(full[field], list)
                    else full[field]
                )
                for field in sorted(KEPT_EXACTLY)
            },
            "block_widths": {
                field: {
                    "released": int(full[field]),
                    "reduced": int(body[field]),
                    "factor": round(int(full[field]) / int(body[field]), 4),
                }
                for field in sorted(BLOCK_WIDTHS)
            },
            "counts": {
                field: {
                    "released": int(full[field]),
                    "reduced": int(body[field]),
                    "factor": round(int(full[field]) / int(body[field]), 4),
                }
                for field in sorted(COUNT_FIELDS)
            },
            "derived": {
                field: {"rule": rule, "value": (
                    list(body[field]) if isinstance(body[field], tuple)
                    else body[field]
                )}
                for field, rule in sorted(DERIVED_FIELDS.items())
            },
            "vision_excluded": {
                "released_vision_n_layers": int(full["vision_n_layers"]),
                "reduced_vision_n_layers": 0,
                "why": (
                    "TA-DS41-EOS-1 is text only, the vision tower is not on a "
                    "text token's decode path, and plan section 10.2's subject "
                    "is the CSA2 mode sequence. This is an EXCLUSION, not a "
                    "reduction: the fixture therefore has no ViT, no aligner, "
                    "no image-span embeddings and no per-expert bias_vl"
                ),
            },
        },
        "engram": {
            "bucket_factor": chosen_factor,
            "bucket_factor_rule": (
                "the smallest power of two for which the two engram tables keep "
                "no more than their released share of the checkpoint's bytes"
            ),
            "released_share": round(released_share, 6),
            "released_share_source": (
                "data/inventory/deepseek-v4.1-flash.json "
                "lookup_table_bytes.engram_table_packed / checkpoint_bytes"
            ),
            "non_engram_bytes": other_bytes,
            "non_engram_bytes_probe_factor": int(arguments.engram_share_limit),
            "search": search,
            "row_derivation": engram_check,
            "fixture_bytes": bytes_now["engram"],
            "fixture_share": round(bytes_now["engram"] / bytes_now["total"], 6),
        },
        "config": {
            key: (list(value) if isinstance(value, tuple) else value)
            for key, value in sorted(body.items())
        },
        "budget": budget(body, len(prompt), len(generated)),
        "seed_selection": selection,
        "weight_construction": {
            "initializer_range": initializer_range,
            "initializer_range_source": "config.json text_config.initializer_range",
            "stream": "numpy Philox keyed by sha256(seed:tensor_name)",
            "by_format": {
                "float8_e8m0fnu": "byte 0x7F, a scale of exactly 2**0",
                "float4_e2m1fn_x2": (
                    "raw stream bytes; E2M1 has no NaN and no infinity, so "
                    "every byte is a valid pair of finite weights"
                ),
                "float8_e4m3fn": "N(0, initializer_range) cast to the format",
                "gains": (
                    "ones, the reference implementation's own initialisation "
                    "for RMSNorm weights and the engram gate"
                ),
                "other": "N(0, initializer_range)",
            },
        },
        "snapshot": {
            "path": _repo_relative(arguments.snapshot),
            "files": source["expected_files"],
            "lock_id": lock["lock_id"],
            "lock_path": _repo_relative(arguments.lock),
            "parameter_tensor_count": len(list(model.named_parameters())),
            "parameter_count": parameter_count,
            "parameter_bytes": bytes_now["total"],
        },
        "workload": {
            "path": _repo_relative(workload_path),
            "digest": workload["digest"],
            "sha256": _sha256_file(workload_path),
            "token_ids": prompt,
            "gold_token_ids": generated,
        },
        "not_a_claim": [
            "the reduced model is a constructed regression fixture, not a "
            "trained model; its token ids establish control flow, composition "
            "and emission, never numerics at full dimension",
            "this is not the V4.1 reference oracle: no shipped-dimension V4.1 "
            "token has been produced in this repository",
            "no number here is a TPOT",
        ],
    }
    arguments.summary.parent.mkdir(parents=True, exist_ok=True)
    arguments.summary.write_bytes(canonical_json(summary) + b"\n")
    print(json.dumps(summary["budget"]["transactions_accounting"], indent=2))
    print(
        f"seed={seed} tried={selection['seeds_tried']} "
        f"generated={generated} lock={lock['lock_id'][:16]} "
        f"params={parameter_count:,} bytes={bytes_now['total']:,} "
        f"engram_factor={chosen_factor}"
    )
    print(f"cache view: {cache_view}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
