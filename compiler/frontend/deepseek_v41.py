"""Official DeepSeek-V4.1 graph and checkpoint tensor adapter.

This is the V4.1 sibling of :mod:`compiler.frontend.deepseek_v4` and it reads
the same way: it accepts only a content-pinned release record, resolves every
expected checkpoint tensor from that release's official config, and fails on any
missing, extra, mistyped or misshaped tensor.  It does not execute the release's
Python code.  ``TensorSpec``, the tensor builder and ``tensor_structure_sha256``
are reused from the V4 module unchanged, so a V4.1 contract is the same kind of
object as a V4 one and every consumer downstream keeps working.

Why a sibling rather than a third record in ``deepseek_v4``
----------------------------------------------------------
DeepSeek-V4.1-Flash is not a V4 with different numbers.  Six structural
differences change *which* tensors exist rather than how large they are, and
each is derived here from a released config field:

* **Nested config.**  The language model's scalars live under ``text_config``,
  its ``rope_scaling`` with them, and the weight quantization stays at the root.
  The record's ``config_layout`` says where each is, so nothing here assumes.
* **Causal Encoder-Decoder.**  Attention no longer owns its KV per layer.  Only
  ``kv_source_layer_ids`` carry a compressor; every later layer reads the latent
  those publish.  ``candidate_source_layer_id`` adds a block-level pool above
  the indexer, and ``index_source_layer_ids`` -- a superset of the KV sources --
  say which layers score against it.  So a layer's weights depend on two lists,
  not on its own compression ratio.
* **Split indexer.**  An indexer always owns its query side (``wq_b``,
  ``weights_proj``); it owns the key side (``wk``, ``k_norm``) only where it also
  compresses, because the index key is derived from that layer's own latent
  (``SRC-DSV41-FLASH-MODEL``, ``Indexer.owns_k``).
* **Ratio-1 compressors have no gate.**  ``Compressor.__init__`` builds
  ``wgate`` only when ``compress_ratio > 1``: one token per group is a plain
  projection with nothing to pool.  V4.1's 20 decoder layers are ratio 1, and
  layer 20 is both a KV source and ratio 1, so the gate's presence is derived
  from the ratio table and not from the source list.
* **Engram.**  ``engram_layer_ids`` carry an FP8 n-gram table whose row count is
  per layer (``engram_num_embeddings``), plus the projection that turns
  ``(engram_max_ngram_size - 1) * engram_n_heads`` looked-up rows into one key
  per hyper-connection copy and one shared value.
* **Vision.**  A ViT tower, an aligner, three span-delimiter embeddings, and a
  second router bias (``bias_vl``) selected for image positions.  All of it is
  sized from ``vision_config``; ``vision_enabled`` is that section's presence.

What V4.1 *drops* matters as much: there is no global or per-stage
``hc_head_*``, no compressor ``ape``, and no hash-routed ``tid2eid`` table.
"""

from __future__ import annotations

import hashlib
import math
from pathlib import Path
from typing import Any, Mapping

from compiler.frontend.checkpoint import load_checkpoint_source
from compiler.frontend.deepseek_v4 import (
    TensorSpec,
    _add_hyper_connection,
    _TensorBuilder,
    tensor_structure_sha256,
)
from compiler.frontend.deepseek_v4_releases import (
    V41_FLASH,
    DeepSeekV4Release,
    DeepSeekV4ReleaseError,
    resolve_release,
)
from compiler.ir.model import load_strict_json


#: The default release.  Every name below is one of its fields, following the
#: V4 module's convention so the two front ends are read the same way.
V41_FLASH_RELEASE = V41_FLASH

MODEL_ID = V41_FLASH_RELEASE.model_id
REPOSITORY = V41_FLASH_RELEASE.repository
REVISION = V41_FLASH_RELEASE.revision
CONFIG_SHA256 = V41_FLASH_RELEASE.config_sha256
INDEX_SHA256 = V41_FLASH_RELEASE.index_sha256
TENSOR_STRUCTURE_SHA256 = V41_FLASH_RELEASE.tensor_structure_sha256
OFFICIAL_CHECKPOINT_LOCK_ID = V41_FLASH_RELEASE.checkpoint_lock_id
OFFICIAL_TENSOR_CONTENT_SHA256 = V41_FLASH_RELEASE.tensor_content_sha256
TENSOR_COUNT = V41_FLASH_RELEASE.tensor_count
PAYLOAD_BYTES = V41_FLASH_RELEASE.payload_bytes

TARGET_DIR = V41_FLASH_RELEASE.target_dir
DEFAULT_CONFIG = V41_FLASH_RELEASE.config_path
DEFAULT_SOURCE = V41_FLASH_RELEASE.checkpoint_source_path


#: The released config section that carries the vision tower.  It is a key name,
#: not a geometry: every extent inside it is read from the section itself.  The
#: release record pins the same section in ``config_sections``, and
#: ``build_official_tensor_specs`` requires the two to agree so this name cannot
#: drift away from the one the gate checks.
VISION_SECTION = "vision_config"


class DeepSeekV41AdapterError(RuntimeError):
    """Raised when the official graph or tensor contract differs."""


# -- configuration gate ---------------------------------------------------


def _expect(section: Mapping[str, Any], key: str, expected: Any, where: str) -> None:
    if key not in section or section[key] != expected:
        raise DeepSeekV41AdapterError(
            f"official config {where}{key!r} differs: "
            f"{section.get(key)!r} versus {expected!r}"
        )


def validate_official_config(
    config: Mapping[str, Any], release: DeepSeekV4Release = V41_FLASH_RELEASE
) -> None:
    """Require exactly one release's architecture-affecting configuration.

    The gate is the same one V4 uses -- every key the front end sizes anything
    by is pinned on the record and confronted key by key -- resolved through the
    record's ``config_layout`` so a nested release is checked in its own
    sections rather than flattened first.  ``compress_ratios`` is confronted
    with the record's own table, which is what decides the 40-layer CED
    structure: the window-only prefix, the ratio-2 encoder and the ratio-1
    decoder, plus the DSpark stages' trailing entries.

    The four V4.1 layer-mode lists are pinned here because every later stage
    reads them and none of them can be inferred from a layer index:
    ``kv_source_layer_ids``, ``index_source_layer_ids``,
    ``candidate_source_layer_id`` and ``engram_layer_ids``.
    """

    release = resolve_release(release)
    if not isinstance(config, Mapping):
        raise DeepSeekV41AdapterError("official model config must be an object")

    def located(structure: str) -> tuple[Mapping[str, Any], str]:
        """One pinned structure's enclosing object, and its path for messages."""

        try:
            section = release.config_section(config, structure)
        except DeepSeekV4ReleaseError as exc:
            raise DeepSeekV41AdapterError(str(exc)) from None
        path = ".".join(release.config_path_for(structure))
        return section, f"{path}." if path else ""

    architecture, prefix = located("architecture")
    for key, expected in release.config_scalars.items():
        _expect(architecture, key, expected, prefix)

    # The three structured values, each confronted in the object the release puts
    # it in: V4 keeps all three at the root, V4.1 keeps two under ``text_config``.
    for structure, pinned in (
        ("quantization_config", dict(release.quantization_config)),
        ("rope_scaling", dict(release.rope_scaling)),
        ("compress_ratios", release.compress_ratios),
    ):
        parent, where = located(structure)
        _expect(parent, structure, pinned, where)

    # Sections pinned whole beside the architecture: a multi-modal release's root
    # identity and its vision tower.  A record that pins none checks none.
    for path, pinned_section in release.config_sections.items():
        section: Any = config
        resolved = True
        for key in filter(None, path.split(".")):
            if not isinstance(section, Mapping) or key not in section:
                resolved = False
                break
            section = section[key]
        if pinned_section is None:
            #: PINNED ABSENT. The record says this release has no such
            #: structure, so a config that carries one contradicts it.
            if resolved:
                raise DeepSeekV41AdapterError(
                    f"official config carries section {path!r}, which "
                    f"{release.model_id} pins as absent"
                )
            continue
        if not resolved:
            raise DeepSeekV41AdapterError(
                f"official config has no section {path!r}"
            )
        if not isinstance(section, Mapping):
            raise DeepSeekV41AdapterError(f"config section {path!r} is not an object")
        for key, expected in pinned_section.items():
            _expect(section, key, expected, f"{path}." if path else "")


def load_official_config(
    path: Path | None = None,
    source_path: Path | None = None,
    release: DeepSeekV4Release = V41_FLASH_RELEASE,
) -> dict[str, Any]:
    """Load the byte-exact committed copy of one release's official config.

    The bytes are authenticated against the release record's own
    ``config_sha256`` and byte length, and again against the checkpoint source
    contract wherever that contract is committed.  A release whose contract is
    not committed yet says so on its record (``checkpoint_source_pending``);
    absence is tolerated only there, and the pinned digest still holds.
    """

    release = resolve_release(release)
    path = release.config_path if path is None else Path(path)
    source_path = (
        release.checkpoint_source_path if source_path is None else Path(source_path)
    )
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise DeepSeekV41AdapterError(
            f"cannot read official config {path}: {exc}"
        ) from exc
    digest = hashlib.sha256(payload).hexdigest()
    if digest != release.config_sha256 or len(payload) != release.config_bytes:
        raise DeepSeekV41AdapterError(
            f"official config {path} is not the pinned {release.model_id} config: "
            f"sha256 {digest} over {len(payload)} bytes against the pinned "
            f"{release.config_sha256} over {release.config_bytes} bytes"
        )
    if source_path.is_file():
        source = load_checkpoint_source(source_path)
        if (
            source["repository"] != release.repository
            or source["revision"] != release.revision
        ):
            raise DeepSeekV41AdapterError(
                f"checkpoint source is not the pinned {release.model_id} release"
            )
        expected = {item["path"]: item for item in source["expected_files"]}[
            "config.json"
        ]
        if digest != expected["sha256"] or len(payload) != expected["size_bytes"]:
            raise DeepSeekV41AdapterError(
                "official config bytes differ from the checkpoint source contract"
            )
    elif not release.checkpoint_source_pending:
        raise DeepSeekV41AdapterError(
            f"checkpoint source contract {source_path} is absent; build it with "
            "tools/build_checkpoint_source.py"
        )
    try:
        config = load_strict_json(path)
    except ValueError as exc:
        raise DeepSeekV41AdapterError(f"invalid official config: {exc}") from exc
    validate_official_config(config, release)
    return config


# -- tensor contract ------------------------------------------------------


def _add_attention(
    builder: _TensorBuilder,
    prefix: str,
    layer: int,
    *,
    architecture: Mapping[str, Any],
    scope: str,
) -> None:
    """The attention weights every V4.1 block owns, CED role notwithstanding.

    Every layer projects its own query and output and normalises its own KV
    latent; what the layer-mode lists decide is only whether it also *produces*
    that latent and whether it scores an index.
    """

    dim = architecture["hidden_size"]
    heads = architecture["num_attention_heads"]
    head_dim = architecture["head_dim"]
    q_rank = architecture["q_lora_rank"]
    groups = architecture["o_groups"]
    o_rank = architecture["o_lora_rank"]

    attn = f"{prefix}.attn"
    builder.add(
        f"{attn}.attn_sink",
        "F32",
        (heads,),
        "attention.sink",
        scope=scope,
        layer=layer,
        logical_dtype="FP32",
    )
    builder.add(
        f"{attn}.kv_norm.weight",
        "BF16",
        (head_dim,),
        "attention.kv_norm.weight",
        scope=scope,
        layer=layer,
    )
    builder.add(
        f"{attn}.q_norm.weight",
        "BF16",
        (q_rank,),
        "attention.q_norm.weight",
        scope=scope,
        layer=layer,
    )
    builder.fp8_linear(
        f"{attn}.wkv", head_dim, dim, "attention.kv_projection", scope=scope, layer=layer
    )
    builder.fp8_linear(
        f"{attn}.wo_a",
        groups * o_rank,
        heads * head_dim // groups,
        "attention.output_a",
        scope=scope,
        layer=layer,
    )
    builder.fp8_linear(
        f"{attn}.wo_b",
        dim,
        groups * o_rank,
        "attention.output_b",
        scope=scope,
        layer=layer,
    )
    builder.fp8_linear(
        f"{attn}.wq_a", q_rank, dim, "attention.query_a", scope=scope, layer=layer
    )
    builder.fp8_linear(
        f"{attn}.wq_b",
        heads * head_dim,
        q_rank,
        "attention.query_b",
        scope=scope,
        layer=layer,
    )
    builder.add(
        f"{prefix}.attn_norm.weight",
        "BF16",
        (dim,),
        "block.attention_norm.weight",
        scope=scope,
        layer=layer,
    )


def _add_kv_source(
    builder: _TensorBuilder,
    prefix: str,
    layer: int,
    compress_ratio: int,
    *,
    architecture: Mapping[str, Any],
    scope: str,
) -> None:
    """The compressor and index-key weights a KV source layer owns.

    ``wgate`` exists only above ratio 1: ``Compressor.forward`` returns
    ``norm(wkv(x))`` directly at ratio 1, so there is nothing to pool and no
    softmax gate to learn.  Both projections are BF16 as stored, whatever the
    released module promotes them to at load time.
    """

    if compress_ratio < 1:
        raise DeepSeekV41AdapterError(
            f"layer {layer} is a KV source at compression ratio {compress_ratio}, "
            "which publishes no latent"
        )
    dim = architecture["hidden_size"]
    head_dim = architecture["head_dim"]
    index_dim = architecture["index_head_dim"]

    compressor = f"{prefix}.attn.compressor"
    builder.add(
        f"{compressor}.norm.weight",
        "BF16",
        (head_dim,),
        "attention.compressor.norm.weight",
        scope=scope,
        layer=layer,
    )
    projections = ["wkv"] + (["wgate"] if compress_ratio > 1 else [])
    for projection in projections:
        builder.add(
            f"{compressor}.{projection}.weight",
            "BF16",
            (head_dim, dim),
            f"attention.compressor.{projection}.weight",
            scope=scope,
            layer=layer,
        )
    indexer = f"{prefix}.attn.indexer"
    builder.add(
        f"{indexer}.k_norm.weight",
        "BF16",
        (index_dim,),
        "attention.indexer.k_norm.weight",
        scope=scope,
        layer=layer,
    )
    builder.add(
        f"{indexer}.wk.weight",
        "BF16",
        (index_dim, head_dim),
        "attention.indexer.key.weight",
        scope=scope,
        layer=layer,
    )


def _add_index_source(
    builder: _TensorBuilder,
    prefix: str,
    layer: int,
    *,
    architecture: Mapping[str, Any],
    scope: str,
) -> None:
    """The query side of an indexer, owned by every index source layer."""

    dim = architecture["hidden_size"]
    q_rank = architecture["q_lora_rank"]
    index_dim = architecture["index_head_dim"]
    index_heads = architecture["index_n_heads"]

    indexer = f"{prefix}.attn.indexer"
    builder.add(
        f"{indexer}.weights_proj.weight",
        "BF16",
        (index_heads, dim),
        "attention.indexer.head_weights.weight",
        scope=scope,
        layer=layer,
    )
    builder.fp8_linear(
        f"{indexer}.wq_b",
        index_heads * index_dim,
        q_rank,
        "attention.indexer.query",
        scope=scope,
        layer=layer,
    )


def _add_engram(
    builder: _TensorBuilder,
    prefix: str,
    layer: int,
    rows: int,
    *,
    architecture: Mapping[str, Any],
    scope: str,
) -> None:
    """One Engram module: an FP8 n-gram table and the projection that reads it.

    ``n_hash_cols`` is ``(engram_max_ngram_size - 1) * engram_n_heads`` -- one
    bucket per (n-gram order, hash head) pair, orders 2 upwards -- and ``wkv``
    maps those rows onto one key per hyper-connection copy plus one shared
    value, so its output is ``hidden_size * (hc_mult + 1)``.  The table's scale
    granularity is the released FP8 block, the same one the linear layers use.
    """

    dim = architecture["hidden_size"]
    hc_mult = architecture["hc_mult"]
    head_dim = architecture["engram_head_dim"]
    hash_columns = (architecture["engram_max_ngram_size"] - 1) * architecture[
        "engram_n_heads"
    ]

    engram = f"{prefix}.engram"
    weight = f"{engram}.embed.weight"
    builder.add(
        weight,
        "F8_E4M3",
        (rows, head_dim),
        "engram.table.weight",
        scope=scope,
        layer=layer,
        logical_dtype="FP8_E4M3FN",
    )
    builder.add(
        f"{engram}.embed.scale",
        "F8_E8M0",
        (rows, math.ceil(head_dim / builder.fp8_block_columns)),
        "engram.table.scale",
        scope=scope,
        layer=layer,
        logical_dtype="UE8M0_SCALE",
        scale_for=weight,
    )
    for branch in ("q", "k"):
        builder.add(
            f"{engram}.{branch}_weight",
            "BF16",
            (hc_mult, dim),
            f"engram.gate.{branch}_weight",
            scope=scope,
            layer=layer,
        )
    builder.fp8_linear(
        f"{engram}.wkv",
        dim * (hc_mult + 1),
        hash_columns * head_dim,
        "engram.lookup_projection",
        scope=scope,
        layer=layer,
    )


def _add_moe(
    builder: _TensorBuilder,
    prefix: str,
    layer: int,
    experts: int,
    *,
    architecture: Mapping[str, Any],
    scope: str,
    vision_enabled: bool,
) -> None:
    """The router, the FP4 routed experts and the FP8 shared expert.

    ``bias_vl`` is the second selection bias ``Gate`` builds when the release
    has a vision tower, and which it substitutes for ``bias`` at image
    positions.  V4.1 hash-routes no layer, so there is no ``tid2eid`` table.
    """

    dim = architecture["hidden_size"]
    inter = architecture["moe_intermediate_size"]

    ffn = f"{prefix}.ffn"
    builder.add(
        f"{ffn}.gate.weight",
        "BF16",
        (experts, dim),
        "moe.router.weight",
        scope=scope,
        layer=layer,
    )
    biases = ["bias"] + (["bias_vl"] if vision_enabled else [])
    for bias in biases:
        builder.add(
            f"{ffn}.gate.{bias}",
            "F32",
            (experts,),
            f"moe.router.selection_{bias}",
            scope=scope,
            layer=layer,
            logical_dtype="FP32",
        )
    for expert in range(experts):
        root = f"{ffn}.experts.{expert}"
        for projection, out_features, in_features, role in (
            ("w1", inter, dim, "gate"),
            ("w2", dim, inter, "down"),
            ("w3", inter, dim, "up"),
        ):
            builder.fp4_linear(
                f"{root}.{projection}",
                out_features,
                in_features,
                f"moe.routed_expert.{role}",
                scope=scope,
                layer=layer,
                expert=expert,
            )
    shared = f"{ffn}.shared_experts"
    for projection, out_features, in_features, role in (
        ("w1", inter, dim, "gate"),
        ("w2", dim, inter, "down"),
        ("w3", inter, dim, "up"),
    ):
        builder.fp8_linear(
            f"{shared}.{projection}",
            out_features,
            in_features,
            f"moe.shared_expert.{role}",
            scope=scope,
            layer=layer,
        )
    builder.add(
        f"{prefix}.ffn_norm.weight",
        "BF16",
        (dim,),
        "block.ffn_norm.weight",
        scope=scope,
        layer=layer,
    )


def _add_block(
    builder: _TensorBuilder,
    prefix: str,
    layer: int,
    compress_ratio: int,
    experts: int,
    *,
    architecture: Mapping[str, Any],
    scope: str,
    vision_enabled: bool,
    kv_source: bool,
    index_source: bool,
    engram_rows: int | None,
    supported_ratios: frozenset[int],
) -> None:
    """One V4.1 block: attention, its CED roles, optional Engram, and the MoE.

    The four role flags come from the released layer-mode lists rather than from
    the layer index, which is the whole point of the CED: a layer's weights are
    decided by whether it publishes KV, whether it scores an index, and whether
    it carries an Engram table, and those three are independent of each other.
    """

    if compress_ratio not in supported_ratios:
        raise DeepSeekV41AdapterError(
            f"compression ratio {compress_ratio} at layer {layer} is not one of "
            f"this release's {sorted(supported_ratios)}"
        )
    _add_attention(
        builder, prefix, layer, architecture=architecture, scope=scope
    )
    if kv_source:
        _add_kv_source(
            builder,
            prefix,
            layer,
            compress_ratio,
            architecture=architecture,
            scope=scope,
        )
    if index_source:
        _add_index_source(
            builder, prefix, layer, architecture=architecture, scope=scope
        )
    if engram_rows is not None:
        _add_engram(
            builder,
            prefix,
            layer,
            engram_rows,
            architecture=architecture,
            scope=scope,
        )
    _add_moe(
        builder,
        prefix,
        layer,
        experts,
        architecture=architecture,
        scope=scope,
        vision_enabled=vision_enabled,
    )
    for branch in ("attn", "ffn"):
        _add_hyper_connection(
            builder,
            prefix,
            branch,
            dim=architecture["hidden_size"],
            hc_mult=architecture["hc_mult"],
            scope=scope,
            layer=layer,
        )


def _add_vision_tower(
    builder: _TensorBuilder,
    *,
    architecture: Mapping[str, Any],
    vision: Mapping[str, Any],
) -> None:
    """The ViT, the aligner and the three image-span delimiter embeddings.

    ``patch_embed.proj`` takes a flattened RGB patch, so its input is
    ``3 * patch_size ** 2``; the aligner's input is ``downsample_ratio ** 2``
    pooled ViT rows; the ViT MLP's first projection is a SwiGLU pair, hence
    ``2 * intermediate_size``.
    """

    dim = architecture["hidden_size"]
    vision_dim = vision["hidden_size"]
    inter = vision["intermediate_size"]
    patch = vision["patch_size"]
    downsample = vision["downsample_ratio"]

    for delimiter in ("image_end", "image_newline", "image_start"):
        builder.add(
            delimiter,
            "BF16",
            (dim,),
            f"model.{delimiter}_embedding",
            scope="global",
        )
    for projection, in_features in (("w1", vision_dim * downsample**2), ("w2", dim)):
        builder.add(
            f"aligner.{projection}.weight",
            "BF16",
            (dim, in_features),
            f"vision.aligner.{projection}.weight",
            scope="vision",
        )
        builder.add(
            f"aligner.{projection}.bias",
            "BF16",
            (dim,),
            f"vision.aligner.{projection}.bias",
            scope="vision",
        )
    builder.add(
        "vision.patch_embed.proj.weight",
        "BF16",
        (vision_dim, 3 * patch**2),
        "vision.patch_embed.weight",
        scope="vision",
    )
    builder.add(
        "vision.patch_embed.proj.bias",
        "BF16",
        (vision_dim,),
        "vision.patch_embed.bias",
        scope="vision",
    )
    builder.add(
        "vision.norm.weight",
        "BF16",
        (vision_dim,),
        "vision.final_norm.weight",
        scope="vision",
    )
    for block in range(vision["num_hidden_layers"]):
        prefix = f"vision.blocks.{block}"
        for projection, out_features in (("wqkv", 3 * vision_dim), ("wo", vision_dim)):
            builder.add(
                f"{prefix}.attn.{projection}.weight",
                "BF16",
                (out_features, vision_dim),
                f"vision.attention.{projection}.weight",
                scope="vision",
                layer=block,
            )
            builder.add(
                f"{prefix}.attn.{projection}.bias",
                "BF16",
                (out_features,),
                f"vision.attention.{projection}.bias",
                scope="vision",
                layer=block,
            )
        builder.add(
            f"{prefix}.mlp.w1.weight",
            "BF16",
            (2 * inter, vision_dim),
            "vision.mlp.gate_up.weight",
            scope="vision",
            layer=block,
        )
        builder.add(
            f"{prefix}.mlp.w2.weight",
            "BF16",
            (vision_dim, inter),
            "vision.mlp.down.weight",
            scope="vision",
            layer=block,
        )
        for norm in ("norm1", "norm2"):
            builder.add(
                f"{prefix}.{norm}.weight",
                "BF16",
                (vision_dim,),
                f"vision.block.{norm}.weight",
                scope="vision",
                layer=block,
            )


def _add_dspark_heads(
    builder: _TensorBuilder,
    release: DeepSeekV4Release,
    *,
    architecture: Mapping[str, Any],
) -> None:
    """What the DSpark stages own beyond a block, and which stage owns it.

    ``DSparkBlock.__init__`` gives stage 0 the projection that folds the target
    layers' hidden states into one, and gives the *last* stage the final norm,
    the Markov head and the confidence head.  Both are read from the release
    rather than from a stage number written here.
    """

    dim = architecture["hidden_size"]
    vocab = architecture["vocab_size"]
    markov_rank = architecture["dspark_markov_rank"]
    targets = architecture["dspark_target_layer_ids"]

    builder.fp8_linear(
        "mtp.0.main_proj",
        dim,
        dim * len(targets),
        "dspark.main_hidden_projection",
        scope="dspark",
        layer=0,
    )
    builder.add(
        "mtp.0.main_norm.weight",
        "BF16",
        (dim,),
        "dspark.main_hidden_norm.weight",
        scope="dspark",
        layer=0,
    )
    final_stage = release.dspark_stage_count - 1
    final_prefix = f"mtp.{final_stage}"
    builder.add(
        f"{final_prefix}.norm.weight",
        "BF16",
        (dim,),
        "dspark.final_norm.weight",
        scope="dspark",
        layer=final_stage,
    )
    for projection, role in (("embed", "markov_embedding"), ("head", "markov_head")):
        builder.add(
            f"{final_prefix}.markov_head.{projection}.weight",
            "BF16",
            (vocab, markov_rank),
            f"dspark.{role}.weight",
            scope="dspark",
            layer=final_stage,
        )
    builder.add(
        f"{final_prefix}.confidence_head.proj.weight",
        "BF16",
        (1, dim + markov_rank),
        "dspark.confidence_head.weight",
        scope="dspark",
        layer=final_stage,
    )


def build_official_tensor_specs(
    config: Mapping[str, Any], release: DeepSeekV4Release = V41_FLASH_RELEASE
) -> tuple[TensorSpec, ...]:
    """Generate one release's complete tensor contract from official semantics.

    The count is the release record's ``tensor_count`` -- 96,085 for
    DeepSeek-V4.1-Flash -- and a derivation that lands anywhere else is refused.
    """

    release = resolve_release(release)
    validate_official_config(config, release)
    architecture = release.config_section(config, "architecture")
    quantization = release.config_section(config, "quantization_config")[
        "quantization_config"
    ]
    if VISION_SECTION not in release.config_sections:
        raise DeepSeekV41AdapterError(
            f"{release.model_id} pins no {VISION_SECTION!r} section, so this "
            "adapter cannot tell whether the release has a vision tower"
        )
    vision = config.get(VISION_SECTION)
    vision_enabled = isinstance(vision, Mapping)
    supported_ratios = frozenset(release.supported_compress_ratios)

    # The FP8 scale geometry is the released block, not a constant: V4 publishes
    # [128, 128] and V4.1 [32, 32], and one generator serves both.
    builder = _TensorBuilder(tuple(quantization["weight_block_size"]))
    dim = architecture["hidden_size"]
    vocab = architecture["vocab_size"]

    for name, shape, role in (
        ("embed.weight", (vocab, dim), "model.token_embedding.weight"),
        ("head.weight", (vocab, dim), "model.lm_head.weight"),
        ("norm.weight", (dim,), "model.final_norm.weight"),
    ):
        builder.add(name, "BF16", shape, role, scope="global")
    if vision_enabled:
        _add_vision_tower(builder, architecture=architecture, vision=vision)

    engram_layers = list(architecture.get("engram_layer_ids", ()))
    engram_rows = list(architecture.get("engram_num_embeddings", ()))
    if len(engram_layers) != len(engram_rows):
        raise DeepSeekV41AdapterError(
            f"{len(engram_layers)} Engram layers but {len(engram_rows)} row counts"
        )
    kv_sources = set(architecture["kv_source_layer_ids"])
    index_sources = set(architecture["index_source_layer_ids"])
    if not kv_sources <= index_sources:
        raise DeepSeekV41AdapterError(
            "every KV source layer must also be an index source, because its "
            f"index key is derived from its own latent: {sorted(kv_sources - index_sources)}"
        )

    for layer, ratio in enumerate(release.main_compress_ratios):
        _add_block(
            builder,
            f"layers.{layer}",
            layer,
            ratio,
            architecture["n_routed_experts"],
            architecture=architecture,
            scope="main",
            vision_enabled=vision_enabled,
            kv_source=layer in kv_sources,
            index_source=layer in index_sources,
            engram_rows=(
                engram_rows[engram_layers.index(layer)]
                if layer in engram_layers
                else None
            ),
            supported_ratios=supported_ratios,
        )
    for stage, ratio in enumerate(release.dspark_compress_ratios):
        _add_block(
            builder,
            f"mtp.{stage}",
            stage,
            ratio,
            architecture["dspark_n_routed_experts"],
            architecture=architecture,
            scope="dspark",
            vision_enabled=vision_enabled,
            kv_source=False,
            index_source=False,
            engram_rows=None,
            supported_ratios=supported_ratios,
        )
    _add_dspark_heads(builder, release, architecture=architecture)

    specs = tuple(builder.specs[name] for name in sorted(builder.specs))
    if len(specs) != release.tensor_count:
        raise DeepSeekV41AdapterError(
            f"adapter generated {len(specs)} tensors instead of the pinned "
            f"{release.tensor_count} for {release.model_id}"
        )
    payload = sum(spec.size_bytes for spec in specs)
    if payload != release.payload_bytes:
        raise DeepSeekV41AdapterError(
            f"adapter generated {payload} payload bytes instead of the pinned "
            f"{release.payload_bytes} for {release.model_id}"
        )
    return specs


__all__ = [
    "CONFIG_SHA256",
    "INDEX_SHA256",
    "MODEL_ID",
    "PAYLOAD_BYTES",
    "REPOSITORY",
    "REVISION",
    "TENSOR_COUNT",
    "TENSOR_STRUCTURE_SHA256",
    "V41_FLASH_RELEASE",
    "DeepSeekV41AdapterError",
    "TensorSpec",
    "build_official_tensor_specs",
    "load_official_config",
    "tensor_structure_sha256",
    "validate_official_config",
]
