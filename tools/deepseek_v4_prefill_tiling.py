#!/usr/bin/env python3
"""Sequence-tiled prefill and KV instrumentation for the DeepSeek-V4 oracle.

Why this exists
---------------
The vendor's ``inference/model.py`` prefills a prompt in one call, and three of
its intermediates are quadratic in the prompt length:

* ``Indexer.forward`` materialises ``index_score`` with shape
  ``[b, s, index_n_heads, s // 4]``.  At s = 200,000 that is 6.4e11 bfloat16
  elements - **1.28 TB** - for one of the twenty-one sparse layers.
* ``Block.hc_post`` materialises ``comb.unsqueeze(-1) * residual.unsqueeze(-2)``
  with shape ``[b, s, hc, hc, d]`` in float32: **52.5 GB** at s = 200,000.
* ``Block.hc_pre`` materialises ``x.flatten(2).float()``: **13.1 GB**.

No GPU in this class runs that, which is why the 32k, 128k and 200k rungs of the
context ladder failed with CUDA OOM.  The failure is a property of the reference
implementation's prefill, not of the model: every one of those intermediates is
a *per-query* quantity, so it can be produced a slice of the sequence at a time
and the arithmetic each output element sees is unchanged.

That is all this module does.  It replaces four vendor ``forward`` bodies with
sequence-tiled transcriptions of the same expressions - same operators, same
order of reduction over the axes that are actually reduced, same dtypes - and
never changes what is computed, only how much of it is resident at once.  The
tiling is proved on this machine by re-running the two rungs that already
executed untiled and requiring the token ids to be identical.

Nothing here changes the numeric policy, the weight streaming, the head split
or the device map: those remain the oracle's.

Also here: the KV traffic counters.  They are attached to the two places where
this model reads context - the sparse-attention kernel's ``topk_idxs``, which
names exactly the (layer, position) pairs a query visits, and the indexer's
scan over its compressed cache - so the ladder can be compared against
``src/opentallas/workload.py::kv_traffic`` at every rung.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

# --------------------------------------------------------------------------
# configuration
# --------------------------------------------------------------------------


@dataclass
class TilingConfig:
    """Byte budgets, not tile counts.

    A fixed tile length would be wrong at both ends of the ladder: the tensors
    being tiled grow with the *context*, not with the tile, so the tile that
    keeps ``index_score`` under a gigabyte at 8k is a hundred times too large at
    200k.  Each budget below is converted to a tile length at run time from the
    sequence length actually being prefilled.
    """

    #: Sequence positions per attention / hyper-connection tile.
    seq_tile: int = 2048
    #: Ceiling for the indexer's ``[C, heads, s/ratio]`` score block.
    index_score_bytes: int = 1 << 30
    #: Ceiling for ``hc_post``'s ``[C, hc, hc, d]`` float32 block.
    hc_bytes: int = 768 << 20
    #: Positions per compressor tile (its blocks are ``[C, 2*ratio, d]`` fp32).
    compressor_positions: int = 1 << 14
    #: Rows per expert tile.
    expert_rows: int = 1 << 15
    #: Sequences at or below this length run the vendor bodies untouched.
    floor: int = 4096
    #: Hold the hyper-connection residual in pinned host memory between tiles.
    host_residual: bool = False

    def hc_tile(self, hc_mult: int, dim: int) -> int:
        per = hc_mult * hc_mult * dim * 4
        return max(64, min(self.seq_tile, self.hc_bytes // max(per, 1)))

    #: When set, the indexer sub-tile is this many rows regardless of context.
    #: A fixed length keeps every rung of a ladder on the same tile geometry,
    #: which a byte budget alone would not: the budget yields 1500 rows at 32k
    #: and 240 at 200k, and a GEMM's result depends on its row count.
    index_tile_rows: int = 0

    def index_tile(self, heads: int, entries: int) -> int:
        if self.index_tile_rows:
            return self.index_tile_rows
        per = heads * max(entries, 1) * 2
        return max(32, min(self.seq_tile, self.index_score_bytes // max(per, 1)))

    def index_score_block_bytes(self, heads: int, entries: int) -> int:
        return self.index_tile(heads, entries) * heads * max(entries, 1) * 2


# --------------------------------------------------------------------------
# KV traffic counters
# --------------------------------------------------------------------------


@dataclass
class PhaseCounters:
    """One phase (``prefill`` or one decode step) of one generation."""

    #: (layer, position) pairs the sparse-attention kernel actually visited.
    main_pairs: int = 0
    #: Bytes of the main KV cache those pairs are.
    main_bytes: int = 0
    #: (layer, position) pairs the indexer scored to make its selection.
    index_pairs: int = 0
    index_bytes: int = 0
    #: Per-layer detail, keyed by layer id.
    per_layer: dict[int, dict[str, int]] = field(default_factory=dict)
    #: Selected compressed positions per query, per sparse layer.
    selected_per_query: dict[int, int] = field(default_factory=dict)
    #: Compressed positions available to select from, per sparse layer.
    candidates_per_query: dict[int, int] = field(default_factory=dict)
    queries: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "attention_context_positions": self.main_pairs,
            "attention_kv_bytes_read": self.main_bytes,
            "index_context_positions": self.index_pairs,
            "index_kv_bytes_read": self.index_bytes,
            "total_kv_bytes_read": self.main_bytes + self.index_bytes,
            "queries": self.queries,
            "per_layer": {str(k): v for k, v in sorted(self.per_layer.items())},
            "selected_per_query": {
                str(k): v for k, v in sorted(self.selected_per_query.items())
            },
            "candidates_per_query": {
                str(k): v for k, v in sorted(self.candidates_per_query.items())
            },
        }


class KVCounters:
    """Counts what attention read, from the tensors attention was handed.

    ``topk_idxs`` is the whole story for this model: the kernel reads exactly
    the cache rows it names and skips the rest, and a ``-1`` entry is a masked
    slot that is read by nobody.  Counting its non-negative entries therefore
    counts (layer, position) pairs directly rather than inferring them.
    """

    def __init__(self) -> None:
        self.enabled = False
        self.phases: list[PhaseCounters] = []
        self.current: PhaseCounters | None = None
        self.layer_id: int | None = None
        self._detail_limit = 64

    def start_phase(self) -> PhaseCounters:
        self.current = PhaseCounters()
        self.phases.append(self.current)
        return self.current

    def _layer(self, kind: str) -> dict[str, int]:
        assert self.current is not None
        entry = self.current.per_layer.setdefault(
            int(self.layer_id or 0),
            {
                "kind": kind,
                "main_pairs": 0,
                "main_bytes": 0,
                "index_pairs": 0,
                "index_bytes": 0,
            },
        )
        entry["kind"] = kind
        return entry

    def note_attention(self, topk_idxs, kv, kind: str) -> None:  # noqa: ANN001
        if not self.enabled or self.current is None:
            return
        pairs = int((topk_idxs >= 0).sum().item())
        entry_bytes = int(kv.size(-1)) * int(kv.element_size())
        self.current.main_pairs += pairs
        self.current.main_bytes += pairs * entry_bytes
        self.current.queries = max(self.current.queries, int(topk_idxs.size(1)))
        layer = self._layer(kind)
        layer["main_pairs"] += pairs
        layer["main_bytes"] += pairs * entry_bytes

    def note_index(self, queries: int, entries: int, cache, selected: int) -> None:  # noqa: ANN001
        if not self.enabled or self.current is None:
            return
        pairs = int(queries) * int(entries)
        entry_bytes = int(cache.size(-1)) * int(cache.element_size())
        self.current.index_pairs += pairs
        self.current.index_bytes += pairs * entry_bytes
        layer = self._layer("csa")
        layer["index_pairs"] += pairs
        layer["index_bytes"] += pairs * entry_bytes
        lid = int(self.layer_id or 0)
        self.current.selected_per_query[lid] = int(selected)
        self.current.candidates_per_query[lid] = int(entries)


COUNTERS = KVCounters()


# --------------------------------------------------------------------------
# index helpers -- transcriptions of the vendor's own topk_idxs builders
# --------------------------------------------------------------------------


def _window_topk_idxs(torch, win: int, seqlen: int, lo: int, hi: int, device):  # noqa: ANN001
    """``get_window_topk_idxs`` for the query rows ``[lo, hi)`` of a prefill.

    The vendor builds the whole ``[seqlen, win]`` matrix at once; each row
    depends only on its own absolute position, so a row slice of it is the same
    matrix restricted to those rows.
    """
    width = min(seqlen, win)
    base = torch.arange(lo, hi, device=device).unsqueeze(1)
    matrix = (base - win + 1).clamp(0) + torch.arange(width, device=device)
    matrix = torch.where(matrix > base, -1, matrix)
    return matrix.int().unsqueeze(0)


def _compress_topk_idxs(torch, ratio, seqlen, lo, hi, offset, device):  # noqa: ANN001
    """``get_compress_topk_idxs`` for the query rows ``[lo, hi)`` of a prefill."""
    columns = seqlen // ratio
    matrix = torch.arange(columns, device=device).expand(hi - lo, columns)
    bound = (torch.arange(lo + 1, hi + 1, device=device) // ratio).unsqueeze(1)
    matrix = torch.where(matrix >= bound, -1, matrix + offset)
    return matrix.int().unsqueeze(0)


# --------------------------------------------------------------------------
# the tiled bodies
# --------------------------------------------------------------------------


def build_patches(model_mod: Any, cfg: TilingConfig) -> dict[str, Any]:
    """Return the tiled ``forward`` bodies, closed over the vendor module."""

    import torch
    import torch.nn.functional as F

    vendor = {
        "Compressor": model_mod.Compressor.forward,
        "Indexer": model_mod.Indexer.forward,
        "Attention": model_mod.Attention.forward,
        "Block": model_mod.Block.forward,
        "MoE": model_mod.MoE.forward,
        "Expert": model_mod.Expert.forward,
        "Transformer": model_mod.Transformer.forward,
    }

    # ---------------- Compressor ----------------
    def compressor_forward(self, x, start_pos: int):  # noqa: ANN001
        seqlen = x.size(1)
        if start_pos != 0 or seqlen <= cfg.floor:
            return vendor["Compressor"](self, x, start_pos)

        bsz = x.size(0)
        ratio, overlap = self.compress_ratio, self.overlap
        d, rd = self.head_dim, self.rope_head_dim
        dtype = x.dtype
        device = x.device
        if seqlen < ratio:  # nothing to compress; defer to the vendor body
            return vendor["Compressor"](self, x, start_pos)

        remainder = seqlen % ratio
        cutoff = seqlen - remainder
        groups = cutoff // ratio
        offset = ratio if overlap else 0

        # The two projections are the widest float32 tensors in the model:
        # ``x.float()`` alone is 3.3 GB at 200k, and it has to be live while
        # both projections of it are produced.  They are evaluated in
        # ``compressor_positions``-row pieces into one preallocated output.
        # A sequence that fits in one piece therefore still sees the vendor's
        # own GEMM row count, which is what makes the equivalence check at 8k
        # exact; above that the row count is the tile, and constant across
        # rungs, which is the property a ladder needs.
        width = self.ape.size(1)
        kv_all = torch.empty(
            bsz, seqlen, width, dtype=torch.float32, device=device
        )
        score_all = torch.empty(
            bsz, seqlen, width, dtype=torch.float32, device=device
        )
        for a in range(0, seqlen, cfg.compressor_positions):
            b = min(a + cfg.compressor_positions, seqlen)
            xf = x[:, a:b].float()
            kv_all[:, a:b] = self.wkv(xf)
            score_all[:, a:b] = self.wgate(xf)
            del xf

        if overlap and cutoff >= ratio:
            self.kv_state[:bsz, :ratio] = kv_all[:, cutoff - ratio : cutoff]
            self.score_state[:bsz, :ratio] = (
                score_all[:, cutoff - ratio : cutoff] + self.ape
            )
        if remainder > 0:
            self.kv_state[:bsz, offset : offset + remainder] = kv_all[:, cutoff:]
            self.score_state[:bsz, offset : offset + remainder] = (
                score_all[:, cutoff:] + self.ape[:remainder]
            )

        pooled = torch.empty(bsz, groups, d if overlap else self.ape.size(1),
                             dtype=torch.float32, device=device)
        step = max(1, cfg.compressor_positions // ratio)
        for g0 in range(0, groups, step):
            g1 = min(g0 + step, groups)
            # ``overlap_transform`` couples group g to group g-1, so a tile of
            # groups reads one extra group of already-projected rows.
            base = max(0, g0 - 1)
            kv = kv_all[:, base * ratio : g1 * ratio].unflatten(1, (-1, ratio))
            score = (
                score_all[:, base * ratio : g1 * ratio].unflatten(1, (-1, ratio))
                + self.ape
            )
            here = g0 - base
            if overlap:
                width = g1 - g0
                nkv = kv.new_zeros(bsz, width, 2 * ratio, d)
                nsc = score.new_full((bsz, width, 2 * ratio, d), float("-inf"))
                nkv[:, :, ratio:] = kv[:, here:, :, d:]
                nsc[:, :, ratio:] = score[:, here:, :, d:]
                if g0 == 0:
                    nkv[:, 1:, :ratio] = kv[:, : width - 1, :, :d]
                    nsc[:, 1:, :ratio] = score[:, : width - 1, :, :d]
                else:
                    nkv[:, :, :ratio] = kv[:, here - 1 : here - 1 + width, :, :d]
                    nsc[:, :, :ratio] = score[:, here - 1 : here - 1 + width, :, :d]
                kv, score = nkv, nsc
            else:
                kv, score = kv[:, here:], score[:, here:]
            pooled[:, g0:g1] = (kv * score.softmax(dim=2)).sum(dim=2)
            del kv, score
        del kv_all, score_all

        kv = self.norm(pooled.to(dtype))
        del pooled
        model_mod.apply_rotary_emb(kv[..., -rd:], self.freqs_cis[:cutoff:ratio])
        if self.rotate:
            kv = model_mod.rotate_activation(kv)
            model_mod.fp4_act_quant(kv, model_mod.fp4_block_size, True)
        else:
            model_mod.act_quant(
                kv[..., :-rd], 64, model_mod.scale_fmt, model_mod.scale_dtype, True
            )
        self.kv_cache[:bsz, : seqlen // ratio] = kv
        return kv

    # ---------------- Indexer (query-tiled selection) ----------------
    def indexer_select(self, x, qr, seqlen, lo, hi, offset):  # noqa: ANN001
        """The vendor's scoring and top-k for the query rows ``[lo, hi)``.

        ``self.compressor`` has already been run over the whole sequence by the
        caller, exactly once, so ``self.kv_cache`` holds every compressed entry
        this selection is allowed to see.

        The score block is ``[rows, heads, seqlen // ratio]``: it grows with the
        *context*, not with the tile, so it gets its own sub-tile.  Sizing the
        whole attention tile from it would drive the query GEMMs down to a
        couple of hundred rows at 200k and waste the GPU; sizing it from the
        attention tile would put 26 GB in one allocation.
        """
        ratio = self.compress_ratio
        rd = self.rope_head_dim
        bsz = x.size(0)
        entries = seqlen // ratio
        selected = min(self.index_topk, entries)
        sub = cfg.index_tile(self.n_local_heads, entries)
        picked = torch.empty(
            bsz, hi - lo, selected, dtype=torch.int32, device=x.device
        )
        for a in range(lo, hi, sub):
            b = min(a + sub, hi)
            q = self.wq_b(qr[:, a - lo : b - lo])
            q = q.unflatten(-1, (self.n_local_heads, self.head_dim))
            model_mod.apply_rotary_emb(q[..., -rd:], self.freqs_cis[a:b])
            q = model_mod.rotate_activation(q)
            model_mod.fp4_act_quant(q, model_mod.fp4_block_size, True)
            weights = self.weights_proj(x[:, a - lo : b - lo]) * (
                self.softmax_scale * self.n_heads**-0.5
            )
            score = torch.einsum("bshd,btd->bsht", q, self.kv_cache[:bsz, :entries])
            del q
            # ``relu_() * weights`` and ``relu_().mul_(weights)`` are the same
            # elementwise product; the in-place form does not need a second
            # [rows, heads, entries] block alive alongside the first.
            score = score.relu_().mul_(weights.unsqueeze(-1)).sum(dim=2)
            bound = (
                torch.arange(a + 1, b + 1, device=x.device) // ratio
            ).unsqueeze(1)
            mask = torch.arange(entries, device=x.device) >= bound
            score += torch.where(mask, float("-inf"), 0)
            del mask
            chosen = score.topk(selected, dim=-1)[1]
            del score
            picked[:, a - lo : b - lo] = torch.where(
                chosen >= bound, -1, chosen + offset
            ).int()
            del chosen
        COUNTERS.note_index(hi - lo, entries, self.kv_cache, selected)
        return picked

    # ---------------- Attention ----------------
    def attention_forward(self, x, start_pos: int, *rest):  # noqa: ANN001
        seqlen = x.size(1)
        kind = (
            "window"
            if not self.compress_ratio
            else ("csa" if self.compress_ratio == 4 else "hca")
        )
        COUNTERS.layer_id = self.layer_id
        if start_pos != 0 or seqlen <= cfg.floor or rest:
            out = vendor["Attention"](self, x, start_pos, *rest)
            return out

        bsz = x.size(0)
        win, ratio, rd = self.window_size, self.compress_ratio, self.rope_head_dim
        device = x.device
        freqs = self.freqs_cis[:seqlen]

        if self.compress_ratio and self.compressor.kv_cache is None:
            self.compressor.kv_cache = self.kv_cache[:, win:]
            self.compressor.freqs_cis = self.freqs_cis
            if self.indexer is not None:
                self.indexer.freqs_cis = self.freqs_cis

        # The compressors run first.  They are the widest thing in this block -
        # a float32 view of the whole sequence plus two float32 projections of
        # it - and the query and window tensors would otherwise be resident
        # throughout.  Nothing here reads them: the compressors take ``x``, and
        # they write a region of the cache the window write never touches.
        kv_compress = None
        if ratio:
            if self.indexer is not None:
                indexer = self.indexer
                if indexer.compressor.kv_cache is None:
                    indexer.compressor.kv_cache = indexer.kv_cache
                    indexer.compressor.freqs_cis = indexer.freqs_cis
                indexer.compressor(x, 0)
            kv_compress = self.compressor(x, 0)

        qr = self.q_norm(self.wq_a(x))

        kv = self.wkv(x)
        kv = self.kv_norm(kv)
        model_mod.apply_rotary_emb(kv[..., -rd:], freqs)
        model_mod.act_quant(
            kv[..., :-rd], 64, model_mod.scale_fmt, model_mod.scale_dtype, True
        )
        # The vendor takes this before concatenating the compressed rows, so it
        # is the raw sequence length either way.
        offset = kv.size(1)

        if seqlen <= win:
            self.kv_cache[:bsz, :seqlen] = kv
        else:
            cutoff = seqlen % win
            self.kv_cache[:bsz, cutoff:win], self.kv_cache[:bsz, :cutoff] = (
                kv[:, -win:].split([win - cutoff, cutoff], dim=1)
            )

        if kv_compress is not None:
            kv = torch.cat([kv, kv_compress], dim=1)
            del kv_compress

        out = torch.empty(bsz, seqlen, self.dim, dtype=x.dtype, device=device)
        wo_a = self.wo_a.weight.view(self.n_local_groups, self.o_lora_rank, -1)
        tile = cfg.seq_tile
        for lo in range(0, seqlen, tile):
            hi = min(lo + tile, seqlen)
            f = freqs[lo:hi]
            q = self.wq_b(qr[:, lo:hi]).unflatten(
                -1, (self.n_local_heads, self.head_dim)
            )
            q *= torch.rsqrt(q.square().mean(-1, keepdim=True) + self.eps)
            model_mod.apply_rotary_emb(q[..., -rd:], f)
            topk_idxs = _window_topk_idxs(torch, win, seqlen, lo, hi, device)
            if ratio:
                if self.indexer is not None:
                    picked = indexer_select(
                        self.indexer, x[:, lo:hi], qr[:, lo:hi], seqlen, lo, hi, offset
                    )
                else:
                    picked = _compress_topk_idxs(
                        torch, ratio, seqlen, lo, hi, offset, device
                    )
                topk_idxs = torch.cat([topk_idxs, picked], dim=-1)
                del picked
            COUNTERS.note_attention(topk_idxs, kv, kind)
            o = model_mod.sparse_attn(
                q, kv, self.attn_sink, topk_idxs, self.softmax_scale
            )
            del q, topk_idxs
            model_mod.apply_rotary_emb(o[..., -rd:], f, True)
            o = o.view(bsz, hi - lo, self.n_local_groups, -1)
            o = torch.einsum("bsgd,grd->bsgr", o, wo_a)
            out[:, lo:hi] = self.wo_b(o.flatten(2))
            del o
        return out

    # ---------------- Block ----------------
    def block_forward(self, x, start_pos: int, input_ids, *attn_args):  # noqa: ANN001
        seqlen = x.size(1)
        if start_pos != 0 or seqlen <= cfg.floor or attn_args:
            return vendor["Block"](self, x, start_pos, input_ids, *attn_args)

        bsz, hc, dim = x.size(0), self.hc_mult, x.size(-1)
        tile = cfg.hc_tile(hc, dim)

        # The residual may live in pinned host memory: nothing in a block reads
        # it except hc_pre and hc_post, and both are strictly per-position, so
        # it is only ever needed one tile at a time.  It is the single largest
        # device-resident tensor at long context ([1, s, 4, 4096] bfloat16 is
        # 6.1 GiB at 200k) and moving it off the device is what makes the top
        # of the ladder fit.  The values are unchanged; only residency is.
        device = self.attn_norm.weight.device
        staged = x.device.type != device.type

        def half(residual, hc_fn, hc_scale, hc_base, norm, body, body_arg):  # noqa: ANN001
            normalised = torch.empty(
                bsz, seqlen, dim, dtype=residual.dtype, device=device
            )
            post_all = torch.empty(
                bsz, seqlen, hc, dtype=torch.float32, device=device
            )
            comb_all = torch.empty(
                bsz, seqlen, hc, hc, dtype=torch.float32, device=device
            )
            for lo in range(0, seqlen, tile):
                hi = min(lo + tile, seqlen)
                chunk = residual[:, lo:hi]
                if staged:
                    chunk = chunk.to(device)
                y, post, comb = self.hc_pre(chunk, hc_fn, hc_scale, hc_base)
                normalised[:, lo:hi] = norm(y)
                post_all[:, lo:hi] = post
                comb_all[:, lo:hi] = comb
                del y, post, comb, chunk
            produced = body(normalised, body_arg)
            del normalised
            for lo in range(0, seqlen, tile):
                hi = min(lo + tile, seqlen)
                # The right-hand side is fully evaluated before the store, and
                # tile ``lo`` reads only tile ``lo`` of the residual, so writing
                # the result back over the residual in place is the same value
                # the vendor would have put in a fresh tensor.
                chunk = residual[:, lo:hi]
                if staged:
                    # Synchronous on purpose: the host overwrites this same
                    # pinned region a few lines below, and an asynchronous read
                    # of it would still be in flight when it did.
                    chunk = chunk.to(device)
                updated = self.hc_post(
                    produced[:, lo:hi],
                    chunk,
                    post_all[:, lo:hi],
                    comb_all[:, lo:hi],
                )
                if staged:
                    # Straight into the pinned destination; ``.to("cpu")``
                    # would stage through a pageable temporary and copy twice.
                    residual[:, lo:hi].copy_(updated)
                else:
                    residual[:, lo:hi] = updated
                del chunk, updated
            del produced, post_all, comb_all
            return residual

        x = half(
            x,
            self.hc_attn_fn,
            self.hc_attn_scale,
            self.hc_attn_base,
            self.attn_norm,
            lambda t, _: self.attn(t, start_pos),
            None,
        )
        x = half(
            x,
            self.hc_ffn_fn,
            self.hc_ffn_scale,
            self.hc_ffn_base,
            self.ffn_norm,
            lambda t, ids: self.ffn(t, ids),
            input_ids,
        )
        return x

    # ---------------- MoE / Expert ----------------
    def moe_forward(self, x, input_ids):  # noqa: ANN001
        shape = x.size()
        rows = 1
        for extent in shape[:-1]:
            rows *= extent
        if rows <= cfg.floor:
            return vendor["MoE"](self, x, input_ids)

        x = x.view(-1, self.dim)
        flat_ids = input_ids.flatten()
        # ``Gate`` casts its whole input to float32; at 200k that is a 3.3 GB
        # copy of a tensor it reduces to 256 scores per row.
        weight_parts, index_parts = [], []
        for lo in range(0, rows, cfg.expert_rows):
            hi = min(lo + cfg.expert_rows, rows)
            w, i = self.gate(x[lo:hi], flat_ids[lo:hi])
            weight_parts.append(w)
            index_parts.append(i)
        weights = torch.cat(weight_parts, dim=0)
        indices = torch.cat(index_parts, dim=0)
        del weight_parts, index_parts

        y = torch.zeros_like(x, dtype=torch.float32)
        counts = torch.bincount(
            indices.flatten(), minlength=self.n_routed_experts
        ).tolist()
        for i in range(self.experts_start_idx, self.experts_end_idx):
            if counts[i] == 0:
                continue
            expert = self.experts[i]
            idx, top = torch.where(indices == i)
            taken = int(idx.numel())
            if taken <= cfg.expert_rows:
                y[idx] += expert(x[idx], weights[idx, top, None])
                continue
            # A hot expert can take tens of thousands of rows at long context;
            # its output alone was 650 MiB at 200k.  ``Expert.forward`` already
            # evaluates it in ``expert_rows`` pieces, so scattering each piece
            # as it is produced changes no GEMM's row count and no value - it
            # only stops the pieces from having to exist all at once.
            for a in range(0, taken, cfg.expert_rows):
                b = min(a + cfg.expert_rows, taken)
                sel = idx[a:b]
                y[sel] += expert(x[sel], weights[sel, top[a:b], None])
        # The shared expert sees every row, so its output is a second
        # full-sequence tensor - 1.5 GB at 200k - alive next to the float32
        # accumulator.  ``Expert.forward`` already evaluates it in
        # ``expert_rows`` pieces, so adding each piece as it is produced keeps
        # every GEMM's row count and every value, and never builds the whole.
        if rows <= cfg.expert_rows:
            y += self.shared_experts(x)
        else:
            for a in range(0, rows, cfg.expert_rows):
                b = min(a + cfg.expert_rows, rows)
                y[a:b] += self.shared_experts(x[a:b])
        return y.type_as(x).view(shape)

    def expert_forward(self, x, weights=None):  # noqa: ANN001
        rows = x.size(0)
        if rows <= cfg.expert_rows:
            return vendor["Expert"](self, x, weights)
        out = None
        for lo in range(0, rows, cfg.expert_rows):
            hi = min(lo + cfg.expert_rows, rows)
            piece = vendor["Expert"](
                self, x[lo:hi], None if weights is None else weights[lo:hi]
            )
            if out is None:
                out = torch.empty(
                    rows, piece.size(-1), dtype=piece.dtype, device=piece.device
                )
            out[lo:hi] = piece
            del piece
        return out

    # ---------------- Transformer ----------------
    def transformer_forward(self, input_ids, start_pos: int = 0):  # noqa: ANN001
        seqlen = input_ids.size(1)
        if start_pos != 0 or seqlen <= cfg.floor:
            return vendor["Transformer"](self, input_ids, start_pos)

        embedded = self.embed(input_ids)
        if cfg.host_residual:
            h = torch.empty(
                embedded.size(0),
                seqlen,
                self.hc_mult,
                embedded.size(-1),
                dtype=embedded.dtype,
                device="cpu",
                pin_memory=True,
            )
            step = max(1, cfg.seq_tile)
            for lo in range(0, seqlen, step):
                hi = min(lo + step, seqlen)
                h[:, lo:hi] = (
                    embedded[:, lo:hi]
                    .unsqueeze(2)
                    .repeat(1, 1, self.hc_mult, 1)
                    .to("cpu", non_blocking=False)
                )
        else:
            h = embedded.unsqueeze(2).repeat(1, 1, self.hc_mult, 1)
        del embedded
        main_hiddens = []
        for i, layer in enumerate(self.layers):
            h = layer(h, start_pos, input_ids)
            if i in self.target_layer_ids:
                main_hiddens.append(h.mean(dim=2))
        dim = h.size(-1)
        tile = cfg.hc_tile(self.hc_mult, dim)
        device = self.norm.weight.device
        reduced = torch.empty(
            h.size(0), seqlen, dim, dtype=h.dtype, device=device
        )
        for lo in range(0, seqlen, tile):
            hi = min(lo + tile, seqlen)
            chunk = h[:, lo:hi]
            if chunk.device.type != device.type:
                chunk = chunk.to(device)
            reduced[:, lo:hi] = layer.hc_head(
                chunk, self.hc_head_fn, self.hc_head_scale, self.hc_head_base
            )
            del chunk
        del h
        # ``RMSNorm`` casts its input to float32 and builds three float32
        # temporaries the width of the whole sequence: at 200k that is about
        # 9 GB, and it is the largest thing this model ever allocates - for a
        # value the head then throws away every row of but the last.  It is
        # per-position, so a tile of it holds the values the whole would have.
        normed = torch.empty_like(reduced)
        for lo in range(0, seqlen, tile):
            hi = min(lo + tile, seqlen)
            normed[:, lo:hi] = self.norm(reduced[:, lo:hi])
        del reduced
        logits = self.head(normed)
        del normed
        output_ids = model_mod.sample(logits, self.temperature)
        main_hidden = torch.cat(main_hiddens, dim=-1) if main_hiddens else None
        return output_ids, logits, main_hidden

    return {
        "vendor": vendor,
        "Compressor": compressor_forward,
        "Attention": attention_forward,
        "Block": block_forward,
        "MoE": moe_forward,
        "Expert": expert_forward,
        "Transformer": transformer_forward,
    }


def install(model_mod: Any, cfg: TilingConfig) -> dict[str, Any]:
    """Install the tiled bodies onto the vendor classes.

    Must be called *before* the engine is constructed: the engine stashes the
    functions it finds and wraps those with weight residency, so installing
    afterwards would either bypass residency or wrap it twice.
    """
    patches = build_patches(model_mod, cfg)
    if hasattr(model_mod, "_opentallas_vendor_forwards"):
        # The engine has already stashed a pristine pair; make sure the pair it
        # wraps is the tiled one, not the body we are about to replace.
        del model_mod._opentallas_vendor_forwards
    model_mod.Compressor.forward = patches["Compressor"]
    model_mod.Attention.forward = patches["Attention"]
    model_mod.Block.forward = patches["Block"]
    model_mod.MoE.forward = patches["MoE"]
    model_mod.Expert.forward = patches["Expert"]
    model_mod.Transformer.forward = patches["Transformer"]
    return patches


def instrument_decode(model_mod: Any) -> None:
    """Attach the counters to whatever bodies are installed.

    This must not assume the tiled prefill is in use.  ``Indexer.forward`` is
    wrapped here rather than in ``install`` because an untiled run also has to
    count index scans: when it did not, an untiled rung reported zero index
    (layer, position) pairs and looked exactly like an implementation that had
    declined to scan its index, which it had not.
    """
    import torch

    vendor_indexer = model_mod.Indexer.forward

    def counted_indexer(self, x, qr, start_pos: int, offset: int):  # noqa: ANN001
        out = vendor_indexer(self, x, qr, start_pos, offset)
        entries = (start_pos + x.size(1)) // self.compress_ratio
        COUNTERS.note_index(x.size(1), entries, self.kv_cache, int(out.size(-1)))
        return out

    model_mod.Indexer.forward = counted_indexer

    vendor_attention = model_mod.Attention.forward

    def counted_attention(self, x, start_pos: int, *rest):  # noqa: ANN001
        COUNTERS.layer_id = self.layer_id
        if start_pos == 0 or not COUNTERS.enabled:
            return vendor_attention(self, x, start_pos, *rest)
        kind = (
            "window"
            if not self.compress_ratio
            else ("csa" if self.compress_ratio == 4 else "hca")
        )
        seen = {}
        vendor_sparse = model_mod.sparse_attn

        def counting_sparse(q, kv, attn_sink, topk_idxs, scale):  # noqa: ANN001
            if not seen:
                seen["done"] = True
                COUNTERS.note_attention(topk_idxs, kv, kind)
            return vendor_sparse(q, kv, attn_sink, topk_idxs, scale)

        model_mod.sparse_attn = counting_sparse
        try:
            return vendor_attention(self, x, start_pos, *rest)
        finally:
            model_mod.sparse_attn = vendor_sparse

    model_mod.Attention.forward = counted_attention


def deduplicate_freqs_cis(model: Any, torch: Any) -> dict[str, Any]:
    """Point layers that computed the same RoPE table at one copy of it.

    ``precompute_freqs_cis`` is called once per layer, and its arguments take
    only two distinct values across the 43 layers, so 41 of the tables are
    duplicates.  At 200k positions each table is 51 MB of complex64 and the set
    is 2.2 GB of device memory holding two distinct values.  Aliasing them is
    not an approximation - the tensors are compared elementwise first and only
    identical ones are merged.
    """
    unique: list[Any] = []
    merged = 0
    saved = 0
    already_shared = 0
    for layer in model.layers:
        table = layer.attn.freqs_cis
        for candidate in unique:
            if candidate is table:
                already_shared += 1
                break
            if candidate.shape == table.shape and torch.equal(candidate, table):
                layer.attn.register_buffer("freqs_cis", candidate, persistent=False)
                merged += 1
                saved += table.numel() * table.element_size()
                break
        else:
            unique.append(table)
    return {
        "distinct_tables": len(unique),
        "layers_newly_aliased": merged,
        "layers_already_sharing_one_tensor": already_shared,
        "device_bytes_reclaimed": int(saved),
        "resident_table_bytes": int(
            sum(t.numel() * t.element_size() for t in unique)
        ),
        "method": "identity first, then elementwise torch.equal; no value changes",
        "note": (
            "precompute_freqs_cis is lru_cache(2) and the 43 layers use only "
            "two distinct argument tuples, so the tables are normally already "
            "one object each; this check proves it rather than assuming it"
        ),
    }


def projected_resident_bytes(seqlen: int, num_layers: int = 43) -> dict[str, int]:
    """Device bytes that cannot be tiled away, as a function of context.

    Every term here is a tensor whose extent is the whole sequence and which is
    live across a whole layer, so no amount of tiling removes it.  This is the
    arithmetic that decides whether a rung can run at all.
    """
    hc_mult, dim, head_dim, index_head_dim = 4, 4096, 512, 128
    # compress_ratios[:43] of the pinned config: 21 layers at ratio 4,
    # 20 at ratio 128, 2 pure sliding-window layers.
    ratio4 = 21
    ratio128 = 20
    window_layers = 2
    window = 128
    residual = seqlen * hc_mult * dim * 2
    main_kv = (
        ratio4 * (window + seqlen // 4)
        + ratio128 * (window + seqlen // 128)
        + window_layers * window
    ) * head_dim * 2
    index_kv = ratio4 * (seqlen // 4) * index_head_dim * 2
    freqs = 2 * seqlen * 32 * 8
    activation = seqlen * dim * 2
    moe_accumulator = seqlen * dim * 4
    total = residual + main_kv + index_kv + freqs + activation + moe_accumulator
    return {
        "hyper_connection_residual_bytes": residual,
        "main_kv_cache_bytes": main_kv,
        "index_kv_cache_bytes": index_kv,
        "rope_table_bytes_after_dedup": freqs,
        "one_full_sequence_activation_bytes": activation,
        "moe_float32_accumulator_bytes": moe_accumulator,
        "total_bytes": total,
    }


def untiled_peak_bytes(seqlen: int) -> dict[str, int]:
    """The three quadratic prefill intermediates the vendor body materialises."""
    heads, hc_mult, dim = 64, 4, 4096
    index_score = seqlen * heads * (seqlen // 4) * 2
    hc_post = seqlen * hc_mult * hc_mult * dim * 4
    hc_pre = seqlen * hc_mult * dim * 4
    query = seqlen * heads * 512 * 2
    return {
        "indexer_index_score_bytes": index_score,
        "hc_post_outer_product_bytes": hc_post,
        "hc_pre_float32_bytes": hc_pre,
        "attention_query_bytes": query,
        "largest_single_allocation_bytes": max(
            index_score, hc_post, hc_pre, query
        ),
    }


__all__ = [
    "COUNTERS",
    "KVCounters",
    "PhaseCounters",
    "TilingConfig",
    "build_patches",
    "deduplicate_freqs_cis",
    "install",
    "instrument_decode",
    "projected_resident_bytes",
    "untiled_peak_bytes",
]
