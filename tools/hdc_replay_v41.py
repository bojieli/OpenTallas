#!/usr/bin/env python3
"""Shipped-shape replay of the DeepSeek-V4.1 decode core program, and the three-layer reconciliation.

    python3 tools/hdc_replay_v41.py [--validate] [--out results/arch/v41_replay.json]

The V4.1 program builder (tools/hdc_program_v41.py) needs the reduced model's weights and hard-codes its
dimensions (160, 640, 32, ...).  This tool re-emits the SAME op sequence from shapes alone:

* `ShapeLayout` computes only what the timing model and the scheduler read -- the ME / QE / HE matrix
  descriptors (n, k, tiles, split / n, nb, tiles, fp4), the vector-memory map (whose addresses decide
  the stream unit's chase distances), the KV region names -- from a shape dict;
* `ShapeBuilder` is the builder's composite operations with every literal replaced by a shape
  parameter, and with ONE DIE's share of a tensor group of `tp` dies (the splits of
  tools/decode_critical_path.py v41_graph: output-split a-projections, heads / o-groups / expert
  intermediate / router experts / vocabulary split, index keys split; the hyper-connection residual
  work replicated).  Counts that depend on the position carry symbolic DYN selectors resolved by
  `dyn_values(shape, pos)` (window, compressed rows, selections, per-die scan counts);
* `simulate` is tools/hdc_timing_v41.simulate (same constants, same unit models) with the stream-unit
  width, the DYN table and a set of design options (`Cfg`) as parameters.

`--validate` builds the real reduced program and checks that the emitter at the reduced shape
(tp = 1) reproduces its instruction list (unit, resolved counts, wait mask, chase, vector mode) and
that both programs price to hdc_timing_v41.simulate's cycle count.

Configurations (all at the shipped shapes, one die of packaging option (b), tensor group 4):
  C  AS BUILT: stream unit 8 lanes, ME 4 groups x 16 lanes (64 BF16 MAC/cycle, the KV-sourced
     head-group mapping), QE 16 block-dot lanes (512 MAC/cycle, no K-split), HE 3 lanes x 8,
     XU select one element per cycle, routed Sinkhorn 41 x 7 cycles, Engram gather + wkv inline;
  B  the SAME sequencer (in-order issue, 6-cycle gap, wait-mask drains, chases) at the DAG's widths:
     stream unit 512 lanes, every matvec (ME, QE, HE) and every KV-sourced op (scores, P.V, index
     scores) at the DAG's per-die MAC rate (mac_rate_per_die / clock) with the DAG's matvec floor
     (IL x min(IL, blocks)), top-k on ot_hdc_tselect (64 lanes, 2 x beats + LAT0), Engram gather +
     wkv prefetched from token start (the DAG's placement);
  A  the DAG itself (results/roofline/critical_path/decode_critical_path.json, option b).
B and C add the DAG's per-token communication (collective latency + bytes + pipeline hops).
"""
import argparse
import json
import math
from dataclasses import dataclass, replace, asdict
from pathlib import Path

import hdc_isa_v41 as I
import hdc_program_v41 as P
import hdc_timing_v41 as T

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/arch/v41_replay.json"
DAG = ROOT / "results/roofline/critical_path/decode_critical_path.json"
TSEL = ROOT / "results/rtl/hdc_v41_tselect_scale_campaign.json"
SCHEMA = "opentallas.v41-replay.v1"
W, IL, BL = I.W_LANES, I.INTERLEAVE, I.BL
HC_SPLIT, RMS_SPLIT, WO_A_SPLIT = 8, 8, 2      # hdc_golden_v41
DY = I.DYN

# -- shapes ------------------------------------------------------------------------------------------------
RATIO = [0, 0] + [2] * 18 + [1] * 20
KV_SRC, IDX_SRC, CAND_SRC, ENGRAM = [2, 8, 14, 20], [2, 8, 14, 20, 24, 28, 32, 36], 20, [1, 14]
REDUCED = dict(name="reduced-v2", dim=160, hc=4, heads=64, hd=32, rd=4, ih=32, ihd=32, q_rank=32, o_groups=8,
               o_rank=32, n_exp=12, k_exp=6, moe_ff=64, window=128, topk=16, vocab=4040, ehd=32, ecols=24,
               cand_b=8, cand_k=64, scan_cap=0, t_max=144, pmax=128, groups=4, tp=1)
SHIPPED = dict(name="deepseek-v4.1-flash", dim=5120, hc=4, heads=64, hd=512, rd=64, ih=32, ihd=128, q_rank=1280,
               o_groups=8, o_rank=1024, n_exp=384, k_exp=6, moe_ff=2304, window=128, topk=512, vocab=129280,
               ehd=256, ecols=24, cand_b=8, cand_k=2048, scan_cap=16384, t_max=640, pmax=1048576, groups=4, tp=4)


def cdiv(a, b):
    return -(-a // b)


def dyn_values(s, pos):
    """Symbolic DYN selectors of the shape-generic program at `pos` (one die of a group of s['tp'])."""
    tp = s["tp"]
    win = min(s["window"], pos + 1)
    nc1, nc2 = pos + 1, (pos + 1) >> 1
    ns1, ns2 = min(s["topk"], nc1), min(s["topk"], nc2)
    cap = s["scan_cap"] or nc1
    return dict(WIN=win, WINM1=win - 1, WIN_ROW=win * s["hd"], WINM1_ROW=(win - 1) * s["hd"],
                NC1=nc1, NC2=nc2, NS1=ns1, NS2=ns2, T0=win, T1=win + ns1, T2=win + ns2,
                SC1=cdiv(nc1, tp), SC2=cdiv(nc2, tp), SCR=cdiv(min(nc1, cap), tp), NSL1=min(s["topk"], cdiv(nc1, tp)),
                NSL2=min(s["topk"], cdiv(nc2, tp)), NSLR=min(s["topk"], cdiv(min(nc1, cap), tp)))


def resolve(sel, dv):
    """A DYN selector: an int (the ISA's table, hdc_isa_v41.dyn_values), a name, or ('ceil', sel, d)."""
    if not sel:
        return 0
    if isinstance(sel, tuple):
        return cdiv(resolve(sel[1], dv), sel[2])
    return dv[sel]


class Alloc(P.Alloc):
    def __init__(self, size=1 << 40, align=32):
        super().__init__(size, align)


class ShapeLayout:
    """Descriptors, vector-memory and KV maps of one die's share, from a shape dict alone."""

    mtp = None                       # the MTP branch's Builder asks the layout; one position here

    def slot_map(self, j):
        return self.vm.map

    def rname(self, name, j):
        return name

    def __init__(self, s, tp_exact=False, constant_bases=None):
        self.s = s
        self.tp_exact = tp_exact
        self.constant_bases = constant_bases
        if constant_bases is not None:
            required = {"rope_plain", "L0.attn_norm", "L0.ffn_norm", "L0.q_norm", "L0.kv_norm",
                        "L0.attn_sink", "L0.gate_bias", "L0.hc_attn_scale", "L0.hc_attn_base",
                        "L0.hc_ffn_scale", "L0.hc_ffn_base"}
            missing = required - constant_bases.keys()
            if missing:
                raise ValueError(f"TP layer-0 CROM bases missing: {sorted(missing)}")
            if any(not isinstance(v, int) or v < 0 or v >= 1 << 30 for v in constant_bases.values()):
                raise ValueError("CROM bases must be nonnegative 30-bit word addresses")
        G = s["groups"]
        self.G = G
        hd, tp = s["hd"], s["tp"]
        self.heads_d = s["heads"] // tp
        self.ogr_d = s["o_groups"] // tp
        self.ff_d = s["moe_ff"] // tp
        v = self.vm = Alloc()
        hcd = s["hc"] * s["dim"]
        for name, n in (("H", hcd), ("T", hcd), ("SSX", 1), ("RF", 1), ("MIX", 32), ("PA", 4), ("POA", 4),
                        ("CA", 16), ("PF", 4), ("POF", 4), ("CF", 16), ("CRAW", 16), ("M4", 4), ("E16", 32),
                        ("X", s["dim"]), ("XN", s["dim"]), ("SS", 8), ("RS", 8), ("QA", s["q_rank"]),
                        ("QR", s["q_rank"]), ("KVA", hd), ("KVN", hd), ("KVQ", hd), ("Q", self.heads_d * hd),
                        ("S", self.heads_d * s["t_max"]), ("M", self.heads_d), ("Z", self.heads_d),
                        ("DEN", self.heads_d), ("ACC", self.heads_d * hd), ("ZA", self.ogr_d * s["o_rank"]),
                        ("Y", s["dim"]), ("CM", hd), ("CE", 2 * hd), ("CD", hd), ("CP", 2 * hd), ("POOL", hd),
                        ("CKA", hd), ("LAT", hd), ("IKA", s["ihd"]), ("IKN", s["ihd"]), ("IKQ", s["ihd"]),
                        ("IQ", s["ih"] * s["ihd"]), ("IQQ", s["ih"] * s["ihd"]), ("WP", s["ih"]), ("WTS", s["ih"]),
                        ("IS", max(s["pmax"] // tp, 128)), ("SEL", max(s["topk"], 16)), ("G12", max(16, s["n_exp"])),
                        ("SC", max(16, s["n_exp"])), ("BI", max(16, s["n_exp"])), ("EID", 8), ("TOT", 1),
                        ("DEN1", 1), ("WGT", 8), ("ER", s["ecols"] * s["ehd"]), ("EKV", (s["hc"] + 1) * s["dim"]),
                        ("ESS", 8), ("ERS", 8), ("ED", 4), ("EDOT", 4), ("EG", 4)):
            v(name, n)
        for k in range(s["k_exp"] + 1):
            v(f"GU{k}", 2 * self.ff_d)
            v(f"ACT{k}", self.ff_d)
            v(f"E{k}", s["dim"] // tp if tp_exact else s["dim"])
        if tp_exact:
            # The collective writes rank-major full vectors. Keep every source
            # disjoint from its destination; the die DMA rejects overlap.
            for name, n in (("QAL", s["q_rank"] // tp), ("KVAL", hd // tp),
                            ("SCL", s["n_exp"] // tp), ("YTMP", s["dim"]),
                            ("YALL", s["dim"])):
                v(name, n)
            for k in range(s["k_exp"] + 1):
                v(f"ACTALL{k}", s["moe_ff"])
        for L in KV_SRC:
            v(f"SLOT{L}", 4 * hd)
            v(f"CKV{L}", (s["pmax"] // RATIO[L]) * hd)
        self.kv = {f"{p}{L}": 0 for L in range(40) for p in ("KT", "KR")}
        self.kv.update({f"IK{L}": 0 for L in KV_SRC})
        # matrices (one die's share)
        D, hcn = s["dim"], s["hc"]
        self.mat, self.qmat = {}, {}
        for L in range(40):
            for wh in ("attn", "ffn"):
                self.mat[(L, wh, "fn")] = dict(n=6 * hcn, k=hcn * D // HC_SPLIT)
            self.mat[(L, "gate")] = self.place(s["n_exp"] // tp, D)
            if tp == 1:
                self.mat[(L, "wo_a")] = self.place_wo_a()
            else:     # the die's o-groups as one block-diagonal matrix on every lane (no idle slots)
                self.mat[(L, "wo_a")] = self.place(self.ogr_d * s["o_rank"], (s["heads"] // s["o_groups"]) * hd)
            if L in KV_SRC:
                self.mat[(L, "cwkv")] = self.place((2 if RATIO[L] == 2 else 1) * hd // tp, D)
                self.mat[(L, "iwk")] = self.place(s["ihd"], hd)
            if L in IDX_SRC:
                self.mat[(L, "iwp")] = self.place(s["ih"] // tp, D)
            q = self.qplace
            self.qmat[(L, "wq_a")] = q(s["q_rank"] // tp, D)
            self.qmat[(L, "wkv")] = q(hd // tp, D)
            self.qmat[(L, "wq_b")] = q(self.heads_d * hd, s["q_rank"])
            self.qmat[(L, "wo_b")] = q(D, s["o_groups"] * s["o_rank"] // tp)
            if L in IDX_SRC:
                self.qmat[(L, "iwq_b")] = q(s["ih"] * s["ihd"], s["q_rank"])
            self.qmat[(L, "exp", 0, "w13")] = q(2 * self.ff_d, D, fp4=1)
            self.qmat[(L, "exp", 0, "w2")] = q(D // tp if tp_exact else D,
                                                s["moe_ff"] if tp_exact else self.ff_d, fp4=1)
            self.qmat[(L, "exp_stride")] = 1
            self.qmat[(L, "shared", "w13")] = q(2 * self.ff_d, D)
            self.qmat[(L, "shared", "w2")] = q(D // tp if tp_exact else D,
                                                s["moe_ff"] if tp_exact else self.ff_d)
            if L in ENGRAM:
                self.qmat[(L, "ewkv")] = q((hcn + 1) * D // tp, s["ecols"] * s["ehd"])
        self.mat["head"] = self.place(cdiv(s["vocab"], tp), D)
        self.cb = {"tmap": 0, "pre0": 0, "norm": 0, "rope_plain": 0, "rope_yarn": 0}
        self.ebase = {L: 0 for L in ENGRAM}

    def place(self, n, k):
        G = self.G
        split = P.G.split_for(n, k, G, W, IL)
        tiles_total = cdiv(n, W * IL)
        return dict(base=0, n=n, k=k // split, tiles=cdiv(tiles_total, G // split), split=split,
                    macs=n * k)

    def place_wo_a(self):
        s, G = self.s, self.G
        tiles_total = s["o_rank"] // W
        k = (s["heads"] // s["o_groups"]) * s["hd"]
        return dict(base=0, n=s["o_groups"] * s["o_rank"], k=k // WO_A_SPLIT,
                    tiles=cdiv(tiles_total, G // WO_A_SPLIT), split=WO_A_SPLIT, macs=s["o_groups"] * s["o_rank"] * k)

    def qplace(self, n, k, fp4=0):
        return dict(base=0, n=n, nb=k // 32, tiles=cdiv(n, BL * IL), fp4=fp4, macs=n * k)

    def const(self, name):
        """CROM word base; an unbound timing/ISA-only layout retains zero."""
        if self.constant_bases is None:
            return 0
        return self.constant_bases[name]


class ShapeBuilder(P.Builder):
    """hdc_program_v41.Builder with the reduced literals replaced by shape parameters."""

    def __init__(self, lay, engram_inline=True):
        self.lay, self.s = lay, lay.s
        self.tp_exact = lay.tp_exact
        self.coll_seq = 0
        self.prog = []
        self.qchunk, self.slot, self.serial_id, self.n_serial, self.dslot_over = None, 0, None, 0, None
        self.V = lay.vm.map
        self.K = lay.kv
        self.engram_inline = engram_inline
        s = self.s
        self.m = type("M", (), dict(eps=1e-6, hc_eps=1e-6, index_w_scale=1.0, attn_scale=1.0, limit=10.0,
                                    route_scale=1.0, engram_scale=1.0, ih=s["ih"], heads=lay.heads_d,
                                    k_exp=s["k_exp"], n_exp=s["n_exp"]))()

    # annotate MACs / KV-sourced for the design-option pricing
    def me(self, mat, x, out, reads, writes, tag, **over):
        super().me(mat, x, out, reads, writes, tag, **over)
        self.prog[-1][0]["_macs"] = mat.get("macs")

    def kvme(self, macs, *a, **kw):
        super().me(*a, **kw)
        self.prog[-1][0]["_kvmacs"] = macs

    def linq(self, mat, x, out, reads, writes, tag, pred=0, **over):
        super().linq(mat, x, out, reads, writes, tag, pred, **over)
        self.prog[-1][0]["_macs"] = mat["macs"]

    def coll(self, op, src, dst, n, reads, writes, tag, rnd=0):
        """v1 blocking collective; addresses and count are VM elements."""
        assert self.tp_exact and self.s["tp"] == 4
        assert n > 0 and n % 16 == 0 and src % 16 == 0 and dst % 16 == 0
        out_n = n if op == I.COLL_ALL_REDUCE_SUM else self.s["tp"] * n
        assert src + n <= dst or dst + out_n <= src, (src, dst, n)
        self.emit(dict(unit=I.UNIT_COLL, wait=31, coll_op=op, coll_src=src, coll_dst=dst,
                       coll_n=n, coll_k=0, coll_ibase=0, coll_seq=self.coll_seq & 255,
                       coll_rnd=rnd), reads, writes, tag)
        self.coll_seq += 1

    # -- composite operations (literals -> shape) --------------------------------------------------------------
    def hc_mix_issue(self, L, wh):
        s, V_ = self.s, self.V
        t = f"L{L}.hc_{wh}"
        self.rms_r("SSX", s["hc"] * s["dim"], "RF", t)
        mat = self.lay.mat[(L, wh, "fn")]
        self.emit(dict(unit=I.UNIT_HE, he_nout=mat["n"], he_k=mat["k"], he_wbase=0, he_xbase=V_["H"],
                       he_obase=V_["MIX"], _macs=mat["n"] * mat["k"] * HC_SPLIT), {"H"}, {"MIX"}, t)

    def hc_mix_finish(self, L, wh):
        m, V_ = self.m, self.V
        Pn, PO, C = {"attn": ("PA", "POA", "CA"), "ffn": ("PF", "POF", "CF")}[wh]
        t = f"L{L}.hc_{wh}"
        sc = self.lay.const(f"L{L}.hc_{wh}_scale")
        bs = self.lay.const(f"L{L}.hc_{wh}_base")
        common = dict(a_si=1, b_base=V_["RF"], m1=I.M1_AB, c_src=I.SRC_CLO, c_si=1, m2=I.M2_C,
                      d_src=I.SRC_CLO, d_si=1, ad=I.AD_D, dst=I.DST_VM, o_si=1, su_nout=1)
        self.su({"MIX", "RF"}, {Pn}, t, su_nin=4, a_base=V_["MIX"], c_base=sc, d_base=bs, sfu=I.SFU_SIGM,
                e1=I.E1_ADDIMM, imm2=0, o_base=V_[Pn], **common)
        self.su({"MIX", "RF"}, {PO}, t, su_nin=4, a_base=V_["MIX"] + 4, c_base=sc + 4, d_base=bs + 4,
                sfu=I.SFU_SIGM, e1=I.E1_MULIMM, imm2=0, o_base=V_[PO], **common)
        common["su_nout"] = 4
        self.su({"MIX", "RF"}, {"CRAW", "M4"}, t, su_nin=4, a_base=V_["MIX"] + 8, a_so=4, c_base=sc + 8, c_so=4,
                d_base=bs + 8, d_so=4, o_base=V_["CRAW"], o_so=4, red=I.RED_MAX, r_base=V_["M4"], r_so=1,
                **common)
        self.su({"CRAW", "M4"}, {"E16"}, t, su_nout=4, su_nin=4, a_base=V_["CRAW"], a_so=4, a_si=1,
                b_base=V_["M4"], b_so=1, ad=I.AD_NEGB, sfu=I.SFU_EXP, dst=I.DST_VM, o_base=V_["E16"], o_so=4,
                o_si=1)
        self.xu({"E16"}, {C}, t, xu_op=I.XU_SINK, xu_src=V_["E16"], xu_dst=V_[C], xu_n=16)

    def hc_pre(self, pre, dst, tag, ss):
        V_, D = self.V, self.s["dim"]
        h = V_["H"]
        self.su({"H", pre}, {"T"}, tag, su_nout=1, su_nin=D, a_base=h, a_si=1, b_base=V_[pre], m1=I.M1_AB,
                c_base=h + D, c_si=1, d_base=V_[pre] + 1, qm=I.QM_POS, ad=I.AD_Q, dst=I.DST_VM, o_base=V_["T"],
                o_si=1)
        self.su({"H", pre, "T"}, {"T"}, tag, su_nout=1, su_nin=D, a_base=h + 2 * D, a_si=1, b_base=V_[pre] + 2,
                m1=I.M1_AB, c_base=V_["T"], c_si=1, ad=I.AD_C, dst=I.DST_VM, o_base=V_["T"], o_si=1)
        self.su({"H", pre, "T"}, {dst, ss}, tag, **P.segmented(dict(
            su_nout=1, su_nin=D, a_base=h + 3 * D, a_si=1, b_base=V_[pre] + 3, m1=I.M1_AB, c_base=V_["T"],
            c_si=1, ad=I.AD_C, rnd=1, dst=I.DST_VM, o_base=V_[dst], o_si=1, red=I.RED_SUM, red_sq=1,
            r_base=V_[ss]), RMS_SPLIT))

    def hc_post(self, y, post, comb, tag):
        V_, D = self.V, self.s["dim"]
        h, Tt = V_["H"], V_["T"]
        self.su({"H", comb}, {"T"}, tag, su_nout=4, su_nin=D, a_base=h, a_si=1, b_base=V_[comb], b_so=1,
                m1=I.M1_AB, c_base=h + D, c_si=1, d_base=V_[comb] + 4, d_so=1, qm=I.QM_POS, ad=I.AD_Q,
                dst=I.DST_VM, o_base=Tt, o_so=D, o_si=1)
        for j in (2, 3):
            self.su({"H", comb, "T"}, {"T"}, tag, su_nout=4, su_nin=D, a_base=h + D * j, a_si=1,
                    b_base=V_[comb] + 4 * j, b_so=1, m1=I.M1_AB, c_base=Tt, c_so=D, c_si=1, ad=I.AD_C,
                    dst=I.DST_VM, o_base=Tt, o_so=D, o_si=1)
        self.su({y, post, "T"}, {"H", "SSX"}, tag, su_nout=4, su_nin=D, a_base=V_[y], a_si=1,
                b_base=V_[post], b_so=1, m1=I.M1_AB, c_base=Tt, c_so=D, c_si=1, ad=I.AD_C, rnd=1,
                dst=I.DST_VM, o_base=h, o_so=D, o_si=1, red=I.RED_SUM, red_sq=1, red_tree=1,
                r_base=V_["SSX"])

    def engram(self, L):
        s, V_, lay = self.s, self.V, self.lay
        D = s["dim"]
        t = f"L{L}.engram"
        h = V_["H"]
        if self.engram_inline:
            self.xu({"EH"}, {"ER"}, t, xu_op=I.XU_EGATHER, xu_src=0, xu_dst=V_["ER"], xu_layer=0, xu_n=s["ecols"])
            self.linq(lay.qmat[(L, "ewkv")], "ER", "EKV", set(), set(), t)
        self.su({"H"}, {"ESS"}, t, su_nout=4, su_nin=D, a_base=h, a_so=D, a_si=1, red=I.RED_SUM, red_sq=1,
                r_base=V_["ESS"], r_so=1)
        self.su({"EKV"}, {"ESS"}, t, su_nout=4, su_nin=D, a_base=V_["EKV"], a_so=D, a_si=1, red=I.RED_SUM,
                red_sq=1, r_base=V_["ESS"] + 4, r_so=1)
        self.su({"H", "EKV"}, {"ED"}, t, su_nout=4, su_nin=D, a_base=h, a_so=D, a_si=1, b_src=I.SRC_CLO,
                b_base=0, b_so=D, b_si=1, m1=I.M1_AB, c_base=V_["EKV"], c_so=D, c_si=1,
                m2=I.M2_C, red=I.RED_SUM, r_base=V_["ED"], r_so=1)
        self.su({"ESS"}, {"ERS"}, t, su_nout=1, su_nin=8, a_base=V_["ESS"], a_si=1, m1=I.M1_DIVIMM,
                imm1=0, ad=I.AD_IMM, imm2=0, sfu=I.SFU_RSQRT, dst=I.DST_VM, o_base=V_["ERS"], o_si=1)
        self.su({"ERS", "ED"}, {"EDOT"}, t, su_nout=1, su_nin=4, a_base=V_["ERS"], a_si=1, b_base=V_["ERS"] + 4,
                b_si=1, m1=I.M1_AB, c_base=V_["ED"], c_si=1, m2=I.M2_C, e1=I.E1_MULIMM,
                imm2=0, dst=I.DST_VM, o_base=V_["EDOT"], o_si=1)
        self.su({"EDOT"}, {"EG"}, t, su_nout=1, su_nin=4, a_base=V_["EDOT"], a_si=1, sfu=I.SFU_EGATE,
                dst=I.DST_VM, o_base=V_["EG"], o_si=1)
        self.su({"EKV", "EG", "H"}, {"H", "SSX"}, t, su_nout=4, su_nin=D, a_base=V_["EKV"] + 4 * D, a_si=1,
                b_base=V_["EG"], b_so=1, m1=I.M1_AB, c_base=h, c_so=D, c_si=1, ad=I.AD_C, rnd=1,
                dst=I.DST_VM, o_base=h, o_so=D, o_si=1, red=I.RED_SUM, red_sq=1, red_tree=1,
                r_base=V_["SSX"])

    def rope(self, region, base, nh, hs, table, dynsel, inverse, tag, pred=0):
        rd = self.s["rd"]
        self.su({region}, {region}, tag, pred=pred, su_nout=nh, su_nin=rd,
                a_base=base + hs - rd, a_so=hs, a_si=1, c_pair=1,
                b_src=I.SRC_CLO, b_base=self.lay.const(table), b_d=dynsel, b_si=1, b_half=1,
                d_src=I.SRC_CHI, d_base=self.lay.const(table), d_d=dynsel, d_si=1,
                m1=I.M1_AB, qm=I.QM_ALT_PN if inverse else I.QM_ALT_NP, ad=I.AD_Q, rnd=1,
                dst=I.DST_VM, o_base=base + hs - rd, o_so=hs, o_si=1)

    def kvt_write(self, src, region, base, rowsel, tag, pred=0, n=1, ind=False, width=None):
        f = dict(pred=pred, su_nout=n, su_nin=width or self.s["hd"], a_base=self.V[src], a_si=1, dst=I.DST_KVT,
                 o_base=base, o_d=rowsel)
        self.su({src}, {region}, tag, **f)

    def compressor(self, L):
        s, V_, lay = self.s, self.V, self.lay
        hd, ihd = s["hd"], s["ihd"]
        t = f"L{L}.compressor"
        r = RATIO[L]
        mat = lay.mat[(L, "cwkv")]
        pred = I.PRED_ODD if r == 2 else 0
        slot = f"SLOT{L}"
        if r == 2:
            self.me(mat, V_["XN"], V_[slot], {"XN"}, {slot}, t, me_d_obase=DY["SLOTW"])
            s0, s1 = V_[slot], V_[slot] + 2 * hd
            self.su({slot}, {"CM"}, t, pred=pred, su_nout=1, su_nin=hd, a_base=s0 + hd, a_si=1, b_base=s1 + hd,
                    b_si=1, m1=I.M1_MAXB, dst=I.DST_VM, o_base=V_["CM"], o_si=1)
            self.su({slot, "CM"}, {"CE"}, t, pred=pred, su_nout=2, su_nin=hd, a_base=s0 + hd, a_so=2 * hd, a_si=1,
                    b_base=V_["CM"], b_si=1, ad=I.AD_NEGB, sfu=I.SFU_EXP, dst=I.DST_VM, o_base=V_["CE"],
                    o_so=hd, o_si=1)
            self.su({"CE"}, {"CD"}, t, pred=pred, su_nout=1, su_nin=hd, a_base=V_["CE"], a_si=1,
                    c_base=V_["CE"] + hd, c_si=1, ad=I.AD_C, dst=I.DST_VM, o_base=V_["CD"], o_si=1)
            self.su({"CE", "CD"}, {"CP"}, t, pred=pred, su_nout=2, su_nin=hd, a_base=V_["CE"], a_so=hd, a_si=1,
                    b_base=V_["CD"], b_si=1, m1=I.M1_DIVB, dst=I.DST_VM, o_base=V_["CP"], o_so=hd, o_si=1)
            self.su({slot, "CP"}, {"POOL", "SS"}, t, **P.segmented(dict(
                pred=pred, su_nout=1, su_nin=hd, a_base=s0, a_si=1, b_base=V_["CP"], b_si=1, m1=I.M1_AB,
                c_base=s1, c_si=1, d_base=V_["CP"] + hd, d_si=1, qm=I.QM_POS, ad=I.AD_Q, rnd=1, dst=I.DST_VM,
                o_base=V_["POOL"], o_si=1, red=I.RED_SUM, red_sq=1, r_base=V_["SS"]), RMS_SPLIT))
            self.rmsnorm("POOL", hd, 0, "LAT", t, pred, have_ss="SS")
        else:
            self.me(mat, V_["XN"], V_["CKA"], {"XN"}, {"CKA"}, t)
            self.bf16("CKA", hd, "CKA", t, sq="SS")
            self.rmsnorm("CKA", hd, 0, "LAT", t, have_ss="SS")
        t2 = f"L{L}.index_key"
        gsel = DY["ROPE_G2"] if r == 2 else DY["ROPE"]
        self.me(lay.mat[(L, "iwk")], V_["LAT"], V_["IKA"], {"LAT"}, {"IKA"}, t2, pred=pred)
        self.bf16("IKA", ihd, "IKA", t2, pred, sq="SS")
        self.rmsnorm("IKA", ihd, 0, "IKN", t2, pred, have_ss="SS")
        self.rope("IKN", V_["IKN"], 1, ihd, "rope_yarn", gsel, False, t2, pred)
        self.qdq(I.QE_QDQ4, "IKN", ihd // 32, V_["IKQ"], {"IKQ"}, t2, pred)
        self.kvt_write("IKQ", f"IK{L}", 0, "NC2" if r == 2 else "NC1", t2, pred, width=ihd)
        self.rope("LAT", V_["LAT"], 1, hd, "rope_yarn", gsel, False, t, pred)
        self.qdq(I.QE_QDQ4E, "LAT", hd // 32, V_[f"CKV{L}"], {f"CKV{L}"}, t, pred,
                 dsel=DY["CKV2"] if r == 2 else DY["ROW"])

    def ksel(self, L):
        """(scan count, local selection count) selectors of an index source."""
        r = RATIO[L]
        if L in KV_SRC:
            return ("SC2", "NSL2") if r == 2 else ("SC1", "NSL1")
        return "SCR", "NSLR"

    def indexer(self, L):
        s, V_, lay = self.s, self.V, self.lay
        ih, ihd = s["ih"], s["ihd"]
        t = f"L{L}.indexer"
        r, src = RATIO[L], max(x for x in KV_SRC if x <= L)
        pred = I.PRED_NZ if r == 2 else 0
        nsc, nsl = self.ksel(L)
        self.linq(lay.qmat[(L, "iwq_b")], "QR", "IQ", set(), set(), t, pred)
        self.rope("IQ", V_["IQ"], ih, ihd, "rope_yarn", DY["ROPE"], False, t, pred)
        self.qdq(I.QE_QDQ4, "IQ", ih * ihd // 32, V_["IQQ"], {"IQQ"}, t, pred)
        self.me(lay.mat[(L, "iwp")], V_["XN"], V_["WP"], {"XN"}, {"WP"}, t, pred=pred)
        self.su({"WP"}, {"WTS"}, t, pred=pred, su_nout=1, su_nin=ih, a_base=V_["WP"], a_si=1, a_rnd=1,
                m1=I.M1_AIMM, imm1=0, rnd=1, dst=I.DST_VM, o_base=V_["WTS"], o_si=1)
        self.kv_heads(ih, ihd, "IQQ", f"IK{src}", nsc, t, pred)
        STR = s["t_max"]
        self.su({"S", "WTS"}, {"IS"}, t, pred=pred, su_nout=0, su_d_nout=nsc, su_nin=ih, a_base=V_["S"], a_so=1,
                a_si=STR, a_rnd=1, a_relu=1, b_base=V_["WTS"], b_si=1, m1=I.M1_AB, rnd=1, red=I.RED_SUM,
                red_rnd=1, r_base=V_["IS"], r_so=1)
        if L == CAND_SRC and s["tp"] > 1:
            # candidate blocks (layer 20): block max over cand_b positions + top-cand_k of the die's blocks.
            # ESTIMATED: not in the as-built core program (the reduced shapes keep every block).
            self.su({"IS"}, {"IS"}, t + ".cand", pred=pred, su_nout=0, su_d_nout=("ceil", nsc, s["cand_b"]),
                    su_nin=s["cand_b"], a_base=V_["IS"], a_so=s["cand_b"], a_si=1, red=I.RED_MAX,
                    r_base=V_["IS"], r_so=1, _estimated="candidate block max (SU) not in the as-built program")
            self.xu({"IS"}, {"SEL"}, t + ".cand", pred=pred, xu_op=I.XU_SEL, xu_src=V_["IS"], xu_dst=V_["SEL"],
                    xu_d_n=("ceil", nsc, s["cand_b"]), xu_k=s["cand_k"],
                    _estimated="candidate top-2048 of the die's blocks on the XU select")
        self.xu({"IS"}, {"SEL"}, t, pred=pred, xu_op=I.XU_SEL, xu_src=V_["IS"], xu_dst=V_["SEL"], xu_d_n=nsc,
                xu_d_k=nsl)
        if s["tp"] > 1:
            # cross-die final: the tp local selections (after the all-gather) re-selected to topk.
            # ESTIMATED: the single-core program has no cross-die merge.
            self.xu({"SEL"}, {"SEL"}, t + ".final", pred=pred, xu_op=I.XU_SEL, xu_src=V_["SEL"],
                    xu_dst=V_["SEL"], xu_n=s["tp"] * s["topk"], xu_k=s["topk"],
                    _estimated="cross-die final select over tp x topk on the XU select")

    def kv_heads(self, heads, hd, q, kvreg, rows, tag, pred=0):
        """KV-sourced scores (q . k over `rows` rows) in head groups of IL heads; a round covers
        G/H tiles of W rows (ot_hdc_v41_matvec)."""
        V_, G, STR = self.V, self.lay.G, self.s["t_max"]
        per_op = IL * G
        for hb in range(0, heads, per_op):
            nh = min(per_op, heads - hb)
            H = min(G, cdiv(nh, IL))
            hg = H.bit_length() - 1
            self.kvme(("S", nh, rows, hd), dict(n=0, tiles=0, k=hd, base=0), V_[q] + hb * hd, V_["S"] + hb * STR,
                      {q, kvreg}, {"S"}, tag, pred=pred, me_xcs=IL * hd, me_wsrc=1, me_ts=hd, me_ks=1, me_js=0,
                      me_jsh=3, me_xks=1, me_xjs=hd, me_ots=1, me_ojs=STR // W, me_mmode=1, me_d_nout=rows,
                      me_d_tiles=("ceil", rows, W * (G // H)), me_hg=hg, me_ogs=IL * STR // W)

    def attention(self, L, hook=None):
        s, V_, lay, K = self.s, self.V, self.lay, self.K
        hd, hdd = s["hd"], lay.heads_d
        t = f"L{L}.attn"
        r = RATIO[L]
        table = "rope_yarn" if r > 0 else "rope_plain"
        self.linq(lay.qmat[(L, "wq_a")], "XN", "QAL" if self.tp_exact else "QA", set(), set(), t)
        self.linq(lay.qmat[(L, "wkv")], "XN", "KVAL" if self.tp_exact else "KVA", set(), set(), t)
        if self.tp_exact:
            self.coll(I.COLL_ALL_GATHER, V_["QAL"], V_["QA"], s["q_rank"] // s["tp"],
                      {"QAL"}, {"QA"}, t + ".q_a_gather")
            self.coll(I.COLL_ALL_GATHER, V_["KVAL"], V_["KVA"], hd // s["tp"],
                      {"KVAL"}, {"KVA"}, t + ".kv_gather")
        self.rmsnorm("QA", s["q_rank"], lay.const(f"L{L}.q_norm"), "QR", t)
        self.linq(lay.qmat[(L, "wq_b")], "QR", "Q", set(), set(), t)
        self.rmsnorm("KVA", hd, lay.const(f"L{L}.kv_norm"), "KVN", t)
        self.rope("KVN", V_["KVN"], 1, hd, table, DY["ROPE"], False, t)
        self.qdq(I.QE_QDQ8, "KVN", hd // 32, V_["KVQ"], {"KVQ"}, t)
        # The full-shape attention adapter owns a bounded local 0..639 row
        # window. Physical HBM ring slots and selected CKV IDs are mapped by
        # the die prefetcher; neither is an adapter row number.
        self.kvt_write("KVQ", f"KT{L}", 0, "WINM1" if self.tp_exact else DY["POS"], t)
        self.su({"KVQ"}, {f"KR{L}"}, t, su_nout=1, su_nin=hd, a_base=V_["KVQ"], a_si=1, dst=I.DST_KV,
                o_base=0, o_d="WINM1_ROW" if self.tp_exact else DY["ROW"], o_si=1)
        self.rope("Q", V_["Q"], hdd, hd, table, DY["ROPE"], False, t)
        if r > 0:
            src = max(x for x in KV_SRC if x <= L)
            if L == src:
                self.compressor(L)
            if L in IDX_SRC:
                self.indexer(L)
            nsel = "NS2" if r == 2 else "NS1"
            ta = f"L{L}.gather"
            self.su({f"CKV{src}", "SEL"}, {f"KT{L}"}, ta, su_nout=0, su_d_nout=nsel, su_nin=hd,
                    a_base=V_[f"CKV{src}"], a_so=hd, a_si=1, a_ind=I.IND_O, a_ibase=V_["SEL"], dst=I.DST_KVT,
                    o_base=0, o_d="WIN" if self.tp_exact else DY["POS1"])
            self.su({f"CKV{src}", "SEL"}, {f"KR{L}"}, ta, su_nout=0, su_d_nout=nsel, su_nin=hd,
                    a_base=V_[f"CKV{src}"], a_so=hd, a_si=1, a_ind=I.IND_O, a_ibase=V_["SEL"], dst=I.DST_KV,
                    o_base=0, o_d="WIN_ROW" if self.tp_exact else DY["ROW1"], o_so=hd, o_si=1)
        Tn = {0: "T0", 1: "T1", 2: "T2"}[r]
        if hook and P.ATTN_HOOK == "qkv":
            hook()
        self.kv_heads(hdd, hd, "Q", f"KT{L}", Tn, f"L{L}.scores")
        if hook and P.ATTN_HOOK == "scores":
            hook()
        STR = s["t_max"]
        sm = dict(su_nout=hdd, su_nin=0, su_d_nin=Tn, a_base=V_["S"], a_so=STR, a_si=1, dst=I.DST_VM,
                  o_base=V_["S"], o_so=STR, o_si=1)
        tsm = f"L{L}.softmax"
        self.su({"S"}, {"S", "M"}, tsm, m1=I.M1_AIMM, imm1=0, red=I.RED_MAX, r_base=V_["M"], r_so=1, **sm)
        self.su({"S", "M"}, {"S", "Z"}, tsm, b_base=V_["M"], b_so=1, ad=I.AD_NEGB, sfu=I.SFU_EXP, red=I.RED_SUM,
                r_base=V_["Z"], r_so=1, **sm)
        if hook and P.ATTN_HOOK == "softmax":
            hook()
        tp_ = f"L{L}.pv"
        G = lay.G
        for hb in range(0, hdd, IL * 2):     # 2 head groups of 8 heads; a round covers G/2 tiles of W dims
            nh = min(IL * 2, hdd - hb)
            self.kvme(("PV", nh, Tn, hd), dict(n=hd, tiles=cdiv(hd, W * (G // 2)), k=0, base=0),
                      V_["S"] + hb * STR, V_["ACC"] + hb * hd,
                      {"S", f"KR{L}"}, {"ACC"}, tp_, me_xcs=IL * STR, me_wsrc=1, me_ts=1, me_ks=hd // W, me_js=0,
                      me_jsh=3, me_xks=1, me_xjs=STR, me_ots=1, me_ojs=hd // W, me_mmode=1, me_d_k=Tn,
                      me_hg=1, me_ogs=IL * hd // W)
        self.su({"M", "Z"}, {"DEN"}, tsm, su_nout=1, su_nin=hdd, a_src=I.SRC_CLO,
                a_base=lay.const(f"L{L}.attn_sink"),
                a_si=1, b_base=V_["M"], b_si=1, ad=I.AD_NEGB, sfu=I.SFU_EXP, c_base=V_["Z"], c_si=1,
                e1=I.E1_ADDC, dst=I.DST_VM, o_base=V_["DEN"], o_si=1)
        self.su({"ACC", "DEN"}, {"ACC"}, tsm, su_nout=hdd, su_nin=hd, a_base=V_["ACC"], a_so=hd, a_si=1,
                b_base=V_["DEN"], b_so=1, m1=I.M1_DIVB, rnd=1, dst=I.DST_VM, o_base=V_["ACC"], o_so=hd, o_si=1)
        self.rope("ACC", V_["ACC"], hdd, hd, table, DY["ROPE"], True, tsm)
        if hook and P.ATTN_HOOK == "pv":
            hook()
        to = f"L{L}.out"
        mat = lay.mat[(L, "wo_a")]
        zn = lay.ogr_d * s["o_rank"]
        self.me(mat, V_["ACC"], V_["ZA"], {"ACC"}, {"ZA"}, to, me_xjs=zn, me_ots=1, me_ojs=2)
        self.bf16("ZA", zn, "ZA", to)
        self.linq(lay.qmat[(L, "wo_b")], "ZA", "YTMP" if self.tp_exact else "Y", set(), set(), to,
                  **({"qe_unrounded": 1} if self.tp_exact else {}))
        if self.tp_exact:
            self.coll(I.COLL_ALL_REDUCE_SUM, V_["YTMP"], V_["Y"], s["dim"],
                      {"YTMP"}, {"Y"}, to + ".wo_b_reduce", rnd=1)

    def moe(self, L, hook=None):
        s, m, V_, lay = self.s, self.m, self.V, self.lay
        t = f"L{L}.router"
        stride = lay.qmat[(L, "exp_stride")]
        ff = lay.ff_d
        tp = s["tp"]

        def expert(k):
            shared = k == m.k_exp
            te = f"L{L}.shared" if shared else f"L{L}.experts"
            if shared:
                w13, w2, ind = lay.qmat[(L, "shared", "w13")], lay.qmat[(L, "shared", "w2")], {}
            else:
                w13, w2 = lay.qmat[(L, "exp", 0, "w13")], lay.qmat[(L, "exp", 0, "w2")]
                ind = dict(qe_ind=1, qe_ibase=V_["EID"] + k, qe_istride=stride)
            gu = V_[f"GU{k}"]
            f = dict(su_nout=1, su_nin=ff, a_base=gu, a_si=1, a_min=1, imm3=0, c_base=gu + ff, c_si=1,
                     c_clip=1, sfu=I.SFU_SILU, e1=I.E1_MULC, rnd=1, dst=I.DST_VM, o_base=V_[f"ACT{k}"], o_si=1)
            if not shared:
                f.update(b_base=V_["WGT"] + k, e2=I.E2_MULB)
            def activate():
                self.su({f"GU{k}", "WGT"}, {f"ACT{k}"}, te, **f)
                if self.tp_exact:
                    self.coll(I.COLL_ALL_GATHER, V_[f"ACT{k}"], V_[f"ACTALL{k}"], ff,
                              {f"ACT{k}"}, {f"ACTALL{k}"}, te + f".act{k}_gather")

            return (lambda: self.linq(w13, "XN", f"GU{k}", {"EID"}, set(), te, **ind),
                    activate,
                    lambda: self.linq(w2, f"ACTALL{k}" if self.tp_exact else f"ACT{k}",
                                      f"E{k}", {"EID"}, set(), te, **ind))

        sh = expert(m.k_exp)
        sh[0]()
        self.me(lay.mat[(L, "gate")], V_["XN"], V_["G12"], {"XN"}, {"G12"}, t)
        sh[1]()
        sh[2]()
        self.su({"G12"}, {"SCL" if self.tp_exact else "SC"}, t,
                su_nout=1, su_nin=m.n_exp // tp, a_base=V_["G12"], a_si=1, sfu=I.SFU_SPSQRT,
                dst=I.DST_VM, o_base=V_["SCL"] if self.tp_exact else V_["SC"], o_si=1)
        if self.tp_exact:
            self.coll(I.COLL_ALL_GATHER, V_["SCL"], V_["SC"], m.n_exp // tp,
                      {"SCL"}, {"SC"}, t + ".router_gather")
        self.su({"SC"}, {"BI"}, t, su_nout=1, su_nin=m.n_exp, a_base=V_["SC"], a_si=1, d_src=I.SRC_CLO,
                d_base=lay.const(f"L{L}.gate_bias"), d_si=1, ad=I.AD_D, dst=I.DST_VM, o_base=V_["BI"], o_si=1)
        self.xu({"BI"}, {"EID"}, t, xu_op=I.XU_SEL, xu_src=V_["BI"], xu_dst=V_["EID"], xu_n=m.n_exp, xu_k=m.k_exp)
        self.su({"SC", "EID"}, {"TOT"}, t, su_nout=1, su_nin=m.k_exp, a_base=V_["SC"], a_si=1, a_ind=I.IND_I,
                a_ibase=V_["EID"], red=I.RED_SEQ, r_base=V_["TOT"])
        self.su({"TOT"}, {"DEN1"}, t, su_nout=1, su_nin=1, a_base=V_["TOT"], ad=I.AD_IMM, imm2=0,
                dst=I.DST_VM, o_base=V_["DEN1"])
        self.su({"SC", "EID", "DEN1"}, {"WGT"}, t, su_nout=1, su_nin=m.k_exp, a_base=V_["SC"], a_si=1,
                a_ind=I.IND_I, a_ibase=V_["EID"], b_base=V_["DEN1"], m1=I.M1_DIVB, m2=I.M2_IMM,
                imm1=0, dst=I.DST_VM, o_base=V_["WGT"], o_si=1)
        ex = [expert(k) for k in range(m.k_exp)]
        ex[0][0]()
        if m.k_exp > 1:
            ex[1][0]()
        for k in range(m.k_exp):
            if hook and k == P.MOE_HOOK:
                hook()
            if k > 0:
                ex[k - 1][2]()
            ex[k][1]()
            if k + 2 < m.k_exp:
                ex[k + 2][0]()
        ex[m.k_exp - 1][2]()
        if hook and P.MOE_HOOK >= m.k_exp:
            hook()
        ty = f"L{L}.moe_sum"
        D = s["dim"] // tp if self.tp_exact else s["dim"]
        for k in range(1, m.k_exp + 1):
            src = V_["E0"] if k == 1 else V_["Y"]
            self.su({"E0" if k == 1 else "Y", f"E{k}"}, {"Y"}, ty, su_nout=1, su_nin=D, a_base=src, a_si=1,
                    c_base=V_[f"E{k}"], c_si=1, ad=I.AD_C, rnd=int(k == m.k_exp), dst=I.DST_VM, o_base=V_["Y"],
                    o_si=1)
        if self.tp_exact:
            self.coll(I.COLL_ALL_GATHER, V_["Y"], V_["YALL"], D,
                      {"Y"}, {"YALL"}, ty + ".y_gather")

    def build(self, layers=None, embed=True, head=True):
        s, V_, lay = self.s, self.V, self.lay
        D = s["dim"]
        layers = range(40) if layers is None else layers
        if self.tp_exact and list(layers) != [0]:
            raise ValueError("exact TP emission currently supports only layer 0")
        if embed:
            self.xu(set(), {"EH"}, "embed", xu_op=I.XU_EHASH, xu_src=0)
            self.su(set(), {"PF"}, "embed", su_nout=1, su_nin=4, a_src=I.SRC_CLO, a_base=0, a_si=1,
                    dst=I.DST_VM, o_base=V_["PF"], o_si=1)
            self.su(set(), {"H", "SSX"}, "embed", su_nout=4, su_nin=D, a_src=I.SRC_WROM,
                    a_base=0, a_d=DY["EMBED"], a_si=1, dst=I.DST_VM, o_base=V_["H"], o_so=D,
                    o_si=1, red=I.RED_SUM, red_sq=1, red_tree=1, r_base=V_["SSX"])
        for L in layers:
            if L in ENGRAM:
                self.engram(L)
            self.hc_mix_issue(L, "attn")
            self.hc_pre("PF", "X", f"L{L}.attn_norm", "SS")
            self.rmsnorm("X", D, lay.const(f"L{L}.attn_norm"), "XN", f"L{L}.attn_norm", have_ss="SS")
            self.attention(L, hook=lambda: self.hc_mix_finish(L, "attn"))
            self.hc_post("Y", "POA", "CA", f"L{L}.hc_post")
            self.hc_mix_issue(L, "ffn")
            self.hc_pre("PA", "X", f"L{L}.ffn_norm", "SS")
            self.rmsnorm("X", D, lay.const(f"L{L}.ffn_norm"), "XN", f"L{L}.ffn_norm", have_ss="SS")
            self.moe(L, hook=lambda: self.hc_mix_finish(L, "ffn"))
            self.hc_post("YALL" if self.tp_exact else "Y", "POF", "CF", f"L{L}.hc_post")
        if head:
            self.hc_pre("PF", "X", "head", "SS")
            self.rmsnorm("X", D, 0, "XN", "head", have_ss="SS")
            self.me(lay.mat["head"], V_["XN"], 0, {"XN"}, set(), "head", me_amax=1, me_oen=0)
        self.emit(dict(unit=I.UNIT_END, wait=31), set(), set(), "end")
        prog = P.schedule(self.prog)
        for f, (_f0, rd, wr, _t) in zip(prog, self.prog):
            f["_reads"], f["_writes"] = rd, wr
        return prog


def build(shape, su_lanes=8, engram_inline=True, layers=None, embed=True, head=True):
    """Schedule the shape-generic program at a stream-unit width (the chase distances and vector modes
    depend on it)."""
    old = I.SU_LANES
    I.SU_LANES = su_lanes
    try:
        return ShapeBuilder(ShapeLayout(shape), engram_inline).build(layers, embed, head)
    finally:
        I.SU_LANES = old


def build_tp_layer0(shape=SHIPPED, su_lanes=8, embed=False, head=False, constant_bases=None):
    """First exact TP=4 layer program; other layer types are fail closed.

    This is an ISA sequence, not the timing-model program. Its 12 blocking
    collectives, FP32 VM containers and scratch traffic are not yet priced by
    `price`/`arch_lanes_v41`; reported design-point rates need rebaseline.
    """
    if shape["tp"] != 4:
        raise ValueError("the exact collective sequence is defined for tp=4")
    old = I.SU_LANES
    I.SU_LANES = su_lanes
    try:
        return ShapeBuilder(ShapeLayout(shape, tp_exact=True, constant_bases=constant_bases)).build([0], embed, head)
    finally:
        I.SU_LANES = old


# -- timing ------------------------------------------------------------------------------------------------
@dataclass
class Cfg:
    su_lanes: int = 8
    mac_rate: float = 0.0        # >0: every ME / QE / HE matvec at this many MAC/cycle (DAG floor)
    kv_rate: float = 0.0         # >0: KV-sourced ME ops (scores, P.V, index scores) at this rate
    sel_lanes: int = 0           # >0: XU SELECT as ot_hdc_tselect with this many lanes per beat
    gap: int = 6                 # sequencer issue gap
    scoreboard: bool = False     # wait for the producing op (region scoreboard), not the unit drain
    sinkhorn_free: bool = False  # hypothetical: the Sinkhorn costs nothing
    red_parallel: bool = False   # hypothetical: an ordered (per-segment, VEC_O) reduction spreads over every
                                 # lane (a golden with >= su_lanes partials) instead of one lane per segment


NAMES = {1: "ME", 2: "SU", 3: "QE", 4: "XU", 5: "HE"}
TS_LAT0 = json.loads(TSEL.read_text())["parameters"]["lat0"] if TSEL.exists() else 65


def mv_floor(k):
    """The DAG's matvec floor: IL x min(IL, 32-blocks) cycles."""
    return IL * min(IL, cdiv(k, 32))


def simulate(prog, pos, shape, cfg=Cfg(), k=T.K, dyn=None, stats=None, t0=30):
    """hdc_timing_v41.simulate with the design options of `cfg`.  `dyn`: the ISA table
    (hdc_isa_v41.dyn_values) for integer selectors; names resolve through dyn_values(shape, pos)."""
    k = dict(k, gap=cfg.gap)
    ivals = I.dyn_values(0, pos)
    dv = dyn_values(shape, pos)
    D = lambda sel: ivals[sel] if isinstance(sel, int) else resolve(sel, dv)   # noqa: E731
    lanes = cfg.su_lanes
    t = 0
    free = {u: 0 for u in (1, 2, 3, 4, 5)}
    idle = {u: 0 for u in (1, 2, 3, 4, 5)}
    wdone, rdone = {}, {}                        # scoreboard: region -> completion of its last writer / reader
    su_cls, su_last_retire, su_last_emit = None, 0, 0
    busy = {u: 0 for u in (1, 2, 3, 4, 5)}
    stall, t_prev = {}, 0
    n_issued = n_skipped = 0
    for n, f0 in enumerate(prog):
        f = {name: f0.get(name, 0) for name, _ in I.FIELDS}
        u = f["unit"]
        if u == I.UNIT_END:
            t = max([t] + list(idle.values())) + 1
            break
        skip = (f["pred"] == I.PRED_ODD and not pos & 1) or (f["pred"] == I.PRED_NZ and pos == 0)
        if u == I.UNIT_ME:
            cnt = [f["me_nout"] + D(f["me_d_nout"]), f["me_tiles"] + D(f["me_d_tiles"]), f["me_k"] + D(f["me_d_k"])]
            skip |= 0 in cnt
        elif u == I.UNIT_SU:
            no, ni = f["su_nout"] + D(f["su_d_nout"]), f["su_nin"] + D(f["su_d_nin"])
            skip |= no == 0 or ni == 0
        elif u == I.UNIT_XU and f["xu_op"] == I.XU_SEL:
            skip |= f["xu_n"] + D(f["xu_d_n"]) == 0
        if skip:
            t += k["skip"]
            n_skipped += 1
            continue
        n_issued += 1
        unit = u
        ready = t
        why = "issue gap"
        if cfg.scoreboard:
            for r in f0.get("_reads", ()):
                tw, uw = wdone.get(r, (0, 0))
                if not (uw == unit == I.UNIT_SU and f0.get("su_chase", 0)):
                    ready = max(ready, tw)
            for r in f0.get("_writes", ()):
                tw, uw = wdone.get(r, (0, 0))
                tr, ur = rdone.get(r, (0, 0))
                ready = max(ready, tw if uw != unit else 0, tr if ur != unit else 0)
        else:
            for b in range(5):
                if f["wait"] >> b & 1:
                    if idle[b + 1] > ready:
                        ready, why = idle[b + 1], NAMES[b + 1] + " drain"
        if free[unit] > ready:
            ready, why = free[unit], NAMES[unit] + " busy (own unit)"
        go = ready
        if unit == I.UNIT_SU:
            stages = (f["m1"] not in (I.M1_BYP, I.M1_MAXB), f["m2"] != I.M2_BYP or f["qm"] != I.QM_OFF,
                      f["ad"] != I.AD_BYP, f["e1"] != I.E1_BYP, f["e2"] != I.E2_BYP)
            cls = (f["m1"] in (I.M1_DIVB, I.M1_DIVIMM), f["sfu"]) + stages
            if su_cls is not None and cls != su_cls:
                if su_last_retire + k["su_cls"] > go:
                    go, why = su_last_retire + k["su_cls"], "SU class change"
        s = go + 1
        if unit == I.UNIT_HE:
            e = f["he_k"] * IL
            if cfg.mac_rate:
                e = max(math.ceil(f0["_macs"] / cfg.mac_rate), mv_floor(f["he_k"] * HC_SPLIT))
            free[unit] = s + k["he_start"] + e
            idle[unit] = s + k["he_start"] + e + k["he_drain"]
        elif unit == I.UNIT_ME:
            e = cnt[1] * cnt[2] * IL
            kvm = f0.get("_kvmacs")
            if kvm and cfg.kv_rate:
                kind, nh, rows, hd = kvm
                e = max(1, math.ceil(nh * D(rows) * hd / cfg.kv_rate))
            elif not kvm and cfg.mac_rate and f0.get("_macs"):
                e = max(math.ceil(f0["_macs"] / cfg.mac_rate), mv_floor(f["me_k"] * (1 << f["me_split"])))
            free[unit] = s + k["me_start"] + e - 1 + k["me_next"]
            idle[unit] = s + k["me_start"] + e + k["me_drain"]
        elif unit == I.UNIT_SU:
            vec = f0.get("su_vec", 0)
            e = (no * -(-ni // lanes) if vec == I.VEC_I else
                 -(-no // lanes) * ni if vec == I.VEC_O else no * ni)
            if cfg.red_parallel and vec == I.VEC_O and (f["red"] or f0.get("red_tree")):
                e = cdiv(no * ni, lanes)
            step = 8 if f["red"] == I.RED_SEQ else 1
            depth = (k["su_base"] + (k["su_div"] if cls[0] else 0) + T.SFU_DEPTH[cls[1]] -
                     k["su_stage"] * sum(1 for used in cls[2:] if not used))
            first = s + k["su_start"]
            if f0.get("su_chase", 0) and su_cls == cls:
                first = max(first, su_last_emit + depth + k["su_chase"] - f0["su_chase"])
            last_emit = first + step * (e - 1)
            su_last_emit = last_emit
            free[unit] = last_emit + 1
            su_last_retire = max(su_last_retire, last_emit + depth) if su_cls == cls else last_emit + depth
            su_cls = cls
            idle[unit] = max(idle[unit], su_last_retire + (k["su_red"] if f["red"] else k["su_idle"]))
            if f0.get("red_tree"):
                idle[unit] += k["su_tree"]
                free[unit] = idle[unit] + k["su_tree_free"]
        elif unit == I.UNIT_QE:
            c = s + k["qe_start"] + (k["qe_idx"] if f["qe_ind"] else 0) + f["qe_nb"]
            if f["qe_mode"] == I.QE_LINQ:
                if cfg.mac_rate:
                    c += max(math.ceil(f0["_macs"] / cfg.mac_rate), mv_floor(f["qe_nb"] * 32))
                else:
                    c += k["qe_load"]
                    c += (4 - (c + t0 + k["qe_phase0"])) % IL
                    c += f["qe_tiles"] * f["qe_nb"] * IL
                done = c + k["qe_rows_lat"]
            else:
                done = c + k["qe_qdq_lat"]
            free[unit] = done
            idle[unit] = done + 1
        else:
            op = f["xu_op"]
            if op == I.XU_SEL:
                nn = f["xu_n"] + D(f["xu_d_n"])
                kk = min(f["xu_k"] + D(f["xu_d_k"]), nn)
                if cfg.sel_lanes:
                    beats = cdiv(nn, cfg.sel_lanes)
                    done = s + beats + 2 * beats + TS_LAT0
                else:
                    done = s + nn + kk + k["xu_sel"]
            elif op == I.XU_SINK:
                done = s + (0 if cfg.sinkhorn_free else 41 * k["sk_step"] + k["xu_skmc"])
            elif op == I.XU_EHASH:
                done = s + k["xu_ehash"]
            else:
                done = s + 24 + k["xu_egather"]
            free[unit] = done
            idle[unit] = done + 1
        busy[unit] += idle[unit] - s if unit != I.UNIT_SU else free[unit] - s
        if cfg.scoreboard:
            for r in f0.get("_writes", ()):
                wdone[r] = (idle[unit], unit)
            for r in f0.get("_reads", ()):
                rdone[r] = (max(rdone.get(r, (0, 0))[0], free[unit]), unit)
        stall[why] = stall.get(why, 0) + go - t_prev
        t_prev = go
        t = go + k["gap"]
    if stats is not None:
        stats.update(busy={name: busy[u] for name, u in (("ME", 1), ("SU", 2), ("QE", 3), ("XU", 4), ("HE", 5))},
                     issued=n_issued, skipped=n_skipped, time_by_binding=stall)
    return t


# -- validation --------------------------------------------------------------------------------------------
KEYS = ("unit", "wait", "pred", "su_chase", "su_vec", "su_nout", "su_nin", "red", "red_tree", "sfu", "m1", "m2",
        "qm", "ad", "e1", "e2", "me_tiles", "me_k", "me_nout", "me_hg", "qe_mode", "qe_nb", "qe_tiles", "qe_ind",
        "xu_op", "xu_n", "xu_k", "he_k", "he_nout")


def resolved(f, pos, shape):
    ivals, dv = I.dyn_values(0, pos), dyn_values(shape, pos)
    D = lambda sel: ivals[sel] if isinstance(sel, int) else resolve(sel, dv)   # noqa: E731
    out = {x: f.get(x, 0) for x in KEYS}
    for x, d in (("su_nout", "su_d_nout"), ("su_nin", "su_d_nin"), ("me_nout", "me_d_nout"),
                 ("me_tiles", "me_d_tiles"), ("me_k", "me_d_k"), ("xu_n", "xu_d_n"), ("xu_k", "xu_d_k")):
        out[x] = out[x] + D(f.get(d, 0))
    return out


def validate(pos=7, real=None, lanes=None, layout=None):
    """The emitter at the reduced shape against the real builder (hdc_program_v41.Builder), at a stream-unit
    width (default the ISA's).  `real`: a prebuilt program at that width; `layout`: a prebuilt Layout."""
    lanes = lanes or I.SU_LANES
    old = I.SU_LANES
    I.SU_LANES = lanes
    try:
        if real is None:
            if layout is None:
                import hdc_golden_v41 as V
                layout = P.Layout(V.Model())
            real = P.Builder(layout).build()
        c_ref = T.simulate(real, pos)
    finally:
        I.SU_LANES = old
    mine = build(REDUCED, su_lanes=lanes)
    assert len(mine) == len(real), (len(mine), len(real))
    diffs = []
    for i, (a, b) in enumerate(zip(real, mine)):
        ra, rb = resolved(a, pos, REDUCED), resolved(b, pos, REDUCED)
        if ra != rb:
            diffs.append(dict(i=i, tag=a.get("_tag"), real={x: ra[x] for x in ra if ra[x] != rb[x]},
                              mine={x: rb[x] for x in ra if ra[x] != rb[x]}))
    c_real = simulate(real, pos, REDUCED, Cfg(su_lanes=lanes))
    c_mine = simulate(mine, pos, REDUCED, Cfg(su_lanes=lanes))
    return dict(pos=pos, su_lanes=lanes, instructions=len(real), field_mismatches=len(diffs),
                first_mismatches=diffs[:5], hdc_timing_v41=c_ref, this_simulate_real_program=c_real,
                this_simulate_emitted_program=c_mine, exact=not diffs and c_ref == c_real == c_mine)


# -- shipped replay and reconciliation ---------------------------------------------------------------------
def layer_types():
    """Representative layers: (label, layer)."""
    return [("swa (0)", 0), ("swa+engram (1)", 1), ("csa2 r2 source+index (2)", 2), ("r2 reuse (3)", 3),
            ("r2 source+index+engram (14)", 14), ("r1 source+index+cand (20)", 20), ("r1 reuse (21)", 21),
            ("r1 reindex (24)", 24)]


def price(shape, pos, cfg, engram_inline=True, progs=None):
    key = (cfg.su_lanes, engram_inline)
    if progs is not None and key in progs:
        prog = progs[key]
    else:
        prog = build(shape, cfg.su_lanes, engram_inline)
        if progs is not None:
            progs[key] = prog
    st = {}
    cyc = simulate(prog, pos, shape, cfg, stats=st)
    return cyc, st


def per_layer(shape, pos, cfg, engram_inline=True):
    out = {}
    for label, L in layer_types():
        prog = build(shape, cfg.su_lanes, engram_inline, layers=[L], embed=False, head=False)
        st = {}
        cyc = simulate(prog, pos, shape, cfg, stats=st)
        out[label] = dict(cycles=cyc, instructions=st["issued"], skipped=st["skipped"], busy=st["busy"])
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--validate", action="store_true")
    ap.add_argument("--out", type=Path, default=OUT)
    a = ap.parse_args()
    dag = json.loads(DAG.read_text())
    clock = dag["clock"]["hz"]
    ob = dag["packaging_options"]["options"]["b_two_die_group4_across_pair"]
    comm_us = sum(ob["batch1"]["breakdown_us"][x] for x in ("collective_latency", "collective_bytes", "pipeline_hops"))
    rate = dag["deepseek_v41_flash"]["array_batch1"]["mac_rate_per_die"] / clock
    rec = dict(schema=SCHEMA, tool="tools/hdc_replay_v41.py", clock_hz=clock, reduced_shape=REDUCED,
               shipped_shape=SHIPPED, dag_mac_per_cycle_per_die=rate, dag_su_lanes=512,
               comm_us_per_token_from_dag=comm_us,
               comm_note="collective latency + collective bytes + pipeline hops of the DAG's option (b) batch-1 "
                         "path at 200k, added to B and C at every context (link terms do not depend on context)")
    if a.validate:
        import hdc_golden_v41 as V
        lay = P.Layout(V.Model())
        rec["validation"] = [validate(lanes=w, layout=lay) for w in (4, 8, 16, 64)]
        for v in rec["validation"]:
            print({x: v[x] for x in ("su_lanes", "instructions", "field_mismatches", "hdc_timing_v41",
                                     "this_simulate_emitted_program", "exact")})
    C = Cfg()
    B = Cfg(su_lanes=512, mac_rate=rate, kv_rate=rate, sel_lanes=64)
    contexts = (8192, 200000, 1048576)
    progs = {}
    rows = {}
    for ctx in contexts:
        pos = ctx - 1
        r = dict(A=dict(tokens_s_per_user=ob["by_context"][str(ctx)]["batch1"]["tokens_s_per_user"]))
        r["A"]["us_per_token"] = 1e6 / r["A"]["tokens_s_per_user"]
        for name, cfg, eng in (("B", B, False), ("C", C, True)):
            cyc, st = price(SHIPPED, pos, cfg, eng, progs)
            us = cyc / clock * 1e6 + comm_us
            r[name] = dict(compute_cycles=cyc, compute_us=cyc / clock * 1e6, us_per_token=us,
                           tokens_s_per_user=1e6 / us, instructions=st["issued"], busy_cycles=st["busy"],
                           sequencer_time_by_binding_cycles=st["time_by_binding"])
        rows[str(ctx)] = r
        print(ctx, {n: round(r[n]["tokens_s_per_user"], 2) for n in "ABC"},
              {n: round(r[n]["us_per_token"], 1) for n in "ABC"})
    rec["three_layer"] = rows
    if "200000" in rows:
        rec["dag_breakdown_us_200k"] = ob["batch1"]["breakdown_us"]
    # attribution at 200k: one factor at a time, both directions
    pos = 199999
    factors = dict(
        su_width=(dict(su_lanes=512), dict(su_lanes=8)),
        matvec_width=(dict(mac_rate=rate), dict(mac_rate=0.0)),
        attention_indexer_mapping=(dict(kv_rate=rate), dict(kv_rate=0.0)),
        select=(dict(sel_lanes=64), dict(sel_lanes=0)),
    )
    base_c, _ = price(SHIPPED, pos, C, True, progs)
    base_b, _ = price(SHIPPED, pos, B, False, progs)
    att = {}
    for name, (dagv, built) in factors.items():
        c_fixed, _ = price(SHIPPED, pos, replace(C, **dagv), True, progs)
        b_broken, _ = price(SHIPPED, pos, replace(B, **built), False, progs)
        att[name] = dict(from_C_fix_this_saves_us=(base_c - c_fixed) / clock * 1e6,
                         from_B_break_this_costs_us=(b_broken - base_b) / clock * 1e6)
    c_fixed, _ = price(SHIPPED, pos, C, False, progs)
    b_broken, _ = price(SHIPPED, pos, B, True, progs)
    att["engram_inline_vs_prefetched"] = dict(from_C_fix_this_saves_us=(base_c - c_fixed) / clock * 1e6,
                                              from_B_break_this_costs_us=(b_broken - base_b) / clock * 1e6)
    for name, dagv, built in (("ordered_reductions_vs_lane_parallel", dict(red_parallel=True), {}),
                              ("drains_vs_scoreboard", dict(scoreboard=True), dict(scoreboard=False)),
                              ("issue_gap_6_vs_1", dict(gap=1), dict(gap=6)),
                              ("sinkhorn_vs_free", dict(sinkhorn_free=True), dict(sinkhorn_free=False))):
        c_fixed, _ = price(SHIPPED, pos, replace(C, **dagv), True, progs)
        b_fixed, _ = price(SHIPPED, pos, replace(B, **dagv), False, progs)
        att[name] = dict(in_C_us=(base_c - c_fixed) / clock * 1e6, in_B_us=(base_b - b_fixed) / clock * 1e6)
    rec["attribution_200k"] = att
    rec["attribution_note"] = ("one factor switched at a time; from_C_fix: C with that factor at the DAG's value; "
                               "from_B_break: B with that factor as built. Non-additive: factors interact through "
                               "the overlap of units (the slowest unit hides the others). drains/gap/sinkhorn are "
                               "not DAG-vs-built width factors: they report what an idealised option removes "
                               "inside each configuration (scoreboard = wait for the producing op's region, not the "
                               "whole unit's drain).")
    rec["per_layer_200k"] = dict(C=per_layer(SHIPPED, pos, C, True), B=per_layer(SHIPPED, pos, B, False))
    # B with the golden's reduction order relaxed, then also a region scoreboard, then a 1-cycle issue gap
    Bx = replace(B, red_parallel=True)
    rec["B_variants"] = {}
    for ctx in contexts:
        row = {}
        for name, cfg in (("B_red_parallel", Bx), ("B_red_parallel_scoreboard", replace(Bx, scoreboard=True)),
                          ("B_red_parallel_scoreboard_gap1", replace(Bx, scoreboard=True, gap=1))):
            cyc, st = price(SHIPPED, ctx - 1, cfg, False, progs)
            us = cyc / clock * 1e6 + comm_us
            row[name] = dict(compute_us=cyc / clock * 1e6, us_per_token=us, tokens_s_per_user=1e6 / us,
                             busy_cycles=st["busy"], sequencer_time_by_binding_cycles=st["time_by_binding"])
        rec["B_variants"][str(ctx)] = row
        print(ctx, {k: round(v["tokens_s_per_user"], 1) for k, v in row.items()})
    rec["per_layer_200k"]["B_red_parallel"] = per_layer(SHIPPED, pos, Bx, False)
    rec["estimated_ops"] = [
        "layer-20 candidate blocks: an SU block-max (RED_MAX over 8) + an XU select of top-2048 of the die's blocks "
        "(ot_hdc_tselect_cand is separate RTL; the core program keeps every block at the reduced shape)",
        "cross-die final index select over tp x 512 on the XU (collective not in the ISA; the all-gather itself "
        "is in the DAG's communication term)",
        "every op's count exceeds the as-built memories (VM 65,536 elements, KV 32,768 words, 16-bit counts): "
        "priced by the unit models from their counts, not encodable in the as-built ISA",
        "per-die wo_a as one block-diagonal ME matrix (2 of 8 o-groups) instead of the one-group-per-slot "
        "placement (which would idle 6 of 8 slots on a die)",
        "KV-sourced head-group ops with 16 heads per die use hg = 1 (H = 2 head groups of G/2 lane groups)",
        "collectives, hops, and the all-gathered vectors: not in the core ISA; the DAG's per-token communication "
        "is added",
    ]
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1, default=str))
    print("wrote", a.out)


if __name__ == "__main__":
    main()
