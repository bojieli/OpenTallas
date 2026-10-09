"""DFlash (z-lab/Qwen3-8B-DFlash-b16) on the generic HBM die through HGI-1: one speculative STEP per doorbell.

A step is one doorbell {token = anchor (the last committed token), pos = its position}; it runs

  1. counts      DMA.LOAD of the U32 count table T[q] = q at POS + 1 + s (ibcast, one row per slot): the N_FROM_VM
                 I tables that carry pos + s + 1 (slot s's causal row count) -- no slot DYN bank is needed;
  2. draft ctx   the drafter's context K/V for the B most recent committed positions [pos - B, pos): the captured
                 target features (layers 1, 9, 17, 25, 33; BF16 rows in HBM CTXF) -> fc (5 K-blocks of 4,096, SM fmt 0,
                 the die's 1/TP output rows, partials added pairwise by the SU) -> COLL.ALL_GATHER -> hidden_norm ->
                 per drafter layer k/v projection (SM fmt 0), k_norm, RoPE at the row's position, DMA.STORE to the
                 drafter KV cache (BF16).  Rewriting rows that are already there writes the same values (they are
                 committed), so the step needs no "last step's accept count";
  3. draft block slot 0 = embed(anchor) (TOKEN), slots 1..B-1 = embed(mask 151,669) (static row); 5 drafter layers
                 (BF16 weights, no row scale) with NON-CAUSAL attention: every slot sees the drafter context rows
                 [0, pos) (ATT B, n_sel = POS) followed by the block's own B rows (ATT C, static n = B, HBM scratch
                 DBLK); final norm; the TARGET LM head (INT8 + row scale) for slots 1..B-1, <= 4 slots a head pass
                 (VM holds 4 x 37,984 logits); ARGMAX.LOCAL + COLL.ARGMAX_MERGE per slot -> draft ids D (U32);
  4. verify      the target over B slots (anchor, D[1..B-1]) at positions pos..pos+B-1: every weight matrix in
                 SM.MATVEC passes of <= 8 slots (param [4:2] = P - 1); per slot RoPE row and KV append at
                 POS + s (static offset); attention per KV head over groups of G slots (16 lanes = 4 q heads x 4
                 slots): ATT B = rows [0, pos) (n_sel POS) + C = block rows [pos, pos + s_last + 1) (static n), then
                 a per-slot SU softmax over its own count (N_FROM_VM) and +0 written over the slot's masked tail
                 (rows pos+s+1 .. pos+s_last) so the group's PV equals each slot's own causal PV bit for bit;
                 captures X of layers [1,9,17,25,33] for all slots to CTXF (BF16); head as in 3 -> POST (U32);
  5. accept      D[1..B-1] and POST[0..B-2] stored (U32) and reloaded as INT8 bytes; SU: sum of squared byte
                 differences per id, min(., 1) -> mismatch flags; a leading 0 and a trailing 1; ARGMAX.LOCAL (lowest
                 index on ties, imm_a 0) gives k = a + 1 = committed tokens; POST[0..k-1] are the committed tokens;
  6. TOKX        PROPOSED CTL.TOKX (SPEC_GAP Q-MTP-1): A[0] = k, A[1..k] = tokens -> k completion beats; END.

KV rollback is free: rejected rows at >= pos + k are never read (every count is pos-derived) and the next step
overwrites them.  The host rings the next step with {POST[k-1], pos + k}.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hbm_generic_iface as HGI  # noqa: E402
import hdc_isa_v41 as I  # noqa: E402

from . import qwen_compiler as QC  # noqa: E402
from .records import DYN, MDesc, Rec  # noqa: E402

F = np.float32
TP = QC.TP
NSEL = HGI.NSEL_FROM_VM
MASK_ID = 151669
SM_MAX_SLOTS = 8              # SM.MATVEC param [4:2]: one weight read serves <= 8 slots
HEAD_SLOTS = 4                # VM: 4 x 37,984 FP32 logits a head pass (TP4)
NL = 64                       # replicated count words per I table (>= the largest LOOP count)


def al(n, a=32):
    return -(-n // a) * a


class DGeom:
    """Shapes and maps of one DFlash step on one die (TP4).  cfg: target config; dcfg: drafter config."""

    def __init__(self, cfg, dcfg, ctx, B, G=None):
        self.t = QC.Geometry(cfg, ctx)
        t = self.t
        self.B, self.ctx = B, ctx
        self.H, self.HD, self.nq, self.nk, self.ff, self.hrows = t.H, t.HD, t.nq, t.nk, t.ff, t.hrows
        self.grp = self.nq // self.nk
        self.G = G or max(1, min(B, 16 // self.grp))           # slots an attention record serves (lanes = grp*G)
        self.lanes = self.grp * self.G
        self.P = min(B, SM_MAX_SLOTS)
        self.PH = min(B, HEAD_SLOTS)
        self.caps = list(dcfg["dflash_config"]["target_layer_ids"])
        self.nD = dcfg["num_hidden_layers"]
        self.L = t.L
        self.mask_id = dcfg["dflash_config"]["mask_token_id"]
        assert dcfg["hidden_size"] == t.H and dcfg["num_attention_heads"] == cfg["num_attention_heads"]
        H, HD, P = self.H, self.HD, self.P
        self.PMAX = al(ctx + B, 8)
        self.rows_qkv = t.rows_qkv
        # ---- VM: persistent regions, then the union U (phases reuse it) ----------------------------------------
        vm, cur = {}, [0]

        def put(name, n, align=32):
            cur[0] = al(cur[0], align)
            vm[name] = (cur[0], n)
            cur[0] += n
        put("X", B * H)
        put("ROPE", B * HD)
        put("ROPEC", B * HD)
        put("CNT", B * NL)
        put("PV", self.lanes * HD)
        put("MAX", self.lanes)
        put("Z", self.lanes)
        put("ESC", B)
        put("D", B)
        put("AMX", 2 * B)
        put("TOKX", B + 2)                    # [value word][k][POST 0..B-1]
        put("ACC", 4 * (B + 2) * 2)
        put("FLAG", B + 2)
        put("ONE", 1)
        ubase = al(cur[0], 128)
        self.ubase = ubase
        uses = {}

        def phase(items, at=0):
            o = at
            for name, n in items:
                o = al(o, 32)
                vm[name] = (ubase + o, n)
                o += n
            uses[items[0][0]] = o
            return o
        PH, HT = self.PH, H // TP
        nf = len(self.caps)
        phase([("HN", P * H), ("QKV", P * self.rows_qkv), ("QN", P * (self.nq + self.nk) * HD),
               ("QR", P * (self.nq + self.nk) * HD)])
        sc_end = phase([("SC", self.lanes * self.PMAX)])
        # QB (all B slots' rounded queries) and ATTN (all slots' attention outputs) live across the attention phase:
        # beyond SC and beyond every pre-attention / FFN buffer
        phase([("OPART", P * H), ("OSUM", P * H)])
        vm["HN2"] = (ubase, P * H)
        vm["GU"] = (ubase + al(P * H), P * 2 * self.ff)
        vm["DPART"] = (ubase, P * H)                                   # over HN2 + GU: dead after the GLU
        vm["DSUM"] = (ubase + al(P * H), P * H)
        act0 = al(max(al(P * H) + P * 2 * self.ff, 2 * al(P * H)))
        vm["ACT"] = (ubase + act0, P * self.ff)
        ffn_end = act0 + P * self.ff
        live0 = al(max(sc_end, ffn_end, uses["HN"], uses["OPART"]))
        phase([("QB", B * self.nq * HD), ("ATTN", B * self.nq * HD)], at=live0)
        phase([("HF", PH * H), ("LOG", PH * self.hrows)])
        fcp = [(f"FCP{j}", P * HT) for j in range(nf)]
        phase([("FIN", P * H)] + fcp + [("FCG", TP * P * HT), ("HC", P * H), ("DKV", P * 2 * self.nk * HD),
                                         ("DKN", P * self.nk * HD), ("DKR", P * self.nk * HD)])
        self.vm_end = ubase + max(uses.values())
        assert self.vm_end <= 1 << 18, f"DFlash VM map needs {self.vm_end} words (> 262,144)"
        self.vm = vm
        self.spans = {k: (v[0], v[0] + v[1]) for k, v in vm.items()}
        # ---- HBM: the target image (QC layout) + the drafter, the caches and the step scratch -----------------
        self.hbm = dict(t.hbm)
        base = 1 << 32
        self.hbm.update(DWEIGHTS=base * 8, DKVC=base * 10, CTXF=base * 12, DBLK=base * 13, CNTT=base * 14,
                        MBOX=base * 15)
        dl = {}
        off = 0

        def hput(name, nbytes):
            nonlocal off
            off = al(off)
            dl[name] = off
            off += nbytes
        hput("qkv", self.rows_qkv * H * 2)
        hput("o", H * self.nq * HD * 2)
        hput("gu", 2 * self.ff * H * 2)
        hput("down", H * self.ff * 2)
        for g_ in ("ln1", "ln2"):
            hput(g_, H * 2)
        for g_ in ("qn", "kn"):
            hput(g_, HD * 2)
        self.dlayer_bytes = al(off, 4096)
        self.dlay = dl
        self.dfc = self.dlayer_bytes * self.nD                  # fc: nf K-blocks of [H/TP rows][H] BF16
        self.dfc_blk = al((H // TP) * H * 2)
        self.dhn = self.dfc + len(self.caps) * self.dfc_blk                  # hidden_norm gain
        self.dnorm = self.dhn + al(H * 2)                       # the drafter's final norm gain
        self.dkv_plane = ctx * HD * 2                           # BF16 [pos][HD] per (layer, kv head, K|V)
        self.dkv_layer = self.nk * 2 * self.dkv_plane
        self.ctxf_row = len(self.caps) * H * 2                  # BF16 [pos][captured layer][H]
        self.dblk_plane = al(B * HD * 2)
        self.dblk_layer = self.nk * 2 * self.dblk_plane
        self.cnt_n = ctx + B + 2                                # U32 count table T[q] = q, then FP32 1.0
        self.cnt_one = 4 * self.cnt_n


# ----------------------------------------------------------------------------------------------------------------
# hazard bookkeeping by address span (U regions alias each other across phases)
# ----------------------------------------------------------------------------------------------------------------
class SpanBuilder(QC.Builder):
    def __init__(self, g):
        super().__init__(g.t)
        self.sp = g.spans

    def _x(self, names):
        out = set()
        for n in names:
            if n not in self.sp:
                out.add(n)
                continue
            lo, hi = self.sp[n]
            out |= {k for k, (a, b) in self.sp.items() if a < hi and lo < b}
        return out

    def add(self, rec, reads, writes):
        return super().add(rec, self._x(reads), self._x(writes))


def sut(**kw):
    return QC.sut(**kw)


class Emit:
    """Record helpers bound to one geometry and builder."""

    def __init__(self, g, b, md):
        self.g, self.b, self.md = g, b, md

    def V(self, name, n, m=1, stride=0, off=0, n_sel=0, ibcast=0, fmt="FP32", istride=0, dyn_sel=0, dyn_mul=0):
        return MDesc(space="VM", fmt=fmt, base=self.g.vm[name][0] + off, n=n, m=m, stride=stride, n_sel=n_sel,
                     ibcast=ibcast, istride=istride, dyn_sel=dyn_sel, dyn_mul=dyn_mul)

    def Hb(self, region, off, fmt, n, m=1, stride=0, lstride=0, dyn_sel=0, dyn_mul=0, n_sel=0, ibcast=0, indexed=0):
        return MDesc(space="HBM", fmt=fmt, base=self.g.hbm[region] + off, n=n, m=m, stride=stride, lstride=lstride,
                     dyn_sel=dyn_sel, dyn_mul=dyn_mul, n_sel=n_sel, ibcast=ibcast, indexed=indexed)

    def cnt(self, s):
        """The I table whose replicated word is pos + s + 1 (slot s's causal count)."""
        return self.V("CNT", NL, fmt="U32", off=s * NL)

    def rec(self, unit, op, reads, writes, tag, family, **kw):
        return self.b.add(Rec(unit, op, tag=tag, family=family, **kw), reads, writes)

    def su(self, tag, family, desc, reads, writes, **t):
        t.setdefault("dst", I.DST_VM)
        return self.rec("SU", "VOP", reads, writes, tag, family, sut=sut(**t), desc=desc)

    def sm(self, tag, family, x, w, o, P, fmt, reads, writes):
        return self.rec("SM", "MATVEC", reads, writes, tag, family, param=fmt | ((P - 1) << 2),
                        desc=dict(A=x, B=w, O=o))

    def norm(self, tag, family, a, gain, o, seg, reads, writes):
        du = (a.n * a.m) // 128 if seg == 0 else a.n // 128      # seg 128: one descriptor row (m rows of n)
        return self.rec("FUSED", "ROW_NORM", reads, writes, tag, family,
                        param=du | (seg << 6), imm_a=self.md["norm_eps"],
                        desc=dict(A=a, B=gain, O=o))


# ----------------------------------------------------------------------------------------------------------------
# the step program
# ----------------------------------------------------------------------------------------------------------------
def step_program(g: DGeom, md, timing_pos=None):
    b = SpanBuilder(g)
    e = Emit(g, b, md)
    t = g.t
    H, HD, B, P, PH = g.H, g.HD, g.B, g.P, g.PH
    nq, nk, grp, G = g.nq, g.nk, g.grp, g.G
    QK = (nq + nk) * HD
    HT = H // TP
    nf = len(g.caps)
    scale = md["attn_scale"]
    tp = timing_pos if timing_pos is not None else 0
    W = t.lay
    LB = t.layer_bytes
    KVL = t.kv_layer
    passes = [(s0, min(P, B - s0)) for s0 in range(0, B, P)]
    groups = [(s0, min(G, B - s0)) for s0 in range(0, B, G)]

    def cnt_hint(s):
        return tp + s + 1

    def V(*a, **k):
        return e.V(*a, **k)

    # ---- 0. counts, rope rows, constants ------------------------------------------------------------------
    e.rec("DMA", "LOAD", [], ["CNT"], "counts", "mtp_counts", desc=dict(
        A=e.Hb("CNTT", 4, "U32", NL, m=B, stride=4, dyn_sel=DYN["POS"], dyn_mul=4, ibcast=1),
        O=V("CNT", NL, m=B, stride=NL, fmt="U32")))
    e.rec("DMA", "LOAD", [], ["ROPE"], "rope.rows", "rope", desc=dict(
        A=e.Hb("TABLES", t.tables["rope"], "FP32", HD, m=B, stride=t.rope_row, dyn_sel=DYN["POS"],
               dyn_mul=t.rope_row), O=V("ROPE", HD, m=B, stride=HD)))
    e.rec("DMA", "LOAD", [], ["ROPEC"], "rope.ctx_rows", "rope", desc=dict(
        A=e.Hb("TABLES", t.tables["rope"] - B * t.rope_row, "FP32", HD, m=B, stride=t.rope_row,
               dyn_sel=DYN["POS"], dyn_mul=t.rope_row), O=V("ROPEC", HD, m=B, stride=HD)))
    e.rec("DMA", "LOAD", [], ["ONE"], "const.one", "swiglu", desc=dict(
        A=e.Hb("TABLES", t.tables["one"], "FP32", 1), O=V("ONE", 1)))
    e.rec("DMA", "LOAD", [], ["FLAG"], "const.flag0", "accept", desc=dict(
        A=e.Hb("CNTT", 0, "FP32", 1), O=V("FLAG", 1)))                                       # T[0] = 0 -> +0.0
    e.rec("DMA", "LOAD", [], ["FLAG"], "const.flagB", "accept", desc=dict(
        A=e.Hb("CNTT", g.cnt_one, "FP32", 1), O=V("FLAG", 1, off=B)))                        # 1.0

    # ---- 1. drafter context rows [pos - B, pos) -----------------------------------------------------------
    DW = g.dlay
    DLB = g.dlayer_bytes

    def dW(name, fmt, n, m, stride, off=0, lstride=None):
        return e.Hb("DWEIGHTS", DW[name] + off, fmt, n, m=m, stride=stride, lstride=DLB if lstride is None else lstride)

    for (c0, pp) in passes:
        fcp = []
        for j in range(nf):
            e.rec("DMA", "LOAD", [], ["FIN"], f"draft_ctx.feat{j}.c{c0}", "draft_ctx", desc=dict(
                A=e.Hb("CTXF", j * H * 2 + (c0 - B) * g.ctxf_row, "BF16", H, m=pp, stride=g.ctxf_row,
                       dyn_sel=DYN["POS"], dyn_mul=g.ctxf_row),
                O=V("FIN", H, m=pp, stride=H)))
            nm = f"FCP{j}"
            e.sm(f"draft_ctx.fc{j}.c{c0}", "draft_fc", V("FIN", H, m=pp, stride=H),
                 e.Hb("DWEIGHTS", g.dfc + j * g.dfc_blk, "BF16", H, m=HT, stride=H * 2),
                 V(nm, HT, m=pp, stride=HT), pp, 0, ["FIN"], [nm])
            fcp.append(nm)
        dst = V("FCG", HT, m=pp, stride=HT, dyn_sel=DYN["RANK"], dyn_mul=P * HT)
        if nf == 1:
            e.su(f"draft_ctx.fc_copy.c{c0}", "draft_fc", dict(A=V(fcp[0], HT, m=pp, stride=HT), O=dst), [fcp[0]],
                 ["FCG"], m1=I.M1_BYP)
        else:
            lv = list(fcp)
            while len(lv) & (len(lv) - 1):
                lv.append(None)
            k = 0
            while len(lv) > 1:
                nxt = []
                last = len(lv) == 2
                for i in range(0, len(lv), 2):
                    a_, c_ = lv[i], lv[i + 1]
                    if c_ is None:
                        nxt.append(a_)
                        continue
                    o_ = dst if last else V(a_, HT, m=pp, stride=HT)
                    e.su(f"draft_ctx.fc_add{k}.c{c0}", "draft_fc", dict(
                        A=V(a_, HT, m=pp, stride=HT), C=V(c_, HT, m=pp, stride=HT), O=o_), [a_, c_],
                        ["FCG"] if last else [a_], m1=I.M1_BYP, ad=I.AD_C)
                    k += 1
                    nxt.append(a_)
                lv = nxt
        e.rec("COLL", "ALL_GATHER", ["FCG"], ["FCG"], f"draft_ctx.gather.c{c0}", "draft_fc", desc=dict(
            A=V("FCG", TP * P * HT), O=V("FCG", TP * P * HT)))
        for c in range(pp):
            e.norm(f"draft_ctx.hidden_norm.c{c0 + c}", "draft_ctx", V("FCG", HT, m=TP, stride=P * HT, off=c * HT),
                   e.Hb("DWEIGHTS", g.dhn, "BF16", H), V("HC", H, off=c * H, fmt="BF16"), 0, ["FCG"], ["HC"])
        e.rec("CTL", "LOOP", [], [], "draft_ctx.layers", "", param=g.nD)
        e.sm(f"draft_ctx.kv.c{c0}", "draft_ctx", V("HC", H, m=pp, stride=H),
             dW("qkv", "BF16", H, 2 * nk * HD, H * 2, off=nq * HD * H * 2), V("DKV", 2 * nk * HD, m=pp, stride=2 * nk * HD),
             pp, 0, ["HC"], ["DKV"])
        e.norm(f"draft_ctx.knorm.c{c0}", "draft_ctx", V("DKV", nk * HD, m=pp, stride=2 * nk * HD),
               dW("kn", "BF16", HD, 1, 0), V("DKN", nk * HD, m=pp, stride=nk * HD), HD, ["DKV"], ["DKN"])
        for c in range(pp):
            e.su(f"draft_ctx.rope.c{c0 + c}", "draft_ctx", dict(
                A=V("DKN", HD, m=nk, stride=HD, off=c * nk * HD), B=V("ROPEC", HD // 2, m=nk, stride=0, off=(c0 + c) * HD),
                D=V("ROPEC", HD // 2, m=nk, stride=0, off=(c0 + c) * HD + HD // 2),
                O=V("DKR", HD, m=nk, stride=HD, off=c * nk * HD)), ["DKN", "ROPEC"], ["DKR"],
                m1=I.M1_AB, qm=I.QM_ALT_NP, ad=I.AD_Q, c_pair=1, b_half=1)
        for h in range(nk):
            for kind, src, off, st in ((0, "DKR", h * HD, nk * HD), (1, "DKV", nk * HD + h * HD, 2 * nk * HD)):
                e.rec("DMA", "STORE", [src], ["DKVCACHE"], f"draft_ctx.store{'KV'[kind]}{h}.c{c0}", "draft_ctx",
                      desc=dict(A=V(src, HD, m=pp, stride=st, off=off),
                                O=e.Hb("DKVC", (h * 2 + kind) * g.dkv_plane + (c0 - B) * HD * 2, "BF16", HD, m=pp,
                                       stride=HD * 2, lstride=g.dkv_layer, dyn_sel=DYN["POS"], dyn_mul=HD * 2)))
        e.rec("CTL", "ENDLOOP", [], [], "draft_ctx.layers", "")
    e.rec("DMA", "FENCE", [], ["DKVCACHE"], "draft_ctx.fence", "draft_ctx")

    # ---- shared decoder-layer emitter (drafter: BF16 weights, non-causal; target: INT8 + scales, causal) ---------
    def layer(kind, lw, kvreg):
        """kind 'draft' | 'verify'; lw(name, fmt, n, m, stride) -> weight MDesc; kvreg: KV descriptors factory."""
        dr = kind == "draft"
        wf, wfmt = (0, "BF16") if dr else (3, "INT8")
        for (s0, pp) in passes:
            for s in range(s0, s0 + pp):
                e.norm(f"{kind}.prenorm.s{s}", f"{kind}_prenorm", V("X", H, off=s * H), lw("ln1", "BF16", H, 1, 0),
                       V("HN", H, off=(s - s0) * H, fmt="BF16"), 0, ["X"], ["HN"])
            e.sm(f"{kind}.qkv.p{s0}", f"{kind}_qkv", V("HN", H, m=pp, stride=H), lw("qkv", wfmt, H, g.rows_qkv, H * (2 if dr else 1)),
                 V("QKV", g.rows_qkv, m=pp, stride=g.rows_qkv), pp, wf, ["HN"], ["QKV"])
            if not dr:
                e.su(f"verify.qkv_scale.p{s0}", "verify_row_scale", dict(
                    A=V("QKV", g.rows_qkv, m=pp, stride=g.rows_qkv), B=lw("qkv_s", "BF16", g.rows_qkv, pp, 0),
                    O=V("QKV", g.rows_qkv, m=pp, stride=g.rows_qkv)), ["QKV"], ["QKV"], m1=I.M1_AB)
            e.norm(f"{kind}.qnorm.p{s0}", f"{kind}_qknorm", V("QKV", nq * HD, m=pp, stride=g.rows_qkv),
                   lw("qn", "BF16", HD, 1, 0), V("QN", nq * HD, m=pp, stride=QK), HD, ["QKV"], ["QN"])
            e.norm(f"{kind}.knorm.p{s0}", f"{kind}_qknorm", V("QKV", nk * HD, m=pp, stride=g.rows_qkv, off=nq * HD),
                   lw("kn", "BF16", HD, 1, 0), V("QN", nk * HD, m=pp, stride=QK, off=nq * HD), HD, ["QKV"], ["QN"])
            for s in range(s0, s0 + pp):
                p = s - s0
                e.su(f"{kind}.rope.s{s}", f"{kind}_rope", dict(
                    A=V("QN", HD, m=nq + nk, stride=HD, off=p * QK), B=V("ROPE", HD // 2, m=nq + nk, stride=0, off=s * HD),
                    D=V("ROPE", HD // 2, m=nq + nk, stride=0, off=s * HD + HD // 2),
                    O=V("QR", HD, m=nq + nk, stride=HD, off=p * QK)), ["QN", "ROPE"], ["QR"],
                    m1=I.M1_AB, qm=I.QM_ALT_NP, ad=I.AD_Q, c_pair=1, b_half=1)
                for kv in range(nk):
                    e.su(f"{kind}.round_q.s{s}.kv{kv}", f"{kind}_round_q", dict(
                        A=V("QR", grp * HD, off=p * QK + kv * grp * HD),
                        O=V("QB", grp * HD, off=((kv * B + s) * grp) * HD)), ["QR"], ["QB"], rnd=1)
            for h in range(nk):
                for kd, src, off, st in ((0, "QR", nq * HD + h * HD, QK), (1, "QKV", (nq + nk) * HD + h * HD, g.rows_qkv)):
                    e.rec("DMA", "STORE", [src], [kvreg["name"]], f"{kind}.store{'KV'[kd]}{h}.p{s0}", f"{kind}_kv_append",
                          desc=dict(A=V(src, HD, m=pp, stride=st, off=off), O=kvreg["store"](h, kd, s0, pp)))
        e.rec("DMA", "FENCE", [], [kvreg["name"]], f"{kind}.kv_fence", f"{kind}_kv_fence")
        # attention: groups of G slots, one ATT record a KV head and group
        for h in range(nk):
            for (s0, gg) in groups:
                sl = s0 + gg - 1
                ln = gg * grp
                ncount = (tp + B) if dr else cnt_hint(sl)
                Icnt = e.cnt(B - 1 if dr else sl)
                e.rec("ATT", "QK", ["QB", kvreg["name"]], ["SC"], f"{kind}.qk.kv{h}.g{s0}", f"{kind}_attention_qk",
                      param=(ln & 0xF) | ((HD // 64 - 1) << 4), desc=dict(
                          A=V("QB", HD, m=ln, stride=HD, off=((h * B + s0) * grp) * HD),
                          B=kvreg["ctx"](h, 0), C=kvreg["blk"](h, 0, sl),
                          O=V("SC", ncount, m=ln, stride=g.PMAX)))
                segs = [(s0, gg)] if dr else [(s, 1) for s in range(s0, s0 + gg)]
                for (s, k) in segs:
                    r0 = (s - s0) * grp
                    m = k * grp
                    nh = (tp + B) if dr else cnt_hint(s)
                    Ic = e.cnt(B - 1 if dr else s)
                    sc = V("SC", nh, m=m, stride=g.PMAX, off=r0 * g.PMAX, n_sel=NSEL)
                    e.su(f"{kind}.softmax.max.s{s}.kv{h}", f"{kind}_softmax", dict(
                        A=sc, R=V("MAX", 1, m=m, stride=1, off=r0), I=Ic), ["SC", "CNT"], ["MAX"],
                        m1=I.M1_AIMM, imm1=scale, red=I.RED_MAX, dst=I.DST_NONE)
                    e.su(f"{kind}.softmax.exp_sum.s{s}.kv{h}", f"{kind}_softmax", dict(
                        A=sc, B=V("MAX", 1, m=m, stride=1, off=r0, ibcast=1), O=sc,
                        R=V("Z", 1, m=m, stride=1, off=r0), I=Ic), ["SC", "MAX", "CNT"], ["SC", "Z"],
                        m1=I.M1_AIMM, imm1=scale, ad=I.AD_NEGB, sfu=I.SFU_EXP, red=I.RED_SUM)
                    e.su(f"{kind}.softmax.bf16.s{s}.kv{h}", f"{kind}_softmax", dict(A=sc, O=sc, I=Ic), ["SC", "CNT"],
                         ["SC"], rnd=1)
                    if not dr and s < sl:
                        z = V("SC", sl - s, m=m, stride=g.PMAX, off=r0 * g.PMAX + s + 1, dyn_sel=DYN["POS"], dyn_mul=1)
                        e.su(f"verify.mask_tail.s{s}.kv{h}", "verify_mask", dict(A=z, O=z), ["SC"], ["SC"],
                             m1=I.M1_AIMM, imm1=0)
                e.rec("ATT", "PV", ["SC", kvreg["name"], "CNT"], ["PV"], f"{kind}.pv.kv{h}.g{s0}", f"{kind}_attention_pv",
                      param=(ln & 0xF) | ((HD // 64 - 1) << 4), desc=dict(
                          A=V("SC", ncount, m=ln, stride=g.PMAX, n_sel=NSEL), B=kvreg["ctx"](h, 1),
                          C=kvreg["blk"](h, 1, sl), O=V("PV", HD, m=ln, stride=HD), I=Icnt))
                for s in range(s0, s0 + gg):
                    r0 = (s - s0) * grp
                    e.su(f"{kind}.pv_norm.s{s}.kv{h}", f"{kind}_pv_normalize", dict(
                        A=V("PV", HD, m=grp, stride=HD, off=r0 * HD), B=V("Z", HD, m=grp, stride=1, off=r0, ibcast=1),
                        O=V("ATTN", HD, m=grp, stride=HD, off=s * nq * HD + h * grp * HD)), ["PV", "Z"], ["ATTN"],
                        m1=I.M1_DIVB)
        for (s0, pp) in passes:
            e.sm(f"{kind}.o.p{s0}", f"{kind}_o", V("ATTN", nq * HD, m=pp, stride=nq * HD, off=s0 * nq * HD),
                 lw("o", wfmt, nq * HD, H, nq * HD * (2 if dr else 1)), V("OPART", H, m=pp, stride=H), pp, wf,
                 ["ATTN"], ["OPART"])
            e.rec("COLL", "ALL_REDUCE_SUM", ["OPART"], ["OSUM"], f"{kind}.all_reduce_o.p{s0}", f"{kind}_all_reduce",
                  desc=dict(A=V("OPART", pp * H), O=V("OSUM", pp * H)))
            res = dict(A=V("OSUM", H, m=pp, stride=H), C=V("X", H, m=pp, stride=H, off=s0 * H),
                       O=V("X", H, m=pp, stride=H, off=s0 * H))
            if dr:
                e.su(f"draft.residual_o.p{s0}", "draft_residual", res, ["OSUM", "X"], ["X"], m1=I.M1_BYP, ad=I.AD_C)
            else:
                res["B"] = lw("o_s", "BF16", H, pp, 0)
                e.su(f"verify.scale_o+res.p{s0}", "verify_row_scale", res, ["OSUM", "X"], ["X"], m1=I.M1_AB, ad=I.AD_C)
            for s in range(s0, s0 + pp):
                e.norm(f"{kind}.prenorm2.s{s}", f"{kind}_prenorm", V("X", H, off=s * H), lw("ln2", "BF16", H, 1, 0),
                       V("HN2", H, off=(s - s0) * H, fmt="BF16"), 0, ["X"], ["HN2"])
            e.sm(f"{kind}.gu.p{s0}", f"{kind}_gu", V("HN2", H, m=pp, stride=H),
                 lw("gu", wfmt, H, 2 * g.ff, H * (2 if dr else 1)), V("GU", 2 * g.ff, m=pp, stride=2 * g.ff), pp, wf,
                 ["HN2"], ["GU"])
            if not dr:
                e.su(f"verify.gu_scale.p{s0}", "verify_row_scale", dict(
                    A=V("GU", 2 * g.ff, m=pp, stride=2 * g.ff), B=lw("gu_s", "BF16", 2 * g.ff, pp, 0),
                    O=V("GU", 2 * g.ff, m=pp, stride=2 * g.ff)), ["GU"], ["GU"], m1=I.M1_AB)
            e.rec("SFU", "GLU", ["GU", "ONE"], ["ACT"], f"{kind}.swiglu.p{s0}", f"{kind}_swiglu", imm_a=QC.FLT_MAX,
                  desc=dict(A=V("GU", g.ff, m=pp, stride=2 * g.ff), B=V("GU", g.ff, m=pp, stride=2 * g.ff, off=g.ff),
                            C=V("ONE", g.ff, m=pp, stride=0, ibcast=1), O=V("ACT", g.ff, m=pp, stride=g.ff, fmt="BF16")))
            e.sm(f"{kind}.down.p{s0}", f"{kind}_down", V("ACT", g.ff, m=pp, stride=g.ff),
                 lw("down", wfmt, g.ff, H, g.ff * (2 if dr else 1)), V("DPART", H, m=pp, stride=H), pp, wf,
                 ["ACT"], ["DPART"])
            e.rec("COLL", "ALL_REDUCE_SUM", ["DPART"], ["DSUM"], f"{kind}.all_reduce_down.p{s0}", f"{kind}_all_reduce",
                  desc=dict(A=V("DPART", pp * H), O=V("DSUM", pp * H)))
            res = dict(A=V("DSUM", H, m=pp, stride=H), C=V("X", H, m=pp, stride=H, off=s0 * H),
                       O=V("X", H, m=pp, stride=H, off=s0 * H))
            if dr:
                e.su(f"draft.residual_down.p{s0}", "draft_residual", res, ["DSUM", "X"], ["X"], m1=I.M1_BYP, ad=I.AD_C)
            else:
                res["B"] = lw("down_s", "BF16", H, pp, 0)
                e.su(f"verify.scale_down+res.p{s0}", "verify_row_scale", res, ["DSUM", "X"], ["X"], m1=I.M1_AB,
                     ad=I.AD_C)

    def head(kind, slots, gain, out_name, out_off):
        """Final norm + the target LM head (INT8 + row scale) + argmax / merge per slot, <= PH slots a pass."""
        HB = g.hbm["HEAD"]
        hr = g.hrows
        for i0 in range(0, len(slots), PH):
            ss = slots[i0:i0 + PH]
            for k, s in enumerate(ss):
                e.norm(f"{kind}.final_norm.s{s}", f"{kind}_prenorm", V("X", H, off=s * H), gain,
                       V("HF", H, off=k * H, fmt="BF16"), 0, ["X"], ["HF"])
            e.sm(f"{kind}.head.s{ss[0]}", f"{kind}_head", V("HF", H, m=len(ss), stride=H),
                 MDesc(space="HBM", fmt="INT8", base=HB, n=H, m=hr, stride=H), V("LOG", hr, m=len(ss), stride=hr),
                 len(ss), 3, ["HF"], ["LOG"])
            e.su(f"{kind}.head_scale.s{ss[0]}", f"{kind}_head_scale", dict(
                A=V("LOG", hr, m=len(ss), stride=hr), B=MDesc(space="HBM", fmt="BF16", base=HB + al(hr * H), n=hr,
                                                               m=len(ss), stride=0),
                O=V("LOG", hr, m=len(ss), stride=hr)), ["LOG"], ["LOG"], m1=I.M1_AB)
            for k, s in enumerate(ss):
                e.rec("ARGMAX", "LOCAL", ["LOG"], ["AMX"], f"{kind}.argmax.s{s}", f"{kind}_argmax", imm_a=hr,
                      desc=dict(A=V("LOG", hr, off=k * hr), O=V("AMX", 2, off=2 * s)))
                e.rec("COLL", "ARGMAX_MERGE", ["AMX"], [out_name], f"{kind}.merge.s{s}", f"{kind}_argmax",
                      desc=dict(A=V("AMX", 2, off=2 * s), O=V(out_name, 1, off=out_off + s, fmt="U32")))

    # ---- 2. draft block --------------------------------------------------------------------------------------
    E_ = g.hbm["EMBED"]
    e.rec("DMA", "LOAD", [], ["X"], "draft.embed.anchor", "draft_embed", desc=dict(
        A=MDesc(space="HBM", fmt="INT8", base=E_, n=H, dyn_sel=DYN["TOKEN"], dyn_mul=t.emb_row), O=V("X", H)))
    e.rec("DMA", "LOAD", [], ["ESC"], "draft.embed.anchor_scale", "draft_embed", desc=dict(
        A=MDesc(space="HBM", fmt="BF16", base=E_ + H, n=1, dyn_sel=DYN["TOKEN"], dyn_mul=t.emb_row), O=V("ESC", 1)))
    if B > 1:
        e.rec("DMA", "LOAD", [], ["X"], "draft.embed.mask", "draft_embed", desc=dict(
            A=MDesc(space="HBM", fmt="INT8", base=E_ + g.mask_id * t.emb_row, n=H, m=B - 1, stride=0),
            O=V("X", H, m=B - 1, stride=H, off=H)))
        e.rec("DMA", "LOAD", [], ["ESC"], "draft.embed.mask_scale", "draft_embed", desc=dict(
            A=MDesc(space="HBM", fmt="BF16", base=E_ + g.mask_id * t.emb_row + H, n=1, m=B - 1, stride=0),
            O=V("ESC", 1, m=B - 1, stride=1, off=1)))
    e.su("draft.embed.dequant", "draft_embed", dict(A=V("X", H, m=B, stride=H), B=V("ESC", H, m=B, stride=1, ibcast=1),
                                                    O=V("X", H, m=B, stride=H)), ["X", "ESC"], ["X"], m1=I.M1_AB)
    dkv = dict(name="DBLKC",
               store=lambda h, kd, s0, pp: e.Hb("DBLK", (h * 2 + kd) * g.dblk_plane + s0 * HD * 2, "BF16", HD, m=pp,
                                                 stride=HD * 2, lstride=g.dblk_layer),
               ctx=lambda h, kd: e.Hb("DKVC", (h * 2 + kd) * g.dkv_plane, "BF16", 1, m=1, stride=HD * 2,
                                      lstride=g.dkv_layer, n_sel=DYN["POS"]),
               blk=lambda h, kd, sl: e.Hb("DBLK", (h * 2 + kd) * g.dblk_plane, "BF16", B, stride=HD * 2,
                                          lstride=g.dblk_layer))
    e.rec("CTL", "LOOP", [], [], "draft.layers", "", param=g.nD)
    layer("draft", lambda name, fmt, n, m, stride: dW(name, fmt, n, m, stride), dkv)
    e.rec("CTL", "ENDLOOP", [], [], "draft.layers", "")
    head("draft", list(range(1, B)), e.Hb("DWEIGHTS", g.dnorm, "BF16", H), "D", 0)

    # ---- 3. verify ---------------------------------------------------------------------------------------------
    e.rec("DMA", "LOAD", [], ["X"], "verify.embed.anchor", "verify_embed", desc=dict(
        A=MDesc(space="HBM", fmt="INT8", base=E_, n=H, dyn_sel=DYN["TOKEN"], dyn_mul=t.emb_row), O=V("X", H)))
    e.rec("DMA", "LOAD", [], ["ESC"], "verify.embed.anchor_scale", "verify_embed", desc=dict(
        A=MDesc(space="HBM", fmt="BF16", base=E_ + H, n=1, dyn_sel=DYN["TOKEN"], dyn_mul=t.emb_row), O=V("ESC", 1)))
    for s in range(1, B):
        e.rec("DMA", "LOAD", ["D"], ["X"], f"verify.embed.s{s}", "verify_embed", desc=dict(
            A=MDesc(space="HBM", fmt="INT8", base=E_, n=H, dyn_mul=t.emb_row, indexed=1), O=V("X", H, off=s * H),
            I=V("D", 1, off=s, fmt="U32")))
        e.rec("DMA", "LOAD", ["D"], ["ESC"], f"verify.embed_scale.s{s}", "verify_embed", desc=dict(
            A=MDesc(space="HBM", fmt="BF16", base=E_ + H, n=1, dyn_mul=t.emb_row, indexed=1), O=V("ESC", 1, off=s),
            I=V("D", 1, off=s, fmt="U32")))
    e.su("verify.embed.dequant", "verify_embed", dict(A=V("X", H, m=B, stride=H), B=V("ESC", H, m=B, stride=1, ibcast=1),
                                                      O=V("X", H, m=B, stride=H)), ["X", "ESC"], ["X"], m1=I.M1_AB)
    KVB = g.hbm["KV"]
    tkv = dict(name="KVCACHE",
               store=lambda h, kd, s0, pp: MDesc(space="HBM", fmt="FP8E4M3", base=KVB + (h * 2 + kd) * t.kv_plane + s0 * HD,
                                                 n=HD, m=pp, stride=HD, lstride=KVL, dyn_sel=DYN["POS"], dyn_mul=HD),
               ctx=lambda h, kd: MDesc(space="HBM", fmt="FP8E4M3", base=KVB + (h * 2 + kd) * t.kv_plane, n=1, m=1,
                                       stride=HD, lstride=KVL, n_sel=DYN["POS"]),
               blk=lambda h, kd, sl: MDesc(space="HBM", fmt="FP8E4M3", base=KVB + (h * 2 + kd) * t.kv_plane, n=sl + 1,
                                           stride=HD, lstride=KVL, dyn_sel=DYN["POS"], dyn_mul=HD))
    WB = g.hbm["WEIGHTS"]
    l0 = 0
    for seg_end in sorted(set(g.caps + [g.L - 1])):
        cnt = seg_end - l0 + 1
        if cnt <= 0:
            continue

        def tw(name, fmt, n, m, stride, _l0=l0):
            return MDesc(space="HBM", fmt=fmt, base=WB + W[name] + _l0 * LB, n=n, m=m, stride=stride, lstride=LB)
        tkv_l = dict(tkv)
        for k_ in ("store", "ctx", "blk"):
            f_ = tkv[k_]
            tkv_l[k_] = (lambda f_: (lambda *a: _shift(f_(*a), l0 * KVL)))(f_)
        if cnt > 1:
            e.rec("CTL", "LOOP", [], [], f"verify.layers{l0}", "", param=cnt)
        layer("verify", tw, tkv_l)
        if cnt > 1:
            e.rec("CTL", "ENDLOOP", [], [], f"verify.layers{l0}", "")
        if seg_end in g.caps:
            j = g.caps.index(seg_end)
            e.rec("DMA", "STORE", ["X"], ["CTXFR"], f"verify.capture.L{seg_end}", "verify_capture", desc=dict(
                A=V("X", H, m=B, stride=H), O=e.Hb("CTXF", j * H * 2, "BF16", H, m=B, stride=g.ctxf_row,
                                                   dyn_sel=DYN["POS"], dyn_mul=g.ctxf_row)))
        l0 = seg_end + 1
    head("verify", list(range(B)), MDesc(space="HBM", fmt="BF16", base=g.hbm["TABLES"] + t.tables["norm"], n=H),
         "TOKX", 2)

    # ---- 4. accept ---------------------------------------------------------------------------------------------
    if B > 1:
        nb = B - 1
        e.rec("DMA", "STORE", ["D"], ["MBOX"], "accept.store_draft", "accept", desc=dict(
            A=V("D", nb, off=1, fmt="U32"), O=e.Hb("MBOX", 0, "U32", nb)))
        e.rec("DMA", "STORE", ["TOKX"], ["MBOX"], "accept.store_post", "accept", desc=dict(
            A=V("TOKX", nb, off=2, fmt="U32"), O=e.Hb("MBOX", 4 * B, "U32", nb)))
        # CTL.FENCE (not DMA.FENCE): the reloads below are DMA records too, so the posted stores must be visible
        # before the CP dispatches them
        e.rec("CTL", "FENCE", ["MBOX"], [], "accept.fence", "accept")
        e.rec("DMA", "LOAD", ["MBOX"], ["ACC"], "accept.load_draft_bytes", "accept", desc=dict(
            A=e.Hb("MBOX", 0, "INT8", 4 * nb), O=V("ACC", 4 * nb)))
        e.rec("DMA", "LOAD", ["MBOX"], ["ACC"], "accept.load_post_bytes", "accept", desc=dict(
            A=e.Hb("MBOX", 4 * B, "INT8", 4 * nb), O=V("ACC", 4 * nb, off=4 * (B + 2))))
        e.su("accept.diff2", "accept", dict(A=V("ACC", 4, m=nb, stride=4), B=V("ACC", 4, m=nb, stride=4, off=4 * (B + 2)),
                                            R=V("FLAG", 1, m=nb, stride=1, off=1)), ["ACC"], ["FLAG"],
             m1=I.M1_BYP, ad=I.AD_NEGB, red=I.RED_SUM, red_sq=1, dst=I.DST_NONE)
        e.su("accept.flag", "accept", dict(A=V("FLAG", nb, off=1), O=V("FLAG", nb, off=1)), ["FLAG"], ["FLAG"],
             a_min=1, imm3=QC.f32u(1.0))
    e.rec("ARGMAX", "LOCAL", ["FLAG"], ["TOKX"], "accept.count", "accept", imm_a=0,
          desc=dict(A=V("FLAG", B + 1), O=V("TOKX", 2)))
    e.rec("CTL", "TOKX", ["TOKX"], [], "tokx", "end", desc=dict(A=V("TOKX", B + 1, off=1, fmt="U32")))
    e.rec("CTL", "END", ["TOKX"], [], "end", "end", desc=dict(A=V("TOKX", 1, off=2, fmt="U32")))
    return QC.assign_waits(b.recs)


def _shift(d, by):
    import copy as _c
    d = _c.copy(d)
    d.base += by
    return d
