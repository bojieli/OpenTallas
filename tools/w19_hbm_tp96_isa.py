#!/usr/bin/env python3
"""TP-96 program and 96-rank executor of the DeepSeek-V4.1-Flash HBM comparator's decode token, checked per layer
bit for bit against the released-checkpoint golden (W19 build step B1).

    HDC_V41_ARITH=chunk8 python3 tools/w19_hbm_tp96_isa.py --layers 0 [--layers 0-39 --head] \
        [--variant oreduce] [--record results/rtl/w19_hbm_tp96_isa.json] [--program-out FILE]

THE MACHINE.  The V4.1 HBM comparator is a tensor group of 96 GPU-organised dies (docs/MICROARCH_MODEL.md, the W19
audit): SMs with Tensor-Core-style exact MMA units, dedicated units for the irregular operators, a switched
deterministic collective fabric.  Every matrix is split over the 96 dies by OUTPUT ROWS, and each row keeps its whole K
inside one SM (the SM's lane tree is the golden's chunk-8 csum tree, rtl/gpu/ot_gpu_sm.sv), so a row-split product
is exact by construction and no collective ever adds partial sums except where the variant below says so.

THE PROGRAM.  compile_layer() emits, for one decode position, the TP-96 op list of one layer; compile_head() the
final norm, the LM head and the argmax.  The program is data (JSON; --program-out writes it) and the executor only
follows it.  Op kinds:

  mv          an SM matvec: matrix, golden arithmetic class (linear_q FP8/FP4 block dot, mv/linear_bf16 BF16 csum,
              the grouped wo_a), input buffer, output buffer, and every rank's output rows [r0, r1) (even contiguous
              split, or the head-aligned split: head h's 512 wq_b rows on die h, h < 64);
  local       a dedicated-unit / stream-unit step on named ranks (all, the 64 head dies, or one owner die), the
              golden's own function on the rank's local buffers (hyper-connection mixes and Sinkhorn, norms, RoPE,
              quantisers, top-6 routing, SwiGLU, the per-row expert sum, the compressor pooling, the index scores
              over the rank's own keys, local top-k);
  all_gather  a collective: every rank's written segment of each named buffer to every rank (a fused gather carries
              several buffers ready at the same point);
  all_reduce  (variant oreduce only) the grouped wo_a as a K-split over the 8 head dies of each o-group, reduced in
              the golden's pairwise tree order ((p0 + p1) + (p2 + p3)) + ((p4 + p5) + (p6 + p7)) and multicast to all 96
              dies: each head's 512 inputs are 64 aligned chunk-8 chunks, a whole subtree of the golden csum, so the
              reduction is exact and the o all-gather disappears;
  topk_merge  a collective: every rank's local top-k (value, global index) to every rank, merged with the golden's
              order (value descending, lower index first): the global top-k is a subset of the union of the local
              ones, so the merge is exact (96 x 512 for the index selection, 96 x 2,048 for layer 20's candidates);
  kv_gather   a collective: the selected compressed-KV rows from their owner dies to the 64 head dies (288 B a row
              in the stored FP4 format); layers that reuse an index source's selection reuse the gathered rows.

STATE.  The window rows of every layer are replicated (every die forms the new row from the gathered wkv output).
Compressed KV rows and index keys are SHARDED BY SEQUENCE POSITION: group i lives on die (i // 8) mod 96 (blocks of 8,
layer 20's candidate block, so a candidate block never straddles dies); a die reads only rows it owns (asserted).
The compressor's open group lives on the owner die of the group being filled.  The entering state is the W17
reference state (tools/rtl_v41_fullshape_layer_campaign.synthetic_state, seed 20260930 at 1M: the reference token
21946), rebuilt as arrays with the same generators and checked against the golden record's state digest.

CHECK.  After each layer, every rank's copy of each replicated result, and the assembly of every sharded one, is
compared with the golden shard of the W17 reference run (/home/ubuntu/w17work/ref/ctx1048576_seed20260930):
L.attn_norm, L.attn, L.ffn_norm, L.router, L.ffn, blockL, preL, the new window row, the compressor's appended rows,
the index scores, the index selection and the experts.  The executor feeds its own layer output forward, so a
multi-layer run is an end-to-end TP-96 token, and --head checks the next token against the reference.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

os.environ.setdefault("HDC_V41_ARITH", "chunk8")

import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden as G  # noqa: E402
import hdc_golden_v41 as V  # noqa: E402
import rtl_v41_fullshape_layer_campaign as LC  # noqa: E402

F = np.float32
SCHEMA = "opentallas.rtl.w19_hbm_tp96_isa.v1"
TP = 96
HEAD_DIES = 64
KEY_BLOCK = 8                      # sequence-sharding granule of compressed rows / index keys
KV_ROW_BYTES = 512 // 2 + 512 // 16  # a compressed-KV row in its stored FP4 (E4M3 block-16 scale) format
REF_SEED = 20260930
REF_CTX = 1048576
REF_RECORD = ROOT / "results/rtl/w17_v41_1m_reference_token.json"
REF_SHARDS = Path("/home/ubuntu/w17work/ref/ctx1048576_seed20260930")
OUT = ROOT / "results/rtl/w19_hbm_tp96_isa.json"


class Defect(Exception):
    """A program / dataflow defect (unwritten read, ownership violation), not an arithmetic mismatch."""


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def even(n: int, tp: int = TP) -> list[list[int]]:
    return [[r * n // tp, (r + 1) * n // tp] for r in range(tp)]


def key_owner(i):
    return (np.asarray(i) // KEY_BLOCK) % TP


# ======================================================================================================================
# the compiler: one layer's TP-96 op list for one decode position
# ======================================================================================================================
class Compiler:
    def __init__(self, m, pos: int, variant: str = "gather"):
        assert variant in ("gather", "oreduce")
        self.m, self.pos, self.variant = m, pos, variant
        self.ops: list[dict] = []

    def emit(self, **op):
        op["id"] = len(self.ops)
        self.ops.append(op)
        return op

    def mv(self, L, w, fn, x, out, n, k, fmt, rows=None, out_dtype="bf16", tag=""):
        return self.emit(kind="mv", unit="SM", layer=L, w=w, fn=fn, x=x, out=out, n=n, k=k, fmt=fmt,
                         rows=rows or even(n), out_dtype=out_dtype, tag=tag)

    def local(self, L, fn, ranks="all", tag="", **kw):
        return self.emit(kind="local", unit="DU", layer=L, fn=fn, ranks=ranks, tag=tag, **kw)

    def gather(self, L, bufs, tag, dest="all"):
        # bufs: [(name, elements, bytes per element)]
        return self.emit(kind="all_gather", unit="COLL", layer=L, bufs=[b[0] for b in bufs],
                         elems=sum(b[1] for b in bufs), bytes=sum(b[1] * b[2] for b in bufs), dest=dest, tag=tag)

    def compile_layer(self, L: int, first: bool = False) -> list[dict]:
        m, pos = self.m, self.pos
        P = m.P(L)
        yarn = m.ratio[L] > 0
        comp = yarn and L == m.kv_of[L]
        idx = yarn and L == m.idx_of[L]
        r = m.ratio[L]
        # ---------------------------------------------------------------- Engram (layers 1, 14)
        if L in m.engram.layer_ids:
            wk = P + "engram.wkv.weight"
            nrow, kk = 25600, 6144
            self.local(L, "engram_fetch", tag="engram.rows (HBM table rows by hash, owner die = id mod 96)")
            self.gather(L, [("eg_rows", kk, 2)], "engram.rows_gather")
            self.mv(L, wk, "linear_q", "eg_rows", "eg_kv", nrow, kk, "fp8", tag="engram.wkv")
            self.gather(L, [("eg_kv", nrow, 2)], "engram.kv_gather")
            self.local(L, "engram_mix", tag="engram.mix")
        # ---------------------------------------------------------------- attention
        self.local(L, "hc_mixes", which="attn", tag="hc_attn (mixes + Sinkhorn)")
        self.local(L, "hc_pre_norm", which="attn", tag="attn_norm")
        g = [("qa", 1280, 2), ("kvraw", 512, 2)]
        self.mv(L, P + "attn.wq_a.weight", "linear_q", "x", "qa", 1280, 5120, "fp8", tag="wq_a")
        self.mv(L, P + "attn.wkv.weight", "linear_q", "x", "kvraw", 512, 5120, "fp8", tag="wkv")
        if comp:
            if r > 1:
                self.mv(L, [P + "attn.compressor.wkv.weight", P + "attn.compressor.wgate.weight"], "mv", "x",
                        "cmp", 1024, 5120, "bf16", out_dtype="fp32", tag="compressor.wkv|wgate")
                g.append(("cmp", 1024, 4))
            else:
                self.mv(L, P + "attn.compressor.wkv.weight", "linear_bf16", "x", "cmp", 512, 5120, "bf16",
                        tag="compressor.wkv")
                g.append(("cmp", 512, 2))
        if idx:
            self.mv(L, P + "attn.indexer.weights_proj.weight", "linear_bf16", "x", "iwr", 32, 5120, "bf16",
                    tag="indexer.weights_proj")
            g.append(("iwr", 32, 2))
        self.gather(L, g, "x_projections_gather")
        self.local(L, "q_norm_kv_row", tag="q_norm, kv_norm, RoPE, FP8 window row (replicated window)")
        heads = [[h * 512, (h + 1) * 512] if h < HEAD_DIES else [0, 0] for h in range(TP)]
        self.mv(L, P + "attn.wq_b.weight", "linear_q", "qr", "q", 32768, 1280, "fp8", rows=heads,
                tag="wq_b (head-aligned: head h on die h)")
        self.local(L, "q_rope", ranks="heads", tag="q RoPE (own head)")
        if comp:
            n_prev = pos // r if r > 1 else pos
            owner = int(key_owner(n_prev))
            self.local(L, "compressor", ranks=[owner], group=n_prev, closes=(pos + 1) % r == 0,
                       tag=f"compressor pooling + indexer.wk + k_norm + RoPE + FP4 (owner die {owner})")
        if idx:
            n = (pos + 1) // r
            self.mv(L, P + "attn.indexer.wq_b.weight", "linear_q", "qr", "iq", 4096, 1280, "fp8",
                    tag="indexer.wq_b")
            self.gather(L, [("iq", 4096, 2)], "indexer.q_gather")
            self.local(L, "index_q", tag="indexer q RoPE + FP4, weights scale")
            self.local(L, "index_scores", n=n, src=m.kv_of[L], tag="index scores over the die's own keys")
            if L == m.cand_src:
                nb = -(-n // m.cand_b)
                self.local(L, "cand_local", n=n, tag="candidate block scores + local top-2048")
                self.emit(kind="topk_merge", unit="COLL", layer=L, what="cand", k=min(m.cand_k, nb),
                          elems=TP * min(m.cand_k, nb), bytes=TP * min(m.cand_k, nb) * 8, tag="candidate merge")
                self.local(L, "cand_apply", tag="candidate keep flags (sharded)")
            elif 0 <= m.cand_src < L:
                self.local(L, "cand_mask", n=n, tag="candidate mask on the die's own scores")
            k = min(m.topk, n)
            self.local(L, "topk_local", k=k, tag="index local top-512")
            self.emit(kind="topk_merge", unit="COLL", layer=L, what="sel", k=k, elems=TP * k, bytes=TP * k * 8,
                      tag="96 x 512 index merge")
        if yarn and (idx or first):
            k = min(m.topk, (pos + 1) // r)
            self.emit(kind="kv_gather", unit="COLL", layer=L, src=m.kv_of[L], elems=k * 512,
                      bytes=k * KV_ROW_BYTES, dest="heads", tag="selected compressed-KV rows to the head dies")
        self.local(L, "attend", ranks="heads", yarn=yarn, tag="attention of the die's head (window + selection)")
        if self.variant == "oreduce":
            self.mv(L, P + "attn.wo_a.weight", "wo_a_part", "o_own", "zpart", 8192, 512, "bf16",
                    rows=[[(h // 8) * 1024, (h // 8 + 1) * 1024] if h < HEAD_DIES else [0, 0] for h in range(TP)],
                    out_dtype="fp32", tag="wo_a K-split: the die's head against its o-group's 1,024 rows")
            self.emit(kind="all_reduce", unit="COLL", layer=L, buf="zpart", out="z", groups=8, per_group=8,
                      elems=8192, bytes=8192 * 4 * 8 // 8, dest="all", round="bf16",
                      tag="o-group tree reduce (8 contributors) + multicast")
        else:
            self.gather(L, [("o", 32768, 2)], "o_gather")
            self.mv(L, P + "attn.wo_a.weight", "wo_a", "o", "z", 8192, 4096, "bf16", tag="wo_a (grouped)")
            self.gather(L, [("z", 8192, 2)], "z_gather")
        self.mv(L, P + "attn.wo_b.weight", "linear_q", "z", "y", 5120, 8192, "fp8", tag="wo_b")
        self.gather(L, [("y", 5120, 2)], "attn_out_gather")
        self.local(L, "hc_post", which="attn", tag="hc_post attn")
        # ---------------------------------------------------------------- MoE
        self.local(L, "hc_mixes", which="ffn", tag="hc_ffn (mixes + Sinkhorn)")
        self.local(L, "hc_pre_norm", which="ffn", tag="ffn_norm")
        self.mv(L, P + "ffn.gate.weight", "mv", "x", "gsc", 384, 5120, "bf16", out_dtype="fp32", tag="router gate")
        self.local(L, "router_act", tag="sqrt(softplus) on the die's own router rows")
        self.gather(L, [("gsc", 384, 4)], "router_gather")
        self.local(L, "route", tag="top-6 + weights (replicated)")
        self.emit(kind="expert_fetch", unit="HBM", layer=L, experts=m.k_exp, tag="routed-expert slices HBM -> SMEM "
                  "(descriptors after the router; B2)")
        for e in range(m.k_exp + 1):
            nm = f"e{e}"
            fmt = "fp4" if e < m.k_exp else "fp8"
            self.mv(L, (e, "w1"), "linear_q", "x", nm + ".g", 2304, 5120, fmt, tag=f"expert slot {e} w1")
            self.mv(L, (e, "w3"), "linear_q", "x", nm + ".u", 2304, 5120, fmt, tag=f"expert slot {e} w3")
            self.local(L, "swiglu", slot=e, tag=f"expert slot {e} SwiGLU x route weight (own rows)")
        self.gather(L, [("ea", (m.k_exp + 1) * 2304, 2)], "expert_intermediate_gather")
        for e in range(m.k_exp + 1):
            fmt = "fp4" if e < m.k_exp else "fp8"
            self.mv(L, (e, "w2"), "linear_q", f"ea{e}", f"e{e}.d", 5120, 2304, fmt, tag=f"expert slot {e} w2")
        self.local(L, "moe_sum", tag="expert sum in id order, then shared (own rows)")
        self.gather(L, [("yf", 5120, 2)], "ffn_out_gather")
        self.local(L, "hc_post", which="ffn", tag="hc_post ffn")
        return self.ops

    def compile_head(self) -> list[dict]:
        self.local(-1, "final_norm", tag="final hc_pre + norm")
        self.mv(-1, "head.weight", "mv", "x", "logits", 129280, 5120, "bf16", out_dtype="fp32", tag="LM head")
        self.local(-1, "argmax_local", tag="local argmax (lowest id on ties)")
        self.emit(kind="topk_merge", unit="COLL", layer=-1, what="argmax", k=1, elems=TP, bytes=TP * 8,
                  tag="argmax merge")
        return self.ops


# ======================================================================================================================
# the state, sharded
# ======================================================================================================================
class State:
    """The reference decode state entering position ctx - 1 as arrays (LC.synthetic_state's generators, same order,
    same whole-state digest).  win[L]: the 127 synthetic window rows (every die's replicated copy starts from them);
    ckv[s], ik[s]: every compressed row / index key, with room for this token's appended group; slots[s]: the open
    group (position -> (kv, sc))."""

    def __init__(self, m, ctx, seed, layers):
        pos = ctx - 1
        h = hashlib.sha256()
        self.win, self.ckv, self.ik, self.n, self.slots, self.sha = {}, {}, {}, {}, {}, {}

        def rng_of(kind, L):
            return np.random.default_rng([seed, ctx, kind, L])
        for L in range(m.L):
            if L not in layers:
                continue
            g = m.lw(L, "attn.kv_norm.weight")
            rows = np.concatenate(list(LC._gained(rng_of(0, L), m.window - 1, m.hd, g)))
            rows = V.qdq_fp8(rows.reshape(-1)).reshape(m.window - 1, m.hd)
            self.win[L] = rows
            h.update(rows.tobytes())
            self.sha[f"win{L}"] = hashlib.sha256(rows.tobytes()).hexdigest()
        for s in m.kv_src:
            if not any(m.kv_of.get(L) == s for L in layers):
                continue
            r = m.ratio[s]
            n_prev = pos // r if r > 1 else pos
            gk = m.lw(s, "attn.compressor.norm.weight")
            gi = m.lw(s, "attn.indexer.k_norm.weight")
            ckv = np.empty((n_prev + 1, m.hd), dtype=F)
            ik = np.empty((n_prev + 1, m.ihd), dtype=F)
            i = 0
            for blk in LC._gained(rng_of(1, s), n_prev, m.hd, gk):
                ckv[i:i + len(blk)] = V.qdq_fp4_e4m3(blk.reshape(-1), 16).reshape(blk.shape)
                i += len(blk)
            i = 0
            for blk in LC._gained(rng_of(2, s), n_prev, m.ihd, gi):
                ik[i:i + len(blk)] = V.qdq_fp4_e8m0(blk.reshape(-1)).reshape(blk.shape)
                i += len(blk)
            h.update(ckv[:n_prev].tobytes())
            h.update(ik[:n_prev].tobytes())
            self.sha[f"ckv{s}"] = hashlib.sha256(ckv[:n_prev].tobytes()).hexdigest()
            self.sha[f"ik{s}"] = hashlib.sha256(ik[:n_prev].tobytes()).hexdigest()
            ckv[n_prev:] = np.nan
            ik[n_prev:] = np.nan
            self.ckv[s], self.ik[s], self.n[s] = ckv, ik, n_prev
            rng = rng_of(3, s)
            self.slots[s] = {}
            if r > 1 and pos % r:
                for p in range(pos - pos % r, pos):
                    kv = rng.standard_normal(m.hd).astype(F)
                    sc = rng.standard_normal(m.hd).astype(F)
                    self.slots[s][p] = (kv, sc)
                    h.update(kv.tobytes())
                    h.update(sc.tobytes())
        self.state_sha256 = h.hexdigest()


# ======================================================================================================================
# the ranks and the executor
# ======================================================================================================================
class Rank:
    def __init__(self, r):
        self.r = r
        self.mem: dict[str, np.ndarray] = {}
        self.ok: dict[str, np.ndarray] = {}
        self.win: dict[int, np.ndarray] = {}        # layer -> this die's window rows (oldest first)
        self.sel_rows: dict[int, np.ndarray] = {}   # kv source -> the gathered selected rows (head dies)
        self.cand = None                            # layer-20 keep flags of the blocks this die owns

    def alloc(self, name, n, dtype=F):
        self.mem[name] = np.zeros(n, dtype=dtype)
        self.ok[name] = np.zeros(n, dtype=bool)

    def put(self, name, vals, lo=0, n=None):
        vals = np.asarray(vals).reshape(-1)
        if name not in self.mem or (n is not None and self.mem[name].size != n):
            self.alloc(name, n if n is not None else vals.size, vals.dtype if vals.dtype != np.float64 else np.float64)
        self.mem[name][lo:lo + vals.size] = vals
        self.ok[name][lo:lo + vals.size] = True

    def get(self, name, lo=0, hi=None):
        if name not in self.mem:
            raise Defect(f"rank {self.r}: read of buffer {name} never written")
        hi = self.mem[name].size if hi is None else hi
        if not self.ok[name][lo:hi].all():
            raise Defect(f"rank {self.r}: read of unwritten elements of {name}[{lo}:{hi}]")
        return self.mem[name][lo:hi]

    def clear(self, keep=("h", "pre", "sel")):
        for k in [k for k in self.mem if k not in keep]:
            del self.mem[k], self.ok[k]


class Executor:
    def __init__(self, m, st: State, pos: int, hist, variant: str, log=print):
        self.m, self.st, self.pos, self.hist, self.variant, self.log = m, st, pos, hist, variant, log
        self.ranks = [Rank(r) for r in range(TP)]
        self.coll_log, self.sm_log = [], []
        self.fetch_log = []

    def ranks_of(self, spec):
        if spec == "all":
            return self.ranks
        if spec == "heads":
            return self.ranks[:HEAD_DIES]
        return [self.ranks[r] for r in spec]

    # -- weights: the rank's own rows only ------------------------------------------------------------------------
    def wrows(self, name, r0, r1):
        if isinstance(name, list):                    # a fused op over concatenated matrices
            parts, off = [], 0
            for nm in name:
                w = self.m.w[nm]
                n = w.shape[0]
                a, b = max(r0 - off, 0), min(r1 - off, n)
                if a < b:
                    parts.append(w[a:b])
                off += n
            return np.concatenate(parts) if parts else np.zeros((0, self.m.w[name[0]].shape[1]), dtype=F)
        w = self.m.w[name]
        if isinstance(w, V.Q8):
            return V.Q8(w.q[r0:r1], w.e[r0:r1])
        return w[r0:r1]

    def expert_name(self, slot, mat, L):
        ids = self.route_ids
        if slot < len(ids):
            return f"{self.m.P(L)}ffn.experts.{ids[slot]}.{mat}.weight"
        return f"{self.m.P(L)}ffn.shared_experts.{mat}.weight"

    # -- op dispatch ------------------------------------------------------------------------------------------------
    def run(self, ops):
        for op in ops:
            k = op["kind"]
            if k == "mv":
                self.op_mv(op)
            elif k == "local":
                for rk in self.ranks_of(op["ranks"]):
                    getattr(self, "f_" + op["fn"])(rk, op)
            elif k == "all_gather":
                self.op_gather(op)
            elif k == "all_reduce":
                self.op_reduce(op)
            elif k == "topk_merge":
                self.op_merge(op)
            elif k == "kv_gather":
                self.op_kv_gather(op)
            elif k == "expert_fetch":
                self.op_fetch(op)
            else:
                raise Defect(f"op {op['id']}: unknown kind {k}")

    def op_mv(self, op):
        L = op["layer"]
        w = op["w"]
        n = op["n"]
        rmax = 0
        for rk in self.ranks:
            r0, r1 = op["rows"][rk.r]
            if r1 <= r0:
                continue
            rmax = max(rmax, r1 - r0)
            fn = op["fn"]
            if isinstance(w, list) and len(w) == 2 and isinstance(w[0], int):
                w = tuple(w)
            name = self.expert_name(w[0], w[1], L) if isinstance(w, tuple) else w
            if fn == "wo_a":                            # grouped: row n of group n // 1024 reads o[g * 4096 ...]
                full = self.m.w[name]
                x = rk.get(op["x"])
                out = np.empty(r1 - r0, dtype=F)
                for g in range(r0 // 1024, (r1 - 1) // 1024 + 1):
                    a, b = max(r0, g * 1024), min(r1, (g + 1) * 1024)
                    out[a - r0:b - r0] = V.matvec_c(full[a:b], x[g * 4096:(g + 1) * 4096], V.WO_A_SPLIT)
                out = G.to_bf16(out)
            elif fn == "wo_a_part":                     # K-split: the die's head's 512 columns, its group's rows
                full = self.m.w[name]
                h = rk.r
                x = rk.get("o_own")
                j = h % 8
                out = V.csum(G.mul(np.asarray(full[r0:r1, j * 512:(j + 1) * 512], dtype=F), G.to_bf16(x)[None, :]))
            else:
                x = rk.get(op["x"])
                wr = self.wrows(name, r0, r1)
                if fn == "linear_q":
                    out = V.linear_q(wr, x)
                elif fn == "mv":
                    out = V.mv(wr, x)
                elif fn == "linear_bf16":
                    out = V.linear_bf16(wr, x)
                else:
                    raise Defect(f"op {op['id']}: unknown matvec fn {fn}")
            rk.put(op["out"], out, lo=r0, n=n)
        self.sm_log.append(dict(op=op["id"], layer=L, tag=op["tag"], n=n, k=op["k"], fmt=op["fmt"],
                                rows_per_die_max=int(rmax)))

    def op_gather(self, op):
        for name in op["bufs"]:
            seg = []
            for rk in self.ranks:
                if name in rk.mem:
                    seg.append((rk.r, rk.ok[name].copy(), rk.mem[name].copy()))
            if not seg:
                raise Defect(f"op {op['id']}: gather of {name} that no rank wrote")
            n = seg[0][2].size
            full = np.zeros(n, dtype=seg[0][2].dtype)
            have = np.zeros(n, dtype=bool)
            for r, ok, v in seg:
                if (have & ok).any():
                    raise Defect(f"op {op['id']}: {name} written by two ranks")
                full[ok] = v[ok]
                have |= ok
            if not have.all():
                raise Defect(f"op {op['id']}: gather of {name} with {int((~have).sum())} elements unwritten")
            for rk in self.ranks_of(op["dest"]):
                rk.put(name, full, n=n)
        self.coll_log.append(dict(op=op["id"], layer=op["layer"], kind="all_gather", tag=op["tag"],
                                  elems=op["elems"], bytes=op["bytes"]))

    def op_reduce(self, op):
        n = op["elems"]
        z = np.zeros(n, dtype=F)
        for g in range(op["groups"]):
            parts = [self.ranks[g * 8 + j].get(op["buf"], g * 1024, (g + 1) * 1024) for j in range(8)]
            while len(parts) > 1:
                parts = [G.add(parts[i], parts[i + 1]) for i in range(0, len(parts), 2)]
            z[g * 1024:(g + 1) * 1024] = parts[0]
        z = G.to_bf16(z)
        for rk in self.ranks:
            rk.put(op["out"], z, n=n)
        self.coll_log.append(dict(op=op["id"], layer=op["layer"], kind="all_reduce", tag=op["tag"],
                                  elems=n, bytes=op["bytes"]))

    def op_merge(self, op):
        what = op["what"]
        vals, idx = [], []
        for rk in self.ranks:
            v, i = rk.get(f"{what}_v"), rk.get(f"{what}_i")
            vals.append(v)
            idx.append(i)
        v, i = np.concatenate(vals), np.concatenate(idx).astype(np.int64)
        if what == "argmax":                          # max, lowest id on ties
            order = np.lexsort((i, -v.astype(np.float64)))
            for rk in self.ranks:
                rk.put("token", np.array([i[order[0]]], dtype=np.int64))
        else:
            order = np.lexsort((i, -v.astype(np.float64)))[:op["k"]]
            for rk in self.ranks:
                rk.put(f"{what}_mv", v[order].astype(np.float64), n=len(order))
                rk.put(f"{what}_mi", i[order], n=len(order))
            if what == "sel":
                s = np.sort(i[order])
                for rk in self.ranks:
                    rk.put("sel", s, n=len(s))
        self.coll_log.append(dict(op=op["id"], layer=op["layer"], kind="topk_merge", tag=op["tag"],
                                  elems=op["elems"], bytes=op["bytes"]))

    def op_kv_gather(self, op):
        s = op["src"]
        sel = self.ranks[0].get("sel").astype(np.int64)
        own = key_owner(sel)
        rows = np.empty((len(sel), self.m.hd), dtype=F)
        for rk in self.ranks:                         # each owner contributes only rows it holds
            mine = own == rk.r
            rows[mine] = self.st.ckv[s][sel[mine]]
        if np.isnan(rows).any():
            raise Defect(f"op {op['id']}: a selected compressed row was never written")
        for rk in self.ranks_of(op["dest"]):
            rk.sel_rows[s] = rows.copy()
        self.coll_log.append(dict(op=op["id"], layer=op["layer"], kind="kv_gather", tag=op["tag"],
                                  elems=op["elems"], bytes=op["bytes"]))

    def op_fetch(self, op):
        L = op["layer"]
        tot = 0
        for slot in range(len(self.route_ids)):
            for mat in ("w1", "w3", "w2"):
                raw, _, shape = self.m.w.ck.raw(self.expert_name(slot, mat, L))
                tot += raw.size
                sc = self.expert_name(slot, mat, L)[:-len(".weight")] + ".scale"
                tot += self.m.w.ck.raw(sc)[0].size
        self.fetch_log.append(dict(op=op["id"], layer=L, experts=list(self.route_ids),
                                   bytes_total=int(tot), bytes_per_die=int(-(-tot // TP))))

    # -- local functions (the golden's own arithmetic on the rank's buffers) -----------------------------------------
    def f_engram_fetch(self, rk, op):
        m, L = self.m, op["layer"]
        li = m.engram.layer_ids.index(L)
        ids = m.engram.hashes(self.hist, li).reshape(-1)
        codes, sc = m.emb_codes[L]
        mine = np.nonzero(ids % TP == rk.r)[0]
        width = codes.shape[1]
        rk.alloc("eg_rows", len(ids) * width)
        for t in mine:
            rk.put("eg_rows", V.decode_engram_rows(codes, sc, ids[t:t + 1]).reshape(-1), lo=int(t) * width)

    def f_engram_mix(self, rk, op):
        m, L = self.m, op["layer"]
        h = rk.get("h").reshape(m.hc, m.dim)
        kv = rk.get("eg_kv")
        key = kv[:m.hc * m.dim].reshape(m.hc, m.dim)
        value = kv[m.hc * m.dim:]
        wgt = G.mul(m.lw(L, "engram.q_weight"), m.lw(L, "engram.k_weight"))
        out = []
        for j in range(m.hc):
            hj, kj = h[j], key[j]
            nn = F(m.dim)
            rstd = G.mul(G.rsqrt(G.add(V.div(V.reduce_sum_c(G.mul(hj, hj)), nn), m.eps)),
                         G.rsqrt(G.add(V.div(V.reduce_sum_c(G.mul(kj, kj)), nn), m.eps)))
            dot = G.mul(G.mul(V.reduce_sum_c(G.mul(G.mul(hj, wgt[j]), kj)), rstd), m.engram_scale)
            mag = V.sqrt(np.maximum(np.abs(dot), F(1e-6)).astype(F))
            gate = V.sigmoid(np.where(dot < 0, G.neg(mag), mag).astype(F))
            out.append(G.add(hj, G.mul(gate, value)))
        rk.put("h", G.to_bf16(np.stack(out)))
        rk.put("engram_h", rk.get("h"))

    def f_hc_mixes(self, rk, op):
        m = self.m
        h = rk.get("h").reshape(m.hc, m.dim)
        pre, post, comb = m.hc_mixes(h, op["layer"], op["which"])
        w = op["which"]
        rk.put(f"{w}_pre", pre)
        rk.put(f"{w}_post", post)
        rk.put(f"{w}_comb", comb)
        rk.put(f"{w}_res", h)

    def f_hc_pre_norm(self, rk, op):
        m, L = self.m, op["layer"]
        h = rk.get("h").reshape(m.hc, m.dim)
        if op["which"] == "attn":
            pre, nw = rk.get("pre"), "attn_norm.weight"
        else:
            pre, nw = rk.get("attn_pre"), "ffn_norm.weight"
        x = V.rmsnorm_fold(m.hc_pre(h, pre), m.lw(L, nw), m.eps)
        rk.put("x", x)
        rk.put(f"{op['which']}_x", x)

    def f_q_norm_kv_row(self, rk, op):
        m, L = self.m, op["layer"]
        cs = self.cs(L)
        rk.put("qr", V.rmsnorm_fold(rk.get("qa"), m.lw(L, "attn.q_norm.weight"), m.eps))
        kv = V.rmsnorm_bf16(rk.get("kvraw"), m.lw(L, "attn.kv_norm.weight"), m.eps)
        row = V.qdq_fp8(V.rope_tail(kv, cs))
        rk.put("win_new", row)
        rk.win[L] = np.concatenate([self.st.win[L], row[None, :]])[-m.window:]

    def cs(self, L):
        return V.rope_cs(self.m.freqs_yarn if self.m.ratio[L] > 0 else self.m.freqs_plain, self.pos)

    def f_q_rope(self, rk, op):
        h = rk.r
        q = rk.get("q", h * 512, (h + 1) * 512)
        rk.put("q_own", V.rope_tail(q.reshape(1, 512), self.cs(op["layer"])).reshape(-1))

    def f_compressor(self, rk, op):
        m, L, st = self.m, op["layer"], self.st
        r = m.ratio[L]
        grp = op["group"]
        if int(key_owner(grp)) != rk.r:
            raise Defect(f"compressor of group {grp} on rank {rk.r}, owner {int(key_owner(grp))}")
        if r == 1:
            latent = V.rmsnorm_bf16(rk.get("cmp"), m.lw(L, "attn.compressor.norm.weight"), m.eps)
        else:
            kv, sc = np.split(rk.get("cmp"), 2)
            slots = st.slots[L]
            slots[self.pos] = (kv, sc)
            if not op["closes"]:
                return
            ps = sorted(slots)
            kvs, scs = np.stack([slots[p][0] for p in ps]), np.stack([slots[p][1] for p in ps])
            mx = np.max(scs, axis=0)
            e = G.exp(G.add(scs, G.neg(mx)))
            p = V.div(e, V.seqsum(list(e))[None, :])
            pooled = V.seqsum([G.mul(kvs[i], p[i]) for i in range(r)])
            latent = V.rmsnorm_bf16(G.to_bf16(pooled), m.lw(L, "attn.compressor.norm.weight"), m.eps)
            st.slots[L] = {}
        gcs = V.rope_cs(m.freqs_yarn, self.pos + 1 - r)
        k = V.rmsnorm_bf16(V.linear_bf16(m.lw(L, "attn.indexer.wk.weight"), latent),
                           m.lw(L, "attn.indexer.k_norm.weight"), m.eps)
        if st.n[L] != grp:
            raise Defect(f"compressor appends group {grp} but the store holds {st.n[L]}")
        st.ik[L][grp] = V.qdq_fp4_e8m0(V.rope_tail(k, gcs))
        st.ckv[L][grp] = V.qdq_fp4_e4m3(V.rope_tail(latent, gcs), 16)
        st.n[L] = grp + 1
        rk.put("new_ik", st.ik[L][grp])
        rk.put("new_ckv", st.ckv[L][grp])

    def f_index_q(self, rk, op):
        m, L = self.m, op["layer"]
        q = V.rope_tail(rk.get("iq").reshape(m.ih, m.ihd), V.rope_cs(m.freqs_yarn, self.pos))
        rk.put("iqf", np.stack([V.qdq_fp4_e8m0(q[h]) for h in range(m.ih)]))
        rk.put("iw", G.to_bf16(G.mul(rk.get("iwr"), m.index_w_scale)))

    def owned(self, rk, n):
        """The global indices of the keys < n this die owns (blocks of KEY_BLOCK, round robin)."""
        blocks = np.arange(rk.r, -(-n // KEY_BLOCK), TP)
        idx = (blocks[:, None] * KEY_BLOCK + np.arange(KEY_BLOCK)[None, :]).reshape(-1)
        return idx[idx < n]

    def f_index_scores(self, rk, op):
        m = self.m
        n, s = op["n"], op["src"]
        if self.st.n[s] < n:
            raise Defect(f"index scores over {n} keys of source {s}, store holds {self.st.n[s]}")
        idx = self.owned(rk, n)
        q, wts = rk.get("iqf").reshape(m.ih, m.ihd), rk.get("iw")
        out = np.empty(len(idx), dtype=np.float64)
        CH = 1 << 14
        for a in range(0, len(idx), CH):
            keys = self.st.ik[s][idx[a:a + CH]]
            score = G.to_bf16(V.dots_q4(q, keys))
            terms = G.to_bf16(G.mul(np.maximum(score, F(0)), wts[:, None]))
            out[a:a + CH] = G.to_bf16(V.reduce_rows(terms.T, cls="idx")).astype(np.float64)
        rk.put("is_i", idx.astype(np.int64), n=len(idx))
        rk.put("is_v", out, n=len(idx))

    def f_cand_local(self, rk, op):
        m, n = self.m, op["n"]
        b = m.cand_b
        assert b == KEY_BLOCK
        idx, v = rk.get("is_i"), rk.get("is_v")
        nb = -(-n // b)
        blocks = np.arange(rk.r, nb, TP)
        bs = np.full(len(blocks), -np.inf)
        pos_in = {int(bk): j for j, bk in enumerate(blocks)}
        bj = np.array([pos_in[int(i) // b] for i in idx], dtype=np.int64) if len(idx) else np.zeros(0, np.int64)
        np.maximum.at(bs, bj, v)
        bs[blocks == (n - 1) // b] = np.inf
        k = min(m.cand_k, nb, len(blocks))
        order = np.lexsort((blocks, -bs))[:k]
        rk.put("cand_v", bs[order], n=k)
        rk.put("cand_i", blocks[order].astype(np.int64), n=k)
        rk.put("cand_blocks", blocks.astype(np.int64), n=len(blocks))

    def f_cand_apply(self, rk, op):
        mv, mi = rk.get("cand_mv"), rk.get("cand_mi")
        keep_blocks = set(int(i) for i, v in zip(mi, mv) if v > -np.inf)
        blocks = rk.get("cand_blocks")
        rk.cand = {int(bk): (int(bk) in keep_blocks) for bk in blocks}

    def f_cand_mask(self, rk, op):
        idx, v = rk.get("is_i"), rk.get("is_v")
        if rk.cand is None:
            raise Defect("candidate mask before layer 20's candidates")
        keep = np.array([rk.cand[int(i) // KEY_BLOCK] for i in idx], dtype=bool)
        rk.put("is_v", np.where(keep, v, -np.inf), n=len(v))

    def f_topk_local(self, rk, op):
        idx, v = rk.get("is_i"), rk.get("is_v")
        k = min(op["k"], len(idx))
        order = np.lexsort((idx, -v))[:k]
        rk.put("sel_v", v[order], n=k)
        rk.put("sel_i", idx[order], n=k)

    def f_attend(self, rk, op):
        m, L = self.m, op["layer"]
        h = rk.r
        cs = self.cs(L)
        rows = rk.win[L]
        if op["yarn"]:
            rows = np.concatenate([rows, rk.sel_rows[m.kv_of[L]]])
        q = rk.get("q_own").reshape(1, m.hd)
        sink = m.lw(L, "attn.attn_sink")[h:h + 1]
        s = G.mul(V.dots(q, rows), m.attn_scale)
        mb = np.max(s, axis=1)
        e = G.exp(G.add(s, G.neg(mb)[:, None]))
        pv = V.dots(G.to_bf16(e), rows.T)
        den = V.reduce_rows(e)
        den = G.add(den, G.exp(G.add(sink, G.neg(mb))))
        o = G.to_bf16(V.div(pv, den[:, None]))
        o = V.rope_tail(o, cs, inverse=True).reshape(-1)
        rk.put("o", o, lo=h * 512, n=32768)
        rk.put("o_own", o)

    def f_hc_post(self, rk, op):
        m = self.m
        w = op["which"]
        y = rk.get("y" if w == "attn" else "yf")
        h = m.hc_post(y, rk.get(f"{w}_res").reshape(m.hc, m.dim), rk.get(f"{w}_post"),
                      rk.get(f"{w}_comb").reshape(m.hc, m.hc))
        rk.put("h", h)
        if w == "ffn":
            rk.put("pre", rk.get("ffn_pre"))

    def f_router_act(self, rk, op):
        r0, r1 = even(384)[rk.r]
        if r1 > r0:
            rk.put("gsc", V.sqrt(V.softplus(rk.get("gsc", r0, r1))), lo=r0)

    def f_route(self, rk, op):
        m, L = self.m, op["layer"]
        scores = rk.get("gsc")
        bi = G.add(scores, m.lw(L, "ffn.gate.bias"))
        rk.put("router", bi)
        ids = sorted(int(i) for i in V.topk_lowest_index(bi, m.k_exp))
        total = V.seqsum([scores[i] for i in ids])
        den = G.add(total, F(1e-20))
        wg = [G.mul(V.div(scores[i], den), m.route_scale) for i in ids]
        rk.put("route_ids", np.array(ids, dtype=np.int64))
        rk.put("route_w", np.array(wg, dtype=F))
        if rk.r == 0:
            self.route_ids = ids
        elif ids != self.route_ids:
            raise Defect(f"rank {rk.r} routed {ids}, rank 0 {self.route_ids}")

    def f_swiglu(self, rk, op):
        m = self.m
        e = op["slot"]
        r0, r1 = even(2304)[rk.r]
        g, u = rk.get(f"e{e}.g", r0, r1), rk.get(f"e{e}.u", r0, r1)
        u = np.clip(u, -m.limit, m.limit).astype(F)
        g = np.minimum(g, m.limit).astype(F)
        a = G.mul(V.silu(g), u)
        if e < m.k_exp:
            a = G.mul(rk.get("route_w")[e], a)
        rk.put("ea", G.to_bf16(a), lo=e * 2304 + r0, n=(m.k_exp + 1) * 2304)
        if e == m.k_exp:                               # the gathered buffer is split per slot for the w2 inputs
            pass

    def f_moe_sum(self, rk, op):
        m = self.m
        r0, r1 = even(5120)[rk.r]
        y = np.zeros(r1 - r0, dtype=F)
        for e in range(m.k_exp + 1):
            y = G.add(y, rk.get(f"e{e}.d", r0, r1))
        rk.put("yf", G.to_bf16(y), lo=r0, n=5120)

    def f_final_norm(self, rk, op):
        m = self.m
        h = rk.get("h").reshape(m.hc, m.dim)
        rk.put("x", V.rmsnorm_fold(m.hc_pre(h, rk.get("pre")), m.w["norm.weight"], m.eps))

    def f_argmax_local(self, rk, op):
        r0, r1 = even(129280)[rk.r]
        lg = rk.get("logits", r0, r1)
        j = int(np.argmax(lg))
        rk.put("argmax_v", np.array([lg[j]], dtype=F))
        rk.put("argmax_i", np.array([r0 + j], dtype=np.int64))

    # the w2 inputs: slot e's 2,304 intermediates, split out of the gathered buffer
    def split_ea(self):
        m = self.m
        for rk in self.ranks:
            ea = rk.get("ea")
            for e in range(m.k_exp + 1):
                rk.put(f"ea{e}", ea[e * 2304:(e + 1) * 2304])


# ======================================================================================================================
# driver: per layer compile, execute, check
# ======================================================================================================================
def check(name, want, got_per_rank, tol_nan=False):
    want = np.asarray(want)
    res = []
    for r, got in got_per_rank:
        got = np.asarray(got)
        if want.dtype == np.float64 or got.dtype == np.float64:
            same = got.shape == want.shape and np.array_equal(got.astype(np.float64), want.astype(np.float64))
            bad = None if same else int(np.argmax(got.reshape(-1) != want.reshape(-1))) if got.shape == want.shape \
                else -1
        else:
            gb, wb = G.bits(np.asarray(got, dtype=F).reshape(-1)), G.bits(np.asarray(want, dtype=F).reshape(-1))
            same = gb.shape == wb.shape and np.array_equal(gb, wb)
            bad = None if same else (int(np.nonzero(gb != wb)[0][0]) if gb.shape == wb.shape else -1)
        res.append((r, same, bad))
    ok = all(s for _, s, _ in res)
    return dict(region=name, bit_exact=ok, ranks_checked=len(res),
                first_bad=[dict(rank=r, index=b) for r, s, b in res if not s][:3])


def run(layers, head, variant, log=print, program_out=None):
    ref = json.loads(REF_RECORD.read_text())
    ctx, seed = ref["context"], ref["seed"]
    assert (ctx, seed) == (REF_CTX, REF_SEED)
    pos = ctx - 1
    hist = list(ref["token_history"])
    ck = LC.Checkpoint()
    t0 = time.time()
    m, init_sha = LC.build_model(ck, engram=any(L in (1, 14) for L in layers))
    need = set(layers)
    t1 = time.time()
    st = State(m, ctx, seed, need)
    log(f"state built {time.time() - t1:.0f} s: {st.n}")
    state_check = None
    if need == set(range(m.L)):
        want = json.loads(ref["state"].replace("'", '"')) if isinstance(ref["state"], str) else ref["state"]
        state_check = dict(state_sha256=st.state_sha256, record=want.get("state_sha256"),
                           match=st.state_sha256 == want.get("state_sha256"))
        if not state_check["match"]:
            raise SystemExit(f"synthetic state digest {st.state_sha256} != reference {want.get('state_sha256')}")
    ex = Executor(m, st, pos, hist, variant, log)
    first = layers[0]
    if first == 0:
        h = np.repeat(ck.rows("embed.weight", [hist[-1]]), m.hc, axis=0).astype(F)
        pre = np.array([1, 0, 0, 0], dtype=F)
    else:
        prev = np.load(REF_SHARDS / f"ctx{ctx}_L{first - 1:02d}.npz")
        h, pre = prev["h_out"], prev["pre_out"]
        carry = json.loads((REF_SHARDS / f"ctx{ctx}_L{first - 1:02d}.json").read_text())["ctx_out"]
        for s in m.kv_src:                       # rows the golden appended at earlier layers
            if s < first and s in st.n:
                z = np.load(REF_SHARDS / f"ctx{ctx}_L{s:02d}.npz")
                if f"ckv{s}" in z.files:
                    g = st.n[s]
                    st.ckv[s][g], st.ik[s][g] = z[f"ckv{s}"], z[f"ik{s}"]
                    st.n[s] = g + 1
                    st.slots[s] = {}
        if "sel" in carry:
            for rk in ex.ranks:
                rk.put("sel", np.array(carry["sel"], dtype=np.int64))
        if "cand_file" in carry:
            cand = np.load(REF_SHARDS / carry["cand_file"])["cand"]
            for rk in ex.ranks:
                nb = -(-len(cand) // KEY_BLOCK)
                rk.cand = {int(b): bool(cand[b * KEY_BLOCK]) for b in range(rk.r, nb, TP)}
    for rk in ex.ranks:
        rk.put("h", h)
        rk.put("pre", pre)
    program, results = [], []
    for L in layers:
        tl = time.time()
        comp = Compiler(m, pos, variant)
        ops = comp.compile_layer(L, first=(L == first))
        program.append(dict(layer=L, ops=ops))
        z = np.load(REF_SHARDS / f"ctx{ctx}_L{L:02d}.npz")
        js = json.loads((REF_SHARDS / f"ctx{ctx}_L{L:02d}.json").read_text())
        rin = [check("input", z["h_in"], [(rk.r, rk.get("h")) for rk in ex.ranks]),
               check("input_pre", z["pre_in"], [(rk.r, rk.get("pre")) for rk in ex.ranks])]
        ncoll0 = len(ex.coll_log)
        # execute, splitting the gathered expert intermediates for the w2 ops
        split_at = next(o["id"] for o in ops if o["kind"] == "all_gather" and o["tag"] == "expert_intermediate_gather")
        defect = None
        try:
            ex.run(ops[:split_at + 1])
            ex.split_ea()
            ex.run(ops[split_at + 1:])
        except Defect as e:
            defect = str(e)
            log(f"L{L} DEFECT {e}")
        R = ex.ranks
        regs = list(rin)
        if defect is None:
            if f"L{L}.engram" in z.files:
                regs.append(check(f"L{L}.engram", z[f"L{L}.engram"], [(rk.r, rk.get("engram_h")) for rk in R]))
            regs += [check(f"L{L}.attn_norm", z[f"L{L}.attn_norm"], [(rk.r, rk.get("attn_x")) for rk in R]),
                     check(f"win{L}", z[f"win{L}"], [(rk.r, rk.get("win_new")) for rk in R]),
                     check(f"L{L}.attn", z[f"L{L}.attn"], [(rk.r, rk.get("y")) for rk in R]),
                     check(f"L{L}.ffn_norm", z[f"L{L}.ffn_norm"], [(rk.r, rk.get("ffn_x")) for rk in R]),
                     check(f"L{L}.router", z[f"L{L}.router"], [(rk.r, rk.get("router")) for rk in R]),
                     check(f"L{L}.ffn", z[f"L{L}.ffn"], [(rk.r, rk.get("yf")) for rk in R]),
                     check(f"block{L}", z[f"block{L}"], [(rk.r, rk.get("h")) for rk in R]),
                     check(f"pre{L}", z[f"pre{L}"], [(rk.r, rk.get("pre")) for rk in R])]
            for s in m.kv_src:
                if f"ckv{s}" in z.files:
                    owner = [rk for rk in R if "new_ckv" in rk.mem]
                    regs.append(check(f"ckv{s}", z[f"ckv{s}"], [(rk.r, rk.get("new_ckv")) for rk in owner]))
                    regs.append(check(f"ik{s}", z[f"ik{s}"], [(rk.r, rk.get("new_ik")) for rk in owner]))
            if f"L{L}.index_scores" in z.files:
                want = z[f"L{L}.index_scores"]
                got = np.full(len(want), np.nan)
                for rk in R:
                    if "is_v" in rk.mem:
                        pass
                # the scores the dies computed (before the candidate mask, which the golden applies first too)
                for rk in R:
                    got[rk.get("is_i")] = rk.get("is_v")
                regs.append(check(f"L{L}.index_scores", want, [(-1, got)]))
            if js.get("index_select_sha256"):
                sel = R[0].get("sel").astype(np.int64)
                ok = hashlib.sha256(sel.tobytes()).hexdigest() == js["index_select_sha256"] and \
                    all(np.array_equal(rk.get("sel"), R[0].get("sel")) for rk in R)
                regs.append(dict(region=f"L{L}.index_select", bit_exact=bool(ok), ranks_checked=TP, first_bad=[]))
            regs.append(dict(region=f"L{L}.experts", bit_exact=ex.route_ids == js["experts"], ranks_checked=TP,
                             first_bad=[] if ex.route_ids == js["experts"] else [dict(got=ex.route_ids,
                                                                                         want=js["experts"])]))
        ok = defect is None and all(x["bit_exact"] for x in regs)
        colls = ex.coll_log[ncoll0:]
        results.append(dict(layer=L, kind=js["kind"], verdict="pass" if ok else "fail", defect=defect,
                            regions=regs, experts=js["experts"], collectives=len(colls),
                            collective_bytes=int(sum(c["bytes"] for c in colls)),
                            ops=len(ops), wall_s=round(time.time() - tl, 1)))
        log(f"L{L:02d} {js['kind']:28s} {'PASS' if ok else 'FAIL'} collectives {len(colls)} "
            f"({sum(c['bytes'] for c in colls)} B) ops {len(ops)} {time.time() - tl:.0f} s"
            + ("" if ok else f"  bad: {[x['region'] for x in regs if not x['bit_exact']]}"))
        for k in [k for k in m.w if k.startswith(f"layers.{L}.")]:
            del m.w[k]
        for rk in R:
            rk.clear(keep=("h", "pre", "sel"))
        if not ok:
            break
    head_res = None
    if head and results and all(r["verdict"] == "pass" for r in results) and layers[-1] == m.L - 1:
        comp = Compiler(m, pos, variant)
        ops = comp.compile_head()
        program.append(dict(layer="head", ops=ops))
        ex.run(ops)
        lg = np.zeros(129280, dtype=F)
        for rk in ex.ranks:
            r0, r1 = even(129280)[rk.r]
            lg[r0:r1] = rk.get("logits", r0, r1)
        tok = int(ex.ranks[0].get("token")[0])
        head_res = dict(next_token=tok, reference_next_token=ref["next_token"],
                        logits_sha256=LC.digest(lg), reference_logits_sha256=ref["logits_sha256"],
                        verdict="pass" if tok == ref["next_token"] and LC.digest(lg) == ref["logits_sha256"]
                        else "fail", tokens_agree_all_ranks=all(int(rk.get("token")[0]) == tok for rk in ex.ranks))
        log(f"head: token {tok} (reference {ref['next_token']}) logits "
            f"{'BIT-EXACT' if head_res['verdict'] == 'pass' else 'MISMATCH'}")
    if program_out:
        Path(program_out).write_text(json.dumps(dict(schema=SCHEMA + ".program", tp=TP, head_dies=HEAD_DIES,
                                                      key_block=KEY_BLOCK, position=pos, variant=variant,
                                                      layers=program), default=list) + "\n")
    return dict(context=ctx, position=pos, seed=seed, variant=variant, state_check=state_check, layers=results,
                head=head_res, collectives=ex.coll_log, sm_ops=ex.sm_log, expert_fetch=ex.fetch_log,
                model_init_sha256=init_sha)


SOURCES = ("tools/w19_hbm_tp96_isa.py", "tools/hdc_golden_v41.py", "tools/hdc_golden.py",
           "tools/rtl_v41_fullshape_layer_campaign.py", "results/rtl/w17_v41_1m_reference_token.json",
           "compiler/models/deepseek-v4.1-flash/inference_config.json")


def parse_layers(s):
    out = []
    for part in s.split(","):
        a, _, b = part.partition("-")
        out += list(range(int(a), int(b or a) + 1))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--layers", default="0")
    ap.add_argument("--head", action="store_true")
    ap.add_argument("--variant", default="gather", choices=("gather", "oreduce"))
    ap.add_argument("--record", type=Path)
    ap.add_argument("--program-out", type=Path)
    a = ap.parse_args()
    if V.ARITH != "chunk8":
        raise SystemExit("HDC_V41_ARITH must be chunk8 (the reference token's contract)")
    layers = parse_layers(a.layers)
    t0 = time.time()
    res = run(layers, a.head, a.variant, program_out=a.program_out)
    res["wall_s"] = round(time.time() - t0, 1)
    passed = all(r["verdict"] == "pass" for r in res["layers"]) and len(res["layers"]) == len(layers) and \
        (res["head"] is None or res["head"]["verdict"] == "pass")
    print(f"{'PASS' if passed else 'FAIL'}: {len(res['layers'])} layers, head {res['head']}")
    if a.record:
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
        key = f"{a.variant}:L{a.layers}" + (":head" if a.head else "")
        rec = dict(schema=SCHEMA, status="pass" if passed else "fail")
        old = json.loads(a.record.read_text()) if a.record.exists() else {}
        runs = dict(old.get("runs", {}))
        if key in runs and runs[key]["status"] == "fail":
            old.setdefault("failed_runs", []).append(runs[key])      # failed verdicts are never overwritten
        runs[key] = dict(status=rec["status"], generated_utc=datetime.datetime.now(datetime.timezone.utc)
                         .strftime("%Y-%m-%dT%H:%M:%SZ"), source_commit=head, arith=V.ARITH,
                         source_sha256={s: sha(ROOT / s) for s in SOURCES}, result=res)
        rec.update(claim_boundary="ISA-level (op-program) execution of the TP-96 V4.1 HBM-comparator decode token "
                                  "on 96 ranks against the released-checkpoint golden (W17 reference state, seed "
                                  "20260930 at 1M). Matvec arithmetic is the golden's on each rank's own output "
                                  "rows; dataflow, ownership, collectives and merges are the program's. No RTL, "
                                  "cycle, or physical verdict.",
                   runs=runs, failed_runs=old.get("failed_runs", []),
                   reproduction="HDC_V41_ARITH=chunk8 python3 tools/w19_hbm_tp96_isa.py --layers 0-39 --head "
                                "--variant V --record OUT (needs the released checkpoint and the W17 reference "
                                "shards at /home/ubuntu/w17work/ref/ctx1048576_seed20260930)")
        rec["status"] = "pass" if all(v["status"] == "pass" for v in runs.values()) else "fail"
        a.record.write_text(json.dumps(rec, indent=1, default=int) + "\n")
        print("wrote", a.record)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
