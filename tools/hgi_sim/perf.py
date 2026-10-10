#!/usr/bin/env python3
"""hgi_perf: a FAST performance simulator for any model on the generic HBM die (HGI-1 records, timing only).

    python3 -m hgi_sim.perf --config CONFIG.json [--ctx 8192] [--tp 4] [--batch 1] [--out REC.json]
    python3 -m hgi_sim.perf --validate --out results/arch/hgi_perf_20261009/validation.json
    python3 -m hgi_sim.perf --survey DIR_OF_CONFIGS --out results/arch/hgi_perf_20261009/survey.json

WHAT IT RUNS.  The same kind of HGI-1 record stream the bit-exact compilers emit (unit, op, every operand as a memory
descriptor with its real shape and format, wait masks from region hazards), but no arithmetic: a generic front end
maps a Hugging Face config.json onto per-layer specs (mixer: GQA / sliding-window GQA / MLA / MLA + DSA indexer /
Gated-DeltaNet-style linear attention; FFN: dense GLU / MoE with shared experts) and a generic lowering emits the
records of each layer type with the 28+ op families of spec 7.2 (MoE experts through indexed SM descriptors over the
IDX.TOPK ids, GDN through tools/hgi_sim/gdn.py's lowering).  hgi_sim.timing schedules them: event-driven per-unit
queues, the command processor (fetch, decode, wait masks, in-order dispatch, head-of-line blocking, wires).

COSTS (1.2 GHz cycles): hgi_sim.timing.cost -- SM lines on the measured BF16-lane rate (13 exact sm_v RTL cases) or
the HBM stream, whichever binds; HBM at the measured sustained 3,166.7 B / cycle a die (95 % of 4.0 TB/s, refresh and
bank effects included) with the measured first access (worst of 64 refresh phases); SU by the measured-depth model
(== RTL emit -> write for every op class); ATT tile fixed 225 (measured) + the row stream -- plus the collective model
measured on the TU endpoint RTL (results/rtl/dshbm_1m_allmeasured_20261004/collectives.json: endpoint cycles a flit,
the labelled crossing budget, the striping tail) for groups beyond one package, and the in-package TP <= 8 all-reduce
calibration (1,350 cycles at 1 KB) plus serialisation.  Estimates stay labelled (calibration.json grades).

SPEED.  A layer type is simulated alone, not the whole model: the token time is composed from the schedule of the
embedding + one layer of each type + the head, plus (count - 1) x the steady-state increment of each layer type
(measured by scheduling two consecutive layers of that type), exactly as the per-stage benches compose (AGENTS:
simulate the minimum component).  Seconds per model on one core.

BATCH.  b users share every dense weight read (SM.MATVEC param[4:2] positions: up to 8 slots a weight pass; the lane
array still issues every slot's MACs); routed experts are read per user (b x top-k distinct experts, conservative while
b x top-k << experts); attention, KV, SU and collective payloads scale with b.  Per-user rate = 1 / step time; aggregate = b / step time.
"""
from __future__ import annotations

import argparse
import copy
import datetime
import hashlib
import json
import math
import sys
import time
from collections import Counter
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))
import hdc_isa_v41 as I  # noqa: E402

from hgi_sim import timing as T  # noqa: E402
from hgi_sim.qwen_compiler import Builder, assign_waits, sut  # noqa: E402
from hgi_sim.records import DYN, MDesc, Rec  # noqa: E402

CLK = 1.2e9
FLT_MAX = 0x7F7FFFFF
DIE_HBM_GB = 144.0                 # the r25 die's HBM (model-survey capacity basis: 144 GB a die, 4 GB reserve)
DIE_RESERVE_GB = 4.0
GROUPS = (1, 2, 4, 8, 16, 32, 64, 96)


# ----------------------------------------------------------------------------------------------------------------
# front end: HF config -> per-layer specs
# ----------------------------------------------------------------------------------------------------------------
def g(c, *keys, default=None):
    for k in keys:
        if k in c and c[k] is not None:
            return c[k]
    return default


def from_params_json(p):
    """Mistral params.json -> the Hugging Face key names the front end reads."""
    moe = p.get("moe") or {}
    c = dict(model_type="mistral_params", hidden_size=p["dim"], num_hidden_layers=p["n_layers"],
             num_attention_heads=p["n_heads"], num_key_value_heads=p.get("n_kv_heads", p["n_heads"]),
             head_dim=p.get("head_dim"), intermediate_size=p.get("hidden_dim"), vocab_size=p.get("vocab_size", 131072),
             max_position_embeddings=p.get("max_position_embeddings", 131072),
             tie_word_embeddings=p.get("tied_embeddings", False))
    if p.get("kv_lora_rank"):
        c.update(kv_lora_rank=p["kv_lora_rank"], q_lora_rank=p.get("q_lora_rank", 0),
                 qk_nope_head_dim=p.get("qk_nope_head_dim", 128), qk_rope_head_dim=p.get("qk_rope_head_dim", 64),
                 v_head_dim=p.get("v_head_dim", 128))
    if moe:
        c.update(num_experts=moe["num_experts"], num_experts_per_tok=moe["num_experts_per_tok"],
                 moe_intermediate_size=moe.get("expert_hidden_dim", p.get("hidden_dim")),
                 n_shared_experts=moe.get("num_shared_experts", 0), first_k_dense_replace=moe.get(
                     "first_k_dense_replace", 0))
    return c


def arch_from_config(cfg, name=""):
    """Map a Hugging Face config.json (or params.json) onto the generic families.  Returns (arch, notes)."""
    if "dim" in cfg and "n_layers" in cfg and "hidden_size" not in cfg:
        cfg = from_params_json(cfg)
    c = cfg.get("text_config") or cfg.get("language_config") or cfg
    if "llm_config" in cfg:
        c = cfg["llm_config"]
    notes = []
    H = g(c, "hidden_size", "dim", "d_model")
    L = g(c, "num_hidden_layers", "n_layers", "num_layers")
    V = g(c, "vocab_size", "padded_vocab_size")
    nq = g(c, "num_attention_heads", "n_heads")
    nkv = g(c, "num_key_value_heads", "n_kv_heads", "num_attention_groups", default=nq)
    hd = g(c, "head_dim", default=(H // nq) if nq else None)
    if hd is None or isinstance(hd, (list, dict)):
        hd = H // nq
    win = g(c, "sliding_window", default=0) or 0
    ctx_max = g(c, "max_position_embeddings", "max_seq_len", "model_max_length", default=131072)
    qk_norm = bool(g(c, "use_qk_norm", "qk_norm", default=False)) or c.get("model_type", "").startswith("qwen3")
    gate = bool(g(c, "attn_output_gate", "use_head_wise_attn_gate", "mla_use_output_gate", default=False))
    # MLA / DSA
    mla = None
    if g(c, "kv_lora_rank", default=None):
        mla = dict(q_lora=g(c, "q_lora_rank", default=0) or 0, kv_lora=c["kv_lora_rank"],
                   nope=g(c, "qk_nope_head_dim", default=128), rope=g(c, "qk_rope_head_dim", default=64),
                   v=g(c, "v_head_dim", default=128))
    idx = None
    if g(c, "index_topk", "index_n_heads", default=None):
        idx = dict(heads=g(c, "index_n_heads", default=64), dim=g(c, "index_head_dim", default=128),
                   topk=g(c, "index_topk", default=2048))
    # DeepSeek-V4-style hybrid (shared latent KV, window + compressed selection)
    ds4 = "compress_ratios" in c or "compress_ratio" in c
    if ds4:
        mla = mla or dict(q_lora=g(c, "q_lora_rank", default=1024), kv_lora=g(c, "head_dim", default=512), nope=448,
                          rope=g(c, "qk_rope_head_dim", "rope_head_dim", default=64), v=g(c, "head_dim", default=512))
        win = g(c, "sliding_window", "window_size", default=128)
        idx = idx or dict(heads=g(c, "index_n_heads", default=64), dim=g(c, "index_head_dim", default=128),
                          topk=g(c, "index_topk", default=512))
        notes.append("DS-V4 hybrid mapped to MLA-style shared latent (window + indexer-selected compressed rows); "
                     "HC, Engram, compressor and MTP not modelled")
    # linear attention
    lin = None
    if g(c, "linear_num_value_heads", default=None):
        lin = dict(kind="gdn", nk=c["linear_num_key_heads"], nv=c["linear_num_value_heads"],
                   dk=c["linear_key_head_dim"], dv=c["linear_value_head_dim"], conv=g(c, "linear_conv_kernel_dim",
                                                                                      default=4))
    lacfg = c.get("linear_attn_config") or {}
    if lacfg:
        lin = dict(kind=lacfg.get("kda") and "kda" or "linear", nk=lacfg.get("num_heads", nq),
                   nv=lacfg.get("num_heads", nq), dk=lacfg.get("head_dim", 128), dv=lacfg.get("head_dim", 128),
                   conv=lacfg.get("short_conv_kernel_size", 4))
        notes.append("KDA / linear attention lowered as Gated-DeltaNet (same state traffic and SU work per head)")
    # layer types
    types = g(c, "layer_types", default=None)
    if not types and lin:
        fi = g(c, "full_attention_interval", default=4)
        types = ["full_attention" if (i + 1) % fi == 0 else "linear_attention" for i in range(L)]
    if not types and lacfg.get("full_attn_layers"):
        full = {x - 1 for x in lacfg["full_attn_layers"]}           # Kimi: 1-based
        types = ["full_attention" if i in full else "linear_attention" for i in range(L)]
    if not types and g(c, "attention_type_pattern", default=None):
        types = c["attention_type_pattern"]
    types = list(types or ["full_attention"] * L)[:L]
    # FFN
    E = g(c, "n_routed_experts", "num_experts", "num_local_experts", "moe_num_experts", "n_experts", default=0) or 0
    if isinstance(E, list):
        E = E[0]
    topk = g(c, "num_experts_per_tok", "num_experts_per_token", "moe_topk", "moe_top_k", "top_k", "experts_per_token",
             "moe_k", default=0) or 0
    if isinstance(topk, list):
        topk = topk[0]
    inter = g(c, "intermediate_size", "ffn_hidden_size", "ffn_dim", default=4 * H)
    minter = g(c, "moe_intermediate_size", "expert_ffn_hidden_size", "moe_ffn_hidden_size", default=inter)
    shared = g(c, "n_shared_experts", "num_shared_experts", "moe_num_shared_experts", default=0) or 0
    sinter = g(c, "shared_expert_intermediate_size", "share_expert_dim", default=None) or (minter * shared if shared
                                                                                            else 0)
    first_dense = g(c, "first_k_dense_replace", "first_k_dense", "moe_layer_start_index", default=0) or 0
    if isinstance(first_dense, list):
        first_dense = 0
    freq = g(c, "moe_layer_freq", default=1) or 1
    mlp_only = set(g(c, "mlp_only_layers", default=[]) or [])
    if isinstance(c.get("moe_layers_enum"), str) and c["moe_layers_enum"]:
        moe_set = {int(x) for x in c["moe_layers_enum"].split(",")}
        mlp_only |= {i for i in range(L) if i not in moe_set}
    layers = []
    for i in range(L):
        t = types[i]
        if t in ("linear_attention", "linear", "kda", "lightning") and lin:
            mixer = dict(kind="gdn", **{k: v for k, v in lin.items() if k != "kind"})
        elif mla:
            mixer = dict(kind="mla", heads=nq, **mla, idx=idx, window=win if ds4 else 0)
        else:
            w = win if (t in ("sliding_attention", "sliding_window", "swa") or (win and not g(
                c, "layer_types", default=None) and g(c, "use_sliding_window", default=True) and
                c.get("model_type") in ("mistral",))) else 0
            mixer = dict(kind="gqa", heads=nq, kv=nkv, hd=hd, window=w, qk_norm=qk_norm, gate=gate)
        moe = E and topk and i >= first_dense and (i % freq == 0 if isinstance(freq, int) else True) \
            and i not in mlp_only
        ffn = dict(kind="moe", experts=E, topk=topk, inter=minter, shared_inter=sinter) if moe else \
            dict(kind="dense", inter=inter)
        layers.append(dict(mixer=mixer, ffn=ffn))
    tied = bool(g(c, "tie_word_embeddings", default=False))
    q = cfg.get("quantization_config") or c.get("quantization_config") or {}
    efmt = "fp4" if (c.get("expert_dtype") == "fp4" or q.get("quant_method") == "mxfp4" or
                     "mxfp4" in str(q.get("format", ""))) else "fp8"
    params = param_count(H, V, layers, tied)
    arch = dict(name=name, hidden=H, layers=layers, vocab=V, ctx_max=ctx_max, params=params, tied=tied,
                mtp=g(c, "num_nextn_predict_layers", "mtp_num_hidden_layers", default=0), wfmt="fp8", efmt=efmt)
    return arch, notes


def mixer_params(H, m):
    k = m["kind"]
    if k == "gqa":
        return H * (m["heads"] + 2 * m["kv"]) * m["hd"] + m["heads"] * m["hd"] * H + (H * m["heads"] * m["hd"]
                                                                                      if m["gate"] else 0)
    if k == "mla":
        q = (H * m["q_lora"] + m["q_lora"] * m["heads"] * (m["nope"] + m["rope"])) if m["q_lora"] else \
            H * m["heads"] * (m["nope"] + m["rope"])
        kv = H * (m["kv_lora"] + m["rope"]) + m["kv_lora"] * m["heads"] * (m["nope"] + m["v"])
        ix = (H * m["idx"]["heads"] * m["idx"]["dim"] + H * m["idx"]["dim"]) if m.get("idx") else 0
        return q + kv + m["heads"] * m["v"] * H + ix
    if k == "gdn":
        return H * (2 * m["nk"] * m["dk"] + 2 * m["nv"] * m["dv"] + 2 * m["nv"]) + m["nv"] * m["dv"] * H
    return 0


def param_count(H, V, layers, tied):
    tot = V * H * (1 if tied else 2)
    act = V * H * (1 if tied else 2)
    for ly in layers:
        mp = mixer_params(H, ly["mixer"])
        f = ly["ffn"]
        if f["kind"] == "dense":
            fp = fa = 3 * H * f["inter"]
        else:
            fp = 3 * H * f["inter"] * f["experts"] + 3 * H * f["shared_inter"] + H * f["experts"]
            fa = 3 * H * f["inter"] * f["topk"] + 3 * H * f["shared_inter"] + H * f["experts"]
        tot += mp + fp
        act += mp + fa
    return dict(total=tot, active=act)


def kv_bytes_per_pos(arch):
    """FP8 KV bytes a position over all layers (the whole model, before TP)."""
    b = 0
    for ly in arch["layers"]:
        m = ly["mixer"]
        if m["kind"] == "gqa":
            b += 2 * m["kv"] * m["hd"]
        elif m["kind"] == "mla":
            b += m["kv_lora"] + m["rope"] + (m["idx"]["dim"] if m.get("idx") else 0)
    return b


def state_bytes(arch):
    b = 0
    for ly in arch["layers"]:
        m = ly["mixer"]
        if m["kind"] == "gdn":
            b += 4 * m["nv"] * m["dk"] * m["dv"] + 4 * (m["conv"] - 1) * (2 * m["nk"] * m["dk"] + m["nv"] * m["dv"])
    return b


def choose_tp(arch, ctx, batch=1):
    """The smallest legal group whose per-die weights (8-bit) + KV (FP8, replicated latent for MLA) + state fit."""
    for tp in GROUPS:
        w = arch["params"]["total"] / tp                                       # 8-bit weights, 1 B a parameter
        kv = 0
        for ly in arch["layers"]:
            m = ly["mixer"]
            if m["kind"] == "gqa":
                kv += 2 * max(1, m["kv"] // tp) * m["hd"] * min(ctx, m["window"] or ctx)
            elif m["kind"] == "mla":
                kv += (m["kv_lora"] + m["rope"]) * min(ctx, ctx) + (m["idx"]["dim"] * ctx / tp if m.get("idx") else 0)
        kv *= batch
        st = state_bytes(arch) / tp * batch
        if (w + kv + st) / 1e9 <= DIE_HBM_GB - DIE_RESERVE_GB:
            return tp, (w + kv + st) / 1e9
    return None, None


# ----------------------------------------------------------------------------------------------------------------
# generic lowering (timing only: descriptors carry the real shapes and formats)
# ----------------------------------------------------------------------------------------------------------------
SMFMT = {"int8": (3, "INT8"), "fp8": (1, "FP8E4M3"), "fp4": (2, "FP4E2M1"), "bf16": (0, "BF16")}


class Em:
    def __init__(self, H, tp, ctx, batch=1, wfmt="fp8", efmt="fp8"):
        self.H, self.tp, self.ctx, self.batch, self.wfmt, self.efmt = H, tp, ctx, batch, wfmt, efmt
        self.b = Builder(None)
        self.vm, self.vcur = {}, 0
        self.hcur = 1 << 32

    def V(self, name, n, m=1, stride=0, ibcast=0, n_sel=0, fmt="FP32"):
        if name not in self.vm:
            self.vm[name] = self.vcur
            self.vcur += max(n * m, 1) + 64
        return MDesc(space="VM", fmt=fmt, base=self.vm[name], n=n, m=m, stride=stride, ibcast=ibcast, n_sel=n_sel)

    def W(self, n, m, fmt="INT8", **kw):
        es = {"INT8": 1, "BF16": 2, "FP32": 4, "FP8E4M3": 1, "FP4E2M1": 0.5}[fmt]
        base = self.hcur
        self.hcur += -(-int(n * m * es) // 4096) * 4096 + 4096
        return MDesc(space="HBM", fmt=fmt, base=base, n=n, m=m, stride=-(-int(n * es) // 32) * 32, **kw)

    def add(self, rec, rd, wr, fam):
        rec.family = rec.family or fam
        rec.tag = rec.tag or fam
        self.b.add(rec, rd, wr)

    # -- primitives ----------------------------------------------------------------------------------------------
    def norm(self, x, n, out, fam, seg=0, fmt="BF16"):
        self.add(Rec("FUSED", "ROW_NORM", param=(max(n // 128, 1) & 0x3F) | (seg << 6), imm_a=0x358637BD,
                     desc=dict(A=self.V(x, n), B=self.W(seg or n, 1, "BF16"), O=self.V(out, n, fmt=fmt))),
                 [x], [out], fam)

    def mv(self, x, K, rows, out, fam, indexed=False, idt="EID", wfmt=None):
        code, fmt = SMFMT[wfmt or (self.efmt if indexed else self.wfmt)]
        B = self.W(K, max(rows, 1), fmt, indexed=int(indexed), dyn_mul=K * max(rows, 1) if indexed else 0)
        d = dict(A=self.V(x, K), B=B, O=self.V(out, max(rows, 1)))
        if indexed:
            d["I"] = self.V(idt, 1, fmt="U32")
        pos = min(self.batch, 8)
        self.add(Rec("SM", "MATVEC", param=code | ((pos - 1) << 2), desc=d), [x] + ([idt] if indexed else []), [out],
                 fam)

    def mv_split(self, x, K, rows, out, fam):
        """A projection every die needs whole (MLA q_a / kv_a, the indexer query, the router): each die computes
        its even share of the rows, then an all-gather (the DS lowering), when that beats replicating it."""
        if self.tp > 1 and rows >= 256:
            self.mv(x, K, -(-rows // self.tp), out + "p", fam)
            self.coll("ALL_GATHER", rows, out + "p", out, fam + "_gather")
        else:
            self.mv(x, K, rows, out, fam)

    def su(self, A_, n, out, fam, reads=(), m=1, R=None, **t):
        d = dict(A=self.V(A_, n, m=m, stride=n))
        if out:
            d["O"] = self.V(out, n, m=m, stride=n)
        if R:
            d["R"] = self.V(R, 1, m=m, stride=1)
        self.add(Rec("SU", "VOP", sut=sut(dst=I.DST_VM if out else 0, **t), desc=d), [A_, *reads],
                 [x for x in (out, R) if x], fam)

    def coll(self, op, n, buf, out, fam):
        self.add(Rec("COLL", op, desc=dict(A=self.V(buf, n), O=self.V(out, n))), [buf], [out], fam)

    def att(self, lanes, hd, rows, kv_hbm_rows, fam, tag, src="QB", out="SC", fmt="FP8E4M3"):
        B = MDesc(space="HBM", fmt=fmt, base=self.hcur, n=rows, m=1, stride=hd)
        self.hcur += -(-kv_hbm_rows * hd // 4096) * 4096 + 4096
        self.add(Rec("ATT", "QK", param=min(lanes, 15) | ((max(hd // 64, 1) - 1) << 4),
                     desc=dict(A=self.V(src, hd, m=lanes, stride=hd), B=B, O=self.V(out, rows, m=lanes, stride=rows))),
                 [src, "KV"], [out], fam)
        self.add(Rec("ATT", "PV", param=min(lanes, 15) | ((max(hd // 64, 1) - 1) << 4),
                     desc=dict(A=self.V(out, rows, m=lanes, stride=rows), B=B, O=self.V("PV", hd, m=lanes, stride=hd))),
                 [out, "KV"], ["PV"], fam)

    # -- blocks ----------------------------------------------------------------------------------------------------
    def embed(self):
        H = self.H
        self.add(Rec("DMA", "LOAD", desc=dict(A=MDesc(space="HBM", fmt="INT8", base=1 << 30, n=H, dyn_sel=DYN["TOKEN"],
                                                      dyn_mul=H + 32), O=self.V("X", H))), [], ["X"], "embedding")
        self.su("X", H, "X", "embedding", m1=I.M1_AB)

    def gqa(self, m):
        H, tp, ctx = self.H, self.tp, self.ctx
        nq = max(1, m["heads"] // tp)
        nk = max(1, m["kv"] // tp)
        hd = m["hd"]
        rows = (nq + 2 * nk) * hd + (nq * hd if m["gate"] else 0)
        P = min(ctx, m["window"] or ctx)
        self.norm("X", H, "H", "prenorm")
        self.mv("H", H, rows, "QKVRAW", "qkv")
        self.su("QKVRAW", rows, "QKV", "row_scale_qkv", m1=I.M1_AB)
        if m["qk_norm"]:
            self.norm("QKV", nq * hd, "QN", "qknorm", seg=hd, fmt="FP32")
            self.norm("QKV", nk * hd, "QN", "qknorm", seg=hd, fmt="FP32")
        self.su("QN" if m["qk_norm"] else "QKV", hd, "QR", "rope", m=nq + nk, c_pair=1, m1=I.M1_AB, qm=I.QM_ALT_NP,
                ad=I.AD_Q)
        self.su("QR", nq * hd, "QB", "round_q", rnd=1)
        for _ in range(2):
            self.add(Rec("DMA", "STORE", desc=dict(A=self.V("QR", hd, m=nk, stride=hd), O=MDesc(
                space="HBM", fmt="FP8E4M3", base=1 << 31, n=hd, m=nk, stride=hd, dyn_sel=DYN["POS"], dyn_mul=hd))),
                ["QR"], ["KV"], "kv_append")
        self.add(Rec("DMA", "FENCE"), [], ["KV"], "kv_fence")
        lanes = max(1, nq // nk)
        for h in range(nk):
            self.att(lanes, hd, P, P, "attention", f"att.kv{h}")
        self.su("SC", P, None, "softmax", m=nq, R="MAX", m1=I.M1_AIMM, red=I.RED_MAX)
        self.su("SC", P, "E", "softmax", reads=["MAX"], m=nq, R="Z", m1=I.M1_AIMM, ad=I.AD_NEGB, sfu=I.SFU_EXP,
                red=I.RED_SUM)
        self.su("E", P, "E", "softmax", m=nq, rnd=1)
        self.su("PV", hd, "ATTN", "pv_normalize", reads=["Z"], m=nq, m1=I.M1_DIVB)
        if m["gate"]:
            self.su("ATTN", nq * hd, "ATTN", "attn_gate", reads=["QKV"], sfu=I.SFU_SIGM, e1=I.E1_MULC)
        self.mv("ATTN", nq * hd, H, "OPART", "o")
        self.out_ar("OPART", "o")

    def out_ar(self, part, fam):
        H = self.H
        if self.tp > 1:
            self.coll("ALL_REDUCE_SUM", H, part, "OSUM", f"all_reduce_{fam}")
            part = "OSUM"
        self.su(part, H, "X", f"row_scale_{fam}+residual", reads=["X"], m1=I.M1_AB, ad=I.AD_C)

    def mla(self, m):
        H, tp, ctx = self.H, self.tp, self.ctx
        nh = max(1, m["heads"] // tp)
        dq = m["nope"] + m["rope"]
        lat = m["kv_lora"] + m["rope"]
        self.norm("X", H, "H", "prenorm")
        if m["q_lora"]:
            self.mv_split("H", H, m["q_lora"], "QA", "q_a")
            self.norm("QA", m["q_lora"], "QAN", "q_a_norm")
            self.mv("QAN", m["q_lora"], nh * dq, "Q", "q_b")
        else:
            self.mv("H", H, nh * dq, "Q", "q")
        self.mv_split("H", H, lat, "KVA", "kv_a")
        self.norm("KVA", m["kv_lora"], "KVN", "kv_norm")
        self.su("KVN", m["rope"], "KVR", "rope", c_pair=1, m1=I.M1_AB, qm=I.QM_ALT_NP, ad=I.AD_Q)
        self.su("Q", m["rope"], "QR", "rope", m=nh, c_pair=1, m1=I.M1_AB, qm=I.QM_ALT_NP, ad=I.AD_Q)
        self.mv("Q", m["nope"], nh * m["kv_lora"], "QL", "absorb_uk")            # q_nope -> latent (W_uk absorbed)
        self.add(Rec("DMA", "STORE", desc=dict(A=self.V("KVR", lat), O=MDesc(
            space="HBM", fmt="FP8E4M3", base=1 << 31, n=lat, dyn_sel=DYN["POS"], dyn_mul=lat))), ["KVR"], ["KV"],
            "kv_append")
        self.add(Rec("DMA", "FENCE"), [], ["KV"], "kv_fence")
        if m.get("idx"):
            ix = m["idx"]
            self.mv_split("QAN" if m["q_lora"] else "H", m["q_lora"] or H, ix["heads"] * ix["dim"], "IQ", "index_q")
            nkeys = -(-ctx // tp)
            k = min(ix["topk"], ctx)
            kl = min(k, nkeys, 2048)
            # G18: one IDX.INDEX frame (query quantiser, scores over the die's keys, local top-k); the key store is
            # the engine's (timing: B describes the keys streamed), O / R the local selection in VM
            self.add(Rec("IDX", "INDEX", param=kl, imm_a=nkeys, desc=dict(
                A=self.V("IQ", ix["heads"] * ix["dim"]), B=MDesc(space="HBM", fmt="FP8E4M3", base=1 << 31,
                                                                  n=ix["dim"], m=nkeys, stride=ix["dim"]),
                O=self.V("IDS", kl, fmt="U32"), R=self.V("ISV", kl))), ["IQ", "KV"], ["IDS", "ISV"], "index_frame")
            self.coll("TOPK_MERGE", 2 * k, "IDS", "SEL", "index_merge")
            P = k + (m.get("window") or 0)
        else:
            P = ctx
        for g0 in range(0, nh, 8):
            self.att(min(8, nh - g0), lat, P, P, "attention", f"att.g{g0}", src="QL")
        self.su("SC", P, None, "softmax", m=nh, R="MAX", m1=I.M1_AIMM, red=I.RED_MAX)
        self.su("SC", P, "E", "softmax", reads=["MAX"], m=nh, R="Z", m1=I.M1_AIMM, ad=I.AD_NEGB, sfu=I.SFU_EXP,
                red=I.RED_SUM)
        self.su("E", P, "E", "softmax", m=nh, rnd=1)
        self.su("PV", m["kv_lora"], "OL", "pv_normalize", reads=["Z"], m=nh, m1=I.M1_DIVB)
        self.mv("OL", m["kv_lora"], nh * m["v"], "ATTN", "absorb_uv")
        self.mv("ATTN", nh * m["v"], H, "OPART", "o")
        self.out_ar("OPART", "o")

    def gdn(self, m, int8=True):
        from hgi_sim import gdn as GD
        c = dict(hidden=self.H, nk=m["nk"], nv=m["nv"], dk=m["dk"], dv=m["dv"], conv=m["conv"], eps=1e-6)
        tp0, GD.VM_CHECK = GD.TP, False
        GD.TP = self.tp if m["nk"] % self.tp == 0 and m["nv"] % self.tp == 0 else max(
            t for t in (1, 2, 4, 8) if m["nk"] % t == 0)
        try:
            recs = GD.program(GD.Geo(c), c["eps"])
        finally:
            GD.TP, GD.VM_CHECK = tp0, True
        for r in recs:
            if r.unit == "CTL" and r.op == "END":
                continue
            if r.unit == "SM" and int8:
                code, fmt = SMFMT[self.wfmt]
                r.param = code | ((min(self.batch, 8) - 1) << 2)
                r.desc["B"].fmt = fmt
                r.desc["B"].stride = r.desc["B"].n
            r.family = r.family or r.tag
            self.b.add(r, getattr(r, "reads", []), getattr(r, "writes", []))

    def ffn(self, f):
        H, tp = self.H, self.tp
        self.norm("X", H, "H", "prenorm")
        if f["kind"] == "dense":
            ff = -(-f["inter"] // tp)
            self.mv("H", H, 2 * ff, "GURAW", "gu")
            self.su("GURAW", 2 * ff, "GU", "row_scale_gu", m1=I.M1_AB)
            self.glu(ff, "swiglu")
            self.mv("ACT", ff, H, "DPART", "down")
            self.out_ar("DPART", "down")
            return
        E, k = f["experts"], f["topk"]
        self.mv_split("H", H, E, "RL", "router")
        self.su("RL", E, "RS", "router_act", sfu=I.SFU_SIGM)
        self.add(Rec("IDX", "TOPK", param=min(k, 2048), desc=dict(A=self.V("RS", E), O=self.V("EID", k, fmt="U32"))),
                 ["RS"], ["EID"], "route")
        self.su("RS", k, "RW", "route_weights", reads=["EID"], red=I.RED_SUM, R="RT", m1=I.M1_DIVB)
        ff = -(-f["inter"] // tp)
        for e in range(k):
            self.mv("H", H, 2 * ff, f"G{e}", "expert_gu", indexed=True)
            self.glu(ff, "expert_swiglu", src=f"G{e}", out=f"A{e}")
            self.mv(f"A{e}", ff, H, f"D{e}", "expert_down", indexed=True)
        if f["shared_inter"]:
            sf = -(-f["shared_inter"] // tp)
            self.mv("H", H, 2 * sf, "SG", "shared_gu")
            self.glu(sf, "shared_swiglu", src="SG", out="SA")
            self.mv("SA", sf, H, "SD", "shared_down")
        for e in range(k):
            self.su(f"D{e}", H, "DPART", "moe_sum", reads=["DPART"], ad=I.AD_C)
        self.out_ar("DPART", "down")

    def glu(self, n, fam, src="GU", out="ACT"):
        self.add(Rec("SFU", "GLU", imm_a=FLT_MAX, desc=dict(A=self.V(src, n), B=self.V(src + "u", n),
                                                            C=self.V("ONE", n, ibcast=1),
                                                            O=self.V(out, n, fmt="BF16"))), [src, "ONE"], [out], fam)

    def head(self, V):
        H, tp = self.H, self.tp
        hr = -(-V // tp)
        self.norm("X", H, "H", "prenorm.final")
        # the logits stream: head matvec -> STREAM 0 -> row scale (SU) -> STREAM 1 -> ARGMAX (no VM round trip)
        code, fmt = SMFMT[self.wfmt]
        S0 = MDesc(space="STREAM", fmt="FP32", base=0, n=hr)
        S1 = MDesc(space="STREAM", fmt="FP32", base=1, n=hr)
        self.add(Rec("SM", "MATVEC", param=code | ((min(self.batch, 8) - 1) << 2), desc=dict(
            A=self.V("H", H), B=self.W(H, max(hr, 1), fmt), O=S0)), ["H"], [], "head")
        self.add(Rec("SU", "VOP", sut=sut(m1=I.M1_AB, dst=I.DST_VM), desc=dict(A=S0, B=self.V("LSCL", hr), O=S1)),
                 ["LSCL"], [], "head_scale")
        self.add(Rec("ARGMAX", "LOCAL", imm_a=hr, desc=dict(A=S1, O=self.V("AMX", 2))), [], ["AMX"], "argmax")
        if tp > 1:
            self.add(Rec("COLL", "ARGMAX_MERGE", desc=dict(A=self.V("AMX", 2), O=self.V("TOK", 1, fmt="U32"))),
                     ["AMX"], ["TOK"], "argmax_merge")
        self.add(Rec("CTL", "END", desc=dict(A=self.V("TOK", 1, fmt="U32"))), ["TOK"], [], "end")

    def layer(self, ly):
        k = ly["mixer"]["kind"]
        getattr(self, k)(ly["mixer"])
        if k == "gdn":
            pass                                 # gdn.program already ends with its residual add
        self.ffn(ly["ffn"])


def layer_key(ly):
    return json.dumps(ly, sort_keys=True)


# ----------------------------------------------------------------------------------------------------------------
# costs: timing.cost + the measured collective model + IDX + batch scaling
# ----------------------------------------------------------------------------------------------------------------
_COLL = None


def coll_classes():
    global _COLL
    if _COLL is None:
        try:
            _COLL = json.loads((ROOT / "results/rtl/dshbm_1m_allmeasured_20261004/collectives.json").read_text())
        except Exception:                                      # noqa: BLE001
            _COLL = {}
    return _COLL


def coll_cycles(op, nbytes, G):
    """Collective latency (1.2 GHz cycles).  G <= 8 (one package, owner tree): the TP4 all-reduce calibration (1,350
    cycles at 1 KB, measured_budget) + endpoint serialisation of the extra flits; G > 8 (TU switch): the measured TU
    endpoint model -- endpoint 108.6 + 23.75 cycles a 64-B flit a rank (fit to the exact ha2hub gather classes),
    one 377.6 ns crossing per gather / two per all-reduce, 0.15 us striping tail."""
    if G <= 1:
        return 0.0, "measured", "no collective (group of 1)"
    f = max(1, math.ceil(nbytes / G / 64))
    if G <= 8:
        f0 = math.ceil(1024 / G / 64)
        base = T.cv("units", "COLL.ALL_REDUCE_SUM") if op == "ALL_REDUCE_SUM" else T.cv("units", "COLL.ARGMAX_MERGE")
        return base + max(0, f - f0) * 13.2 * (2 if op == "ALL_REDUCE_SUM" else 1), "measured_budget", \
            f"in-package {op} G {G}: {f} flits a rank"
    cross = 2 if op in ("ALL_REDUCE_SUM", "GROUP_REDUCE_MCAST") else 1
    ep = (108.6 + 23.75 * f) * (2 if cross == 2 else 1)
    return ep + cross * 377.6e-9 * CLK + 0.15e-6 * CLK, "measured_tu_budget", f"TU {op} G {G}: {f} flits a rank"


_SMT = None


def sm_table():
    global _SMT
    if _SMT is None:
        import dshbm_1m_allmeasured as DA
        _SMT = DA.WC.SMTable([json.loads((DA.ROOT / "results/rtl/w19_sm_real_ops.json").read_text()),
                              json.loads((DA.BASE / "sm_real_ops.json").read_text())], "ar")
    return _SMT


class PerfCost:
    """knobs (SM-binding study only; defaults = the surveyed hardware): sm_fixed scales the per-record SM fixed
    cost (first access + overhead + drain), sm_lines the lane issue (lines), sm_share = slots one weight line serves
    in the MAC array (1 = the lane array issues every slot)."""

    def __init__(self, tp, batch=1, coll_model="measured", ctx=8192, sm_fixed=1.0, sm_lines=1.0, sm_share=1):
        self.tp, self.batch, self.coll_model, self.ctx = tp, batch, coll_model, ctx
        self.sm_fixed, self.sm_lines, self.sm_share = sm_fixed, sm_lines, sm_share
        self.knobs = (sm_fixed, sm_lines, sm_share) != (1.0, 1.0, 1)
        self.sm_parts = Counter()                     # fixed / lines / stream / busy, accumulated per call

    def __call__(self, r, dyn, L):
        u, op, b = r.unit, r.op, self.batch
        if u == "COLL":
            n = r.desc["A"].n if "A" in r.desc else 1
            es = 2 if op != "ARGMAX_MERGE" else 8
            if self.coll_model == "calibration":
                c, gr, how = T.cost(r, dyn, L)
                return c, gr, how
            return coll_cycles(op, n * es * b, self.tp)
        if u == "IDX":
            if op == "INDEX":
                d = r.desc["B"]
                nb = d.n * d.m
                rate = 16 * 4                         # keys a cycle a die: ot_hbm_accel_index_stack 16 / stack x 4
                c = T.first_access() + max(nb / T.cv("hbm", "bytes_per_cycle"), d.m / rate)
                c += 20 + d.m / 16                    # the frame's local top-k over the scores
                return c * b, "measured_rate", f"index frame over {d.m} keys"
            if op == "TOPK":
                n = r.desc["A"].n
                return (20 + n / 16) * b, "estimate", f"top-k over {n}"
            return 100.0 * b, "estimate", op
        if u == "SFU":
            n = r.desc["A"].n
            return max(T.cv("units", "SFU.GLU"), n / 51.2) * b, "estimate", "GLU (60 cycles a 3,072-element die)"
        if u in ("DMA",) and op == "FENCE":
            return T.cost(r, dyn, L)
        if u == "SM" and (r.param & 3) in (1, 2):
            # FP8 / FP4 block-dot: the measured DS SM table (ot_gpu_sm_v lines + drain on real operands) and the
            # supply barrier, as the DS composition walk prices it; each 8-slot pass re-issues the lines
            bd = r.desc["B"]
            _, n, m, _, _ = T.eff(bd, dyn, L)
            lines, drain, hw = sm_table().op("fp8" if (r.param & 3) == 1 else "fp4", n, -(-m // 32))
            stream = n * m * (1.0 if (r.param & 3) == 1 else 0.5) / T.cv("hbm", "bytes_per_cycle")
            per = 1 if bd.indexed else 8          # routed experts: each user its own experts (no shared weight pass)
            c = 0.0
            for p_ in range(0, b, per):
                ln = lines * self.sm_lines * math.ceil(min(per, b - p_) / self.sm_share)
                fx = (drain + 78) * self.sm_fixed
                c += max(ln, stream) + fx
                self.sm_parts.update(fixed=fx, lines=ln, stream=stream, busy=max(ln, stream) + fx)
            return c, "measured", (f"SM {m}x{n} {bd.fmt}: {lines} lines + {drain} drain ({hw}) vs HBM stream "
                                   f"{stream:.0f}")
        if u == "SM" and "SM.bf16_lines_per_row_k" in T.MEAS:
            # BF16 / fmt3 lanes (== timing.cost at batch 1); one weight pass serves up to 8 slots (param[4:2]); the
            # lane array issues every slot's MACs
            bd = r.desc["B"]
            _, n, m, _, _ = T.eff(bd, dyn, L)
            tr = T.TRANSPORT if (r.param & 3) == 3 else 1.0
            stream = n * m * T.ESZ[bd.fmt] * tr / T.cv("hbm", "bytes_per_cycle")
            lines = math.ceil(T.MEAS["SM.bf16_lines_per_row_k"]["value"] * -(-m // 32) * n * T.SM_RATE)
            fa = T.MEAS["hbm.first_access"]["value"] + T.MEAS["SM.overhead"]["value"]
            c = 0.0
            per = 1 if bd.indexed else 8          # routed experts: each user its own experts
            for p_ in range(0, b, per):
                slots = min(per, b - p_)
                ln = lines * self.sm_lines * math.ceil(slots / self.sm_share)
                fx, dr = fa * self.sm_fixed, T.MEAS["SM.drain"]["value"] * self.sm_fixed
                c += fx + max(ln + dr, stream)
                self.sm_parts.update(fixed=fx + dr, lines=ln, stream=stream, busy=fx + max(ln + dr, stream))
            return c, "measured", f"SM {m}x{n}: {math.ceil(b / 8)} weight passes, {b} slots"
        c, gr, how = T.cost(r, dyn, L)
        if u in ("ATT", "SU", "FUSED", "ARGMAX", "DMA"):
            return c * b, gr, how + (f" x {b} users" if b > 1 else "")
        return c, gr, how


# ----------------------------------------------------------------------------------------------------------------
# composition
# ----------------------------------------------------------------------------------------------------------------
def build(arch, tp, ctx, batch, layers_of):
    em = Em(arch["hidden"], tp, ctx, batch, arch.get("wfmt", "fp8"), arch.get("efmt", "fp8"))
    em.embed()
    for ly in layers_of:
        em.layer(ly)
    em.head(arch["vocab"])
    return assign_waits(em.b.recs)


def sched(recs, ctx, cost, mode="S2"):
    s = T.schedule(recs, min(ctx, 1 << 20) - 1, mode, cost_fn=cost)
    s["recs"] = recs
    return s


def simulate(arch, ctx=8192, tp=None, batch=1, coll_model="measured", detail=True, **knobs):
    t0 = time.time()
    if tp is None:
        tp, gb = choose_tp(arch, ctx, batch)
        if tp is None:
            return dict(error="does not fit 96 dies at 8-bit", arch=arch["name"])
    cost = PerfCost(tp, batch, coll_model, ctx, **knobs)
    kinds = {}
    for i, ly in enumerate(arch["layers"]):
        kinds.setdefault(layer_key(ly), []).append(i)
    first = arch["layers"][0]
    base1 = sched(build(arch, tp, ctx, batch, [first]), ctx, cost)
    T1 = base1["total_cycles"]
    inc = {}
    for key, ids in kinds.items():
        ly = arch["layers"][ids[0]]
        s1 = sched(build(arch, tp, ctx, batch, [first, ly]), ctx, cost)
        s2 = sched(build(arch, tp, ctx, batch, [first, ly, ly]), ctx, cost)
        inc[key] = dict(layers=len(ids), first=s1["total_cycles"] - T1, steady=s2["total_cycles"] - s1["total_cycles"],
                        mixer=ly["mixer"]["kind"], ffn=ly["ffn"]["kind"], window=ly["mixer"].get("window", 0),
                        records=len(build(arch, tp, ctx, batch, [ly])) - len(build(arch, tp, ctx, batch, [])),
                        per_unit=s2["per_unit"])
    fk = layer_key(first)
    total = T1 + sum(v["steady"] * (v["layers"] - (1 if key == fk else 0)) for key, v in inc.items())
    step = total
    out = dict(model=arch["name"], ctx=ctx, tp=tp, batch=batch, step_cycles=round(step, 1),
               step_us=round(step / CLK * 1e6, 2), tok_s_per_user=round(CLK / step, 1),
               tok_s_aggregate=round(batch * CLK / step, 1), dies=tp,
               tok_s_aggregate_per_die=round(batch * CLK / step / tp, 2),
               params_B=dict(total=round(arch["params"]["total"] / 1e9, 2),
                             active=round(arch["params"]["active"] / 1e9, 2)),
               layer_types=[dict(mixer=v["mixer"], ffn=v["ffn"], window=v["window"], layers=v["layers"],
                                 cycles_per_layer=round(v["steady"], 1), records_per_layer=v["records"])
                            for v in inc.values()],
               composition="embedding + first layer + head scheduled together, + (count - 1 for the first type) x "
                           "each layer type's steady increment (two consecutive layers scheduled)")
    if detail:
        # unit / op-family busy time weighted by layer counts, and the critical path of one layer of each type
        def busy(s_):
            u_, f_ = Counter(), Counter()
            for i, (k, *_) in enumerate(s_["ex"]):
                dt = s_["end"][i] - s_["start"][i]
                u_[s_["recs"][k].unit] += dt
                f_[s_["recs"][k].family] += dt
            return u_, f_
        base = sched(build(arch, tp, ctx, batch, []), ctx, cost)
        unit, fam = busy(base)
        bu, bf = busy(base)
        for ids in kinds.values():
            tu, tf = busy(sched(build(arch, tp, ctx, batch, [arch["layers"][ids[0]]]), ctx, cost))
            for k in tu:
                unit[k] += (tu[k] - bu.get(k, 0)) * len(ids)
            for k in tf:
                fam[k] += (tf[k] - bf.get(k, 0)) * len(ids)
        out["unit_busy_cycles"] = {k: round(v, 1) for k, v in unit.most_common()}
        out["op_family_busy_cycles"] = {k: round(v, 1) for k, v in fam.most_common(25)}
        rep = [arch["layers"][ids[0]] for ids in kinds.values()]
        recs = build(arch, tp, ctx, batch, rep)
        s = sched(recs, ctx, cost)
        out["critical_path_one_layer_each"] = [dict(tag=x["tag"], unit=x["unit"], start=x["start"], end=x["end"])
                                               for x in T.critical_path(s, recs)[-25:]]
    out["wall_s"] = round(time.time() - t0, 2)
    return out


# ----------------------------------------------------------------------------------------------------------------
# validation against the bit-exact timed runs
# ----------------------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------
# DeepSeek-V4.1: the native record stream as the layer templates (the program that runs bit-exact at 1M)
# ----------------------------------------------------------------------------------------------------------------
DS41_TEMPLATE = ROOT / "results/arch/hgi_perf_20261009/ds41_native_template.json"


# ----------------------------------------------------------------------------------------------------------------
# SM-binding study: why the SM units bind, and what the hardware levers buy per model class
# ----------------------------------------------------------------------------------------------------------------
STUDY_MODELS = [  # (class, config file)
    ("dense small", "Qwen_Qwen3-8B.json"), ("dense mid", "ByteDance-Seed_Seed-OSS-36B-Instruct.json"),
    ("dense large", "mistralai_Devstral-2-123B-Instruct-2512.json"), ("GDN hybrid dense", "Qwen_Qwen3.5-27B.json"),
    ("MoE small (GQA)", "Qwen_Qwen3.6-35B-A3B.json"), ("MoE small (SWA)", "openai_gpt-oss-120b.json"),
    ("MoE large (GQA)", "MiniMaxAI_MiniMax-M2.5.json"), ("MoE large (GDN hybrid)", "Qwen_Qwen3.5-397B-A17B.json"),
    ("MoE MLA", "moonshotai_Kimi-K2.5.json"), ("MoE MLA", "zai-org_GLM-5.json"), ("MoE MLA+DSA", "deepseek-ai_DeepSeek-V3.2.json")]


def sm_parts(arch, ctx, tp, batch, **knobs):
    """Weighted SM component cycles of one token (embedding + layers + head, layer types x their counts)."""
    cost = PerfCost(tp, batch, "measured", ctx, **knobs)
    kinds = {}
    for i, ly in enumerate(arch["layers"]):
        kinds.setdefault(layer_key(ly), []).append(i)
    sched(build(arch, tp, ctx, batch, []), ctx, cost)
    base = Counter(cost.sm_parts)
    tot = Counter(base)
    for ids in kinds.values():
        cost.sm_parts = Counter()
        sched(build(arch, tp, ctx, batch, [arch["layers"][ids[0]]]), ctx, cost)
        for k, v in cost.sm_parts.items():
            tot[k] += (v - base.get(k, 0)) * len(ids)
    return {k: round(v, 1) for k, v in tot.items()}


def sm_study(cfg_dir, ctx=8192, models=STUDY_MODELS):
    rows = []
    for cls, fn in models:
        cfg = json.loads((Path(cfg_dir) / fn).read_text())
        arch0, _ = arch_from_config(cfg, fn[:-5].split("_", 1)[-1])
        row = dict(model=arch0["name"], cls=cls, ctx=ctx)
        for wf in ("fp8", "int8"):
            arch = dict(arch0, wfmt=wf)
            tp, _ = choose_tp(arch, ctx, 1)
            row["tp_fit"] = tp
            r = {}
            base = simulate(arch, ctx, tp, 1, detail=True)
            parts = sm_parts(arch, ctx, tp, 1)
            r["base"] = dict(tok_s=base["tok_s_per_user"], step=base["step_cycles"],
                             sm_busy_share=round(base["unit_busy_cycles"].get("SM", 0) / base["step_cycles"], 3),
                             sm_parts=parts,
                             sm_split=dict(fixed=round(parts["fixed"] / parts["busy"], 3),
                                           lane_excess=round(max(0.0, parts["busy"] - parts["fixed"] - parts["stream"])
                                                             / parts["busy"], 3),
                                           stream=round(min(parts["stream"], parts["busy"] - parts["fixed"])
                                                        / parts["busy"], 3)))
            for nm, kn in (("no_fixed", dict(sm_fixed=0.0)), ("lanes_x2", dict(sm_lines=0.5)),
                           ("lanes_inf", dict(sm_lines=0.0)), ("no_fixed_lanes_inf", dict(sm_fixed=0.0, sm_lines=0.0))):
                x = simulate(arch, ctx, tp, 1, detail=False, **kn)
                r[nm] = dict(tok_s=x["tok_s_per_user"], gain_pct=round(100 * (x["tok_s_per_user"] / base["tok_s_per_user"] - 1), 1))
            b8 = {}
            for k in (1, 2, 4, 8):
                x = simulate(arch, ctx, tp, 8, detail=False, sm_share=k)
                b8[f"share{k}"] = dict(tok_s_user=x["tok_s_per_user"], tok_s_agg=x["tok_s_aggregate"])
            r["batch8"] = b8
            row[wf] = r
            print(arch0["name"], wf, tp, r["base"]["tok_s"], r["base"]["sm_split"],
                  {k: v["gain_pct"] for k, v in r.items() if "gain_pct" in v},
                  {k: v["tok_s_agg"] for k, v in b8.items()}, flush=True)
        rows.append(row)
    return rows


def is_ds41(cfg):
    c = cfg.get("text_config") or cfg
    return cfg.get("model_type") == "deepseek_v41" or c.get("model_type", "").startswith("deepseek_v41") or \
        (g(c, "hidden_size", "dim") == 5120 and g(c, "num_hidden_layers", "n_layers") == 40 and "compress_ratios" in c)


def ds41_template(dump_path, out=DS41_TEMPLATE):
    """Layer-type templates from a ds_native --program-out dump: layers whose (unit.op, tag) sequence is identical
    share one template (the first such layer's records)."""
    from hgi_sim.records import decode_one
    raw = Path(dump_path).read_bytes()
    d = json.loads(raw)
    types, layers = {}, []
    for lay in d["layers"]:
        sig = []
        for x in lay["records"]:
            r, _ = decode_one(bytes.fromhex(x["hex"]), 0)
            sig.append(f"{r.unit}.{r.op}:{x['tag']}")
        k = hashlib.sha256("|".join(sig).encode()).hexdigest()[:12]
        if k not in types:
            types[k] = dict(first_layer=lay["layer"], n_records=len(lay["records"]), records=lay["records"])
        layers.append([lay["layer"], k])
    rec = dict(schema="opentallas.hgi_perf.ds41_template.v1",
               source="hgi_sim.ds_native --program-out (rank 0, a head die) of the bit-exact DS-V4.1-Flash 1M token "
                      "on the approved HGI-1 encoding",
               dump_sha256=hashlib.sha256(raw).hexdigest(), layer_types=types, layers=layers, ops=d["ops"])
    Path(out).write_text(json.dumps(rec, default=int) + "\n")
    return rec


def ds41_simulate(detail=True):
    """DS-V4.1-Flash at 1M, TP96: per-layer-type native records (rank 0) composed like the generic path; engine
    records walk-priced, SU per record (hgi_sim.ds_native_timing.NativeCost)."""
    from hgi_sim.ds_native_timing import NativeCost
    from hgi_sim.records import decode_one
    t0 = time.time()
    tpl = json.loads(DS41_TEMPLATE.read_text())

    def recs_of(keys):
        out = []
        for k in keys:
            one = []
            for x in tpl["layer_types"][k]["records"]:
                r, _ = decode_one(bytes.fromhex(x["hex"]), 0)
                r.tag, r.family, r.reads, r.writes = x["tag"], x["family"], x["reads"], x["writes"]
                r.src_key = None if not x["src"] else f"{x['src'][0]}:{x['src'][1]}"
                r.src_extra = [f"{x['src'][0]}:{e}" for e in x["src"][2]] if x["src"] and len(x["src"]) > 2 else []
                one.append(r)
            sh = Counter((r.src_key, r.unit) for r in one if r.src_key)
            for r in one:                    # an op's price splits over its records within ONE layer instance
                r.share = sh.get((r.src_key, r.unit), 1)
            out += one
        return T.rebuild_waits(out)
    layers = [k for L, k in tpl["layers"] if L != "head"]
    head = [k for L, k in tpl["layers"] if L == "head"]
    allr = recs_of(list(tpl["layer_types"]))
    cost = NativeCost(tpl["ops"], allr)

    def S(keys):
        rr = recs_of(keys)
        cost.prepare(rr)
        return T.schedule(rr, (1 << 20) - 1, "S2", cost_fn=cost)["total_cycles"]
    cnt = Counter(layers)
    T1 = S([layers[0]] + head)
    inc = {}
    for k in cnt:
        a, b = S([layers[0], k] + head), S([layers[0], k, k] + head)
        inc[k] = b - a
    total = T1 + sum(inc[k] * (cnt[k] - (1 if k == layers[0] else 0)) for k in cnt)
    return dict(model="DeepSeek-V4.1-Flash (native template)", ctx=1 << 20, tp=96, batch=1,
                step_cycles=round(total, 1), step_us=round(total / CLK * 1e6, 2),
                tok_s_per_user=round(CLK / total, 1), tok_s_aggregate=round(CLK / total, 1), dies=96,
                layer_types=[dict(template=k, first_layer=tpl["layer_types"][k]["first_layer"], layers=cnt[k],
                                  cycles_per_layer=round(inc[k], 1), records=tpl["layer_types"][k]["n_records"])
                             for k in cnt],
                wall_s=round(time.time() - t0, 1),
                note="the bit-exact native record stream of rank 0 (a head die) per layer type; 1M context only")


def validate():
    rows = []
    res = ROOT / "results/arch/hgi_sim_20261009"
    # 1. Qwen3-8B at P8191, TP4: the bit-exact program's S2 (qwen_timing, same calibration)
    q = json.loads((ROOT / "compiler/models/qwen3-8b/config.json").read_text())
    arch, _ = arch_from_config(q, "Qwen3-8B")
    arch["wfmt"] = "int8"                                       # the Qwen3-8B contract: INT8 fmt 3
    ref = json.loads((res / "qwen_timing_P8191_v10.json").read_text())["result"]["S2"]["total_cycles"]
    for cm in ("calibration", "measured"):
        p = simulate(arch, ctx=8192, tp=4, coll_model=cm, detail=False)
        rows.append(dict(vehicle="Qwen3-8B token, P8191, TP4", reference="hgi_sim.qwen_timing S2 on the bit-exact "
                         "qwen_compiler program (qwen_timing_P8191_v10.json)", reference_cycles=ref,
                         collective_model=cm, perf_cycles=p["step_cycles"],
                         error_pct=round(100 * (p["step_cycles"] / ref - 1), 2), perf_wall_s=p["wall_s"]))
    # 2. one GDN layer (Qwen3-Next dims, TP4): the bit-exact gdn program's S2
    gref = json.loads((res / "gdn_layer_v10.json").read_text())["result"]["timing"]["S2_cycles"]
    from hgi_sim import gdn as GD
    em = Em(2048, 4, 8192)
    em.gdn(dict(nk=16, nv=32, dk=128, dv=128, conv=4), int8=False)        # the reference's BF16 projections
    em.add(Rec("CTL", "END", desc=dict(A=em.V("TOK", 1, fmt="U32"))), ["TOK"], [], "end")
    recs = assign_waits(em.b.recs)
    sg = sched(recs, 8192, PerfCost(4, 1, "calibration"))
    rows.append(dict(vehicle="Gated DeltaNet layer (Qwen3-Next dims), TP4", reference="hgi_sim.gdn S2 "
                     "(gdn_layer_v10.json; BF16 projections in both)", reference_cycles=gref,
                     collective_model="calibration", perf_cycles=round(sg["total_cycles"], 1),
                     error_pct=round(100 * (sg["total_cycles"] / gref - 1), 2)))
    # 3. DS-V4.1 1M token: the native record stream's timing (walk-priced engines)
    nt = res / "ds_native_timing_1M.json"
    if nt.exists():
        dref = json.loads(nt.read_text())["result"]["S2"]["total_cycles"]
        dcfg = json.loads((ROOT / "compiler/models/deepseek-v4.1-flash/config.json").read_text())
        arch, notes = arch_from_config(dcfg, "DeepSeek-V4.1-Flash")
        p = simulate(arch, ctx=1 << 20, tp=96, detail=False)
        rows.append(dict(vehicle="DeepSeek-V4.1-Flash token, 1M, TP96 (generic MLA front end)",
                         reference="hgi_sim.ds_native_timing S2 on "
                         "the bit-exact native record stream (ds_native_timing_1M.json)", reference_cycles=dref,
                         collective_model="measured", perf_cycles=p["step_cycles"],
                         error_pct=round(100 * (p["step_cycles"] / dref - 1), 2), notes=notes))
        p2 = ds41_simulate()
        rows.append(dict(vehicle="DeepSeek-V4.1-Flash token, 1M, TP96 (native-template path)",
                         reference="hgi_sim.ds_native_timing S2 (whole native stream scheduled at once)",
                         reference_cycles=dref, collective_model="walk (measured)", perf_cycles=p2["step_cycles"],
                         error_pct=round(100 * (p2["step_cycles"] / dref - 1), 2), perf_wall_s=p2["wall_s"]))
        rows.append(dict(vehicle="DeepSeek-V4.1-Flash token, 1M, TP96 (generic MLA front end)", reference="published RTL-measured composition "
                         "(dshbm_1m_allmeasured walk, 460.05 us)", reference_cycles=460.05e-6 * CLK,
                         collective_model="measured", perf_cycles=p["step_cycles"],
                         error_pct=round(100 * (p["step_cycles"] / (460.05e-6 * CLK) - 1), 2)))
    return rows


OUT_OF_SCOPE = {"nemotron_h": "Mamba-2 hybrid (owner: out of scope)", "granitemoehybrid": "Mamba hybrid",
                "nemotron_nas": "Nemotron (Mamba hybrid family; owner: out of scope)"}


def survey(cfg_dir, ctxs=(8192, 131072), batch=8, shard=(0, 1)):
    need = {"SM.bf16_lines_per_row_k", "SM.drain", "SM.overhead", "SU.model_check", "hbm.first_access"}
    if not need <= set(T.MEAS):                     # never fall back silently to the estimate entries
        raise SystemExit(f"measured calibration missing: {sorted(need - set(T.MEAS))}")
    sm_table()
    rows = []
    files = sorted(p for p in Path(cfg_dir).glob("*.json") if not p.name.endswith(".params.json"))
    files = files[shard[0]::shard[1]]
    for p in files:
        name = p.stem.split("_", 1)[-1]
        try:
            cfg = json.loads(p.read_text())
        except Exception as e:                                  # noqa: BLE001
            alt = p.with_name(p.stem + ".params.json")
            if alt.exists():
                cfg = json.loads(alt.read_text())
            else:
                rows.append(dict(model=name, skipped=f"no config.json released ({p.read_text()[:40].strip()})"))
                continue
        c = cfg.get("text_config") or cfg
        mt = c.get("model_type", cfg.get("model_type", ""))
        if mt in OUT_OF_SCOPE or "hybrid_override_pattern" in c or "nemotron" in mt.lower():
            rows.append(dict(model=name, skipped=OUT_OF_SCOPE.get(mt, "Mamba hybrid (owner: out of scope)")))
            continue
        try:
            arch, notes = arch_from_config(cfg, name)
        except Exception as e:                                  # noqa: BLE001
            rows.append(dict(model=name, error=f"front end: {type(e).__name__}: {e}"))
            continue
        r = dict(model=name, model_type=mt, params_B=dict(total=round(arch["params"]["total"] / 1e9, 1),
                                                          active=round(arch["params"]["active"] / 1e9, 1)),
                 ctx_max=arch["ctx_max"], mixers=dict(Counter(ly["mixer"]["kind"] + ("-swa" if ly["mixer"].get(
                     "window") and ly["mixer"]["kind"] == "gqa" else "") for ly in arch["layers"])),
                 ffn=dict(Counter(ly["ffn"]["kind"] for ly in arch["layers"])), notes=notes, runs=[])
        t0 = time.time()
        for ctx in sorted({min(x, arch["ctx_max"] or x) for x in ctxs} | {min(arch["ctx_max"] or 8192, 1 << 20)}):
            for b in (1, batch):
                tp, gb = choose_tp(arch, ctx, b)
                if tp is None:
                    r["runs"].append(dict(ctx=ctx, batch=b, error="does not fit 96 dies (8-bit weights)"))
                    continue
                try:
                    x = simulate(arch, ctx, tp, b, detail=(b == 1 and ctx == min(ctxs)))
                except Exception as e:                          # noqa: BLE001
                    r["runs"].append(dict(ctx=ctx, batch=b, tp=tp, error=f"{type(e).__name__}: {e}"))
                    continue
                x["hbm_gb_per_die"] = round(gb, 1)
                x["tp_rule"] = "smallest group that fits (8-bit weights + FP8 KV + state)"
                x.pop("model", None)
                r["runs"].append(x)
                if b == 1:                       # latency-first: the fastest legal group at or above the fit
                    best = x
                    for tp2 in [t for t in GROUPS if t > tp]:
                        y = simulate(arch, ctx, tp2, b, detail=False)
                        if y["tok_s_per_user"] > best["tok_s_per_user"]:
                            best = y
                    if best is not x:
                        best = dict(best, tp_rule="fastest legal group (latency-first)")
                        best.pop("model", None)
                        r["runs"].append(best)
        if is_ds41(cfg) and DS41_TEMPLATE.exists():
            x = ds41_simulate()
            x["tp_rule"] = "the bit-exact native record stream (template path), 1M, 96 dies"
            r["runs"].append(x)
        r["wall_s"] = round(time.time() - t0, 1)
        rows.append(r)
        print(name, r["wall_s"], [(x.get("ctx"), x.get("batch"), x.get("tp"), x.get("tok_s_per_user"),
                                   x.get("error")) for x in r["runs"]], flush=True)
    return rows


def table(rows):
    """Markdown summary of a survey: per model and context, the smallest group that fits and the fastest group."""
    out = ["| Model | Params total / active (B) | Mixers | Context | Fit TP | tok/s/user at fit TP | Fastest TP | "
           "tok/s/user fastest | Batch 8 at fit TP: tok/s/user / aggregate | Busiest unit (8K, fit TP) |",
           "|---|---|---|---:|---:|---:|---:|---:|---|---|"]
    for r in rows:
        if "runs" not in r:
            out.append(f"| {r['model']} | | | | | | | | | {r.get('skipped') or r.get('error')} |")
            continue
        mix = ", ".join(f"{k} {v}" for k, v in r["mixers"].items())
        ctxs = sorted({x["ctx"] for x in r["runs"] if "ctx" in x})
        busiest = ""
        for x in r["runs"]:
            if x.get("unit_busy_cycles"):
                u = max(x["unit_busy_cycles"].items(), key=lambda kv: kv[1])
                busiest = f"{u[0]} ({100 * u[1] / x['step_cycles']:.0f} %)"
                break
        for ctx in ctxs:
            fit = next((x for x in r["runs"] if x.get("ctx") == ctx and x.get("batch") == 1 and
                        x.get("tp_rule", "").startswith("smallest")), None)
            best = next((x for x in r["runs"] if x.get("ctx") == ctx and x.get("batch") == 1 and
                         x.get("tp_rule", "").startswith("fastest")), fit)
            tpl = next((x for x in r["runs"] if x.get("ctx") == ctx and x.get("tp_rule", "").startswith(
                "the bit-exact")), None)
            b8 = next((x for x in r["runs"] if x.get("ctx") == ctx and x.get("batch") == 8), None)
            err = next((x.get("error") for x in r["runs"] if x.get("ctx") == ctx and x.get("error")), None)
            if fit is None:
                out.append(f"| {r['model']} | {r['params_B']['total']} / {r['params_B']['active']} | {mix} | {ctx:,} | "
                           f"| | | | | {err or ''} |")
                continue
            out.append(f"| {r['model']} | {r['params_B']['total']} / {r['params_B']['active']} | {mix} | {ctx:,} | "
                       f"{fit['tp']} | {fit['tok_s_per_user']:,.0f} | {best['tp']} | {best['tok_s_per_user']:,.0f} | "
                       + (f"{b8['tok_s_per_user']:,.0f} / {b8['tok_s_aggregate']:,.0f} (TP {b8['tp']})" if b8 and
                          "tok_s_per_user" in b8 else "") + f" | {busiest if ctx == ctxs[0] else ''} |")
            if tpl:
                out.append(f"| {r['model']} (native bit-exact records) | | | {ctx:,} | | | {tpl['tp']} | "
                           f"{tpl['tok_s_per_user']:,.0f} | | template path (error vs the full stream: validation.json) |")
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--config", type=Path)
    ap.add_argument("--ctx", type=int, default=8192)
    ap.add_argument("--tp", type=int)
    ap.add_argument("--batch", type=int, default=1)
    ap.add_argument("--validate", action="store_true")
    ap.add_argument("--survey", type=Path)
    ap.add_argument("--sm-study", type=Path, help="config dir: SM-binding study (sm_binding.json)")
    ap.add_argument("--ds41-template", type=Path, help="ds_native --program-out dump -> ds41_native_template.json")
    ap.add_argument("--shard", default="0/1", help="i/n: this process runs configs i, i + n, ... (survey)")
    ap.add_argument("--merge", nargs="*", type=Path, help="survey shard JSONs to merge into --out")
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    if a.config:
        arch, notes = arch_from_config(json.loads(a.config.read_text()), a.config.stem)
        r = simulate(arch, a.ctx, a.tp, a.batch)
        r["notes"] = notes
        print(json.dumps(r, indent=1))
        rec = r
    elif a.ds41_template:
        t = ds41_template(a.ds41_template)
        rec = ds41_simulate()
        rec["template_types"] = len(t["layer_types"])
    elif a.sm_study:
        rec = dict(schema="opentallas.hgi_perf.sm_binding.v1",
                   generated_utc=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                   configs=str(a.sm_study), ctx=a.ctx, rows=sm_study(a.sm_study, a.ctx),
                   method=["fit TP (8-bit weights + FP8 KV + state in 140 GB / die), batch 1 unless stated",
                           "fp8 = the survey's weight path (FP8 block-dot, measured DS SM table: lines / 32 rows / K "
                           "0.0125 vs HBM stream 0.0101 -> lanes 1.24x the stream); int8 = fmt3 on the BF16 lanes "
                           "(the approved two-beat front: 128-code line in two 64-code beats, 1.25 B transport / code "
                           "-> lanes 1.24x the stream)",
                           "sm_split: of the SM busy time, fixed = per-record first access + overhead + drain; "
                           "stream = HBM streaming time; lane_excess = lane issue beyond the stream (MAC throughput)",
                           "no_fixed: per-record SM fixed cost 0 (bound on record batching / prefetch); lanes_x2: "
                           "lines halved (= one-beat INT8 for int8; 2x lanes for fp8); lanes_inf: lines 0 (SM = HBM "
                           "stream + fixed: the most any MAC-rate lever can buy)",
                           "batch8 shareK: 8 users, dense weight passes shared by 8 slots (routed experts per user); "
                           "K slots' MACs issue per weight line (share1 = today's lane array: every slot re-issues)"])
    elif a.validate:
        rec = dict(schema="opentallas.hgi_perf.validation.v1",
                   generated_utc=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                   rows=validate(),
                   reading=["Qwen3-8B, calibration collectives: the same cost tables as the timed bit-exact program, so "
                            "the error is the generic lowering + layer composition only",
                            "Qwen3-8B, measured collectives: the in-package all-reduce of 16 KB pays the endpoint "
                            "serialisation the 1 KB calibration entry lacks",
                            "GDN: hgi_perf reuses the bit-exact gdn lowering; the residual (< 1 %) is the composition "
                            "of one layer and the SU HBM first-access charge the reference predates",
                            "DS-V4.1: the generic MLA front end prices DS UNFUSED and unscheduled, so it lands ~25 % "
                            "above the native stream (fused SU chains, CP-aware order); the native-template path (the "
                            "bit-exact records per layer type, steady increments) is within ~3 %; the published walk "
                            "is a fused-chain composition without a command processor, not a record stream"],
                   sources={p: hashlib.sha256((TOOLS / p).read_bytes()).hexdigest() for p in (
                       "hgi_sim/perf.py", "hgi_sim/timing.py", "hgi_sim/ds_native_timing.py")})
        print(json.dumps(rec, indent=1))
    elif a.survey or a.merge:
        if a.merge:
            rows = sorted((r for p in a.merge for r in json.loads(p.read_text())["rows"]),
                          key=lambda r: r["model"].lower())
            a.survey = Path(json.loads(a.merge[0].read_text())["configs"])
        else:
            i, n = (int(x) for x in a.shard.split("/"))
            rows = survey(a.survey, shard=(i, n))
        rec = dict(schema="opentallas.hgi_perf.survey.v1",
                   generated_utc=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                   configs=str(a.survey), method=__doc__, die=dict(hbm_gb=DIE_HBM_GB, reserve_gb=DIE_RESERVE_GB,
                                                                   groups=GROUPS),
                   weights="8-bit (FP8 block, the measured DS SM path) for every model; routed experts FP4 where "
                           "released FP4 / MXFP4 (DS-V4, gpt-oss, Kimi K3); KV FP8; linear-attention state FP32",
                   validation="results/arch/hgi_perf_20261009/validation.json", rows=rows,
                   sources={p: hashlib.sha256((TOOLS / p).read_bytes()).hexdigest() for p in (
                       "hgi_sim/perf.py", "hgi_sim/timing.py", "hgi_sim/gdn.py", "hgi_sim/calibration.json")})
        if a.out:
            a.out.with_name("survey_table.md").write_text(
                "# hgi_perf survey: tok/s per user on the generic HBM die (r25), HGI-1 records, timing only\n\n"
                "Pathfinding estimates from hgi_sim.perf (see survey.json `method`, validation.json for the error "
                "against the bit-exact timed runs).  Fit TP = the smallest legal group whose per-die HBM (144 GB, "
                "4 GB reserve) holds 8-bit weights + FP8 KV + state; fastest TP = the legal group with the highest "
                "per-user rate.\n\n" + table(rows))
    else:
        raise SystemExit("--config, --validate or --survey")
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(rec, indent=1, default=float) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
