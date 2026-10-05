"""The pinned DeepSeek-V4 releases, one frozen record each.

Three modules make up the DeepSeek-V4 front end: ``deepseek_v4`` derives the
checkpoint tensor contract, ``deepseek_v4_graph`` derives the source-mapped node
graph, and ``compiler/frontends/v3/deepseek_v4`` lowers that graph into Tensor
Kernel IR v3.  Each of them used to carry the DeepSeek-V4-Flash-0731 numbers as
module constants, so a second release could not be named without editing the
code that reads them.  This module holds the release facts instead: every
architecture-affecting number is written once here and read from there.

A record is a pin, not a description
------------------------------------
``config_scalars`` is the gate.  The front end refuses any released
``config.json`` that disagrees with it key by key, so a record that is wrong
makes a build fail rather than making it quietly produce a different graph.  The
same holds for ``main_compress_ratios``: it decides which layers own compressor
and indexer weights, and it is confronted with the released ``compress_ratios``
list on every load.

Both releases pin ``checkpoint_lock_id`` and ``tensor_content_sha256``, which
are outputs of reading every payload byte through
``tools/build_checkpoint_lock.py``.  A record that names a lock the host cannot
produce fails closed and says which tool produces it, so a checkpoint cannot be
substituted for the pinned one without the mismatch surfacing.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

#: Where the local Hugging Face cache keeps a snapshot, and where
#: ``tools/build_checkpoint_lock.py`` writes a lock.  Both are host paths, not
#: release facts, so they are composed from the identity below rather than
#: written out per release.
HUGGINGFACE_HUB = Path.home() / ".cache/huggingface/hub"
CHECKPOINT_LOCK_ROOT = Path.home() / ".cache/opentallas"
MODELS_DIR = Path(__file__).resolve().parents[1] / "models"


#: The structures a front end resolves out of a released ``config.json``, and
#: the key path each one sits at.  A flat release keeps all four at the root.
CONFIG_LAYOUT_KEYS = (
    "architecture",
    "compress_ratios",
    "quantization_config",
    "rope_scaling",
)
_FLAT_CONFIG_LAYOUT = MappingProxyType({key: () for key in CONFIG_LAYOUT_KEYS})
_NO_CONFIG_SECTIONS: Mapping[str, Mapping[str, Any]] = MappingProxyType({})


class DeepSeekV4ReleaseError(RuntimeError):
    """Raised when a release is named that this front end does not carry."""


@dataclass(frozen=True)
class DeepSeekV4Release:
    """One content-pinned DeepSeek-V4 release.

    ``config_scalars`` carries every architecture-affecting root-config key.
    ``quantization_config``, ``rope_scaling`` and the compression-ratio tables
    are the released structured values and are checked the same way.
    """

    model_id: str
    repository: str
    revision: str
    config_sha256: str
    config_bytes: int
    index_sha256: str
    shard_count: int
    tensor_count: int
    payload_bytes: int
    tensor_structure_sha256: str
    tensor_structure_evidence: str
    inference_config_sha256: str
    #: ``None`` where the model HAS no such artefact. A released model always
    #: has all three; a committed regression fixture has none of them -- its
    #: checkpoint source lists four files and not one is a tokenizer or a card.
    #:
    #: The annotation widens rather than gaining a default on purpose: every
    #: caller still has to say what it means, so a released record cannot grow a
    #: silent None by omission, and a fixture's None is a statement rather than
    #: an oversight.
    model_card_sha256: str | None
    tokenizer_sha256: str | None
    tokenizer_config_sha256: str | None
    main_compress_ratios: tuple[int, ...]
    dspark_compress_ratios: tuple[int, ...]
    config_scalars: Mapping[str, Any]
    quantization_config: Mapping[str, Any]
    rope_scaling: Mapping[str, Any]
    #: Outputs of a complete pass over the checkpoint payload.  ``None`` until
    #: ``tools/build_checkpoint_lock.py`` has produced the lock.
    checkpoint_lock_id: str | None = None
    tensor_content_sha256: str | None = None
    #: True while ``checkpoint_source.json`` is not yet committed for this
    #: release.  It is the registry-listing witness that
    #: ``tools/build_checkpoint_source.py`` writes, and it needs the complete
    #: snapshot; the committed ``config.json`` is authenticated against
    #: ``config_sha256`` either way.
    checkpoint_source_pending: bool = False
    #: The canonical-application evidence this release has, quoted verbatim in
    #: the graph contract's covered scope.  ``None`` where no such application
    #: has been built, because the scope list may not claim one that has not.
    canonical_application_claim: str | None = None
    #: The pooling widths this release's ``compress_ratios`` may name.  V4
    #: publishes window-only, ratio-4 and ratio-128 layers; V4.1's Causal
    #: Encoder-Decoder publishes ratio 2 and ratio 1 instead.  The admissible
    #: set is a release fact, so it is written here rather than frozen into the
    #: predicate that checks it.
    supported_compress_ratios: tuple[int, ...] = (0, 4, 128)
    #: Where each pinned structure sits inside a released ``config.json``, as a
    #: key path from the root; the empty path is the root object itself.  V4
    #: publishes one flat object, so every default is the root.  V4.1 nests the
    #: language model under ``text_config`` while leaving the weight
    #: quantization at the root, and says so here instead of leaving a front end
    #: to assume one shape or the other.
    config_layout: Mapping[str, tuple[str, ...]] = _FLAT_CONFIG_LAYOUT
    #: Pinned sections of the released config besides the architecture section,
    #: keyed by the same key path joined with ``.`` (``""`` is the root).  A
    #: multi-modal release carries its own tower and its own root identity
    #: alongside the language model's scalars.
    #:
    #: A value of ``None`` PINS THE SECTION ABSENT, which is a different
    #: statement from not pinning it at all.  Front ends read the presence of a
    #: key here to decide whether a record can speak about that structure --
    #: ``build_official_tensor_specs`` refuses a record that pins no
    #: ``vision_config``, because such a record cannot say whether the release
    #: has a tower -- and they read the section's presence in the CONFIG to
    #: decide whether the structure exists.  Those are two different questions,
    #: and a text-only model needs to answer the first yes and the second no.
    #: Without ``None`` it cannot: pinning the section forces the config to
    #: carry it, and omitting the pin makes the front end refuse.
    #:
    #: It stays a pin, not a silence.  ``validate_official_config`` refuses a
    #: config that DOES carry a section pinned absent, so "absent" is asserted
    #: and checked rather than merely unmentioned.
    config_sections: Mapping[str, Mapping[str, Any] | None] = _NO_CONFIG_SECTIONS

    def __post_init__(self) -> None:
        layers = self.config_scalars.get("num_hidden_layers")
        if layers != len(self.main_compress_ratios):
            raise DeepSeekV4ReleaseError(
                f"{self.model_id}: num_hidden_layers={layers} but the pinned "
                f"main ratio table has {len(self.main_compress_ratios)} entries"
            )
        unsupported = sorted(
            set(self.main_compress_ratios) | set(self.dspark_compress_ratios)
        )
        if any(ratio not in set(self.supported_compress_ratios) for ratio in unsupported):
            raise DeepSeekV4ReleaseError(
                f"{self.model_id}: unsupported compression ratios {unsupported}"
            )

    # -- identity ---------------------------------------------------------
    @property
    def snapshot(self) -> Path:
        """The local snapshot root for the pinned revision."""

        owner, name = self.repository.split("/", 1)
        return (
            HUGGINGFACE_HUB
            / f"models--{owner}--{name}"
            / "snapshots"
            / self.revision
        )

    @property
    def checkpoint_lock(self) -> Path:
        return CHECKPOINT_LOCK_ROOT / self.model_id / "checkpoint.lock.json"

    @property
    def checkpoint_index(self) -> Path:
        return self.snapshot / "model.safetensors.index.json"

    @property
    def target_dir(self) -> Path:
        return MODELS_DIR / self.model_id

    @property
    def config_path(self) -> Path:
        return self.target_dir / "config.json"

    @property
    def inference_config_path(self) -> Path:
        return self.target_dir / "inference_config.json"

    @property
    def checkpoint_source_path(self) -> Path:
        return self.target_dir / "checkpoint_source.json"

    # -- released values --------------------------------------------------
    @property
    def compress_ratios(self) -> list[int]:
        """The released ``compress_ratios`` list: main layers then MTP stages.

        ``inference/model.py`` builds ``DSparkBlock(args.n_layers + stage)`` and
        ``Block.__init__`` reads ``args.compress_ratios[layer_id]``, so the
        trailing entries are the DSpark stages' own ratios.
        """

        return [*self.main_compress_ratios, *self.dspark_compress_ratios]

    @property
    def num_hidden_layers(self) -> int:
        return int(self.config_scalars["num_hidden_layers"])

    @property
    def dspark_stage_count(self) -> int:
        return len(self.dspark_compress_ratios)

    def scalar(self, key: str) -> Any:
        """One pinned root-config value."""

        try:
            return self.config_scalars[key]
        except KeyError:  # pragma: no cover - a typo in a caller, not a release
            raise DeepSeekV4ReleaseError(
                f"{self.model_id} has no pinned config key {key!r}"
            ) from None

    def config_path_for(self, structure: str) -> tuple[str, ...]:
        """The key path a released config keeps one pinned structure at."""

        if structure not in CONFIG_LAYOUT_KEYS:
            raise DeepSeekV4ReleaseError(
                f"{structure!r} is not one of the located config structures "
                + ", ".join(CONFIG_LAYOUT_KEYS)
            )
        return tuple(self.config_layout.get(structure, ()))

    def config_section(self, config: Mapping[str, Any], structure: str) -> Any:
        """Resolve one pinned structure's enclosing object in a released config.

        ``architecture`` resolves the object ``config_scalars`` is checked
        against; the others resolve the object their same-named field is checked
        against.  A path that does not resolve to an object is a refusal rather
        than a silent fall back to the root, because falling back would let a
        nested release pass the flat release's gate.
        """

        node: Any = config
        walked: list[str] = []
        for key in self.config_path_for(structure):
            if not isinstance(node, Mapping) or key not in node:
                raise DeepSeekV4ReleaseError(
                    f"{self.model_id}: released config has no section "
                    f"{'.'.join([*walked, key])!r} for {structure}"
                )
            node = node[key]
            walked.append(key)
        if not isinstance(node, Mapping):
            raise DeepSeekV4ReleaseError(
                f"{self.model_id}: config section {'.'.join(walked) or 'root'!r} "
                f"for {structure} is not an object"
            )
        return node

    @property
    def lock_identity_established(self) -> bool:
        return (
            self.checkpoint_lock_id is not None
            and self.tensor_content_sha256 is not None
        )


#: The released FP8 weight-quantization block and the YaRN interpolation.  Both
#: releases publish the same two structures; they are shared here so a
#: difference would have to be written down to exist.
_QUANTIZATION_CONFIG = MappingProxyType(
    {
        "activation_scheme": "dynamic",
        "fmt": "e4m3",
        "quant_method": "fp8",
        "scale_fmt": "ue8m0",
        "weight_block_size": [128, 128],
    }
)
_ROPE_SCALING = MappingProxyType(
    {
        "beta_fast": 32,
        "beta_slow": 1,
        "factor": 16,
        "original_max_position_embeddings": 65536,
        "type": "yarn",
    }
)

#: ``inference/model.py:902`` builds one ``DSparkBlock`` per stage at
#: ``args.n_layers + stage``, and ``Block.__init__`` reads
#: ``args.compress_ratios[layer_id]``, so the three trailing zeros of both
#: releases' lists are the stages' ratios: the draft blocks are window-only in
#: both.
_DSPARK_RATIOS = (0, 0, 0)

#: Flash: two pure sliding-window layers, then 41 alternating compressed ones.
#: Pro: no window-only layer at all -- layers 0 and 1 are ratio 128, and the
#: remaining 59 alternate.  Both tables are confronted with the released
#: ``compress_ratios`` on every config load.
_FLASH_MAIN_RATIOS = (0, 0) + (4, 128) * 20 + (4,)
_PRO_MAIN_RATIOS = (128, 128) + (4, 128) * 29 + (4,)


FLASH = DeepSeekV4Release(
    model_id="deepseek-v4-flash-0731",
    repository="deepseek-ai/DeepSeek-V4-Flash-0731",
    revision="7872f01b1d1fe23eabc4c98b48bffcef5a386062",
    config_sha256="6c8f3d2d3b48707541b88f32f22ef3f0f8a6b57d8523281e2b8d3cdb0ae9a023",
    config_bytes=1_888,
    index_sha256="98efab455cf08dfbbbaaba6f570e1bf10bf927d2b4c3c453a59c2f6f0e3be92b",
    shard_count=48,
    tensor_count=72_317,
    payload_bytes=166_878_536_440,
    tensor_structure_sha256=(
        "18285fe60ca3655be488bbabb88b59489b8ee03cff7fc4f4729424051ca83e0e"
    ),
    tensor_structure_evidence="shard_header_inventory",
    inference_config_sha256=(
        "c90861f3d10a9e4ef5954f8f1a34c529d480da1c5799f84660028f4e38e14e71"
    ),
    model_card_sha256="252acafdc9204d0dba3fde1b0a93d71cd1664a4ceadfe222b60117ed0ccc56ff",
    tokenizer_sha256="8f9f37ca37fdc4f5fd36d5cf4d3b0e8392edb4e894fd10cc0d70b4957c8633cf",
    tokenizer_config_sha256=(
        "6ac8c8dc065ed118161d02dd532749ae3f52c243deac27872134fae2f50d8547"
    ),
    main_compress_ratios=_FLASH_MAIN_RATIOS,
    dspark_compress_ratios=_DSPARK_RATIOS,
    config_scalars=MappingProxyType(
        {
            "architectures": ["DeepseekV4ForCausalLM"],
            "bos_token_id": 0,
            "compress_rope_theta": 160000,
            "dspark_block_size": 5,
            "dspark_markov_rank": 256,
            "dspark_noise_token_id": 128799,
            "dspark_target_layer_ids": [40, 41, 42],
            "eos_token_id": 1,
            "expert_dtype": "fp4",
            "hc_eps": 1e-6,
            "hc_mult": 4,
            "hc_sinkhorn_iters": 20,
            "head_dim": 512,
            "hidden_act": "silu",
            "hidden_size": 4096,
            "index_head_dim": 128,
            "index_n_heads": 64,
            "index_topk": 512,
            "max_position_embeddings": 1_048_576,
            "model_type": "deepseek_v4",
            "moe_intermediate_size": 2048,
            "n_routed_experts": 256,
            "n_shared_experts": 1,
            "norm_topk_prob": True,
            "num_attention_heads": 64,
            "num_experts_per_tok": 6,
            "num_hash_layers": 3,
            "num_hidden_layers": 43,
            "num_key_value_heads": 1,
            # The release root config says one prediction layer, while the
            # official inference config and checkpoint contain three DSpark
            # stages.  This value remains pinned here; stage resolution is
            # explicit in ``dspark_compress_ratios``.
            "num_nextn_predict_layers": 1,
            "o_groups": 8,
            "o_lora_rank": 1024,
            "q_lora_rank": 1024,
            "qk_rope_head_dim": 64,
            "rms_norm_eps": 1e-6,
            "rope_theta": 10000,
            "routed_scaling_factor": 1.5,
            "scoring_func": "sqrtsoftplus",
            "sliding_window": 128,
            "swiglu_limit": 10.0,
            "tie_word_embeddings": False,
            "topk_method": "noaux_tc",
            "torch_dtype": "bfloat16",
            "use_cache": True,
            "vocab_size": 129280,
        }
    ),
    quantization_config=_QUANTIZATION_CONFIG,
    rope_scaling=_ROPE_SCALING,
    checkpoint_lock_id=(
        "30b3d07304b92cb26440e5ea9e28dcb06c835dbf35652529fa9a856da07ad760"
    ),
    tensor_content_sha256=(
        "7ca2e951786c4cd46b64b437d975da3565a1692bdceeb804c09d5fe9e1503b3f"
    ),
    canonical_application_claim=(
        "complete official 72,317-tensor, 77,116-assignment MP=4 canonical "
        "application with independent replay identity "
        "b20ac53d48714c2328470b45f44b06aed11bed4c6dc7ef48f27185c5ba813f28"
    ),
)


#: DeepSeek-V4-Pro-0813.  Twelve architecture-affecting root-config keys move
#: against Flash and every other key is equal; the twelve are
#: ``dspark_markov_rank``, ``dspark_target_layer_ids``, ``hidden_size``,
#: ``index_topk``, ``moe_intermediate_size``, ``n_routed_experts``,
#: ``num_attention_heads``, ``num_hidden_layers``, ``o_groups``,
#: ``q_lora_rank``, ``routed_scaling_factor`` and ``compress_ratios``.
#:
#: Provenance of the numbers that are not read out of the config:
#:
#: * ``config_sha256``/``config_bytes``, ``inference_config_sha256`` and
#:   ``model_card_sha256`` were measured with ``sha256sum`` over the downloaded
#:   snapshot's ``config.json`` (1,967 bytes), ``inference/config.json`` (1,240
#:   bytes) and ``README.md`` (7,522 bytes).  The first also equals
#:   ``data/inventory/deepseek-v4-pro-0813.json``'s ``config_sha256``.
#: * ``index_sha256`` and ``shard_count`` come from the committed registry
#:   listing ``data/inventory/deepseek-v4-pro-0813-registry-listing.json``,
#:   whose LFS record for ``model.safetensors.index.json`` gives
#:   ``2de2ac1e...`` at 11,651,606 bytes, and which agrees with the same
#:   inventory's ``index_sha256`` and ``shard_count``.
#: * ``tokenizer_sha256`` and ``tokenizer_config_sha256`` are Flash's, and that
#:   is a measurement rather than an assumption: the registry listing's Git
#:   blob ids for Pro's ``tokenizer.json`` and ``tokenizer_config.json``
#:   (``628e3364...``, ``f3dad388...``) equal ``git hash-object`` over the
#:   local Flash files, so the two releases ship the same two files byte for
#:   byte.  The four ``inference/*.py`` digests and the encoding digest, held
#:   in ``deepseek_v4_graph``, were re-measured equal on the Pro snapshot.
#: * ``tensor_count`` and ``payload_bytes`` are what ``build_official_tensor_specs``
#:   derives from this record, and both were confronted with the released
#:   ``model.safetensors.index.json``: its ``weight_map`` has exactly the same
#:   149,782 names, and its ``metadata.total_size`` is 892,727,580,904.  The
#:   governed inventory carries the same two numbers.
PRO = DeepSeekV4Release(
    model_id="deepseek-v4-pro-0813",
    repository="deepseek-ai/DeepSeek-V4-Pro-0813",
    revision="72e1d3230f6c080a530b0a1d46f8eb4602340597",
    config_sha256="9dd2a89255469e120b333668ef5a169b7ae46c00f6bbab786bf0be457546aec0",
    config_bytes=1_967,
    index_sha256="2de2ac1e43134f8b03bf6156067715b7c3c73b1a507329e606023c601a56d30a",
    shard_count=66,
    tensor_count=149_782,
    payload_bytes=892_727_580_904,
    # Derived from this record by ``tensor_structure_sha256`` over the 149,782
    # generated specs, not read back out of shard headers: no shard header has
    # been read yet.  ``tensor_structure_evidence`` says so, and
    # ``build_expected_tensor_contract`` reports it.
    tensor_structure_sha256=(
        "b776f80c8422880de39e49a0679d4d5b81d218bdd4074b66c691760b65cc0eeb"
    ),
    tensor_structure_evidence="adapter_derivation_pending_shard_headers",
    inference_config_sha256=(
        "801bc719d08cd5be57cddc185cac621417522810e29d0314849c939bf0176ee7"
    ),
    model_card_sha256="61755d88e95789fcd7a36f50892f97bba977a30fc99d0f2907ab787ed10b0e66",
    tokenizer_sha256="8f9f37ca37fdc4f5fd36d5cf4d3b0e8392edb4e894fd10cc0d70b4957c8633cf",
    tokenizer_config_sha256=(
        "6ac8c8dc065ed118161d02dd532749ae3f52c243deac27872134fae2f50d8547"
    ),
    main_compress_ratios=_PRO_MAIN_RATIOS,
    dspark_compress_ratios=_DSPARK_RATIOS,
    config_scalars=MappingProxyType(
        {
            "architectures": ["DeepseekV4ForCausalLM"],
            "bos_token_id": 0,
            "compress_rope_theta": 160000,
            "dspark_block_size": 5,
            "dspark_markov_rank": 512,
            "dspark_noise_token_id": 128799,
            "dspark_target_layer_ids": [58, 59, 60],
            "eos_token_id": 1,
            "expert_dtype": "fp4",
            "hc_eps": 1e-6,
            "hc_mult": 4,
            "hc_sinkhorn_iters": 20,
            "head_dim": 512,
            "hidden_act": "silu",
            "hidden_size": 7168,
            "index_head_dim": 128,
            "index_n_heads": 64,
            "index_topk": 1024,
            "max_position_embeddings": 1_048_576,
            "model_type": "deepseek_v4",
            "moe_intermediate_size": 3072,
            "n_routed_experts": 384,
            "n_shared_experts": 1,
            "norm_topk_prob": True,
            "num_attention_heads": 128,
            "num_experts_per_tok": 6,
            "num_hash_layers": 3,
            "num_hidden_layers": 61,
            "num_key_value_heads": 1,
            "num_nextn_predict_layers": 1,
            "o_groups": 16,
            "o_lora_rank": 1024,
            "q_lora_rank": 1536,
            "qk_rope_head_dim": 64,
            "rms_norm_eps": 1e-6,
            "rope_theta": 10000,
            "routed_scaling_factor": 2.5,
            "scoring_func": "sqrtsoftplus",
            "sliding_window": 128,
            "swiglu_limit": 10.0,
            "tie_word_embeddings": False,
            "topk_method": "noaux_tc",
            "torch_dtype": "bfloat16",
            "use_cache": True,
            "vocab_size": 129280,
        }
    ),
    quantization_config=_QUANTIZATION_CONFIG,
    rope_scaling=_ROPE_SCALING,
    # Both values are outputs of tools/build_checkpoint_lock.py over the
    # complete snapshot: 892,727,580,904 payload bytes across 149,782
    # tensors in 66 shards, read and hashed in 953 s.  The tensor-content
    # digest is over the sorted per-tensor records, so it moves if any
    # tensor's name, dtype, shape, shard or payload digest moves, and the
    # lock id covers those plus the source expectation the lock was
    # checked against.
    checkpoint_lock_id=(
        "4aff8a9e24558c5f11a8277cf0a3a63d688c3b378f02d3530137644eed35a462"
    ),
    tensor_content_sha256=(
        "be1727c7c091d88d3ff6518ca3e54a9dd87518377fe7391845c09ba62963a90d"
    ),
)


#: DeepSeek-V4.1-Flash, released 2026-09-10 (``SRC-DSV41-FLASH-CARD``).  The
#: release that stops being a V4 variant: a 40-layer Causal Encoder-Decoder
#: whose KV is published by four source layers rather than owned per layer, an
#: Engram n-gram memory at two layers, a candidate-pool level above the sparse
#: indexer, and a ViT tower.
#:
#: Three structural facts separate it from the two V4 records, and each is
#: carried as a field rather than as a special case in a front end:
#:
#: * The released ``config.json`` is nested.  The language model's scalars live
#:   under ``text_config`` and its ``rope_scaling`` with them, while the weight
#:   quantization stays at the root -- so ``config_layout`` locates all four
#:   pinned structures and ``config_sections`` pins the root identity and the
#:   vision tower beside them.
#: * ``compress_ratios`` names 2 and 1, not 4 and 128, so
#:   ``supported_compress_ratios`` says so.
#: * ``quantization_config.weight_block_size`` is ``[32, 32]``, not
#:   ``[128, 128]``; ``build_official_tensor_specs`` reads it, so both the FP8
#:   scale geometry of V4 and of V4.1 come out of one generator.
#:
#: Provenance of the numbers that are not read out of the config:
#:
#: * ``config_sha256``/``config_bytes``, ``model_card_sha256``,
#:   ``inference_config_sha256``, ``tokenizer_sha256`` and
#:   ``tokenizer_config_sha256`` were measured with ``sha256sum`` over the
#:   pinned snapshot's ``config.json`` (3,311 bytes), ``README.md`` (13,110),
#:   ``inference/config.json`` (1,982), ``tokenizer.json`` (6,367,257) and
#:   ``tokenizer_config.json`` (801).  The first three equal the digests
#:   ``docs/SOURCES.md`` records for ``SRC-DSV41-FLASH-CONFIG`` and ``-CARD``,
#:   and ``config_sha256`` equals ``data/inventory/deepseek-v4.1-flash.json``'s.
#:   ``tokenizer_config_sha256`` is byte-for-byte the V4 Flash and Pro file;
#:   ``tokenizer.json`` is new to this release.
#: * ``index_sha256`` was measured over the snapshot's
#:   ``model.safetensors.index.json`` (7,470,294 bytes) and equals both
#:   ``SRC-DSV41-FLASH-INDEX`` and the governed inventory's ``index_sha256``.
#: * ``tensor_count``, ``payload_bytes`` and ``tensor_structure_sha256`` are what
#:   ``compiler/frontend/deepseek_v41.build_official_tensor_specs`` derives from
#:   this record, confronted with the 48 pinned shard headers cached under
#:   ``.cache/hf/headers/`` -- every tensor name, dtype and shape equal -- and
#:   with the released index's ``metadata.total_size`` of 510,286,023,000.
#:   ``tensor_structure_evidence`` says so.
#: * ``checkpoint_source_pending`` is ``False``: the complete 48-shard snapshot
#:   arrived and ``tools/build_checkpoint_source.py`` (``make
#:   checkpoint-source-deepseek-v41``) digested all 88 registry-listed files
#:   against the committed witness
#:   ``data/inventory/deepseek-v4.1-flash-registry-listing.json``.  52 of the 88
#:   carry an LFS SHA-256, all 48 shards among them; the other 36 -- including
#:   ``model.safetensors.index.json`` and ``config.json`` -- are plain Git
#:   objects, which the tool reports as witnessed by size alone and whose
#:   published ``blobId`` the release test recomputes locally.  Two local
#:   ``__pycache__`` files the registry does not list are reported and not bound.
#:   Re-running the tool over the same snapshot reproduced the committed
#:   ``checkpoint_source.json`` byte for byte
#:   (sha256 ``da289c466ef00c225f2f1e4458affa5af79021bed22ccbc4bcc90aa947f9f8e4``).
#: * ``checkpoint_lock_id`` and ``tensor_content_sha256`` are outputs of
#:   ``tools/build_checkpoint_lock.py`` (``make checkpoint-lock-deepseek-v41``)
#:   over the complete snapshot: 510,286,023,000 payload bytes across 96,085
#:   tensors in 48 shards, every shard header parsed and every tensor payload
#:   hashed.  ``compiler.frontend.checkpoint.verify_checkpoint_lock`` then rebuilt
#:   the lock from those same bytes and required canonical equality, which held in
#:   568 s -- so the pinned ``lock_id`` is reproducible on this snapshot and not
#:   merely the output of one pass.  The lock's 96,085 tensor names, dtypes and
#:   shapes and its payload total also equal what
#:   ``build_official_tensor_specs`` derives from the config alone, which is an
#:   agreement between a byte-level read and a header-free derivation.

#: SRC-DSV41-FLASH-REPORT section 2.2: the encoder is two window-only layers
#: then three groups of six CSA2 layers at ratio 2, and the decoder is five
#: groups of four at ratio 1 -- 20 + 20, the Causal Encoder-Decoder split the
#: model card states.  The DSpark stages are window-only as in both V4 records.
_V41_WINDOW_ONLY_LAYERS = 2
_V41_ENCODER_GROUPS, _V41_ENCODER_GROUP_LAYERS = 3, 6
_V41_DECODER_GROUPS, _V41_DECODER_GROUP_LAYERS = 5, 4
_V41_FLASH_MAIN_RATIOS = (
    (0,) * _V41_WINDOW_ONLY_LAYERS
    + (2,) * (_V41_ENCODER_GROUPS * _V41_ENCODER_GROUP_LAYERS)
    + (1,) * (_V41_DECODER_GROUPS * _V41_DECODER_GROUP_LAYERS)
)

#: V4.1 keeps FP8 E4M3 weights with UE8M0 scales and FP4 experts, but halves the
#: scale block from 128 to 32 in both dimensions, and carries ``expert_dtype``
#: inside the quantization object rather than at the config root.
_V41_QUANTIZATION_CONFIG = MappingProxyType(
    {
        "activation_scheme": "dynamic",
        "expert_dtype": "fp4",
        "quant_method": "fp8",
        "scale_fmt": "ue8m0",
        "weight_block_size": [32, 32],
    }
)
#: The same YaRN interpolation as both V4 releases, under the key name
#: ``rope_type`` that V4 spells ``type``.
_V41_ROPE_SCALING = MappingProxyType(
    {
        "beta_fast": 32,
        "beta_slow": 1,
        "factor": 16,
        "original_max_position_embeddings": 65536,
        "rope_type": "yarn",
    }
)

V41_FLASH = DeepSeekV4Release(
    model_id="deepseek-v4.1-flash",
    repository="deepseek-ai/DeepSeek-V4.1-Flash",
    revision="dba1be0a40aa45a94ad051997016db3960a90277",
    config_sha256="8be45ce0476004a3f529fd896115a4a2e800a129ad2d3ec05b16050f52e21879",
    config_bytes=3_311,
    index_sha256="74b0686a3d2891980d5e303251b075a3bccae2c2ff650747db2620a649b98fa8",
    shard_count=48,
    tensor_count=96_085,
    payload_bytes=510_286_023_000,
    tensor_structure_sha256=(
        "834a3fd1840230036c63b3edf4467d9356784f69bcc4a7fb156ffec536b8ef2c"
    ),
    tensor_structure_evidence="shard_header_inventory",
    inference_config_sha256=(
        "2e84f45cf1dac8c7fcbb200e96667d4b913275690668ed496f24c7747207a809"
    ),
    model_card_sha256="347c9db4e5506acb531cbc3b724407ab88e9af8781679152f0823d7bac16d251",
    tokenizer_sha256="c90dfa01249db1be4245780a052ede752e1361c612ac6d08e2bdada7d599476b",
    tokenizer_config_sha256=(
        "6ac8c8dc065ed118161d02dd532749ae3f52c243deac27872134fae2f50d8547"
    ),
    main_compress_ratios=_V41_FLASH_MAIN_RATIOS,
    dspark_compress_ratios=_DSPARK_RATIOS,
    config_scalars=MappingProxyType(
        {
            "attention_bias": False,
            "attention_dropout": 0.0,
            "candidate_block_size": 8,
            "candidate_source_layer_id": 20,
            "candidate_topk_blocks": 2048,
            "compress_rope_theta": 160000,
            "dspark_block_size": 5,
            "dspark_markov_rank": 256,
            "dspark_n_routed_experts": 128,
            "dspark_noise_token_id": 128799,
            "dspark_num_experts_per_tok": 3,
            "dspark_target_layer_ids": [37, 38, 39],
            "engram_compressed_vocab_size": 99092,
            "engram_head_dim": 256,
            "engram_layer_ids": [1, 14],
            "engram_max_ngram_size": 4,
            "engram_n_heads": 8,
            "engram_num_embeddings": [384_006_168, 384_016_682],
            "engram_pad_token_id": 2,
            "engram_vocab_size": 16_000_000,
            "hc_eps": 1e-6,
            "hc_mult": 4,
            "hc_sinkhorn_iters": 20,
            "head_dim": 512,
            "hidden_act": "silu",
            "hidden_size": 5120,
            "index_head_dim": 128,
            "index_n_heads": 32,
            "index_source_layer_ids": [2, 8, 14, 20, 24, 28, 32, 36],
            "index_topk": 512,
            "initializer_range": 0.02,
            "kv_source_layer_ids": [2, 8, 14, 20],
            "max_position_embeddings": 1_048_576,
            "model_type": "deepseek_v41_text",
            "moe_intermediate_size": 2304,
            "n_routed_experts": 384,
            "n_shared_experts": 1,
            "norm_topk_prob": True,
            "num_attention_heads": 64,
            "num_experts_per_tok": 6,
            "num_hidden_layers": 40,
            "num_key_value_heads": 1,
            # Unlike both V4 records, the root config and the official inference
            # config agree here: three DSpark stages, three trailing ratios.
            "num_nextn_predict_layers": 3,
            "o_groups": 8,
            "o_lora_rank": 1024,
            "q_lora_rank": 1280,
            "qk_rope_head_dim": 64,
            # Not 1e-6: V4.1 lowers the RMS epsilon by fourteen orders of
            # magnitude, which AM-E10's raisable RMS profile exists to carry.
            "rms_norm_eps": 1e-20,
            "rope_theta": 10000,
            "routed_scaling_factor": 1.5,
            "scoring_func": "sqrtsoftplus",
            "sliding_window": 128,
            "swiglu_limit": 10.0,
            "tie_word_embeddings": False,
            "topk_method": "noaux_tc",
            "use_cache": True,
            "vocab_size": 129280,
        }
    ),
    quantization_config=_V41_QUANTIZATION_CONFIG,
    rope_scaling=_V41_ROPE_SCALING,
    checkpoint_lock_id=(
        "3035f90f54bdb46150c7c45a0fa8224c459583d0849c51d2c24fdb055e627a53"
    ),
    tensor_content_sha256=(
        "312df8e2f3f7abf5868da7403cfb0e9c54c3f58736c35fb3d4ade344efcd53e6"
    ),
    checkpoint_source_pending=False,
    supported_compress_ratios=(0, 1, 2),
    config_layout=MappingProxyType(
        {
            "architecture": ("text_config",),
            "compress_ratios": ("text_config",),
            "quantization_config": (),
            "rope_scaling": ("text_config",),
        }
    ),
    config_sections=MappingProxyType(
        {
            "": MappingProxyType(
                {
                    "architectures": ["DeepseekV41ForCausalLM"],
                    "bos_token_id": 0,
                    "dtype": "bfloat16",
                    "eos_token_id": 1,
                    "image_token_id": 129264,
                    "model_type": "deepseek_v41",
                    "pad_token_id": 2,
                }
            ),
            "vision_config": MappingProxyType(
                {
                    "downsample_ratio": 3,
                    "hidden_size": 1024,
                    "intermediate_size": 2816,
                    "max_image_tokens": 1024,
                    "max_wh_ratio": None,
                    "min_pixels": 295936,
                    "model_type": "deepseek_v41_vision",
                    "num_attention_heads": 16,
                    "num_hidden_layers": 32,
                    "patch_size": 14,
                    "rope_theta": 10000,
                }
            ),
        }
    ),
)


#: The reduced V4.1 regression fixture, pinned as its own release.
#:
#: A SECOND PINNED RECORD, not a weakened pin -- the principle
#: compiler/qwen3/adapter.py states for its own reduced contract. Every
#: check the released path makes is made here against this fixture's own
#: digests and its own shape facts, and a config matching neither record is
#: still refused.
#:
#: Three fields are None because the fixture HAS no such artefact: its
#: checkpoint source lists four files -- the runtime config, one shard, the
#: index and parameter_formats -- and not one is a tokenizer or a model
#: card. ``config_sections`` pins the vision tower ABSENT for the same
#: reason, which is a statement the validator checks rather than a silence.
V41_FLASH_REDUCED = DeepSeekV4Release(
    model_id="deepseek-v4.1-flash-reduced-v1",
    repository="opentallas/deepseek-v4.1-flash-reduced-v1",
    revision="d25fe02d2d3140aaab037e9ec32ed4100f1d4e02",
    config_sha256=(
        "32f6712f9714f0a2863bbe4f54873ed7c1ac9d2815cf096ad65c887e0ffa5189"
    ),
    config_bytes=2938,
    index_sha256=(
        "18458ac663386b63726134a9b14c822802b19e7a3847f84da6536d0a02f0ba18"
    ),
    shard_count=1,
    tensor_count=4_264,
    payload_bytes=40_258_841,
    #: Derived by build_official_tensor_specs from this record's own config
    #: and corroborated against the checkpoint index: 4,264 names agreeing
    #: one for one, no shape or dtype differing, and the same payload total.
    tensor_structure_sha256=(
        "c139eb41d40edc68494f7bca62391cf827d5d220fa59b68464e6f34bdfbe2552"
    ),
    tensor_structure_evidence="derived_and_confronted_with_checkpoint_index",
    inference_config_sha256=(
        "3981625600c458d98afefb214cf374b9fcd73982e1da3dcb95025431cae1a90d"
    ),
    #: No model card: this fixture has none.  It DOES have a tokenizer, and
    #: must: ``engram.build_compressed_token_map`` derives the Engram
    #: compressed token map from it, so a consumer resolving a different
    #: tokenizer would build different hash tables over the same weights.  It is
    #: the released BPE restricted to this vehicle's 4,040-token id space, and
    #: ``engram_compressed_vocab_size`` below is what the release's own
    #: derivation returns for it -- 3,402, not the released 99,092.
    model_card_sha256=None,
    tokenizer_sha256=(
        "595deb8a55b069a7412b4778bdbfb0619c936ae9bf84a2744f1c505034c87db3"
    ),
    tokenizer_config_sha256=(
        "6ac8c8dc065ed118161d02dd532749ae3f52c243deac27872134fae2f50d8547"
    ),
    main_compress_ratios=(0, 0, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1),
    dspark_compress_ratios=(0, 0, 0),
    config_scalars=MappingProxyType(
        {
            "attention_bias": False,
            "attention_dropout": 0.0,
            "candidate_block_size": 8,
            "candidate_source_layer_id": 20,
            "candidate_topk_blocks": 64,
            "compress_rope_theta": 160000,
            "dspark_block_size": 5,
            "dspark_markov_rank": 32,
            "dspark_n_routed_experts": 4,
            "dspark_noise_token_id": 128799,
            "dspark_num_experts_per_tok": 3,
            "dspark_target_layer_ids": [37, 38, 39],
            "engram_compressed_vocab_size": 3402,
            "engram_head_dim": 32,
            "engram_layer_ids": [1, 14],
            "engram_max_ngram_size": 4,
            "engram_n_heads": 8,
            "engram_num_embeddings": [189998, 195592],
            "engram_pad_token_id": 2,
            "engram_vocab_size": 7812,
            "hc_eps": 1e-06,
            "hc_mult": 4,
            "hc_sinkhorn_iters": 20,
            "head_dim": 32,
            "hidden_act": "silu",
            "hidden_size": 160,
            "index_head_dim": 32,
            "index_n_heads": 32,
            "index_source_layer_ids": [2, 8, 14, 20, 24, 28, 32, 36],
            "index_topk": 16,
            "initializer_range": 0.02,
            "kv_source_layer_ids": [2, 8, 14, 20],
            "max_position_embeddings": 128,
            "model_type": "deepseek_v41_text",
            "moe_intermediate_size": 64,
            "n_routed_experts": 12,
            "n_shared_experts": 1,
            "norm_topk_prob": True,
            "num_attention_heads": 64,
            "num_experts_per_tok": 6,
            "num_hidden_layers": 40,
            "num_key_value_heads": 1,
            "num_nextn_predict_layers": 3,
            "o_groups": 8,
            "o_lora_rank": 32,
            "q_lora_rank": 32,
            "qk_rope_head_dim": 4,
            "rms_norm_eps": 1e-20,
            "rope_theta": 10000,
            "routed_scaling_factor": 1.5,
            "scoring_func": "sqrtsoftplus",
            "sliding_window": 128,
            "swiglu_limit": 10.0,
            "tie_word_embeddings": False,
            "topk_method": "noaux_tc",
            "use_cache": True,
            "vocab_size": 4040,
        }
    ),
    quantization_config=MappingProxyType(
        {
            "activation_scheme": "dynamic",
            "expert_dtype": "fp4",
            "quant_method": "fp8",
            "scale_fmt": "ue8m0",
            "weight_block_size": [32, 32],
        }
    ),
    rope_scaling=MappingProxyType(
        {
            "beta_fast": 32,
            "beta_slow": 1,
            "factor": 16,
            "original_max_position_embeddings": 65536,
            "rope_type": "yarn",
        }
    ),
    tensor_content_sha256=(
        "09b0308369f0dac4c833d348e9aa8d1a632b8ffde340d01da66b806d1c4a31f3"
    ),
    checkpoint_lock_id=(
        "2c63f413e81951ab69f9e5ed3520d695af7fcd6a1e6cba09814788d40543f429"
    ),
    supported_compress_ratios=(0, 1, 2),
    config_layout=MappingProxyType(
        {
            "architecture": ("text_config",),
            "rope_scaling": ("text_config",),
            "compress_ratios": ("text_config",),
            "quantization_config": (),
        }
    ),
    config_sections=MappingProxyType(
        {
            "": MappingProxyType(
                {
                    "architectures": ["DeepseekV41ForCausalLM"],
                    "bos_token_id": 0,
                    "dtype": "bfloat16",
                    "eos_token_id": 1,
                    "image_token_id": 129264,
                    "model_type": "deepseek_v41",
                    "pad_token_id": 2,
                }
            ),
            #: PINNED ABSENT: the workload is text only and the reduction
            #: excludes the tower, so a config that carries one is refused.
            "vision_config": None,
        }
    ),
)


#: The reduced V4.1 fixture again, with the routed experts' block scale set so
#: their projection stays inside the architecture's own SwiGLU limit.
#:
#: A THIRD PINNED RECORD, for the same reason the second one exists: a second
#: vehicle is a second pin and not a weakened one.  Everything structural is
#: v1's -- the same 4,264 tensors, the same 40,258,841 payload bytes, the same
#: config, tokenizer and inference config digests, byte for byte, because the
#: reduction changed MAGNITUDES and not architecture.  Only the two digests that
#: cover tensor CONTENT move.
#:
#: Why it exists: v1 writes 0x7F -- a scale of exactly 2**0 -- into every routed
#: expert's E8M0 block scale, leaving uniform-random FP4 nibbles spanning the
#: whole E2M1 range to 6.0.  An independent dequantisation measures the resulting
#: 160-wide expert projection at absmax 119.3 against a ``swiglu_limit`` of 10.0,
#: so 99.8% to 100% of routed gate and up values saturate the clamp and the expert
#: output becomes a function of its operands' SIGNS -- through which no two
#: implementations can be compared.  ``results/abi3/
#: deepseek_v41_reduced_fixture_saturates.json`` records the measurement; this
#: record's fixture sets the exponent to -5, which puts the projection near 3.7.
V41_FLASH_REDUCED_V2 = replace(
    V41_FLASH_REDUCED,
    model_id="deepseek-v4.1-flash-reduced-v2",
    #: Its own repository and revision, from the record the builder generated.
    #: The revision of a constructed checkpoint is its own content -- the digest
    #: of the configuration and the seed that produced every byte -- so it is not
    #: a choice either.
    repository="opentallas/deepseek-v4.1-flash-reduced-v2",
    revision="d25fe02d2d3140aaab037e9ec32ed4100f1d4e02",
    checkpoint_lock_id=(
        "2ea2d142370015c5c3aaa38bcd33f79ca3db3cd4aeb463c54d771c704bfc8548"
    ),
    tensor_content_sha256=(
        "fb6ebe9933aa24a394de2912604f0ebca9d597b232746910307cc2677347bb96"
    ),
)


RELEASES: Mapping[str, DeepSeekV4Release] = MappingProxyType(
    {
        release.model_id: release
        for release in (
            FLASH,
            PRO,
            V41_FLASH,
            V41_FLASH_REDUCED,
            V41_FLASH_REDUCED_V2,
        )
    }
)


def resolve_release(model: str | DeepSeekV4Release) -> DeepSeekV4Release:
    """Return the record for a model id, or pass a record straight through."""

    if isinstance(model, DeepSeekV4Release):
        return model
    try:
        return RELEASES[model]
    except KeyError:
        raise DeepSeekV4ReleaseError(
            f"unknown DeepSeek-V4 release {model!r}; this front end carries "
            + ", ".join(sorted(RELEASES))
        ) from None


__all__ = [
    "CHECKPOINT_LOCK_ROOT",
    "CONFIG_LAYOUT_KEYS",
    "FLASH",
    "HUGGINGFACE_HUB",
    "MODELS_DIR",
    "PRO",
    "RELEASES",
    "V41_FLASH",
    "V41_FLASH_REDUCED",
    "V41_FLASH_REDUCED_V2",
    "DeepSeekV4Release",
    "DeepSeekV4ReleaseError",
    "resolve_release",
]
