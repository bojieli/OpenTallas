#!/usr/bin/env python3
"""The V4.1 G1f reduced oracle: the release's own implementation, reduced widths.

``tools/abi3_g1_models.py`` names this file as the producer of
``results/abi3/deepseek_v41_reduced_reference_oracle.json``, and
``tools/build_abi3_g1f_reduced_end_to_end.py --model deepseek-v4.1-flash``
refuses until it exists:

    deepseek-v4.1-flash: G1f runs the whole reduced workload with nothing
    injected, so the fixture, its lock, its workload and its oracle are all
    prerequisites; missing reduced reference oracle
    (results/abi3/deepseek_v41_reduced_reference_oracle.json)

It is the DeepSeek-V4.1-Flash counterpart of
``tools/run_qwen3_reduced_reference_oracle.py``, and it is a different tool from
``tools/build_deepseek_v41_reduced_model.py`` for the reason that module's
docstring gives: the fixture builder generated its weights in memory and then
wrote them, so its token ids are a statement about a process, not about the
bytes on disk.  This tool READS THE SHARD BACK and runs the reference over
whatever is in it.  If the two ever disagree the fixture is not reproducible,
which is a finding, and ``--expect-summary`` is how that comparison is made.

**The reference implementation.**  DeepSeek-V4.1-Flash is not in
``transformers``, so there is no ``AutoModelForCausalLM`` path and no
``model.generate`` to cross-check against -- the Qwen predecessor's second
opinion has no analogue here and this file does not pretend otherwise.  What
runs is the RELEASE'S OWN ``inference/model.py`` and ``inference/engram.py``,
imported from the pinned 476 GB snapshot by the same
``import_vendor`` the fixture builder used, and the greedy loop is imported from
that builder rather than re-implemented, so there is one loop and not two.

**What is authenticated before a framework is imported.**  The reduced
checkpoint against its committed lock
(``compiler.frontend.checkpoint.verify_checkpoint_lock``, the same function that
binds the 510 GB production checkpoint); the workload against its own digest;
every prompt and EOS id against the reduced vocabulary; and the vendor modules
by SHA-256, recorded in the output so a later reader can tell which
implementation produced these ids.

**What this is not.**  An external comparator, like every oracle in this
repository: it never supplies an accelerator activation and never produces an
accelerator token.  It is also not a claim about the RELEASED model's numerics
-- the weights are a constructed fixture, and the reduced widths are the point.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import platform
import sys
import time
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from compiler.frontend.checkpoint import (  # noqa: E402
    load_checkpoint_lock,
    verify_checkpoint_lock,
)
from runtime.abi3.capability import canonical_json  # noqa: E402
from compiler.frontend.deepseek_v4_releases import V41_FLASH  # noqa: E402
from tools.build_deepseek_v41_reduced_model import (  # noqa: E402
    DEFAULT_LOCK,
    DEFAULT_SNAPSHOT,
    DEFAULT_SUMMARY,
    DEFAULT_WORKLOAD_DIR,
    MODEL_ID,
    WORKLOAD_ID,
    build_model,
    greedy,
    import_vendor,
    released_snapshot,
)

SCHEMA = "opentallas.abi3.reference_oracle.v1"
ORACLE_TOOL = "tools/run_deepseek_v41_reduced_reference_oracle.py"
ORACLE_TOOL_VERSION = "deepseek_v41_reduced_reference_oracle.py:v1"
DEFAULT_OUTPUT = ROOT / "results/abi3/deepseek_v41_reduced_reference_oracle.json"
#: The vendor modules the fixture was built out of, recorded in
#: results/abi3/deepseek_v41_reduced_model.json under release.vendor_modules.
VENDOR_MODULES = ("inference/model.py", "inference/engram.py")


class ReducedOracleError(RuntimeError):
    """A source cannot support reduced-oracle evidence."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while block := handle.read(4 * 1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def install_fp4_dequantised_linear(vendor: Any, convert_mod: Any) -> Any:
    """Replace the vendor's fp4 GEMM with a PyTorch dequantisation of the same bytes.

    THE SHIPPED EXPERT PATH, computed without the kernel that is broken here.  The
    release's ``linear()`` dispatches on weight dtype and sends
    ``float4_e2m1fn_x2`` to ``fp4_gemm``, which on this sm_120 GPU disagrees with
    two mutually independent references -- measured in
    ``runtime/reference/deepseek_v4_oracle.py`` at a maximum absolute error of
    6.5623 against a tolerance of 0.0401 -- and on this fixture returns exactly
    zero for every routed expert.

    The two references it disagrees with are the vendor's own FP4->FP8 recast fed
    to ``fp8_gemm``, and "a direct PyTorch dequantisation using the vendor's
    FP4_TABLE".  The recast path is available already (``--expert-numeric-path
    fp8``) but it changes the arithmetic: FP8xFP8 is not MXFP4, and at reduced
    scale that difference compounds to a different token.  THIS is the other one,
    and it keeps the declared numerics: the same FP4 codes, the same E8M0 block
    scales, the same activation quantisation, and one dequantised matmul in place
    of the kernel.

    Why that matters for the comparison rather than only for correctness: the
    deployment is admitted against MXFP4 contracts, so a reference on the FP4
    path is comparing like with like, while the FP8 recast compares two different
    legitimate arithmetics.  And it needs no change to what is BUILT -- no
    product variant, no front-end edit -- which is what makes it the right
    reference for the shipped configuration.
    """
    import torch

    original_linear = vendor.linear
    table = convert_mod.FP4_TABLE

    def dequantised_linear(x, weight, bias=None):
        if weight.dtype != torch.float4_e2m1fn_x2:
            return original_linear(x, weight, bias)
        assert bias is None
        codes = weight.view(torch.uint8)
        low = codes & 0x0F
        high = (codes >> 4) & 0x0F
        lookup = table.to(codes.device).float()
        values = torch.stack([lookup[low.long()], lookup[high.long()]], dim=-1)
        values = values.flatten(-2)
        out_features, in_features = values.shape
        scale = weight.scale.float()
        blocks = scale.shape[-1]
        block = in_features // blocks
        dequantised = (
            values.unflatten(-1, (blocks, block)) * scale.unsqueeze(-1)
        ).flatten(-2)
        # The activation is quantised exactly as the kernel path would, then
        # dequantised, so the operand seen by the matmul is the one the contract
        # describes rather than the unquantised original.
        quantised, activation_scale = vendor.act_quant(
            x, vendor.fp8_block_size, vendor.scale_fmt, vendor.scale_dtype
        )
        widened = quantised.float()
        a_blocks = activation_scale.shape[-1]
        a_block = widened.shape[-1] // a_blocks
        widened = (
            widened.unflatten(-1, (a_blocks, a_block))
            * activation_scale.float().unsqueeze(-1)
        ).flatten(-2)
        return torch.nn.functional.linear(
            widened, dequantised.to(widened.dtype)
        ).to(x.dtype)

    vendor.linear = dequantised_linear
    return original_linear


def _recast_experts_to_fp8(
    state: dict[str, Any], logical: dict[str, str], convert_mod: Any
) -> int:
    """The release README's own FP8 expert path, applied to the reduced shard.

    ``runtime/reference/deepseek_v4_oracle.py`` established this adaptation and
    recorded why: on this sm_120 GPU the released ``fp4_gemm`` TileLang kernel
    disagrees with two mutually independent references -- the vendor's own
    FP4->FP8 recast fed to ``fp8_gemm``, and a direct PyTorch dequantisation
    through the vendor's ``FP4_TABLE`` -- which agree with each other to bf16
    output rounding.  Its committed probe measures the FP4 path at a maximum
    absolute error of 6.5623 against a tolerance of 0.0401 while the FP8 path
    measures 0.0156, so the V4-Flash oracle runs on FP8 and its three cells
    agree with the device.

    The reduced V4.1 oracle did NOT do this, and the consequence is measured in
    ``results/abi3/deepseek_v41_reduced_oracle_dead_experts.json``: every routed
    expert's second projection returns exactly zero, so the oracle's token comes
    from a shared-expert-only model and no implementation that computes the
    routed experts can reproduce it.

    The recast is the vendor's ``convert.cast_e2m1fn_to_e4m3fn``, which
    ``convert.py`` documents as LOSSLESS: every FP4 value is exactly
    representable in E4M3 and the applied offset is a power of two bounded by
    ``2**6``, so ``6.0 * 2**6 = 384`` stays under E4M3's maximum of 448.  The
    stored shard already holds the packed weights as I8, which is exactly the
    input the function asserts on, so nothing is reinterpreted here either.
    """
    import torch

    recast = 0
    for name in sorted(state):
        if ".ffn.experts." not in name or not name.endswith(".weight"):
            continue
        scale_name = name[: -len(".weight")] + ".scale"
        if scale_name not in state:
            continue
        if logical.get(name) != "float4_e2m1fn_x2":
            continue
        weight = state[name]
        scale = state[scale_name]
        if weight.dtype != torch.int8:
            weight = weight.view(torch.int8)
        # The scale goes in as its OWN dtype, not as raw bytes.
        #
        # ``cast_e2m1fn_to_e4m3fn`` does ``scale.float()`` and divides by 2**6, so
        # a float8_e8m0fnu tensor decodes to the value 1.0 and yields a returned
        # block scale of 2**-6.  Passing ``scale.view(torch.uint8)`` instead made
        # ``.float()`` read the CODE -- 127 for an exponent of zero -- so the
        # returned scale came back as 127/64 = 1.984 and the reconstructed weight
        # as 384 * 2 = 768 against a true 6.0: 128x too large.  I attributed that
        # inflation to the vendor's kernel for several commits; it was this line.
        widened, block_scale = convert_mod.cast_e2m1fn_to_e4m3fn(weight, scale)
        state[name] = widened
        state[scale_name] = block_scale
        logical[name] = "float8_e4m3fn"
        logical[scale_name] = "float8_e8m0fnu"
        recast += 1
    return recast


def _load_weights(
    model: Any, snapshot: Path, *, convert_mod: Any | None = None
) -> dict[str, Any]:
    """Copy the shard's bytes into the model, restoring each logical format.

    ``write_snapshot`` stores the packed FP4 expert weights as I8 because the
    RELEASED checkpoint does -- ``compiler/frontend/checkpoint`` refuses an F4
    header in as many words -- and records the logical dtype of every parameter
    in ``parameter_formats.json``.  The restoration is a reinterpretation of the
    same bytes, never a conversion, and this function refuses rather than casts
    if a stored tensor's byte count does not match the parameter it is loaded
    into.
    """
    import torch
    from safetensors.torch import load_file

    formats = json.loads(
        (snapshot / "parameter_formats.json").read_text(encoding="utf-8")
    )
    logical = formats["logical"]
    index = json.loads(
        (snapshot / "model.safetensors.index.json").read_text(encoding="utf-8")
    )
    shards = sorted(set(index["weight_map"].values()))
    state: dict[str, Any] = {}
    for shard in shards:
        state.update(load_file(str(snapshot / shard)))

    # THE RELEASE'S OWN CONVERSION STEP, because the shard is in the release's
    # STORAGE shape and the runtime model is not.
    #
    # ``inference/model.py`` declares wo_a as ``ColumnParallelLinear(...,
    # dtype=torch.bfloat16)`` where every sibling projection takes the default
    # fp8, and says why beside the einsum that consumes it: "wo_a is
    # block-diagonal over groups (each projects only its own heads), hence
    # einsum not Linear.  convert.py dequantizes it to bf16; an fp8 grouped GEMM
    # would halve the memory."  So the checkpoint ships fp8 with a 32x32-blocked
    # E8M0 scale -- the released shard header says F8_E4M3 beside F8_E8M0 -- and
    # ``convert.py`` is the step between it and the runtime.
    #
    # This is that step, in convert.py's own shape handling.  Before it existed
    # the loader refused a storage-shaped shard with "43 unexpected", naming
    # every wo_a.scale, because the runtime model declares no such parameter.
    converted = 0
    for name in [key for key in state if key.endswith("attn.wo_a.weight")]:
        scale_name = name.replace(".weight", ".scale")
        if scale_name not in state:
            continue
        weight = state[name]
        scale = state.pop(scale_name)
        out_block = weight.size(0) // scale.size(0)
        in_block = weight.size(1) // scale.size(1)
        if (out_block, in_block) not in ((32, 32), (128, 128)):
            raise ReducedOracleError(
                f"{name} is {tuple(weight.shape)} against a scale of "
                f"{tuple(scale.shape)}, a {out_block}x{in_block} block the "
                "release's own convert.py does not accept"
            )
        wide = (
            weight.unflatten(0, (-1, out_block))
            .unflatten(-1, (-1, in_block))
            .float()
            * scale[:, None, :, None].float()
        )
        state[name] = wide.flatten(2, 3).flatten(0, 1).bfloat16()
        logical[name] = "bfloat16"
        converted += 1

    expert_recasts = 0
    if convert_mod is not None:
        expert_recasts = _recast_experts_to_fp8(state, logical, convert_mod)

    parameters = dict(model.named_parameters())
    missing = sorted(set(parameters) - set(state))
    extra = sorted(set(state) - set(parameters))
    if missing or extra:
        raise ReducedOracleError(
            "the shard and the reduced model do not name the same parameters: "
            f"{len(missing)} missing (first: {missing[:3]}), "
            f"{len(extra)} unexpected (first: {extra[:3]})"
        )

    reinterpreted = 0
    widened = 0
    with torch.no_grad():
        for name, parameter in parameters.items():
            stored = state[name]
            want = str(parameter.dtype).removeprefix("torch.")
            if logical.get(name) == "bfloat16" and want == "float32":
                #: A WIDENING THE RELEASE ALSO PERFORMS. The checkpoint stores
                #: head.weight, the compressor's projections and the MTP heads
                #: in BF16 -- its own shard headers say so -- while the vendor
                #: module holds them in F32. Widening is exact, and the bits the
                #: narrowing dropped are gone from the fixture's own generation
                #: too, so the values here are the ones its record was made
                #: from.
                parameter.copy_(stored.to(parameter.dtype))
                widened += 1
                continue
            if logical.get(name) != want:
                raise ReducedOracleError(
                    f"parameter_formats.json records {name!r} as "
                    f"{logical.get(name)!r}; the reduced model wants {want!r}"
                )
            if tuple(stored.shape) != tuple(parameter.shape):
                raise ReducedOracleError(
                    f"{name}: shard shape {tuple(stored.shape)} is not the "
                    f"model's {tuple(parameter.shape)}"
                )
            if stored.dtype == parameter.dtype:
                parameter.copy_(stored)
                continue
            # A reinterpretation: identical byte counts, same element count.
            if stored.element_size() != parameter.element_size():
                raise ReducedOracleError(
                    f"{name}: shard dtype {stored.dtype} is {stored.element_size()} "
                    f"bytes per element and the parameter's {parameter.dtype} is "
                    f"{parameter.element_size()}; this is a conversion, not the "
                    "byte-for-byte reinterpretation the fixture recorded"
                )
            parameter.view(torch.uint8).copy_(stored.view(torch.uint8))
            reinterpreted += 1

    declared = set(formats.get("reinterpreted", ()))
    # The declared reinterpretations are the PACKED FP4 tensors.  On the FP8
    # expert path they were recast before this loop, so they are no longer
    # reinterpretations and the count legitimately drops -- by exactly the number
    # recast, which is checked rather than waived.
    expected = len(declared) - expert_recasts
    if reinterpreted != expected:
        raise ReducedOracleError(
            f"reinterpreted {reinterpreted} tensors; parameter_formats.json "
            f"declares {len(declared)} and {expert_recasts} were recast to the "
            f"FP8 expert path, so {expected} were due"
        )
    return {
        "shards": shards,
        "parameter_count": len(parameters),
        "reinterpreted_tensor_count": reinterpreted,
        "reinterpretation": (
            "packed FP4 expert weights are stored as I8, the released "
            "checkpoint's own convention, and restored to float4_e2m1fn_x2 by "
            "viewing the same bytes"
        ),
        "dequantized_tensor_count": converted,
        "widened_tensor_count": widened,
        "widening": (
            "the checkpoint stores head.weight, the compressor's projections "
            "and the MTP heads in BF16 where the vendor module holds F32, as "
            "the released checkpoint's own shard headers do. Widening is exact; "
            "the bits the narrowing dropped are absent from the fixture's own "
            "generation too"
        ),
        "dequantization": (
            "attn.wo_a ships fp8 with a 32x32-blocked E8M0 scale, as the "
            "released checkpoint's own shard header does, and is dequantized to "
            "bf16 here -- the release's convert.py step, which its model.py "
            "names beside the einsum that consumes the weight. This one IS a "
            "conversion and not a reinterpretation, and it is lossy in the same "
            "way the release's is"
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument("--lock", type=Path, default=DEFAULT_LOCK)
    parser.add_argument("--workload-dir", type=Path, default=DEFAULT_WORKLOAD_DIR)
    parser.add_argument(
        "--expert-numeric-path",
        choices=("fp4", "fp8", "fp4_dequantised"),
        default="fp4",
        help=(
            "which routed-expert numeric path the reference runs on. 'fp4' is "
            "what this tool always did and what the committed artifact was "
            "produced with; on this machine it makes every routed expert return "
            "exactly zero (see results/abi3/"
            "deepseek_v41_reduced_oracle_dead_experts.json), so the oracle is "
            "then a shared-expert-only model. 'fp8' is the release README's own "
            "documented alternative and the path the V4-Flash oracle already "
            "runs on, via the vendor's own lossless recast"
        ),
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--expect-summary",
        type=Path,
        default=DEFAULT_SUMMARY,
        help=(
            "the fixture builder's own record. Its seed_selection.generated_token_ids "
            "were produced from weights held in memory; this run reproduces them "
            "from the bytes on disk, and a disagreement is refused rather than "
            "recorded, because it would mean the fixture is not reproducible"
        ),
    )
    parser.add_argument(
        "--allow-summary-disagreement",
        action="store_true",
        help=(
            "record a disagreement with the fixture record instead of refusing. "
            "For diagnosing one, never for producing evidence"
        ),
    )
    arguments = parser.parse_args(argv)

    # Authenticate every immutable input before a framework is imported: a stale
    # checkpoint or prompt must fail before 34.5 M parameters are allocated.
    lock = load_checkpoint_lock(arguments.lock)
    verified = verify_checkpoint_lock(arguments.snapshot, lock)
    workload_path = arguments.workload_dir / f"{WORKLOAD_ID}.json"
    workload_bytes = workload_path.read_bytes()
    workload = json.loads(workload_bytes)
    if workload["workload_id"] != WORKLOAD_ID:
        raise ReducedOracleError(
            f"{workload_path} declares {workload['workload_id']!r}, not {WORKLOAD_ID!r}"
        )
    if workload["model_id"] != MODEL_ID:
        raise ReducedOracleError(
            f"{workload_path} is for {workload['model_id']!r}, not {MODEL_ID!r}"
        )
    recomputed = hashlib.sha256(
        canonical_json({k: v for k, v in workload.items() if k != "digest"})
    ).hexdigest()
    if recomputed != workload["digest"]:
        raise ReducedOracleError(
            f"{workload_path} digest {workload['digest']} does not cover its body "
            f"(recomputed {recomputed})"
        )

    body = json.loads(
        (arguments.snapshot / "inference_config.json").read_text(encoding="utf-8")
    )
    vocab = int(body["vocab_size"])
    prompt = [int(token) for token in workload["token_ids"]]
    if any(token >= vocab or token < 0 for token in prompt):
        raise ReducedOracleError(
            "a prompt token id lies outside the reduced vocabulary"
        )
    eos_ids = {int(token) for token in workload["official_eos_token_ids"]}
    if any(token >= vocab or token < 0 for token in eos_ids):
        raise ReducedOracleError("an official EOS id lies outside the vocabulary")
    cap = int(workload["max_new_tokens"])
    if len(prompt) + cap > int(body["max_seq_len"]):
        raise ReducedOracleError(
            f"prompt {len(prompt)} + cap {cap} exceeds the fixture's "
            f"max_seq_len {body['max_seq_len']}"
        )

    released = released_snapshot()
    vendor_identity = {
        module: {
            "path": f"{released}/{module}",
            "sha256": _sha256_file(released / module),
            "bytes": (released / module).stat().st_size,
        }
        for module in VENDOR_MODULES
    }

    import importlib

    import torch
    from transformers import AutoTokenizer

    vendor, _engram = import_vendor(released)
    convert_mod = None
    if arguments.expert_numeric_path == "fp4_dequantised":
        # Keep the fp4 weights and the fp4 dispatch; replace only the kernel.
        install_fp4_dequantised_linear(vendor, importlib.import_module("convert"))
    if arguments.expert_numeric_path == "fp8":
        # ``import_vendor`` has already put ``inference/`` on sys.path, which is
        # how ``model.py``'s own ``from kernel import ...`` resolves.
        convert_mod = importlib.import_module("convert")
        # The release README: "If you want to use fp8, just remove
        # "expert_dtype": "fp4" in config.json and specify --expert-dtype fp8 in
        # convert.py."  This is that configuration, stated on the body the model
        # is built from rather than by editing a committed fixture.
        body = dict(body)
        body["expert_dtype"] = None
    # The tokenizer of the snapshot UNDER TEST, not the default one: a second
    # reduced vehicle has its own, and the Engram n-gram state is derived from it.
    tokenizer = AutoTokenizer.from_pretrained(str(arguments.snapshot))

    started = time.perf_counter()
    model = build_model(vendor, body, tokenizer)
    loaded = _load_weights(model, arguments.snapshot, convert_mod=convert_mod)
    model.eval()
    load_seconds = time.perf_counter() - started

    step_started = time.perf_counter()
    with torch.inference_mode():
        generated = greedy(model, prompt, cap=cap, eos=eos_ids)
    elapsed = time.perf_counter() - step_started

    stop = "eos" if generated and generated[-1] in eos_ids else "max_new_tokens"

    summary_agreement: dict[str, Any] | None = None
    if arguments.expect_summary and arguments.expect_summary.is_file():
        summary = json.loads(
            arguments.expect_summary.read_text(encoding="utf-8")
        )
        expected = [
            int(token)
            for token in summary["seed_selection"]["generated_token_ids"]
        ]
        agreed = expected == [int(token) for token in generated]
        summary_agreement = {
            "path": str(arguments.expect_summary),
            "sha256": _sha256_file(arguments.expect_summary),
            "seed": summary["seed_selection"]["seed"],
            "in_memory_generated_token_ids": expected,
            "agreed": agreed,
            "why": (
                "the fixture builder generated from weights held in memory; this "
                "run generated from the bytes it wrote. Agreement is what makes "
                "the fixture reproducible"
            ),
        }
        if not agreed and not arguments.allow_summary_disagreement:
            raise ReducedOracleError(
                "the fixture record and the bytes on disk disagree: builder "
                f"{expected} vs this run {generated}. The fixture is not "
                "reproducible; pass --allow-summary-disagreement to record it"
            )

    report = {
        "schema": SCHEMA,
        "evidence_class": "external_reference_comparator",
        "not_a_claim": [
            "accelerator_execution",
            "artifact_only_execution",
            "timing_or_performance",
            "numerics_at_full_dimension",
            "released_model_numerics",
        ],
        "model_id": MODEL_ID,
        "reduced": True,
        "snapshot": str(arguments.snapshot),
        #: THE TOKENIZER THIS ORACLE TOKENIZED WITH.
        #:
        #: tools/run_accelerator_tokens.py refuses to execute unless the
        #: workload/reference pair binds a 64-hex tokenizer_sha256: a comparison
        #: between two sides that tokenized differently is a comparison of two
        #: different prompts. Every FULL-model oracle binds it and no reduced one
        #: did, so the reduced vehicles could not be deployed at all -- the runner
        #: stopped with "the workload/reference pair does not bind a valid
        #: tokenizer SHA-256" before reaching the accelerator.
        #:
        #: The digest is sha256 of the snapshot's own tokenizer.json, which is the
        #: convention the released oracles already follow: the full V4.1 snapshot's
        #: tokenizer.json hashes to c90dfa01249db1be4245780a052ede752e1361c612ac6
        #: d08e2bdada7d599476b, exactly the value those oracles carry.
        "tokenizer_sha256": _sha256_file(arguments.snapshot / "tokenizer.json"),
        #: WHICH ROUTED-EXPERT NUMERIC PATH THIS GOLD WAS PRODUCED ON.
        #:
        #: run_accelerator_tokens.py requires the oracle's expert_numeric_path to
        #: equal its own --expert-numeric-path, because "a gold produced through a
        #: different numeric path is not this run's comparator". This tool takes
        #: the path as an argument and branches on it, but never recorded it, so
        #: the runner read None and refused every reduced vehicle -- including for
        #: golds that WERE produced on the requested path.
        "expert_numeric_path": arguments.expert_numeric_path,
        "torch_version": torch.__version__,
        "python_version": platform.python_version(),
        "dtype": "bfloat16",
        "selection": "greedy_lowest_token_id_argmax",
        "generation_policy_id": "greedy_argmax_lowest_id_first_eos_v1",
        "include_eos_in_output": True,
        "device_map": str(next(model.parameters()).device),
        "reference_implementation": {
            "same_as_full_oracle": True,
            "loader": (
                "the release's own inference/model.py Transformer, built from the "
                "fixture's inference_config.json and loaded from its shard"
            ),
            "greedy_loop": "tools/build_deepseek_v41_reduced_model.py::greedy",
            "greedy_loop_sha256": _sha256_file(
                ROOT / "tools/build_deepseek_v41_reduced_model.py"
            ),
            "released_snapshot": str(released),
            "released_revision": V41_FLASH.revision,
            "vendor_modules": vendor_identity,
            "cross_checked_against": None,
            "why_no_cross_check": (
                "DeepSeek-V4.1-Flash has no transformers modelling code, so there "
                "is no second greedy implementation to compare against; the Qwen "
                "predecessor cross-checks against transformers.generate and this "
                "one cannot. What IS cross-checked is the fixture record: the same "
                "ids from weights in memory and from the bytes on disk"
            ),
            "weights_read_back_from_disk": True,
        },
        "weight_loading": loaded,
        "producer": {
            "tool": ORACLE_TOOL,
            "tool_version": ORACLE_TOOL_VERSION,
            "command_argv": [ORACLE_TOOL, *(argv if argv is not None else sys.argv[1:])],
            "selected_workload_ids": [WORKLOAD_ID],
        },
        "fixture_record_agreement": summary_agreement,
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
                    "digest_recomputed": recomputed,
                    "size_bytes": len(workload_bytes),
                }
            },
            "inference_config_sha256": _sha256_file(
                arguments.snapshot / "inference_config.json"
            ),
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
        "architecture_under_test": {
            "n_layers": int(body["n_layers"]),
            "compress_ratios": list(body["compress_ratios"]),
            "kv_source_layers": list(body["kv_source_layers"]),
            "index_source_layers": list(body["index_source_layers"]),
            "candidate_source_layer": int(body["candidate_source_layer"]),
            "engram_layer_ids": list(body["engram_layer_ids"]),
            "dspark_target_layer_ids": list(body["dspark_target_layer_ids"]),
            "dim": int(body["dim"]),
            "vocab_size": vocab,
            "why": (
                "the CSA2 mode sequence and every arity are the released model's; "
                "only magnitudes are reduced, which is what makes a G1f run a "
                "witness about this architecture"
            ),
        },
        "results": {
            WORKLOAD_ID: {
                "kind": workload["kind"],
                "workload_digest": workload["digest"],
                "prompt_token_count": len(prompt),
                "prompt_token_ids": prompt,
                "generated_token_ids": [int(token) for token in generated],
                "generated_token_count": len(generated),
                "stop_reason": stop,
                "official_eos_token_ids": sorted(eos_ids),
                "max_new_tokens": cap,
                "wall_seconds": round(elapsed, 3),
                "load_seconds": round(load_seconds, 3),
            }
        },
    }
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_bytes(canonical_json(report) + b"\n")
    print(
        f"{WORKLOAD_ID}: {report['results'][WORKLOAD_ID]['generated_token_ids']} "
        f"stop={stop} -> {arguments.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
