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

from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

#: Where the local Hugging Face cache keeps a snapshot, and where
#: ``tools/build_checkpoint_lock.py`` writes a lock.  Both are host paths, not
#: release facts, so they are composed from the identity below rather than
#: written out per release.
HUGGINGFACE_HUB = Path("/home/ubuntu/.cache/huggingface/hub")
CHECKPOINT_LOCK_ROOT = Path("/home/ubuntu/.cache/opentallas")
MODELS_DIR = Path(__file__).resolve().parents[1] / "models"


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
    model_card_sha256: str
    tokenizer_sha256: str
    tokenizer_config_sha256: str
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
        if any(ratio not in {0, 4, 128} for ratio in unsupported):
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
    checkpoint_source_pending=True,
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


RELEASES: Mapping[str, DeepSeekV4Release] = MappingProxyType(
    {release.model_id: release for release in (FLASH, PRO)}
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
    "FLASH",
    "HUGGINGFACE_HUB",
    "MODELS_DIR",
    "PRO",
    "RELEASES",
    "DeepSeekV4Release",
    "DeepSeekV4ReleaseError",
    "resolve_release",
]
