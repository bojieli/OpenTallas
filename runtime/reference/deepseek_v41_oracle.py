"""DeepSeek-V4.1-Flash layer-streaming reference engine.

The analogue of :class:`runtime.reference.deepseek_v4_oracle.StreamingDeepSeekV4`
for V4.1, and deliberately a thin one: pointing the V4 engine at the V4.1 snapshot
already gets as far as CONSTRUCTING the 96,085-tensor model on ``meta``, so almost
all of the streaming machinery -- the weight store, the meta-parameter slots, the
materialise/release hooks around ``Block.forward`` and ``Expert.forward``, the
head-split sparse attention, the buffer allocation for compressors and indexers --
is inherited rather than rewritten.  What this module adds is exactly the three
things V4.1 needs and V4 does not.

1. **Its own vendor sources.**  V4.1 ships ``inference/engram.py`` and
   ``encoding/encoding.py`` where V4 ships ``encoding/encoding_dsv4.py``, so the
   digest table and the import differ.

2. **Its own cached-helper list.**  ``_materialise_buffers`` clears the vendor's
   ``lru_cache`` helpers by name before rebuilding buffers on the device.  V4 has
   ``get_compress_topk_idxs``; V4.1 has ``get_dspark_topk_idxs``.

3. **An Engram residency policy.**  This is the one that is real work.  The two
   Engram tables are **202.76 GB** and ``ParallelEngramEmbedding.forward`` runs
   ``F.embedding`` over a whole table, which cannot be materialised on a machine
   with 188 GB of host RAM.  But ``F.embedding`` reads only the rows it indexes,
   and at decode the indices are ``[batch, positions, n_hash_cols]`` -- tens of
   rows, not hundreds of millions.  So the lookup is served by a ROW GATHER
   against the memory-mapped shards: read the unique rows the call actually asks
   for, dequantise them exactly as the vendor does, and never give the table a
   resident form at all.

THE EXPERT NUMERIC PATH IS FP8, AND THAT IS THE PRECEDENT, NOT A SHORTCUT.  The
shipped V4-Flash oracle records ``expert_numeric_path: fp8`` -- the vendor's own
documented recast -- because its FP4 GEMM disagrees with a PyTorch dequantisation
of the same checkpoint tensor on this GPU.  V4.1's ``kernel.fp8_gemm`` asserts a
different expert-scale shape than V4's, so the V4 probe cannot even build its test
operand; rather than report an unverified FP4 path, this engine takes the recast
and says so in every record.

WHAT THIS IS NOT.  It is an external comparator over the vendor's own pinned code.
It never produces accelerator tokens and never supplies an activation to the
accelerator (ADR-003 section 18).
"""

from __future__ import annotations

import hashlib
import importlib
import json
import sys
from pathlib import Path
from typing import Any

from runtime.reference.deepseek_v4_oracle import (  # noqa: F401
    OracleConfig,
    OracleError,
    StreamingDeepSeekV4,
    WeightStore,
    cast_experts_to_fp8,
    make_head_split_sparse_attn,
    make_rotate_activation,
    try_import_fast_hadamard,
    verify_head_split_identity,
)

#: The vendor files this engine imports.  Hashed at run time and refused on drift,
#: exactly as the V4 engine does for its own set.
V41_VENDOR_SOURCES: tuple[str, ...] = (
    "inference/model.py",
    "inference/kernel.py",
    "inference/convert.py",
    "inference/engram.py",
    "encoding/encoding.py",
    "inference/config.json",
)

#: The vendor ``lru_cache`` helpers that hold meta-device tensors after the
#: skeleton is built on ``meta`` and must be cleared before real buffers are
#: allocated.  ``get_dspark_topk_idxs`` is where V4 has ``get_compress_topk_idxs``.
V41_CACHED_HELPERS: tuple[str, ...] = (
    "precompute_freqs_cis",
    "get_window_topk_idxs",
    "get_dspark_topk_idxs",
)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_v41_vendor_sources(snapshot: Path) -> dict[str, str]:
    """Hash the V4.1 vendor files this engine imports, refusing any absence."""
    observed: dict[str, str] = {}
    for relative in V41_VENDOR_SOURCES:
        path = snapshot / relative
        if not path.exists():
            raise OracleError(f"vendor source missing: {path}")
        observed[relative] = _sha256_file(path)
    return observed


def import_v41_vendor(snapshot: Path) -> tuple[Any, Any, Any, Any]:
    """Import V4.1's ``model``, ``kernel``, ``convert`` and ``encoding`` modules."""
    for entry in (str(snapshot / "inference"), str(snapshot / "encoding")):
        if entry not in sys.path:
            sys.path.insert(0, entry)
    return (
        importlib.import_module("model"),
        importlib.import_module("kernel"),
        importlib.import_module("convert"),
        importlib.import_module("encoding"),
    )


class _TokenizerForNgramHash:
    """What ``build_compressed_token_map`` needs, and nothing more.

    The vendor's map builder touches exactly two things on a tokenizer:
    ``.backend_tokenizer`` and ``len()``.  The committed verified loader
    (``compiler.frontend.deepseek_v41_tokenizer``) supplies the backend, so this
    bridges the attribute name without reimplementing any tokenizer behaviour.
    """

    def __init__(self, backend: Any) -> None:
        self.backend_tokenizer = backend

    def __len__(self) -> int:
        return self.backend_tokenizer.get_vocab_size(with_added_tokens=True)


class StreamingDeepSeekV41(StreamingDeepSeekV4):
    """The vendor V4.1 ``Transformer`` driven by an on-demand weight loader."""

    def __init__(self, config: OracleConfig, *, tokenizer_backend: Any) -> None:
        import torch

        self.torch = torch
        self.config = config
        self.snapshot = config.snapshot
        self.device = torch.device(config.device)

        self.vendor_digests = verify_v41_vendor_sources(self.snapshot)
        (
            self.model_mod,
            self.kernel_mod,
            self.convert_mod,
            self.encoding_mod,
        ) = import_v41_vendor(self.snapshot)

        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        torch.set_default_dtype(torch.bfloat16)

        self.vendor_sparse_attn = self.kernel_mod.sparse_attn
        self.head_split_evidence = verify_head_split_identity(self.vendor_sparse_attn)
        if not self.head_split_evidence["bitwise_identical"]:
            raise OracleError(
                "head-split sparse attention is not bitwise identical on this "
                "machine; refusing to produce a reference result"
            )
        self.model_mod.sparse_attn = make_head_split_sparse_attn(
            self.vendor_sparse_attn
        )

        self.fast_hadamard = try_import_fast_hadamard()
        rotate, self.hadamard_source = make_rotate_activation(self.fast_hadamard)
        self.model_mod.rotate_activation = rotate

        self.store = WeightStore(
            self.snapshot,
            device=config.device,
            host_cache_dense=config.host_cache_dense,
            pin_host_cache=config.pin_host_cache,
        )

        # See the module docstring: the FP8 recast is the shipped V4 oracle's own
        # expert path and V4.1's fp8_gemm asserts a scale shape the V4 FP4 probe
        # cannot build, so there is no verified FP4 verdict to report here.
        self.expert_dtype = "fp8"
        self.fp4_gemm_evidence = {
            "fp4_gemm_agrees": None,
            "fp8_gemm_agrees": None,
            "note": (
                "not probed: V4.1's kernel.fp8_gemm asserts a different expert "
                "scale shape than V4's, so the V4 probe cannot build its operand. "
                "The expert path is the vendor's documented FP8 recast, which is "
                "also what the shipped V4-Flash oracle records."
            ),
        }
        # V4.1's quantization_config declares weight_block_size [32, 32] where V4
        # declares 128, and the wo_a scale fold is sized from it.
        released = json.loads((self.snapshot / "config.json").read_text())
        quant = released.get("quantization_config") or {}
        block = quant.get("weight_block_size")
        if not block:
            raise OracleError(
                "the released config declares no quantization_config."
                "weight_block_size; refusing to assume one"
            )
        self.store.fp8_block_size = int(block[0])

        self.store.expert_recast = lambda packed, scale: cast_experts_to_fp8(
            self.convert_mod, packed, scale, self.device
        )

        self._engram_dense_cache: dict[int, list[str]] = {}
        self._tokenizer = _TokenizerForNgramHash(tokenizer_backend)
        self.args = self._build_args()
        self._build_skeleton()
        self._install_streaming_hooks()
        self._install_engram_residency()

        self.peak_device_bytes = 0
        self.generation_peak_device_bytes = 0
        self.layer_seconds = 0.0
        self.engram_rows_read = 0
        self.engram_lookups = 0

    # -- construction -----------------------------------------------------
    def _build_skeleton(self) -> None:
        """As the parent, but V4.1's ``Transformer`` takes a tokenizer.

        ``Transformer.__init__`` builds an ``NgramHashState``, which needs a
        tokenizer to derive the compressed token map from; V4 has no Engram and
        so no such argument.
        """
        torch = self.torch
        model_mod = self.model_mod
        vendor_transformer = getattr(
            model_mod, "_opentallas_vendor_transformer", model_mod.Transformer
        )
        model_mod._opentallas_vendor_transformer = vendor_transformer
        tokenizer = self._tokenizer

        class _TransformerWithTokenizer(vendor_transformer):  # type: ignore[misc,valid-type]
            def __init__(self, args, tok=None):  # noqa: ANN001
                super().__init__(args, tokenizer if tok is None else tok)

        model_mod.Transformer = _TransformerWithTokenizer
        try:
            super()._build_skeleton()
        finally:
            model_mod.Transformer = vendor_transformer

    def _materialise_buffers(self) -> None:
        """Re-create every buffer on the device, sized from the meta tensor itself.

        The parent transcribes V4's buffer set by name and shape.  That does not
        port: V4.1's Attention carries ``window_kv_cache`` and
        ``compress_kv_cache`` where V4 carries one ``kv_cache``, its Compressor
        registers ``kv_state``/``score_state`` at a different shape and only for
        ratio > 1, and its Indexer registers ``k_cache`` and no ``head_dim``.
        Transcribing that is four chances to get a shape wrong.

        So nothing is transcribed.  The skeleton is built on ``meta``, which means
        every buffer already exists with its real shape and dtype -- the vendor's
        own ``__init__`` computed them -- and all that is missing is storage.  This
        walks them and allocates each one on the device at the shape it already
        has.  Three fills cover every case:

        * ``freqs_cis`` is a RoPE table and must be RECOMPUTED, not zeroed.  Its
          theta depends on whether the owning layer compresses, which is the one
          piece of V4.1 semantics this method has to know.
        * ``score_state`` is the compressor's gate tail and the vendor fills it
          with ``-inf``, because a zero would be a valid score.
        * everything else is zeros, which is what the vendor's own registrations
          use.

        A buffer the vendor did not register does not appear, so a release that
        adds one is carried automatically instead of silently skipped.
        """
        torch = self.torch
        args = self.args
        model_mod = self.model_mod

        for helper in V41_CACHED_HELPERS:
            target = getattr(model_mod, helper, None)
            if target is not None and hasattr(target, "cache_clear"):
                target.cache_clear()

        rope_tables: dict[tuple, Any] = {}

        def rope_for(module) -> Any:  # noqa: ANN001
            """The RoPE table this module's owner would have built."""
            compress_ratio = getattr(module, "compress_ratio", 0)
            if compress_ratio:
                original_seq_len = args.original_seq_len
                rope_theta = args.compress_rope_theta
            else:
                original_seq_len, rope_theta = 0, args.rope_theta
            key = (module.rope_head_dim, original_seq_len, rope_theta)
            table = rope_tables.get(key)
            if table is None:
                table = model_mod.precompute_freqs_cis(
                    module.rope_head_dim,
                    args.max_seq_len,
                    original_seq_len,
                    rope_theta,
                    args.rope_factor,
                    args.beta_fast,
                    args.beta_slow,
                ).to(self.device)
                rope_tables[key] = table
            return table

        allocated = 0
        allocated_bytes = 0
        for module in self.model.modules():
            for name, buffer in list(module._buffers.items()):
                if buffer is None or buffer.device.type != "meta":
                    continue
                if name == "freqs_cis":
                    replacement = rope_for(module)
                elif name == "score_state":
                    replacement = torch.full(
                        tuple(buffer.shape),
                        float("-inf"),
                        dtype=buffer.dtype,
                        device=self.device,
                    )
                else:
                    replacement = torch.zeros(
                        tuple(buffer.shape), dtype=buffer.dtype, device=self.device
                    )
                module._buffers[name] = replacement
                allocated += 1
                allocated_bytes += replacement.numel() * replacement.element_size()
        self.buffers_allocated = allocated
        self.buffer_bytes = allocated_bytes
        self._log(
            f"{allocated} buffers allocated on the device "
            f"({allocated_bytes / 2**20:.1f} MiB)"
        )

    # -- Engram residency -------------------------------------------------
    def _install_engram_residency(self) -> None:
        """Serve ``ParallelEngramEmbedding`` from a row gather, not a resident table.

        The two tables are 202.76 GB.  ``F.embedding`` reads only the rows it
        indexes and the indices are ``[batch, positions, n_hash_cols]``, so the
        rows actually needed per call are tens, not hundreds of millions.  The
        vendor body is not used: it would require the whole table to be resident.
        Everything it computes is reproduced here on the gathered rows, in the
        same order and the same dtypes.
        """
        model_mod = self.model_mod
        engine = self
        if not hasattr(model_mod, "_opentallas_vendor_engram_embed_forward"):
            model_mod._opentallas_vendor_engram_embed_forward = (
                model_mod.ParallelEngramEmbedding.forward
            )

        def gathering_forward(self, indices):  # noqa: ANN001
            return engine._engram_lookup(self, indices)

        model_mod.ParallelEngramEmbedding.forward = gathering_forward

        # ``Transformer.forward`` calls ``layer.engram(...)`` BEFORE ``layer(...)``,
        # so the Engram runs outside ``Block.forward`` and the block's
        # materialisation window has not opened yet.  Its own projections --
        # ``wkv``, ``q_weight``, ``k_weight``, ``norm`` -- therefore need their own
        # residency, or they are still on meta when the vendor calls them.  The
        # table parameters are excluded: they are served by the row gather and
        # one of them alone is larger than host memory.
        if not hasattr(model_mod, "_opentallas_vendor_engram_forward"):
            model_mod._opentallas_vendor_engram_forward = model_mod.Engram.forward
        vendor_engram_forward = model_mod._opentallas_vendor_engram_forward

        def streaming_engram_forward(self, *args, **kwargs):  # noqa: ANN001
            names = engine._engram_dense_names(self)
            engine._materialise_names(names, cache=engine.config.host_cache_dense)
            try:
                return vendor_engram_forward(self, *args, **kwargs)
            finally:
                engine._release_names(names)
                engine._note_peak()

        model_mod.Engram.forward = streaming_engram_forward

    def _engram_dense_names(self, engram) -> list[str]:  # noqa: ANN001
        """Every Engram parameter except the hash table itself."""
        key = id(engram)
        names = self._engram_dense_cache.get(key)
        if names is None:
            names = [
                name
                for name in self._params_of(engram)
                if ".embed." not in name
            ]
            self._engram_dense_cache[key] = names
        return names

    #: A single Engram table is ~49 GB.  A gather asking for more rows than this
    #: is not a lookup, it is a bug about to become an out-of-memory error, so it
    #: is refused with the count rather than attempted.
    MAX_ENGRAM_ROWS_PER_LOOKUP = 4096

    def _gather_rows(self, name: str, rows: list[int]):
        """Read exactly ``rows`` of a checkpoint tensor, nothing else.

        Two things here are load-bearing.  The read is pinned to the HOST: the
        parent's ``forward`` sets the default device to CUDA for the whole pass,
        and a safetensors slice taken under that default lands on the GPU -- which
        for a 49 GB table is an immediate out-of-memory, as it was on the first
        decode step before this was pinned.  And the row count is bounded: a
        lookup wants tens of rows, so a request for millions is a defect and is
        refused with its own size instead of being handed to the allocator.
        """
        torch = self.torch
        if not rows:
            raise OracleError(f"{name}: empty Engram row gather")
        if len(rows) > self.MAX_ENGRAM_ROWS_PER_LOOKUP:
            raise OracleError(
                f"{name}: Engram gather asked for {len(rows):,} rows, above the "
                f"{self.MAX_ENGRAM_ROWS_PER_LOOKUP:,} bound. A lookup wants tens; "
                "this is a defect in the index path, not a large request"
            )
        filename = self.store.weight_map.get(name)
        if filename is None:
            raise OracleError(f"checkpoint has no tensor {name!r}")
        handle = self.store._handle(filename)
        window = handle.get_slice(name)
        prior = torch.get_default_device()
        torch.set_default_device("cpu")
        try:
            gathered = [window[row : row + 1] for row in rows]
        finally:
            torch.set_default_device(prior)
        self.engram_rows_read += len(rows)
        return torch.cat(gathered, dim=0)

    def _engram_lookup(self, module, indices):  # noqa: ANN001
        """The vendor lookup, computed over gathered rows.

        Mirrors ``ParallelEngramEmbedding.forward``: mask the out-of-shard ids,
        localise them, read the rows, dequantise with the per-row block scales in
        float32, narrow to BF16, and zero the masked positions.  ``world_size``
        is 1 here, so the vendor's ``all_reduce`` is a no-op and is not performed.
        """
        torch = self.torch
        self.engram_lookups += 1
        prefix = self._prefix_of[id(module)]
        weight_name = f"{prefix}.weight"
        scale_name = f"{prefix}.scale"

        mask = (indices < module.vocab_start_idx) | (indices >= module.vocab_end_idx)
        local = (indices - module.vocab_start_idx).masked_fill(mask, 0)
        flat = local.reshape(-1)
        unique, inverse = torch.unique(flat, return_inverse=True)
        rows = [int(r) for r in unique.tolist()]

        weight = self._gather_rows(weight_name, rows).to(self.device)
        scale = self._gather_rows(scale_name, rows).to(self.device)

        values = weight[inverse].float().unflatten(-1, (-1, module.block_size))
        values = values * scale[inverse].float().unsqueeze(-1)
        values = values.flatten(-2).to(torch.bfloat16)
        values = values.reshape(*indices.shape, module.dim)
        return values.masked_fill(mask.unsqueeze(-1), 0)

    def load_endpoints(self) -> dict[str, Any]:
        """Place the embedding, the final norm and the LM head.

        The parent materialises ``norm.weight`` plus ``hc_head_fn``,
        ``hc_head_base`` and ``hc_head_scale`` by name.  **V4.1 has no head-side
        hyper-connection parameters**: its ``Block.forward`` returns the final
        ``pre_mix`` and ``ParallelHead`` takes ``hc_eps`` as a constructor
        argument rather than carrying projection weights, so those three names do
        not exist and the parent raises ``KeyError`` on the first of them.

        The set is therefore DISCOVERED from the skeleton rather than
        transcribed: every top-level parameter that is not the embedding or the
        head is materialised on the device.  A release that adds one is carried;
        a release that drops one does not raise.

        Everything after that is the parent's policy, restated because it is
        short: the embedding is a pure gather so its rows stay in host memory,
        and the LM head is one matmul per step so it stays on the host unless
        ``head_on_device`` is set and there is room.
        """
        torch = self.torch
        report: dict[str, Any] = {}

        endpoints = {"embed.weight", "head.weight"}
        top_level = [
            name
            for name in self._slots
            if "." not in name.replace(".weight", "") or name == "norm.weight"
        ]
        resident = sorted(
            name
            for name in self._slots
            if name not in endpoints
            and not name.startswith(("layers.", "vision.", "dspark"))
        )
        self._materialise_names(resident, cache=False)
        report["resident_top_level"] = resident

        embed_module, embed_local, embed_meta = self._slots["embed.weight"]
        embed_module._parameters[embed_local] = self.store.host_tensor(
            "embed.weight", embed_meta
        )
        report["embed_device"] = "cpu"
        engine = self

        def embed_forward(self, x):  # noqa: ANN001
            weight = self.weight
            out = torch.nn.functional.embedding(x.to(weight.device), weight)
            return out.to(engine.device)

        self.model_mod.ParallelEmbedding.forward = embed_forward

        head_module, head_local, head_meta = self._slots["head.weight"]
        head_host = self.store.host_tensor("head.weight", head_meta)
        free_bytes, _ = torch.cuda.mem_get_info()
        need = head_host.numel() * head_host.element_size()
        if self.config.head_on_device and free_bytes > need * 2:
            head_module._parameters[head_local] = head_host.to(self.device)
            report["head_device"] = "cuda"
        else:
            head_module._parameters[head_local] = head_host
            report["head_device"] = "cpu"
        report["head_dtype"] = str(head_meta.dtype).replace("torch.", "")
        report["head_bytes"] = int(need)

        def head_forward(self, x, full_logits=False):  # noqa: ANN001
            if not full_logits:
                x = x[:, -1]
            weight = self.weight
            return torch.nn.functional.linear(x.float().to(weight.device), weight)

        self.model_mod.ParallelHead.forward = head_forward
        return report

    # -- the Engram tables are never resident -----------------------------
    def _block_dense_names(self, block) -> list[str]:  # noqa: ANN001
        """The parent's list, minus the Engram table parameters.

        The tables are served by :meth:`_engram_lookup` and must never be
        materialised: one of them alone is larger than host memory.
        """
        names = super()._block_dense_names(block)
        return [n for n in names if ".engram.embed." not in n]
