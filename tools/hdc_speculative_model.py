#!/usr/bin/env python3
"""Design-faithful speculative decoding (MTP / draft-and-verify) on the hardwired decode core.

    python3 tools/hdc_speculative_model.py [--out PATH]

The generic study (tools/run_speculative_roofline.py, results/roofline/speculative/{released_dspark,
sota_block_diffusion}) prices a ROM machine as a roofline: a draft pass is a full-array sweep, and on a
compute-in-ROM fabric every verified position is its own pass.  Neither is how the hardwired decode core
(rtl/hdc) works, so that study is the PESSIMISTIC compute-in-ROM bound.  This tool re-prices speculation
on the core we build, on the operator graph and RTL depths the per-token critical path already uses
(tools/decode_critical_path.py, whose nodes carry tools/hdc_timing.py `K` -- the constants fitted to the
Verilator issue trace, 32,191 model vs 32,196 RTL cycles -- and the V4.1 units' campaign depths):

VERIFICATION PASS over n = gamma + 1 positions.  The same graph with n positions riding every operator.
* Matrix engine: each ROM weight word is read once and multiplied by the n activation vectors on m MAC
  lanes per weight lane (m = 1 today: rtl/hdc/ot_hdc_matvec has one MAC per weight lane).  A matvec
  costs ceil(n * users / m) engine passes of its one-vector time (its share of the design's weight sweep,
  or the engine's element-loop floor, whichever is larger).
* Attention: the KV prefix is SHARED by the n positions -- read once, multiplied on the same lanes
  (ceil(n / m) passes per user); the V4.1 selected compressed rows differ per position and are read n
  times (the 128-row window is shared).  The drafts' own causal attention is not charged (<0.01% of rows).
* Stream unit, selections, Sinkhorn: per-position work, so element issue scales with n; every pipeline
  depth (SFU, reducer tail, select latency, Sinkhorn unit clocks) is paid once per pass.  Selections and
  Sinkhorn units are the autoregressive machine's (no free extra units): positions queue on them.
* Collectives and package hops: latency once per pass, payload x n (Fabric pricing unchanged).
* Control (sequencer issue gaps, barriers): once per pass -- same program, same instruction count.
The per-user period of a pass is max(critical path, pipeline occupancy bound) exactly as the AR model.

DRAFT PASS, priced on the same graph machinery with the drafter's real shape:
* DeepSeek-V4.1-Flash: its own DSpark module from the pinned checkpoint config (inference/config.json:
  n_mtp_layers 3, dspark_block_size 5, 128 routed experts top-3 + 1 shared, sliding-window attention,
  main_proj over target layers 37-39, shared embedding and lm_head, a rank-256 Markov head applied
  SEQUENTIALLY per draft position).  Its 7.9 GB sit on ~3 dies of the ROM array, which already stores the
  checkpoint (the draft is inside checkpoint_bytes): one tensor group of the option (b) array, a board
  hop from the target's head and a hop back to the head dies for the shared lm_head and Markov steps.
* Qwen3-8B: no drafter ships in its checkpoint.  The verified external drafter is z-lab's DFlash block-
  diffusion drafter for Qwen3-8B (https://huggingface.co/z-lab/Qwen3-8B-DFlash-b16: 5 Qwen3 layers of the
  target's own shape, block 16, target-feature injection from layers 1/9/17/25/33, shared embedding and
  lm_head; acceptance lengths published in arXiv:2602.06036 Table 1, carried in
  configs/studies/speculative_profiles.json).  Two placements: (a) as extra ROM layers on the reticle
  (quantised like the target -- acceptance at that precision is unmeasured), (b) BF16 weights on an HBM
  side path (1 or 8 HBM3E stacks), the shared lm_head staying in ROM.  An on-die SRAM side path is refused
  on capacity.

GPU SIDE, as a labelled band.  The existing B200 roofline points (fused persistent-kernel / PDL execution:
1.0 us all-SM gather, 370.6 ns handoff per dependent boundary, results/gpu/*.json) are re-assembled for a
verification pass by tools/run_speculative_roofline.speculative_cycle (weight union over n draws, compute x n,
KV prefix once, the serial graph re-priced at users x n, so every boundary is paid once per pass), with the
same drafter and the same acceptance lengths; the DSpark Markov head's gamma sequential steps are charged
two gather boundaries each.  Four blocks, AR and speculative designs chosen separately in each:
* idealised: the study's fastest point as published (no head-divisibility check -- its fastest Qwen3-8B
  point splits 32/8 heads 58 ways);
* feasible: tensor groups that split the heads (Qwen3-8B 1/2/4/8, or 16/32 with KV-head replication);
* feasible_calibrated: plus the per-forward serving overhead fitted to DFlash's MEASURED single-B200 rates
  (arXiv:2602.06036 Table 3: 230 tok/s AR, 1,175 with DFlash at tau 8.01) -- one forward per AR step, two
  (draft, verify) per speculative cycle; the check reproduces both concurrency-1 rows within 5%;
* feasible_calibrated_nccl: plus stock-NCCL 11.0 us all-reduces instead of the study's 2.43 us.
The measured single-B200 rates are carried as the demonstrated row (grade "measured (cited)").

ACCEPTANCE LENGTH is never assumed: every speculative rate is a curve over tau (1.5-8, capped at gamma + 1)
with the published points marked -- LMSYS's DSpark ~5 on V4-Pro; a V4-family tau DERIVED from vLLM's
published per-position survival endpoints (v4_survival_derivation); DFlash's Qwen3-8B Table 1 (temperature
0, block 16); the DSpark paper's Qwen3-8B Table 1 (temperature 1.0, block 7).  No tau is published for
V4.1-Flash or for agentic workloads.

VARIANTS of the added silicon: `me` (m MAC lanes per weight lane), `me_su` (and the stream unit m times as
wide), `su` (the stream unit alone, isolating its share).

AREA AND ENERGY of the lane multiplier: added MAC lanes = (m - 1) x the die's weight lanes, priced between
the closed pipelined BF16 MAC (mac_bf16_fp32_pipe_round_stage, 509.4 um^2) and the whole matrix-engine lane
(ot_hdc_matvec 68,596 um^2 / 64 lanes = 1,071.8 um^2); energy from the committed sign-off
(results/physical_abi3/asap7/signoff/energy_per_token.json): matrix-engine pJ/MAC, ROM/SRAM/HBM pJ/byte,
and the rest of the core per stream-unit element, calibrated on the reduced Qwen vehicle.

Acceptance lengths are inputs (configs/studies/speculative_profiles.json), never fitted.
Output: results/roofline/speculative/hdc_design_faithful.json.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "src"))

import decode_critical_path as D  # noqa: E402
import hdc_isa as I  # noqa: E402
import hdc_timing  # noqa: E402

SCHEMA = "opentallas.hdc-speculative-design-faithful.v1"
OUT = ROOT / "results/roofline/speculative/hdc_design_faithful.json"
PROFILES = ROOT / "configs/studies/speculative_profiles.json"
SIGNOFF = ROOT / "results/physical_abi3/asap7/signoff/energy_per_token.json"
MATVEC_PHYS = ROOT / "results/physical_abi3/asap7/hdc/ot_hdc_matvec/physical.json"
MAC_PHYS = ROOT / "results/physical_abi3/asap7/mac_bf16_fp32_pipe_round_stage/physical.json"
GPU_DEP = ROOT / "results/gpu/blackwell_dependency_latency.json"
GPU_SYNC = ROOT / "results/gpu/blackwell_sync_breakdown.json"
CRIT_RECORD = ROOT / "results/roofline/critical_path/decode_critical_path.json"
GPU_STUDIES = {
    ("Qwen3-8B", 8192): ROOT / "results/roofline/n5_vs_b200/analytical.json",
    ("DeepSeek-V4.1-Flash", 8192): ROOT / "results/roofline/candidates/deepseek-v41-flash-8k/n5_vs_b200/analytical.json",
    ("DeepSeek-V4.1-Flash", 200000): ROOT / "results/roofline/candidates/deepseek-v41-flash/n5_vs_b200/analytical.json",
    ("DeepSeek-V4.1-Flash", 1048576): ROOT / "results/roofline/candidates/deepseek-v41-flash-1m/n5_vs_b200/analytical.json",
}
# DSpark shape, from the pinned checkpoint's inference/config.json (DeepSeek-V4.1-Flash, revision
# dba1be0a40aa45a94ad051997016db3960a90277) and inference/model.py DSparkBlock / DSparkMarkovHead.
DSPARK = dict(n_mtp_layers=3, dspark_block_size=5, dspark_target_layer_ids=[37, 38, 39], dspark_markov_rank=256,
              dspark_n_routed_experts=128, dspark_n_activated_experts=3, window_size=128,
              source="huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash inference/config.json and inference/model.py "
                     "(DSparkBlock, DSparkAttention, DSparkMarkovHead) at revision "
                     "dba1be0a40aa45a94ad051997016db3960a90277; draft bytes configs/models/candidates/"
                     "deepseek-v4.1-flash.json draft_dense_weight_bytes 713,428,872 + draft_routed_weight_bytes "
                     "7,219,445,760")
# DFlash drafter for Qwen3-8B, from its released config.json.
DFLASH = dict(repo="z-lab/Qwen3-8B-DFlash-b16", url="https://huggingface.co/z-lab/Qwen3-8B-DFlash-b16",
              config_url="https://huggingface.co/z-lab/Qwen3-8B-DFlash-b16/raw/main/config.json",
              num_hidden_layers=5, hidden_size=4096, intermediate_size=12288, num_attention_heads=32,
              num_key_value_heads=8, head_dim=128, block_size=16, target_layer_ids=[1, 9, 17, 25, 33],
              vocab_size=151936, dtype="bfloat16", published_params=1048626432,
              published_params_source="HF model config/safetensors of z-lab/Qwen3-8B-DFlash-b16 (checked 2026-09-26): "
                                      "1,048,626,432 BF16 parameters, ~15% of Qwen3-8B's ~6.95 B non-embedding "
                                      "parameters; embedding and LM head shared with the target",
              other_drafters=dict(
                  eagle3=dict(params=0.40e9, repos=["AngelSlim/Qwen3-8B_eagle3", "Tengyunw/qwen3_8b_eagle3"],
                              shape="1 decoder layer + fc + a 32k-token draft LM head",
                              tau="arXiv:2602.06036 Table 1: 2.96 at block 16 (3.40 tree-60), temperature 0; "
                                  "arXiv:2607.05147 Table 1: 2.54-5.30 at block 7, temperature 1.0",
                              priced=False,
                              note="autoregressive: gamma sequential draft steps, each a 1-layer pass plus its LM "
                                   "head; RedHatAI's 1.02 B EAGLE-3 includes a 622 M embedding copy"),
                  native_mtp="Qwen3-8B ships no MTP head"),
              paper="Chen, Liang, Liu, DFlash: Block Diffusion for Flash Speculative Decoding, arXiv:2602.06036 "
                    "(ICML 2026), Table 1 (Qwen3-8B, temperature 0)")
M_LADDER = (1, 2, 4, 8, 16)
BATCHES = (1, 64)
V41_CONTEXTS = (8192, 200000, 1048576)
QWEN_CONTEXTS = (2048, 8192)
BUDGETS = (0.0, 0.05, 0.10, 0.25, 0.50, 1.00)       # added silicon as a fraction of the design's total
HBM_SIDE_STACKS = (1, 8)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rel(path):
    return str(Path(path).resolve().relative_to(ROOT))


# -- graph operators that remember what a pass needs to re-price them ---------------------------------------
class SpecOps(D.Ops):
    """decode_critical_path.Ops that records, on every node, the quantities a multi-position pass scales:
    MACs and bytes per vector of a matvec, KV bytes and MACs of a scan, stream-unit elements; `vpu`
    (vectors per user) overrides the pass's positions for per-user-only operators (the DSpark main_proj,
    the Markov steps)."""

    vpu = None
    bpp = 3.5 / 8

    def _tag(self, node, **kw):
        if self.vpu is not None:
            kw["vpu"] = self.vpu
        self.g.nodes[node].update(kw)
        return node

    def ew(self, name, deps, n, depth_cycles, layer, stream=True, desc=""):
        return self._tag(super().ew(name, deps, n, depth_cycles, layer, stream=stream, desc=desc), elements=n)

    def reduce(self, name, deps, n, layer, segments=1, stream=True, desc=""):
        return self._tag(super().reduce(name, deps, n, layer, segments=segments, stream=stream, desc=desc),
                         elements=n)

    def matvec(self, name, deps, layer, *, n_out, k, bytes_, fmt="fp8", imbalance=1.0, desc=""):
        node = super().matvec(name, deps, layer, n_out=n_out, k=k, bytes_=bytes_, fmt=fmt, imbalance=imbalance,
                              desc=desc)
        base = node[:-5] if node.endswith(".rstd") else node
        self._tag(base, mac_per_vec=n_out * k, wbytes=bytes_)
        return node

    def kvscan(self, name, deps, layer, *, kv_bytes, macs, depth_cycles, desc=""):
        return self._tag(super().kvscan(name, deps, layer, kv_bytes=kv_bytes, macs=macs, depth_cycles=depth_cycles,
                                        desc=desc), kv_bytes=kv_bytes, kv_macs=macs)


class Pass:
    """One pass (verification or draft) of `positions` per user through a machine, on m MAC lanes per weight
    lane.  `per_vec_rate` (s per sweep unit per vector) prices matvecs that are not the target's own sweep
    (the drafter); None: the target machine's weight_sweep_s, spread by decode_critical_path's rule."""

    def __init__(self, mach, p, clock, builder, args, *, positions, m, users, kv_shared=None, per_vec_rate=None,
                 hbm_weight_bw=None, hbm_nodes=None, su_mult=1):
        self.users, self.n, self.m = users, positions, m
        self.experts = None
        vec = users * positions
        # tselect / Sinkhorn provisioning stays the autoregressive machine's: extra positions queue
        p2 = replace(p, tselect_units=max(1, math.ceil(users)))
        self.mach = replace(mach, microbatch=vec, su_width=mach.su_width * su_mult)
        self.p, self.clock = p2, clock
        self.g = D.Graph()
        self.ops = SpecOps(self.g, p2, self.mach, clock)
        self.sink = builder(self.ops, *args)
        basis = mach.sweep_basis
        units = {k: self._unit(nd, basis, vec) for k, nd in self.g.nodes.items() if nd.get("sweep")}
        if per_vec_rate is None:
            self.rate = mach.weight_sweep_s / sum(units.values())
        else:
            self.rate = per_vec_rate
        for k, u in units.items():
            nd = self.g.nodes[k]
            sw = nd["sweep"]
            share = u * self.rate * sw.get("imbalance", 1.0)
            floor1 = sw["floor_s"] / math.ceil(vec)
            per_user_vectors = nd.get("vpu", positions)
            passes = math.ceil(users * per_user_vectors / m)
            t = passes * max(share, floor1)
            cat = "weight_sweep" if share >= floor1 else "compute_chain"
            if hbm_nodes is not None and hbm_nodes(k):
                t = max(t, nd["wbytes"] / hbm_weight_bw)
                cat = "weight_sweep"
            sw["share_s"] = share
            nd.update(issue=t, issue_cat=cat, engine_passes=passes)
        for k, nd in self.g.nodes.items():
            vpu = nd.get("vpu", positions)
            if nd["kind"] == "kvscan":
                f = 1.0 if kv_shared is None else kv_shared(k)
                kvb = nd["kv_bytes"] * (f + (1.0 - f) * vpu) * users
                t_kv = kvb / mach.kv_bw_per_die
                t_mac = nd["kv_macs"] * users * math.ceil(vpu / m) / mach.mac_rate_per_die
                nd.update(issue=max(t_kv, t_mac), issue_cat="kv_sweep" if t_kv >= t_mac else "compute_chain",
                          kv_bytes_pass=kvb)
            elif "elements" in nd and nd["kind"] in ("vector", "reduce") and nd.get("vpu") is not None:
                nd["issue"] = self.ops.cyc(math.ceil(nd["elements"] * users * vpu / self.mach.su_width))

    @staticmethod
    def _unit(nd, basis, vec):
        sw = nd["sweep"]
        return sw[basis] / vec if basis == "macs" else sw[basis]

    def evaluate(self, fabric):
        r = D.Built.evaluate(self, fabric)
        occ = sum(nd["issue"] for nd in self.g.nodes.values() if nd["kind"] not in ("collective", "hop"))
        r["occupancy_sum_s"] = occ
        return r

    def work(self, kv_scale=1.0, elem_scale=1.0):
        """Per-pass totals the energy model needs (whole machine, all users of the pass)."""
        macs = weight_reads = kv_bytes = kv_macs = elements = unique = 0.0
        for name, nd in self.g.nodes.items():
            vpu = nd.get("vpu", self.n)
            if "mac_per_vec" in nd:
                macs += nd["mac_per_vec"] * self.users * vpu
                weight_reads += nd["wbytes"] * nd.get("engine_passes", 1)
                u = nd["wbytes"]
                if name.endswith((".ffn.experts_gu", ".ffn.down")) and self.experts:
                    E_, k_ = self.experts
                    draws = self.users * vpu
                    u *= E_ * (1 - (1 - k_ / E_) ** draws) / k_      # distinct experts over the pass's draws
                unique += u
            if nd["kind"] == "kvscan":
                kv_macs += nd["kv_macs"] * self.users * vpu * kv_scale
                kv_bytes += nd.get("kv_bytes_pass", 0.0) * kv_scale
            if "elements" in nd:
                elements += nd["elements"] * self.users * vpu * elem_scale
        return dict(weight_macs=macs, kv_macs=kv_macs, weight_bytes_read=weight_reads, kv_bytes=kv_bytes,
                    stream_elements=elements, weight_bytes_unique=unique)


# -- DSpark (DeepSeek-V4.1's own MTP) as a graph ------------------------------------------------------------
def v41_sublayer(ops, c, L, sub, h, pre_ready, ctx, hpd, fp4, extra_attn=None):
    """One hyper-connected sublayer, exactly as decode_critical_path.v41_graph builds it (hc mixes and the
    Sinkhorn side branch, collapse, norm, quantise, body, hc_post)."""
    g = ops.g
    D_, HC = c["hidden_size"], c["hc_mult"]
    P = f"L{L}.{sub}"
    res = h
    ss = ops.reduce(f"{P}.hc.sumsq", [res], HC * D_, L)
    rs = ops.ew(f"{P}.hc.rsqrt", [ss], 1, 2 * D.FADD + D.SU["RSQRT"], L, stream=False)
    fn = ops.matvec(f"{P}.hc.fn", [res], L, n_out=6 * HC, k=HC * D_, bytes_=6 * HC * HC * D_ * 4, fmt="fp32")
    mx = ops.ew(f"{P}.hc.pre_post", [fn, rs], 6 * HC, D.FADD * 3 + D.SU["SIGM"], L, stream=False)
    cyc_sk, desc = D.sinkhorn_cycles(ops, c["hc_sinkhorn_iters"], 2 + D.FADD + D.SU["EXP"])
    sk = g.add(f"{P}.hc.sinkhorn", [mx], layer=L, ctrl=ops.bctrl, kind="sinkhorn", depth=ops.cyc(cyc_sk), desc=desc)
    x = ops.ew(f"{P}.hc_pre", [h, pre_ready], HC * D_, D.SU_BASE + 3 * D.FADD, L)
    x = ops.rmsnorm(f"{P}.norm", [x], D_, L, fold=True)
    xq = ops.actquant(f"{P}.quant", [x], D_, L)
    if sub == "attn":
        deps = [xq] + ([extra_attn] if extra_attn else [])
        y = D.v41_attention(ops, c, L, {}, 0, x, ops.join(f"{P}.xq_join", deps, L), {}, ctx, hpd)
    else:
        y = D.v41_moe(ops, c, L, x, xq, fp4)
    h = ops.ew(f"{P}.hc_post", [y, sk, res], HC * D_, D.SU_BASE + 4 * D.FADD, L, stream=False)
    return h, mx


def dspark_graph(ops: SpecOps, c, ctx, gamma):
    """The DSpark draft pass for a block of `gamma` positions (the pass's positions), from the target's
    accepted token: hop to the MTP group, main_proj of the target's layer-37..39 features, 3 DSpark blocks,
    hop back to the head dies, the shared lm_head over the block, then gamma sequential Markov steps."""
    g, m = ops.g, ops.m
    D_, HC, V = c["hidden_size"], c["hc_mult"], c["vocab_size"]
    G = m.group
    hpd = math.ceil(c["num_attention_heads"] / G)
    c2 = dict(c, num_routed_experts=DSPARK["dspark_n_routed_experts"],
              experts_per_token=DSPARK["dspark_n_activated_experts"])
    fp4 = 0.53125
    RES = HC * D_ * 2 + HC * 4
    NT = len(DSPARK["dspark_target_layer_ids"])
    L0 = c["num_layers"]
    start = ops.join("draft.start", [], layer=L0)
    ops.vpu = 1                                            # per user: the accepted token's features
    h0 = ops.hop("draft.to_mtp", [start], L0, payload=NT * D_ * 2 + 8, hop_kind="stage",
                 desc="accepted token + target layer-37..39 features to the MTP group") or start
    mp = ops.matvec("draft.main_proj", [h0], L0, n_out=D_, k=NT * D_, bytes_=NT * D_ * D_, fmt="fp8",
                    desc="main_proj [5120, 15360]")
    mx_ = ops.rmsnorm("draft.main_norm", [mp], D_, L0)
    main_kv = ops.matvec("draft.main_wkv", [mx_], L0, n_out=c["head_dim"], k=D_, bytes_=c["head_dim"] * D_,
                         fmt="fp8", desc="the target position's window KV entry of each DSpark layer (x3 below)")
    ops.vpu = None
    emb = g.add("draft.embed", [h0], layer=L0, depth=ops.cyc(D.SU_BASE) + 2e-9, ctrl=ops.bctrl,
                desc="block embedding [token, noise x (gamma-1)] (ROM rows), 4-copy expand")
    h, pre = emb, emb
    for j in range(DSPARK["n_mtp_layers"]):
        L = L0 + j
        h, pre_mx = v41_sublayer(ops, c2, L, "attn", h, pre, ctx, hpd, fp4, extra_attn=main_kv)
        pre = pre_mx
        h, pre_mx = v41_sublayer(ops, c2, L, "ffn", h, pre, ctx, hpd, fp4)
        pre = pre_mx
    LH = L0 + DSPARK["n_mtp_layers"]
    h = ops.hop("draft.to_head", [h], LH, payload=RES, hop_kind="head",
                desc="block residual to the lm_head dies (the head is shared with the target)") or h
    x = ops.ew("draft.head.hc_pre", [h, pre], HC * D_, D.SU_BASE + 3 * D.FADD, LH)
    x = ops.rmsnorm("draft.head.norm", [x], D_, LH, fold=True)
    lg = ops.matvec("draft.head.lm_head", [x], LH, n_out=V, k=D_, bytes_=V * D_, fmt="fp8",
                    desc="shared lm_head over the block")
    prev = lg
    R = DSPARK["dspark_markov_rank"]
    ops.vpu = 1
    for i in range(gamma):
        e = g.add(f"draft.mk{i}.embed", [prev], layer=LH, depth=ops.cyc(D.SU_BASE) + 2e-9, ctrl=ops.bctrl,
                  desc="Markov embed row [256] of the previous token (ROM)")
        b = ops.matvec(f"draft.mk{i}.head", [e, lg], LH, n_out=V, k=R, bytes_=V * R * 2, fmt="bf16",
                       desc="Markov head [129280, 256] BF16, vocabulary split")
        a = ops.ew(f"draft.mk{i}.add", [b], math.ceil(V / G), D.SU_BASE + D.FADD, LH, desc="logits + bias")
        r = ops.reduce(f"draft.mk{i}.argmax", [a], math.ceil(V / G), LH, desc="local argmax")
        prev = ops.collective(f"draft.mk{i}.merge", [r], LH, op="all_gather", payload=G * 8 / max(1, gamma),
                              desc="best {logit, id} per die -> next draft token") or r
    ops.vpu = None
    return prev


# -- DFlash (external drafter for Qwen3-8B) as a graph --------------------------------------------------------
def dflash_ctx_graph(ops: SpecOps, n_ctx):
    """Per cycle, the drafter's own context K/V for the verified positions: fc over the concatenated
    target features of layers 1/9/17/25/33, then k/v projections (+ k norm, RoPE) in each draft layer."""
    H, NL = DFLASH["hidden_size"], DFLASH["num_hidden_layers"]
    kvd = DFLASH["num_key_value_heads"] * DFLASH["head_dim"]
    nt = len(DFLASH["target_layer_ids"])
    t = ops.join("dctx.start", [], layer=0)
    f = ops.matvec("dctx.fc", [t], 0, n_out=H, k=nt * H, bytes_=nt * H * H * ops.bpp, fmt="w4a8",
                   desc="fc [4096, 20480] over the target features")
    f = ops.rmsnorm("dctx.hidden_norm", [f], H, 0)
    last = f
    for L in range(NL):
        kv = ops.matvec(f"dctx.L{L}.kv", [f], L, n_out=2 * kvd, k=H, bytes_=2 * kvd * H * ops.bpp, fmt="w4a8",
                        desc="k_proj | v_proj of the context features")
        kn = ops.rmsnorm(f"dctx.L{L}.k_norm", [kv], kvd, L, segments=DFLASH["num_key_value_heads"])
        last = ops.ew(f"dctx.L{L}.rope", [kn, last], kvd, D.SU_BASE + 2 * D.FADD, L, desc="RoPE, KV append")
    return last


def dflash_block_shape(bpp):
    return dict(H=DFLASH["hidden_size"], L=DFLASH["num_hidden_layers"], NH=DFLASH["num_attention_heads"],
                KV=DFLASH["num_key_value_heads"], HD=DFLASH["head_dim"], FF=DFLASH["intermediate_size"],
                V=DFLASH["vocab_size"], qk_norm=True, bytes_per_param=bpp)


# -- the ROM targets ---------------------------------------------------------------------------------------------
class Env:
    def __init__(self):
        tech = json.loads(D.TECH.read_text())
        self.links = D.link_consts(tech)
        clock, _ = D.routed_clock()
        self.clock = clock
        self.p = replace(D.Params(), clock_hz=clock)
        self.points, self.designs = D.v41_study_rows()
        self.c = D.v41_shape()
        self.opt = D.packaging("b")
        self.tech = tech


def v41_target(env, batch, ctx):
    opt = env.opt
    mach = D.v41_machine("array", opt["group"], batch, env.points, env.designs, env.p, env.clock,
                         placement=D.HEADLINE_PLACEMENT)
    fab = D.ArrayFabric(env.links, opt["dies_per_package"], "mesh", opt["group"])
    c = env.c
    WIN, TOPK = c["window_tokens"], c["index_topk"]

    def kv_shared(name):
        if not name.endswith(".attn.scores"):
            return 1.0
        L = int(name[1:].split(".")[0])
        ratio = c["compress_ratios"][L] if L < len(c["compress_ratios"]) else 0
        if not ratio:
            return 1.0
        n_sel = min(TOPK, ctx // ratio)
        win = min(WIN, ctx) * 528
        return win / (win + n_sel * 288)
    return dict(mach=mach, fabric=fab, builder=D.v41_graph, args=(c, ctx), kv_shared=kv_shared,
                users=mach.microbatch, kv_scale=opt["group"], elem_scale=opt["group"],
                experts=(c["num_routed_experts"], c["experts_per_token"]),
                label=f"x188 array, packaging option (b): {opt['label']}")


def qwen_target(env, batch, ctx):
    mach = D.hc1_machine(D.QWEN, env.p, env.clock)
    if batch > 1:
        mach = replace(mach, microbatch=float(batch), batch=batch, slots=1.0)
    shape = dict(hdc_timing.SHAPES["qwen3-8b"], qk_norm=True, bytes_per_param=3.5 / 8)
    return dict(mach=mach, fabric=D.SingleFabric(), builder=D.dense_graph, args=(shape, ctx), kv_shared=None,
                users=mach.microbatch, kv_scale=1.0, elem_scale=1.0, shape=shape,
                label="Qwen3-8B on one HC1-class N6 reticle (815 mm2), weights in ROM, KV in on-die SRAM")


_VERIFY = {}


def verify(env, tgt, n, m, su=1):
    """A verification pass of n positions per user (n = 1: the autoregressive token) on m MAC lanes per weight
    lane and a stream unit `su` times the record's width."""
    key = (tgt["builder"].__name__, tgt["args"][-1], tgt["mach"].batch, n, m, su)
    if key not in _VERIFY:
        _VERIFY[key] = _verify(env, tgt, n, m, su)
    return _VERIFY[key]


def _verify(env, tgt, n, m, su):
    ps = Pass(tgt["mach"], env.p, env.clock, tgt["builder"], tgt["args"], positions=n, m=m, users=tgt["users"],
              kv_shared=tgt["kv_shared"], su_mult=su)
    ps.experts = tgt.get("experts")
    r = ps.evaluate(tgt["fabric"])
    mach = tgt["mach"]
    occ = r["occupancy_sum_s"] * mach.slots / max(1, mach.stages)
    return ps, dict(T=r["T"], occ_bound=occ, period=max(r["T"], occ),
                    breakdown_us={k: v * 1e6 for k, v in r["cats"].items()})


def per_vec_rate(env, tgt):
    ps = Pass(tgt["mach"], env.p, env.clock, tgt["builder"], tgt["args"], positions=1, m=1, users=tgt["users"],
              kv_shared=tgt["kv_shared"])
    return ps.rate


def v41_draft(env, tgt, gamma, m, su=1):
    rate = per_vec_rate(env, tgt)
    ps = Pass(tgt["mach"], env.p, env.clock, dspark_graph, (env.c, tgt["args"][1], gamma), positions=gamma, m=m,
              users=tgt["users"], per_vec_rate=rate, su_mult=su)
    ps.experts = (DSPARK["dspark_n_routed_experts"], DSPARK["dspark_n_activated_experts"])
    r = ps.evaluate(tgt["fabric"])
    mach = tgt["mach"]
    # every user in flight drafts on the one MTP group once per cycle
    in_flight = mach.batch / max(1e-9, mach.microbatch)
    occ = r["occupancy_sum_s"] * in_flight
    return ps, dict(T=r["T"], occ_bound=occ, breakdown_us={k: v * 1e6 for k, v in r["cats"].items()})


def qwen_draft(env, tgt, gamma, m, placement, stacks=1, su=1):
    """DFlash on the reticle: `rom` (quantised like the target, extra ROM layers) or `hbm` (BF16 weights on
    `stacks` HBM3E stacks; the shared lm_head stays in ROM).  Two serial parts: the drafter's context K/V
    update for the n = gamma + 1 verified positions, then the block of gamma positions."""
    rate = per_vec_rate(env, tgt)
    ctx = tgt["args"][1]
    bpp = tgt["shape"]["bytes_per_param"] if placement == "rom" else 2.0
    hbm_bw = stacks * env.tech["hbm"]["hbm3e"]["stack_bandwidth_bytes_s"]["value"] if placement == "hbm" else None
    # the drafter's engine time per vector is the target's for the same matrix (same lanes); the target's sweep
    # basis is bytes at its 3.5-bit storage, so BF16 bytes are rescaled to it; on HBM the weight read is also
    # bounded by the stacks' bandwidth
    rate_used = rate * (tgt["shape"]["bytes_per_param"] / bpp if tgt["mach"].sweep_basis == "bytes" else 1.0)
    hbm_nodes = (lambda k: not k.startswith("head.")) if placement == "hbm" else None

    def ctx_builder(ops):
        ops.bpp = bpp
        return dflash_ctx_graph(ops, gamma + 1)
    p1 = Pass(tgt["mach"], env.p, env.clock, ctx_builder, (), positions=gamma + 1, m=m, users=tgt["users"],
              per_vec_rate=rate_used, hbm_weight_bw=hbm_bw, hbm_nodes=hbm_nodes, su_mult=su)
    r1 = p1.evaluate(tgt["fabric"])
    p2 = Pass(tgt["mach"], env.p, env.clock, D.dense_graph, (dflash_block_shape(bpp), ctx), positions=gamma, m=m,
              users=tgt["users"], per_vec_rate=rate_used, hbm_weight_bw=hbm_bw, hbm_nodes=hbm_nodes, su_mult=su)
    r2 = p2.evaluate(tgt["fabric"])
    T = r1["T"] + r2["T"]
    bd = {k: (r1["cats"][k] + r2["cats"][k]) * 1e6 for k in r1["cats"]}
    return (p1, p2), dict(T=T, occ_bound=T, breakdown_us=bd)


def dflash_bytes(bpp):
    H, FF, NL = DFLASH["hidden_size"], DFLASH["intermediate_size"], DFLASH["num_hidden_layers"]
    q = DFLASH["num_attention_heads"] * DFLASH["head_dim"]
    kvd = DFLASH["num_key_value_heads"] * DFLASH["head_dim"]
    layer = H * (q + 2 * kvd) + q * H + 3 * H * FF
    fc = len(DFLASH["target_layer_ids"]) * H * H
    matrices = NL * layer + fc
    assert abs(matrices - DFLASH["published_params"]) / DFLASH["published_params"] < 1e-3   # norms are the rest
    return DFLASH["published_params"] * bpp, DFLASH["published_params"]


# -- energy ------------------------------------------------------------------------------------------------------
def energy_terms(env):
    so = json.loads(SIGNOFF.read_text())
    a = so["architectures"]
    t = so["energy_terms"]
    q = a["qwen3_8b_rom_reticle"]
    v = a["deepseek_v41_rom_array_die"]
    h = a["hbm_comparator"]
    # the reduced Qwen vehicle's graph, for its stream-unit element count (the rest-of-core energy basis)
    red = hdc_timing.SHAPES["qwen3-reduced"]
    mach = D.hc1_machine(D.QWEN, env.p, env.clock)
    shape = dict(red, qk_norm=True, bytes_per_param=2.0)
    veh = Pass(mach, env.p, env.clock, D.dense_graph, (shape, 16), positions=1, m=1, users=1.0).work()
    me_q = q["logic"]["matrix_engine (u_me)"]["TT"]["total_j"]
    rest_q = q["totals_j"]["token_TT"] - me_q - sum(x["energy_j"] for x in q["memory"].values())
    e = dict(
        rom_j_per_byte=t["rom_read_j_per_byte"]["value"], sram_j_per_byte=t["sram_read_j_per_byte"]["value"],
        hbm_j_per_byte=t["hbm_j_per_byte"]["value"],
        me_j_per_mac_qwen=q["pj_per_mac"]["matrix_engine_logic_pj_per_mac"] * 1e-12,
        me_j_per_mac_v41=v["pj_per_mac"]["matrix_engine_logic_pj_per_mac"] * 1e-12,
        rest_j_per_element=rest_q / veh["stream_elements"],
        vehicle=dict(macs_graph=veh["weight_macs"] + veh["kv_macs"], macs_signoff=q["pj_per_mac"]["macs_per_token"],
                     stream_elements_graph=veh["stream_elements"], rest_of_core_j=rest_q,
                     matrix_engine_j=me_q, token_j=q["totals_j"]["token_TT"],
                     hbm_comparator_token_j=h["totals_j"]["token_TT"] if "token_TT" in h["totals_j"] else None),
        grades=dict(rom_read_j_per_byte=t["rom_read_j_per_byte"]["grade"],
                    sram_read_j_per_byte=t["sram_read_j_per_byte"]["grade"],
                    hbm_j_per_byte=t["hbm_j_per_byte"]["grade"],
                    matrix_engine="measured (ASAP7 sign-off, RTL activity on the routed netlist)"),
        leak_w_per_mm2=a["hbm_comparator"]["analytical_comparison"]["static_leakage_w_per_mm2_logic"]["measured"])
    return e


def pass_energy(E, work, users, model, kv_medium, weight_medium="rom", hbm_reads=None):
    """Joules per USER of one pass from its work totals (signoff-anchored)."""
    me = E["me_j_per_mac_v41"] if model == "v41" else E["me_j_per_mac_qwen"]
    w = work
    wj = E[weight_medium + "_j_per_byte"] * (w["weight_bytes_read"] if hbm_reads is None else hbm_reads)
    if weight_medium == "hbm" and hbm_reads is not None:
        wj += E["sram_j_per_byte"] * max(0.0, w["weight_bytes_read"] - hbm_reads)   # re-reads from the tile buffer
    j = (me * (w["weight_macs"] + w["kv_macs"]) + wj + E[kv_medium + "_j_per_byte"] * w["kv_bytes"]
         + E["rest_j_per_element"] * w["stream_elements"])
    return j / users


# -- area ------------------------------------------------------------------------------------------------------------
def area_model(env, tgt, dies, die_mm2):
    lanes = tgt["mach"].mac_rate_per_die / env.clock
    mv = json.loads(MATVEC_PHYS.read_text())["design"]
    mac = json.loads(MAC_PHYS.read_text())["design"]
    hi = mv["area_um2"] / (I.W_LANES * 4)
    lo = mac["area_um2"]
    out = {}
    for m in M_LADDER:
        add_lo = (m - 1) * lanes * lo * 1e-6 * dies
        add_hi = (m - 1) * lanes * hi * 1e-6 * dies
        out[m] = dict(added_mm2_low=add_lo, added_mm2_high=add_hi, added_mm2_per_die_high=add_hi / dies,
                      fraction_of_design_high=add_hi / (dies * die_mm2), fraction_of_design_low=add_lo / (dies * die_mm2))
    return dict(weight_lanes_per_die=lanes, mac_area_um2_low=lo, mac_area_um2_high=hi, dies=dies, die_mm2=die_mm2,
                design_mm2=dies * die_mm2,
                low_source=f"{rel(MAC_PHYS)} design.area_um2 (pipelined BF16 x BF16 -> FP32 MAC, closed={mac['closed']})",
                high_source=f"{rel(MATVEC_PHYS)} design.area_um2 {mv['area_um2']} / 64 lanes (the whole matrix-engine "
                            f"lane incl. operand memory and sequencing, closed={mv['closed']})",
                lanes_basis="the die's weight lanes = decode_critical_path mac_rate_per_die / clock (compute area x 0.9 "
                            "/ the matrix-engine lane area, the record's own lane count); ASAP7 areas applied to "
                            "the N5/N6 compute area as the record does (no node scaling)",
                by_m=out)


# -- GPU ---------------------------------------------------------------------------------------------------------------
_GPU_CACHE = {}


def gpu_env():
    if "S" not in _GPU_CACHE:
        import run_speculative_roofline as S
        from opentallas.roofline import Technology
        _GPU_CACHE["S"] = S
        _GPU_CACHE["tech"] = Technology.load(S.TECHNOLOGY_PATH)
        _GPU_CACHE["profiles"] = json.loads(PROFILES.read_text())["profiles"]
    return _GPU_CACHE


GPU_CANDIDATES = 12          # fastest autoregressive designs per (study, batch, feasibility class) searched
# DFlash's own absolute rates on ONE B200 (arXiv:2602.06036, Table 3: SGLang, FA4 backend, Spec-v2 overlap
# scheduling, greedy, Qwen3-8B, block 16); aggregate tokens/s at each concurrency.
DFLASH_B200 = dict(
    source="arXiv:2602.06036 (DFlash), Table 3: SGLang, FA4 backend, Spec-v2 overlap, one B200, greedy, Qwen3-8B",
    rows=[dict(workload="MATH-500", concurrency=1, ar=230.0, dflash=1175.0, tau=8.01),
          dict(workload="HumanEval", concurrency=1, ar=229.0, dflash=955.0, tau=6.50),
          dict(workload="MATH-500", concurrency=4, ar=861.0, dflash=3884.0, tau=None),
          dict(workload="MATH-500", concurrency=8, ar=1666.0, dflash=7485.0, tau=None),
          dict(workload="MATH-500", concurrency=16, ar=3133.0, dflash=12268.0, tau=None),
          dict(workload="MATH-500", concurrency=32, ar=5694.0, dflash=16076.0, tau=None)])
LMSYS_V4PRO = dict(source="LMSYS Org, https://www.lmsys.org/blog/2026-07-06-dspark-sglang/ (2026-07-06)",
                   model="DeepSeek-V4-Pro", hardware="8x B300, TP=8", batch=1, tokens_s_per_user=383.7, tau=5.0,
                   cycle_s=5.0 / 383.7, verify_ms_example=7.3,
                   note="'383.7 tok/s at accept length ~5 at batch size 1'; 'things outside the target verify "
                        "shrinks by 1.7 ms, against a 7.3 ms verify' (one example profile). No non-speculative "
                        "batch-1 rate is published beside it, so no V4-family overhead can be fitted: the "
                        "V4.1-Flash GPU rows are projections, and their calibrated band transfers the Qwen3-8B/B200 "
                        "per-forward overhead.")
# attention heads (query, KV) for the tensor-parallel feasibility of a GPU point: a tensor group must split the
# heads.  Qwen3-8B: TP in {1, 2, 4, 8} splits the 8 KV heads; 16 and 32 only with KV-head replication (allowed,
# labelled); any other group (the study's x25/x29/x31/x38/x50/x58 tensor points, the 64/72-wide hybrids) cannot
# split 32 query heads.  V4.1-Flash: 64 query heads over one shared latent KV head (replicated by construction).
HEADS = {"Qwen3-8B": (32, 8), "DeepSeek-V4.1-Flash": (64, 1)}
GPU_BLOCKS = ("idealised", "feasible", "feasible_calibrated", "feasible_calibrated_nccl")
# model-specific blocks: Qwen3-8B is compared iso-area on ONE reticle of logic -- the single-B200 point
# normalised to one of its two dies (half the HBM bandwidth, compute and static power; the dependency chain
# unchanged), calibrated with the measured per-forward overhead; the scale-out blocks above are sensitivities.
# V4.1 adds the best head-feasible GPU at the ROM array's total logic area (iso_area).
MODEL_BLOCKS = {"Qwen3-8B": ("single_die", "single_die_calibrated"),
                "DeepSeek-V4.1-Flash": ("iso_area", "iso_area_calibrated")}
HEADLINE_GPU = {"Qwen3-8B": "single_die_calibrated", "DeepSeek-V4.1-Flash": "iso_area_calibrated"}
BLOCK_GRADES = {
    "idealised": "projection: the study's fastest point, head divisibility unchecked, fused persistent kernel, "
                 "2.43 us all-reduce (the idealised bound)",
    "feasible": "projection: head-feasible tensor group, fused persistent kernel, 2.43 us all-reduce",
    "feasible_calibrated": "projection calibrated to DFlash's measured single-B200 rates (per-forward serving "
                           "overhead), head-feasible, 2.43 us all-reduce",
    "feasible_calibrated_nccl": "as feasible_calibrated with stock-NCCL 11.0 us all-reduces",
    "single_die": "projection: one B200 die (half of the single-B200 point: half the HBM bandwidth, compute and "
                  "static power), fused persistent kernel -- one reticle of logic, iso-area with the ROM reticle",
    "single_die_calibrated": "single_die with the per-forward serving overhead measured on one B200 (DFlash "
                             "Table 3) -- the iso-area headline for Qwen3-8B",
    "iso_area": "projection: the best head-feasible B200 configuration within the ROM array's total logic area "
                "(188 x 815 mm2), fused persistent kernel",
    "iso_area_calibrated": "iso_area with the per-forward serving overhead measured on one B200 (transferred from "
                           "Qwen3-8B; no V4.1 measurement exists)",
}


def head_class(model, tg):
    q, kv = HEADS[model]
    tg = int(tg or 1)
    if kv > 1 and kv % tg == 0:
        return "kv_split"
    if q % tg == 0:
        return "kv_replicated"
    return "infeasible"


def nccl_technology():
    """The GPU's in-domain all-reduce at stock NCCL (11.0 us: technology.json links.nvlink5*.hop_latency_s
    range_high, two traversals) instead of the measured 2.43 us one-shot kernel the study carries."""
    ge = gpu_env()
    if "tech_nccl" not in ge:
        raw = json.loads(json.dumps(ge["tech"].raw))
        for k, v in raw["links"].items():
            if k.startswith("nvlink5"):
                v["hop_latency_s"]["value"] = v["hop_latency_s"]["range_high"]
        ge["tech_nccl"] = replace(ge["tech"], raw=raw)
    return ge["tech_nccl"]


def _gpu_study(model, ctx, batch, iso_mm2=None):
    ge = gpu_env()
    S, tech = ge["S"], ge["tech"]
    from opentallas.schema import ModelProfile
    from opentallas.workload import kv_traffic
    path = GPU_STUDIES[(model, ctx)]
    key = (str(path), model, batch, iso_mm2)
    if key not in _GPU_CACHE:
        body = S._load_study_artifact(path)
        designs = {d["name"]: d for d in body["designs"]}
        mp = ModelProfile.load(ROOT / body["inputs"]["models"][model]["path"])
        bal = float(body["technology_derivations"]["efficiencies"]["stage_balance"]["value"])
        pts = [p for p in body["points"] if p["model"] == model and p["family"] == "gpu" and p["feasible"]
               and p["batch_size"] == batch]
        pts.sort(key=lambda p: -p["per_user_tokens_s"])
        kv = kv_traffic(mp, int(pts[0]["context_tokens"]))
        feas = [p for p in pts if head_class(model, p["tensor_group"]) != "infeasible"]
        cand = pts[:GPU_CANDIDATES] + [p for p in feas[:GPU_CANDIDATES] if p not in pts[:GPU_CANDIDATES]]
        cand += [p for p in pts if p["device_count"] == 1 and p not in cand][:1]
        if iso_mm2:
            cand += [p for p in feas if p["silicon_area_mm2"] <= iso_mm2 and p not in cand][:GPU_CANDIDATES]
        dec, problems = [], []
        for p in cand:
            base, pr = S.decompose(p, designs[p["design"]], mp, tech, kv, bal)
            problems += pr
            dec.append((p, base))
        _GPU_CACHE[key] = dict(designs=designs, mp=mp, dec=dec, problems=problems, study=rel(path), kv=kv, bal=bal,
                               feasible_points=len(pts), head_feasible_points=len(feas),
                               head_infeasible_designs_faster_than_best_feasible=[
                                   p["design"] for p in pts if head_class(model, p["tensor_group"]) == "infeasible"
                                   and feas and p["per_user_tokens_s"] > feas[0]["per_user_tokens_s"]][:20])
    return _GPU_CACHE[key]


def _gpu_eval(st, p, base, drafter, gamma, share, markov, nccl=False, die=1.0):
    """(AR step, speculative cycle and its parts, energy terms) of one GPU point, optionally with NCCL all-reduces;
    `die` < 1 prices that fraction of the point's silicon (bandwidth, compute and static power scale; the
    dependency chain does not)."""
    ge = gpu_env()
    S = ge["S"]
    ck = (st["study"], p["design"], p["batch_size"], gamma, share, drafter.profile if drafter else None, nccl, die)
    if ck in _GPU_CACHE:
        return _GPU_CACHE[ck]
    tech = nccl_technology() if nccl else ge["tech"]
    design = st["designs"][p["design"]]
    if die != 1.0:
        k = 1.0 / die
        design = dict(design, weight_read_bytes_s=design["weight_read_bytes_s"] * die,
                      kv_read_bytes_s=design["kv_read_bytes_s"] * die)
        base = replace(base, weight_s=base.weight_s * k, kv_s=base.kv_s * k, compute_s=base.compute_s * k)
        sweep = S._service(base.weight_s, base.kv_s, base.compute_s, base) / base.balance
        path = S._serial_path(p, st["mp"], tech, base.microbatch, sweep)[0]
        ar_step = max(sweep, path) * base.thermal_scale
        base = replace(base, step_time_s=ar_step, raw_step_time_s=ar_step / base.thermal_scale)
    elif nccl:
        S._SERIAL_CACHE.clear()
        base = S.decompose(p, st["designs"][p["design"]], st["mp"], tech, st["kv"], st["bal"])[0]
        sweep = S._service(base.weight_s, base.kv_s, base.compute_s, base) / base.balance
        path = S._serial_path(p, st["mp"], tech, base.microbatch, sweep)[0]
        ar_step = max(sweep, path) * base.thermal_scale
        base = replace(base, step_time_s=ar_step)
    else:
        ar_step = p["step_time_s"]
    cyc = S.speculative_cycle(p, design, st["mp"], tech, base, drafter, gamma, "in_hbm", share)
    if nccl:
        S._SERIAL_CACHE.clear()
    users = max(1e-30, p["pipeline_fill_users"])
    static_per_token = p["energy_j_per_token"] - p["dynamic_energy_j_per_token"]
    served = p["static_power_w"] * p["step_time_s"] / static_per_token if static_per_token > 0 else 1.0
    _GPU_CACHE[ck] = r = dict(ar_step=ar_step, cycle=cyc["cycle_s"] + markov, verify_s=cyc["verify_s"],
                              draft_s=cyc["draft_s"] + markov, dyn_j=cyc["cycle_energy_j"] / users,
                              ar_dyn_j=p["dynamic_energy_j_per_token"], static_w=p["static_power_w"] * die,
                              served=served)
    return r


def gpu_calibration():
    """The single-B200 check against DFlash's own absolute rates, and the per-forward overhead it implies.

    Model: the study's one-B200 Qwen3-8B point (8K context) and its DFlash cycle (block 16).  Measured: Table 3
    at concurrency 1.  The serving stack's per-FORWARD overhead o is fitted on the autoregressive step
    (o = 1/measured - model step); a DFlash cycle is two forwards (draft, verify), so its calibrated cycle is the
    model cycle + 2 o, checked against both concurrency-1 rows with nothing further fitted."""
    ge = gpu_env()
    st = _gpu_study("Qwen3-8B", 8192, 1)
    p, base = next((p, b) for p, b in st["dec"] if p["device_count"] == 1)
    drafter = ge["S"].build_drafter("sota_block_diffusion", ge["profiles"]["sota_block_diffusion"], st["mp"])
    c = _gpu_eval(st, p, base, drafter, 16, 0.0, 0.0)
    o = 1 / DFLASH_B200["rows"][0]["ar"] - p["step_time_s"]
    rows = []
    for r in DFLASH_B200["rows"][:2]:
        pred_ar = 1 / (p["step_time_s"] + o)
        pred = r["tau"] / (c["cycle"] + 2 * o)
        rows.append(dict(r, model_ar=1 / p["step_time_s"], model_dflash=r["tau"] / c["cycle"],
                         calibrated_ar=pred_ar, calibrated_dflash=pred, dflash_error=pred / r["dflash"] - 1,
                         ar_error=pred_ar / r["ar"] - 1, measured_speedup=r["dflash"] / r["ar"],
                         calibrated_speedup=pred / pred_ar, model_speedup=r["tau"] * p["step_time_s"] / c["cycle"],
                         measured_cycle_over_ar_step=(r["tau"] / r["dflash"]) * r["ar"],
                         model_cycle_over_ar_step=c["cycle"] / p["step_time_s"]))
    conc = []
    for r in DFLASH_B200["rows"][2:]:
        sb = _gpu_study("Qwen3-8B", 8192, r["concurrency"])
        pb = next((q for q, _ in sb["dec"] if q["device_count"] == 1), None)
        if pb is None:
            continue
        agg = r["concurrency"] / (pb["step_time_s"] + o)
        conc.append(dict(r, model_ar_aggregate=r["concurrency"] / pb["step_time_s"], calibrated_ar_aggregate=agg,
                         ar_error=agg / r["ar"] - 1))
    return dict(measured=DFLASH_B200, design=p["design"], context_tokens=p["context_tokens"],
                model_ar_step_s=p["step_time_s"], model_dflash_cycle_s=c["cycle"], per_forward_overhead_s=o,
                forwards_per_ar_step=1, forwards_per_spec_cycle=2, concurrency_1=rows, higher_concurrency=conc,
                higher_concurrency_note="the study's 8K context reads far more KV than the benchmark's short prompts, "
                                        "so the model over-charges KV as concurrency grows; concurrency 1 is the "
                                        "calibration and these rows are reported, not fitted",
                v4_family=LMSYS_V4PRO, tolerance="calibrated DFlash rate within 5% of both concurrency-1 rows",
                passes=all(abs(r_["dflash_error"]) <= 0.05 for r_ in rows),
                study_defects=dict(
                    head_divisibility="the roofline study sizes GPU tensor groups with no head-divisibility check: "
                                      "its fastest Qwen3-8B point (b200_sxm-x58-nvl72-tensor) splits 32 query / 8 KV "
                                      "heads 58 ways, which no kernel can do; this layer restricts the GPU to "
                                      "tensor groups that split the heads (Qwen3-8B: 1/2/4/8, or 16/32 with KV-head "
                                      "replication) and keeps the study's choice only as the idealised bound",
                    all_reduce="the study charges a 2.43 us in-domain all-reduce for any rank count (extrapolated "
                               "from 2.37 us measured on 4 GB200, arXiv:2607.16100); stock NCCL is 11.0 us: both "
                               "are carried as the calibrated band's ends",
                    fused_chain="the per-layer fixed chain assumes a fused persistent megakernel; SGLang on one B200 "
                                "runs 1.64x slower than the model's step (230 vs 377 tok/s)"))


def gpu_rows(model, ctx, batch, gamma, profile_name, taus, overhead_s=0.0, iso_mm2=None):
    """The GPU band per (context, batch, gamma): the study's idealised bound (fastest point, any tensor group),
    the head-feasible fused projection, that projection calibrated with the measured per-forward serving
    overhead, and the same with stock-NCCL all-reduces.  AR and speculative designs are chosen separately."""
    ge = gpu_env()
    tech = ge["tech"]
    st = _gpu_study(model, ctx, batch, iso_mm2)
    prof = ge["profiles"][profile_name]
    drafter = ge["S"].build_drafter(profile_name, prof, st["mp"])
    gather = tech.raw["serial_latency"]["gpu_datapath"]["dependent_boundary_gather_s"]["value"]
    markov = gamma * 2 * gather if prof["drafter_family"] == "mtp_stack_with_sequential_markov_bias" else 0.0
    out = dict(study=st["study"], reconstruction_problems=len(st["problems"]), feasible_points=st["feasible_points"],
               head_feasible_points=st["head_feasible_points"], candidates=len(st["dec"]), markov_boundaries_s=markov,
               drafter=profile_name,
               head_infeasible_designs_faster_than_best_feasible=st["head_infeasible_designs_faster_than_best_feasible"])
    out["iso_area_mm2"] = iso_mm2
    for label in GPU_BLOCKS + MODEL_BLOCKS[model]:
        o = overhead_s if "calibrated" in label else 0.0
        nccl = label.endswith("nccl")
        die = 0.5 if label.startswith("single_die") else 1.0
        if label.startswith("single_die"):
            pool = [(p, b) for p, b in st["dec"] if p["device_count"] == 1]
        elif label.startswith("iso_area"):
            pool = [(p, b) for p, b in st["dec"] if head_class(model, p["tensor_group"]) != "infeasible"
                    and p["silicon_area_mm2"] <= iso_mm2]
        else:
            pool = [(p, b) for p, b in st["dec"]
                    if label == "idealised" or head_class(model, p["tensor_group"]) != "infeasible"]
        evs = [(p, _gpu_eval(st, p, b, drafter, gamma, 0.0, markov, nccl, die)) for p, b in pool]
        ar_p, ar_e = min(evs, key=lambda t: t[1]["ar_step"])
        ar_step = ar_e["ar_step"] + o
        blk = dict(grade=BLOCK_GRADES[label], role="headline" if label == HEADLINE_GPU[model] else
                   ("scale-out sensitivity" if model == "Qwen3-8B" and label in GPU_BLOCKS else "band"),
                   silicon_mm2=ar_p["silicon_area_mm2"] * die,
                   ar=dict(design=ar_p["design"], tensor_group=ar_p["tensor_group"],
                           head_class=head_class(model, ar_p["tensor_group"]), tokens_s_per_user=1 / ar_step,
                           step_s=ar_step,
                           energy_j_per_token=ar_e["ar_dyn_j"] + ar_e["static_w"] * ar_step / ar_e["served"]),
                   spec={})
        for band, share in (("draft_kv_low", 0.0), ("draft_kv_high", 1.0)):
            best = None
            for p, b in pool:
                c = _gpu_eval(st, p, b, drafter, gamma, share, markov, nccl, die)
                cycle = c["cycle"] + 2 * o
                if best is None or cycle < best[1]:
                    best = (p, cycle, c)
            p, cycle, c = best
            ej = c["dyn_j"] + c["static_w"] * cycle / c["served"]
            blk["spec"][band] = dict(design=p["design"], tensor_group=p["tensor_group"],
                                     head_class=head_class(model, p["tensor_group"]), cycle_s=cycle,
                                     verify_s=c["verify_s"] + o, draft_s=c["draft_s"] + o, tau_break=cycle / ar_step,
                                     by_tau={str(t): dict(tokens_s_per_user=min(t, gamma + 1) / cycle,
                                                          energy_j_per_accepted_token=ej / min(t, gamma + 1))
                                             for t in taus})
        out[label] = blk
    return out


# -- the program-level cross-check -------------------------------------------------------------------------------
def program_replay(n, m, groups=1024, pos=1024, su_width=1):
    """The verification law applied to the calibrated program replay itself (tools/hdc_timing.simulate on the
    full Qwen3-8B program): every matrix-engine element loop x ceil(n/m), every stream-unit op's elements x n,
    the program (issue gaps, barriers, chases, depths) unchanged."""
    import hdc_program as P
    shape = hdc_timing.SHAPES["qwen3-8b"]
    prog = P.build_program(hdc_timing.ShapeLayout(shape, groups))
    dyn_shape = dict(H=shape["H"], half=shape["HD"] // 2, HD=shape["HD"])
    dyn = hdc_timing.dyn_values(pos, groups=groups, **dyn_shape)
    c = math.ceil(n / m)
    out = []
    for f in prog:
        f = dict(f)
        if f.get("unit") == I.UNIT_ME:
            k = f.get("me_k", 0) + dyn[f.get("me_d_k", 0)]
            f["me_k"] = k * c - dyn[f.get("me_d_k", 0)]
        elif f.get("unit") == I.UNIT_SU:
            f["su_nout"] = f.get("su_nout", 0) * n
        out.append(f)
    _, t = hdc_timing.simulate(out, pos, groups=groups, dyn_shape=dyn_shape, su_width=su_width)
    return t


# -- acceptance lengths: cited points, one derivation, and the curve ------------------------------------------------------
TAU_GRID = tuple(x / 2 for x in range(3, 17))          # 1.5 .. 8.0, capped at gamma + 1 per scenario
VLLM_DSPARK = "https://vllm.ai/blog/2026-08-14-dspark-adaptive-verification"
DSPARK_PAPER = "arXiv:2607.05147 (DSpark, DeepSeek-AI 2026), Table 1: accepted length incl. the bonus token, " \
               "temperature 1.0, chain drafting, block 7, 5-layer drafters retrained on Open-PerfectBlend"
DSPARK_T1 = {  # Qwen3-8B rows of arXiv:2607.05147 Table 1 (GSM8K, MATH, AIME25, MBPP, HumanEval, LCB, MT-Bench,
    # Alpaca, Arena-Hard)
    "benchmarks": ["GSM8K", "MATH", "AIME25", "MBPP", "HumanEval", "LiveCodeBench", "MT-Bench", "Alpaca", "Arena-Hard"],
    "Eagle3": [5.30, 4.77, 3.91, 3.96, 4.33, 4.17, 2.66, 2.54, 2.54],
    "DFlash": [5.33, 4.91, 4.07, 4.36, 4.64, 4.39, 3.11, 2.98, 2.81],
    "DSpark": [6.17, 5.78, 5.01, 5.16, 5.52, 5.17, 3.72, 3.58, 3.21],
}


def v4_survival_derivation():
    """tau from the only per-position survival figures DeepSeek's serving partners publish for the V4 family:
    vLLM's DSpark blog, DeepSeek-V4-Pro-0813, 7-token block, 880 prompts at temperature 1.0: 'the last drafted
    token of a 7-token block survives less than 10% of the time, against more than 70% for the first'.
    With S_k the probability that draft position k is accepted (the survival of the prefix through k),
    tau = 1 + sum_k S_k (the bonus token plus every surviving draft).  Two endpoints do not fix the five
    interior positions, so the interior is interpolated two ways and the hard bounds are stated."""
    s1, s7, g = 0.70, 0.10, 7
    r = (s7 / s1) ** (1 / (g - 1))
    geo = [s1 * r ** k for k in range(g)]
    lin = [s1 + (s7 - s1) * k / (g - 1) for k in range(g)]
    return dict(
        source=VLLM_DSPARK, model="DeepSeek-V4-Pro-0813", gamma=g, hardware="8x B300, TP=8, EP, FP8 KV",
        workload="880 prompts, temperature 1.0, up to 2,048 output tokens (vLLM blog); mix not named",
        published=dict(S1_greater_than=s1, S7_less_than=s7),
        formula="tau = 1 + sum_{k=1..7} S_k, S_k non-increasing in k",
        geometric=dict(ratio=r, survival=geo, tau=1 + sum(geo)),
        linear=dict(survival=lin, tau=1 + sum(lin)),
        hard_bounds=dict(low=1 + s1, high=1 + (g - 1) * 1.0 + s7,
                         note="only S1 > 0.70 and S7 < 0.10 are published: any non-increasing interior is "
                              "consistent, so the bounds are 1.70 (S2..S7 = 0) to 7.10 (S1..S6 = 1)"),
        grade="derived", note="The endpoints are strict inequalities used at their bounds; the interior is an "
                              "interpolation, not a measurement. Both readings (3.3-3.8) sit well below the "
                              "LMSYS ~5, which was measured with confidence-driven variable-length verification "
                              "at temperature unstated.")


def tau_points():
    pr = json.loads(PROFILES.read_text())["profiles"]
    ds, df = pr["released_dspark"], pr["sota_block_diffusion"]
    der = v4_survival_derivation()
    v41 = [dict(tau=ds["acceptance_length"]["points"][0]["value"], gamma=7, drafter="DSpark", model="DeepSeek-V4-Pro",
                workload="not stated by the source", grade="published", label="LMSYS SGLang ~5",
                source="LMSYS Org, https://www.lmsys.org/blog/2026-07-06-dspark-sglang/ (2026-07-06): 'accept length "
                       "~5 at batch size 1 on DeepSeek-V4-Pro, TP=8, B300'"),
           dict(tau=round(der["geometric"]["tau"], 3), gamma=7, drafter="DSpark", model="DeepSeek-V4-Pro-0813",
                workload=der["workload"], grade="derived", label="vLLM survival, geometric interior",
                source=VLLM_DSPARK + " (derivation: v4_survival_derivation)"),
           dict(tau=round(der["linear"]["tau"], 3), gamma=7, drafter="DSpark", model="DeepSeek-V4-Pro-0813",
                workload=der["workload"], grade="derived", label="vLLM survival, linear interior",
                source=VLLM_DSPARK + " (derivation: v4_survival_derivation)")]
    qw = [dict(tau=p_["value"], gamma=16, drafter="DFlash", model="Qwen3-8B", workload=p_["workload"],
               grade="published", label=f"DFlash {p_['workload']}",
               source="arXiv:2602.06036v2 Table 1 (Qwen3-8B, temperature 0, H200, block 16)")
          for p_ in df["acceptance_length"]["points"]]
    qw.append(dict(tau=df["acceptance_length"]["average"]["value"], gamma=16, drafter="DFlash", model="Qwen3-8B",
                   workload="mean of the seven", grade="published", label="DFlash mean",
                   source="arXiv:2602.06036v2 Table 1"))
    for drafter in ("DFlash", "DSpark", "Eagle3"):
        for b, t in zip(DSPARK_T1["benchmarks"], DSPARK_T1[drafter]):
            qw.append(dict(tau=t, gamma=7, drafter=drafter, model="Qwen3-8B", workload=b, grade="published",
                           label=f"{drafter} {b} (T=1.0)", source=DSPARK_PAPER,
                           priced_drafter=drafter == "DFlash"))
    return dict(v41=v41, qwen=qw, v4_survival_derivation=der,
                not_published=["No acceptance length is published for DeepSeek-V4.1-Flash (its DSpark ships in the "
                               "checkpoint; every V4-family tau here is V4-Pro's).",
                               "No acceptance length is published for agentic / tool-use workloads on either model "
                               "(the closest is Xiaomi MiMo's 'agent' 4.29 on a different 1T model, block 8, carried "
                               "in configs/studies/speculative_profiles.json only as a cross-check).",
                               "A measurement of tau on the target workloads may follow; until then every "
                               "speculative figure below is a curve over tau with the published points marked."])


def taus_for(points, gamma):
    grid = [t for t in TAU_GRID if t <= gamma + 1]
    pts = sorted({p_["tau"] for p_ in points if p_["gamma"] == gamma and p_.get("priced_drafter", True)})
    return sorted(set(grid) | set(pts))


# -- the study ---------------------------------------------------------------------------------------------------------
VARIANTS = {"me": "m MAC lanes per weight lane; stream unit as today",
            "me_su": "m MAC lanes per weight lane AND the stream unit m times as wide",
            "su": "the stream unit m times as wide, one MAC per weight lane (isolates the stream unit's share)"}
AREA_BASIS = "low"           # the recommendation prices a replicated lane as the bare pipelined MAC (the weight
                             # path -- ROM port, decode, sequencing -- is shared by the m lanes); the whole-lane
                             # (high) band is carried and its pick reported beside it


def area_rows(area, su_area):
    out = {}
    for v in VARIANTS:
        out[v] = {}
        for m in M_LADDER:
            a = dict(area["by_m"][m])
            if v == "su":
                a = {k: 0.0 for k in a}
            if v in ("me_su", "su"):
                extra = (m - 1) * su_area["su_mm2_per_die"] * area["dies"]
                a = {k: a[k] + (extra if k.startswith("added_mm2") and "per_die" not in k else 0.0) for k in a}
                a["added_mm2_per_die_high"] += (m - 1) * su_area["su_mm2_per_die"]
                a["fraction_of_design_high"] = a["added_mm2_high"] / area["design_mm2"]
                a["fraction_of_design_low"] = a["added_mm2_low"] / area["design_mm2"]
            out[v][m] = a
    return out


def scenario(env, tgt, gamma, draft_fn, energy_fn, taus, ar):
    """Every (variant, m) of one scenario: the cycle, the AR token on the same silicon, energy, the tau curve."""
    out = {}
    for v in VARIANTS:
        out[v] = {}
        for m in M_LADDER:
            su = m if v in ("me_su", "su") else 1
            lanes = 1 if v == "su" else m
            vps, vv = verify(env, tgt, gamma + 1, lanes, su)
            dps, d = draft_fn(lanes, su)
            cycle = max(vv["T"] + d["T"], vv["occ_bound"], d["occ_bound"])
            if lanes == 1 and su == 1:
                ar_m, e_ar_m = ar["period"], ar["energy"]
            else:
                ps_ar, a2 = verify(env, tgt, 1, lanes, su)
                ar_m, e_ar_m = a2["period"], energy_fn(ps_ar, ())
            e_cyc = energy_fn(vps, dps if isinstance(dps, tuple) else (dps,))
            out[v][m] = dict(
                cycle_s=cycle, verify_T_s=vv["T"], verify_occupancy_bound_s=vv["occ_bound"], draft_T_s=d["T"],
                draft_occupancy_bound_s=d["occ_bound"],
                binding="critical path (verify + draft)" if cycle == vv["T"] + d["T"] else
                ("verify occupancy" if cycle == vv["occ_bound"] else "draft occupancy"),
                ar_period_s=ar_m, ar_tokens_s_per_user=1 / ar_m, ar_energy_j_per_token=e_ar_m,
                tau_break=cycle / ar_m, tau_break_vs_m1_ar=cycle / ar["period"],
                verify_breakdown_us={k: round(x, 3) for k, x in vv["breakdown_us"].items()},
                draft_breakdown_us={k: round(x, 3) for k, x in d["breakdown_us"].items()},
                energy_j_per_cycle_per_user=e_cyc,
                curve={str(t): dict(tokens_s_per_user=t / cycle, energy_j_per_accepted_token=e_cyc / t) for t in taus})
    return out


def build():
    env = Env()
    E = energy_terms(env)
    taup = tau_points()
    su_um2 = D.lane_areas_um2()["su_lane"]
    rec = dict(schema=SCHEMA, tool=rel(Path(__file__)),
               supersedes=dict(for_hdc_designs=["results/roofline/speculative/released_dspark/REPORT.md",
                                                "results/roofline/speculative/sota_block_diffusion/REPORT.md"],
                               note="The generic study stays as the pessimistic compute-in-ROM bound: it prices a "
                                    "draft pass as a full-array sweep and each verified position as its own pass "
                                    "(per_stream), which is not the hardwired decode core."),
               clock_hz=env.clock, lane_multipliers=list(M_LADDER), variants=VARIANTS, tau=taup,
               tau_grid=list(TAU_GRID), energy_terms=E, drafters={}, targets={})
    cal = gpu_calibration()
    rec["gpu_calibration"] = cal
    o_fwd = cal["per_forward_overhead_s"]
    rec["drafters"]["v41_dspark"] = DSPARK
    bq, pq = dflash_bytes(3.5 / 8)
    rec["drafters"]["qwen3_dflash"] = dict(DFLASH, params=pq, rom_bytes_quantised=bq, bf16_bytes=dflash_bytes(2.0)[0])

    # ---- DeepSeek-V4.1-Flash on the x188 array, option (b) ----
    des = env.designs[D.ARRAY_DESIGN]
    t0 = v41_target(env, 1, 200000)
    area = area_model(env, t0, 188, des["area_split_per_device"]["total_mm2"])
    su_area = dict(su_width_per_die=t0["mach"].su_width, su_lane_um2=su_um2,
                   su_mm2_per_die=t0["mach"].su_width * su_um2 * 1e-6,
                   source="results/physical_abi3/asap7/hdc/ot_hdc_stream/physical.json design.area_um2 per element/cycle")
    t41 = dict(label=t0["label"], contexts={}, area=area, stream_unit_area=su_area,
               area_by_variant=area_rows(area, su_area), gammas=[5, 7])
    for ctx in V41_CONTEXTS:
        t41["contexts"][str(ctx)] = {}
        for bt in BATCHES:
            tgt = v41_target(env, bt, ctx)
            users = tgt["users"]

            def efn(vps, dps, tgt=tgt, users=users):
                e = 0.0
                for ps in (vps,) + tuple(dps):
                    w = ps.work(tgt["kv_scale"], tgt["elem_scale"])
                    e += pass_energy(E, w, users, "v41", "hbm")
                return e

            def efn_hbm(vps, dps, tgt=tgt, users=users):
                e = 0.0
                for ps in (vps,) + tuple(dps):
                    w = ps.work(tgt["kv_scale"], tgt["elem_scale"])
                    e += pass_energy(E, w, users, "v41", "hbm", weight_medium="hbm", hbm_reads=w["weight_bytes_unique"])
                return e
            ps0, a0 = verify(env, tgt, 1, 1)
            ar = dict(period=a0["period"], energy=efn(ps0, ()))
            cell = dict(ar=dict(period_s=a0["period"], T_s=a0["T"], occupancy_bound_s=a0["occ_bound"],
                                tokens_s_per_user=1 / a0["period"], energy_j_per_token=ar["energy"],
                                hbm_comparator_energy_j_per_token=efn_hbm(ps0, ()),
                                breakdown_us=a0["breakdown_us"], users_per_stage=users, slots=tgt["mach"].slots,
                                stages=tgt["mach"].stages),
                        gamma={})
            for gm in t41["gammas"]:
                taus = taus_for(taup["v41"], gm)
                rom = scenario(env, tgt, gm, lambda m, su, tgt=tgt, gm=gm: v41_draft(env, tgt, gm, m, su), efn,
                               taus, ar)
                # the HBM comparator core's energy on the same passes (weights from HBM, read once per pass)
                vps, _ = verify(env, tgt, gm + 1, 1)
                dps, _ = v41_draft(env, tgt, gm, 1)
                hb = efn_hbm(vps, (dps,))
                gpu = gpu_rows("DeepSeek-V4.1-Flash", ctx, bt, gm, "released_dspark", taus, o_fwd,
                               iso_mm2=188 * des["area_split_per_device"]["total_mm2"])
                cell["gamma"][str(gm)] = dict(rom=rom, gpu=gpu, taus=taus,
                                              hbm_comparator_energy_j_per_cycle_per_user_m1=hb)
            t41["contexts"][str(ctx)][str(bt)] = cell
    rec["targets"]["deepseek_v41_array_option_b"] = t41

    # ---- Qwen3-8B on one reticle ----
    t0 = qwen_target(env, 1, 2048)
    area = area_model(env, t0, 1, 815.0)
    su_area = dict(su_width_per_die=t0["mach"].su_width, su_lane_um2=su_um2,
                   su_mm2_per_die=t0["mach"].su_width * su_um2 * 1e-6,
                   source="results/physical_abi3/asap7/hdc/ot_hdc_stream/physical.json design.area_um2 per element/cycle")
    tq = dict(label=t0["label"], contexts={}, area=area, stream_unit_area=su_area,
              area_by_variant=area_rows(area, su_area), gammas=[7, 16], placements={})
    for ctx in QWEN_CONTEXTS:
        tq["contexts"][str(ctx)] = {}
        for bt in BATCHES:
            tgt = qwen_target(env, bt, ctx)
            users = tgt["users"]

            def efn_for(plc, users=users):
                def efn(vps, dps):
                    e = pass_energy(E, vps.work(), users, "qwen", "sram")
                    for dp in dps:
                        w = dp.work()
                        if plc == "hbm":
                            head = sum(nd["wbytes"] * nd.get("engine_passes", 1) for k, nd in dp.g.nodes.items()
                                       if "wbytes" in nd and k.startswith("head."))
                            e += pass_energy(E, dict(w, weight_bytes_read=head), users, "qwen", "sram")
                            e += E["hbm_j_per_byte"] * sum(nd["wbytes"] for k, nd in dp.g.nodes.items()
                                                           if "wbytes" in nd and not k.startswith("head.")) / users
                        else:
                            e += pass_energy(E, w, users, "qwen", "sram")
                    return e
                return efn

            def efn_hbm(vps, dps, users=users):
                e = 0.0
                for ps in (vps,) + tuple(dps):
                    w = ps.work()
                    e += pass_energy(E, w, users, "qwen", "sram", weight_medium="hbm",
                                     hbm_reads=w["weight_bytes_unique"])
                return e
            ps0, a0 = verify(env, tgt, 1, 1)
            ar = dict(period=a0["period"], energy=efn_for("rom")(ps0, ()))
            kv_need = bt * ctx * hdc_timing.SHAPES["qwen3-8b"]["L"] * 2 * 8 * 128 * 2
            cap = env_kv_capacity()
            cell = dict(ar=dict(period_s=a0["period"], T_s=a0["T"], tokens_s_per_user=1 / a0["period"],
                                energy_j_per_token=ar["energy"], hbm_comparator_energy_j_per_token=efn_hbm(ps0, ()),
                                breakdown_us=a0["breakdown_us"], users_per_core=users, kv_bytes_needed=kv_need,
                                kv_sram_capacity_bytes=cap, kv_fits_on_die=kv_need <= cap),
                        gamma={})
            for gm in tq["gammas"]:
                taus = taus_for(taup["qwen"], gm)
                g_cell = dict(rom={}, taus=taus, gpu=gpu_rows("Qwen3-8B", 8192, bt, gm, "sota_block_diffusion", taus, o_fwd))
                for plc, stacks in (("rom", 0),) + tuple(("hbm", s) for s in HBM_SIDE_STACKS):
                    key = plc if plc == "rom" else f"hbm_x{stacks}"
                    g_cell["rom"][key] = scenario(
                        env, tgt, gm,
                        lambda m, su, tgt=tgt, gm=gm, plc=plc, stacks=stacks: qwen_draft(env, tgt, gm, m, plc, stacks,
                                                                                         su),
                        efn_for(plc), taus, ar)
                cell["gamma"][str(gm)] = g_cell
            tq["contexts"][str(ctx)][str(bt)] = cell
    rom_mm2 = 261.97752020676927
    tq["placements"] = dict(
        rom=dict(extra_rom_bytes=bq, extra_rom_mm2=rom_mm2 * bq / (8.19e9 * 3.5 / 8),
                 note="DFlash's parameters as extra ROM at the target's 3.5-bit storage (the reticle's ROM, 262 mm2, "
                      "is sized to Qwen3-8B, so it grows by the drafter's share). Acceptance at that precision is "
                      "UNMEASURED: every published tau is BF16."),
        hbm=dict(bf16_bytes=dflash_bytes(2.0)[0], stacks=list(HBM_SIDE_STACKS),
                 phy_mm2_per_stack=env.tech["hbm"]["hbm3e"]["phy_area_mm2_per_stack"]["value"],
                 stack_bandwidth_bytes_s=env.tech["hbm"]["hbm3e"]["stack_bandwidth_bytes_s"]["value"],
                 note="BF16 weights as released, read once per draft pass for the whole block; the shared lm_head "
                      "stays in ROM"),
        sram=dict(refused=True, reason=f"{dflash_bytes(2.0)[0] / 1e9:.2f} GB BF16 ({bq / 1e9:.2f} GB at 3.5 bit) "
                                       "against 0.78 GB of on-die SRAM, which already holds the KV"))
    rec["targets"]["qwen3_8b_reticle"] = tq

    # ---- program-level cross-check of the verification law ----
    groups, suw = 8192, qwen_target(env, 1, 2048)["mach"].su_width
    base = program_replay(1, 1, groups=groups, su_width=suw)
    rows = []
    for n in (8, 17):
        for m in (1, 4, 16):
            cyc = program_replay(n, m, groups=groups, su_width=suw)
            g_ratio = verify(env, qwen_target(env, 1, 1024), n, m)[1]["T"] / verify(env, qwen_target(env, 1, 1024), 1, 1)[1]["T"]
            rows.append(dict(n=n, m=m, cycles=cyc, program_ratio=cyc / base, graph_ratio=g_ratio))
    rec["program_replay_check"] = dict(method=program_replay.__doc__.strip(), groups=groups, su_width=suw,
                                       position=1024, ar_cycles=base, rows=rows)
    rec["summary"] = summarize(rec)
    rec["sources"] = {rel(p_): sha(p_) for p_ in sorted(set(
        [Path(__file__), ROOT / "tools/decode_critical_path.py", ROOT / "tools/hdc_timing.py",
         ROOT / "tools/hdc_program.py", ROOT / "tools/run_speculative_roofline.py", PROFILES, SIGNOFF, MATVEC_PHYS,
         MAC_PHYS, GPU_DEP, GPU_SYNC, CRIT_RECORD, D.TECH, D.V41_CONFIG, D.V41_POINTS, D.V41_ANALYTICAL, D.QWEN,
         ROOT / "src/opentallas/critical_path.py", ROOT / "results/physical_abi3/asap7/hdc/ot_hdc_stream/physical.json"]
        + list(GPU_STUDIES.values()) + [p_.parent / "points.json" for p_ in GPU_STUDIES.values()]))}
    return rec


def env_kv_capacity():
    from opentallas.roofline import Technology, taalas_hc1_anchor
    from opentallas.schema import ModelProfile
    chk = taalas_hc1_anchor(Technology.load(D.TECH), ModelProfile.load(D.QWEN))
    return chk.detail["budget"]["kv_capacity_bytes"]


# -- summary: the table, the verdict, the recommendation ------------------------------------------------------------
def blocks_of(key):
    return GPU_BLOCKS + MODEL_BLOCKS["DeepSeek-V4.1-Flash" if key.startswith("deepseek") else "Qwen3-8B"]


ALL_BLOCKS = GPU_BLOCKS + MODEL_BLOCKS["Qwen3-8B"] + MODEL_BLOCKS["DeepSeek-V4.1-Flash"]


def cell_rows(rec, key, ctx, bt, gm, placement=None):
    """One (target, context, batch, gamma[, placement]) at every published tau of that gamma, against every GPU
    block of the band (idealised / feasible / feasible_calibrated / feasible_calibrated_nccl)."""
    t = rec["targets"][key]
    cell = t["contexts"][str(ctx)][str(bt)]
    g = cell["gamma"][str(gm)]
    rom = g["rom"] if placement is None else g["rom"][placement]
    gpu = g["gpu"]
    pts = rec["tau"]["v41" if key.startswith("deepseek") else "qwen"]
    pts = [p_ for p_ in pts if p_["gamma"] == gm and p_.get("priced_drafter", True)]
    out = []
    for p_ in pts:
        tau = p_["tau"]
        row = dict(target=key, placement=placement, context=ctx, batch=bt, gamma=gm, tau=tau, tau_label=p_["label"],
                   tau_grade=p_["grade"], rom_ar=cell["ar"]["tokens_s_per_user"],
                   rom_ar_energy_j=cell["ar"]["energy_j_per_token"],
                   hbm_core_ar_energy_j=cell["ar"]["hbm_comparator_energy_j_per_token"], gpu={}, by={})
        for blk in blocks_of(key):
            b = gpu[blk]
            gs = b["spec"]["draft_kv_low"]["by_tau"][str(tau)]
            row["gpu"][blk] = dict(ar=b["ar"]["tokens_s_per_user"], ar_design=b["ar"]["design"],
                                   spec=gs["tokens_s_per_user"], spec_design=b["spec"]["draft_kv_low"]["design"],
                                   spec_draft_kv_high=b["spec"]["draft_kv_high"]["by_tau"][str(tau)]["tokens_s_per_user"],
                                   ar_energy_j=b["ar"]["energy_j_per_token"],
                                   spec_energy_j=gs["energy_j_per_accepted_token"],
                                   ratio_ar=row["rom_ar"] / b["ar"]["tokens_s_per_user"], grade=b["grade"])
        for v, byv in rom.items():
            for m, r in byv.items():
                s = r["curve"][str(tau)]["tokens_s_per_user"]
                best_rom = max(s, r["ar_tokens_s_per_user"])
                row["by"][f"{v}/m{m}"] = dict(
                    rom_spec=s, rom_ar_same_silicon=r["ar_tokens_s_per_user"], cycle_us=r["cycle_s"] * 1e6,
                    verify_us=r["verify_T_s"] * 1e6, draft_us=r["draft_T_s"] * 1e6,
                    binding=r["binding"], tau_break=r["tau_break"], pays=s > r["ar_tokens_s_per_user"],
                    rom_spec_energy_j=r["curve"][str(tau)]["energy_j_per_accepted_token"],
                    ratio_spec={blk: s / row["gpu"][blk]["spec"] for blk in blocks_of(key)},
                    ratio_best={blk: best_rom / max(row["gpu"][blk]["spec"], row["gpu"][blk]["ar"])
                                for blk in blocks_of(key)})
        out.append(row)
    return out


def summarize(rec):
    out = dict(rows=[], verdict={}, recommendation={})
    for ctx in V41_CONTEXTS:
        for bt in BATCHES:
            for gm in rec["targets"]["deepseek_v41_array_option_b"]["gammas"]:
                out["rows"] += cell_rows(rec, "deepseek_v41_array_option_b", ctx, bt, gm)
    for ctx in QWEN_CONTEXTS:
        for bt in BATCHES:
            for gm in rec["targets"]["qwen3_8b_reticle"]["gammas"]:
                for plc in ("rom", "hbm_x8"):
                    out["rows"] += cell_rows(rec, "qwen3_8b_reticle", ctx, bt, gm, plc)
    # "speculation narrows the ROM advantage everywhere": tested on every (row, variant, m) against every GPU
    # block, as speculative-vs-speculative and as best-vs-best (each side speculates only where it pays)
    verdict = dict(claim="speculation narrows the ROM advantage everywhere (generic study: V4.1 array batch 1 "
                         "7.10x -> 0.18x)", by_gpu_block={})
    for blk in ALL_BLOCKS:
        tests = dict(spec_vs_spec=[0, 0, []], best_vs_best=[0, 0, []])
        for r in out["rows"]:
            if blk not in r["gpu"]:
                continue
            base = r["gpu"][blk]["ratio_ar"]
            for vm, x in r["by"].items():
                tag = [r["target"], r["placement"], r["context"], r["batch"], r["gamma"], r["tau"], vm]
                for name in tests:
                    val = x["ratio_spec" if name == "spec_vs_spec" else "ratio_best"][blk]
                    t_ = tests[name]
                    if val < base - 1e-12:
                        t_[0] += 1
                    else:
                        t_[1] += 1
                        t_[2].append(tag + [round(base, 3), round(val, 3)])
        verdict["by_gpu_block"][blk] = {k: dict(narrowing=v[0], not_narrowing=v[1], holds=v[1] == 0,
                                                counterexamples=v[2][:30]) for k, v in tests.items()}
    # the headline: each row against its own model's headline GPU (Qwen3-8B one die, V4.1 iso total area)
    hl = dict(spec_vs_spec=[0, 0, []], best_vs_best=[0, 0, []])
    for r in out["rows"]:
        blk = HEADLINE_GPU["DeepSeek-V4.1-Flash" if r["target"].startswith("deepseek") else "Qwen3-8B"]
        base = r["gpu"][blk]["ratio_ar"]
        for vm, x in r["by"].items():
            for name in hl:
                val = x["ratio_spec" if name == "spec_vs_spec" else "ratio_best"][blk]
                t_ = hl[name]
                if val < base - 1e-12:
                    t_[0] += 1
                else:
                    t_[1] += 1
                    t_[2].append([r["target"], r["placement"], r["context"], r["batch"], r["gamma"], r["tau"], vm,
                                  round(base, 3), round(val, 3)])
    verdict["headline_gpu"] = {k: dict(narrowing=v[0], not_narrowing=v[1], holds=v[1] == 0,
                                       counterexamples=v[2][:30]) for k, v in hl.items()}
    verdict["holds_everywhere"] = all(v[k]["holds"] for v in verdict["by_gpu_block"].values() for k in v)
    # the same test on today's hardware alone (m = 1, stream unit as built)
    verdict["today_m1"] = {}
    for blk in ALL_BLOCKS:
        n_ok = n_bad = 0
        bad = []
        for r in out["rows"]:
            if blk not in r["gpu"]:
                continue
            x = r["by"]["me/m1"]
            if x["ratio_spec"][blk] < r["gpu"][blk]["ratio_ar"] - 1e-12:
                n_ok += 1
            else:
                n_bad += 1
                bad.append([r["target"], r["placement"], r["context"], r["batch"], r["gamma"], r["tau"]])
        verdict["today_m1"][blk] = dict(narrowing=n_ok, not_narrowing=n_bad, counterexamples=bad[:20])
    out["verdict"] = verdict
    # recommendation: per target, the (variant, m) maximising per-user rate (speculating where it pays) under
    # each added-silicon budget, at the headline context and the published tau points; recommended = the
    # smallest added silicon within 5% of the best at <= 25% of the design's silicon (upper area band)
    for key, ctx, gm, plc in (("deepseek_v41_array_option_b", 200000, 7, None),
                              ("qwen3_8b_reticle", 2048, 16, "rom")):
        t = rec["targets"][key]
        av = t["area_by_variant"]

        def area_of(vm):
            return av[vm.split("/")[0]][int(vm.split("/m")[1])]
        per = {}
        rows = [r for r in out["rows"] if r["target"] == key and r["context"] == ctx and r["gamma"] == gm and
                r["placement"] == plc]
        for r in rows:
            opts = {vm: max(x["rom_spec"], x["rom_ar_same_silicon"]) for vm, x in r["by"].items()}
            k_ = f"b{r['batch']}/tau{r['tau']}"
            per[k_] = {}
            for b in BUDGETS:
                ok = {vm: s for vm, s in opts.items() if area_of(vm)[f"fraction_of_design_{AREA_BASIS}"] <= b + 1e-12}
                best = max(ok, key=ok.get)
                per[k_][f"{b:.2f}"] = dict(option=best, tokens_s_per_user=ok[best], speculating=r["by"][best]["pays"],
                                           added_mm2_high=area_of(best)["added_mm2_high"],
                                           added_mm2_low=area_of(best)["added_mm2_low"])
        def decide(basis):
            dec = {}
            for r in [r_ for r_ in rows if r_["batch"] == 1]:
                opts = {vm: max(x["rom_spec"], x["rom_ar_same_silicon"]) for vm, x in r["by"].items()
                        if not vm.startswith("su/") and area_of(vm)[f"fraction_of_design_{basis}"] <= 0.25 + 1e-12}
                top = max(opts.values())
                cand = [vm for vm, s in opts.items() if s >= 0.95 * top]
                dec[r["tau"]] = min(cand, key=lambda vm: area_of(vm)[f"added_mm2_{basis}"])
            # the pick must hold across every cited tau: the largest (by area) of the per-tau picks
            return dec, max(dec.values(), key=lambda vm: area_of(vm)[f"added_mm2_{basis}"])
        decisions, pick = decide(AREA_BASIS)
        _, pick_other = decide("high" if AREA_BASIS == "low" else "low")
        v_, m_ = pick.split("/")[0], int(pick.split("/m")[1])
        head = next(r for r in rows if r["batch"] == 1)
        b64 = next((r for r in rows if r["batch"] == 64 and r["tau"] == head["tau"]), None)
        out["recommendation"][key] = dict(
            recommended_m=m_, variant=v_, variant_meaning=VARIANTS[v_], context=ctx, gamma=gm, placement=plc,
            per_tau_pick={str(k): v for k, v in decisions.items()},
            decision_tau=head["tau"], decision_tau_label=head["tau_label"],
            rule="per cited tau, the smallest added silicon whose batch-1 per-user rate (speculating where it pays) "
                 "is within 5% of the best MAC-lane option (me or me_su) at <= 25% added silicon, a replicated lane "
                 "priced as the bare pipelined MAC (area basis 'low'); the recommendation is the largest of those "
                 "per-tau picks",
            area_basis=AREA_BASIS, pick_under_whole_lane_area=pick_other,
            tokens_s_per_user_b1=max(head["by"][pick]["rom_spec"], head["by"][pick]["rom_ar_same_silicon"]),
            speculating_b1=head["by"][pick]["pays"],
            tokens_s_per_user_b64=None if b64 is None else max(b64["by"][pick]["rom_spec"],
                                                               b64["by"][pick]["rom_ar_same_silicon"]),
            ar_m1_b1=head["rom_ar"],
            verify_us_b1=head["by"][pick]["verify_us"], draft_us_b1=head["by"][pick]["draft_us"],
            added_mm2_high=area_of(pick)["added_mm2_high"], added_mm2_low=area_of(pick)["added_mm2_low"],
            added_fraction_high=area_of(pick)["fraction_of_design_high"],
            best_option_per_budget=per,
            consumer="the parallel RTL implementations (DeepSeek-V4.1 MTP on ROM and HBM; DFlash for Qwen3-8B) "
                     "take this m per target; per-block draft and verify times per (variant, m) are under "
                     "targets.<target>.contexts.<ctx>.<batch>.gamma.<gamma>.rom[...] draft_T_s / verify_T_s, so "
                     "RTL cycle counts can replace them")
    # the report's table: flat keys, one row per (target, context, batch, gamma, cited tau), ROM placement
    out["table"] = {}
    for r in out["rows"]:
        key = r["target"]
        if r["placement"] not in (None, "rom"):
            continue
        rec_ = out["recommendation"][key]
        pick = f"{rec_['variant']}/m{rec_['recommended_m']}"
        m1, x = r["by"]["me/m1"], r["by"][pick]
        slug = "".join(ch if ch.isalnum() else "_" for ch in r["tau_label"]).strip("_").lower()
        name = f"{'v41' if key.startswith('deepseek') else 'qwen'}_{r['context']}_b{r['batch']}_g{r['gamma']}_{slug}"
        row = dict(target=key, context=r["context"], batch=r["batch"], gamma=r["gamma"], tau=r["tau"],
                   tau_label=r["tau_label"], tau_grade=r["tau_grade"], recommended=pick,
                   rom_ar=r["rom_ar"], rom_spec_m1=m1["rom_spec"], rom_ar_rec=x["rom_ar_same_silicon"],
                   rom_spec_rec=x["rom_spec"], tau_break_m1=m1["tau_break"], tau_break_rec=x["tau_break"],
                   pays_m1=m1["pays"], pays_rec=x["pays"], rom_speedup_rec=x["rom_spec"] / r["rom_ar"],
                   rom_energy_ar_uj=r["rom_ar_energy_j"] * 1e6, rom_energy_spec_m1_uj=m1["rom_spec_energy_j"] * 1e6,
                   rom_energy_spec_rec_uj=x["rom_spec_energy_j"] * 1e6,
                   hbm_core_energy_ar_uj=r["hbm_core_ar_energy_j"] * 1e6)
        for blk in blocks_of(key):
            gb = r["gpu"][blk]
            row[blk] = dict(gpu_ar=gb["ar"], gpu_spec=gb["spec"], gpu_spec_draft_kv_high=gb["spec_draft_kv_high"],
                            gpu_speedup=gb["spec"] / gb["ar"], ratio_ar=gb["ratio_ar"],
                            ratio_spec_m1=m1["ratio_spec"][blk], ratio_spec_rec=x["ratio_spec"][blk],
                            ratio_best_rec=x["ratio_best"][blk], gpu_energy_ar_j=gb["ar_energy_j"],
                            gpu_energy_spec_j=gb["spec_energy_j"], ar_design=gb["ar_design"],
                            spec_design=gb["spec_design"])
        out["table"][name] = row
    # demonstrated GPU (measured, cited): Qwen3-8B on one B200 with DFlash, against the ROM reticle's rows at the
    # same tau (MATH-500 8.01 / HumanEval 6.50 are Table 3's own taus; the ROM rate is its tau / cycle)
    cal = rec.get("gpu_calibration")
    if cal:
        tq = rec["targets"]["qwen3_8b_reticle"]
        rec_ = out["recommendation"]["qwen3_8b_reticle"]
        dem = {}
        for m_row in cal["measured"]["rows"][:2]:
            for bt in ("1",):
                for ctx in QWEN_CONTEXTS:
                    cell = tq["contexts"][str(ctx)][bt]
                    rom = cell["gamma"]["16"]["rom"]["rom"]
                    r1 = rom["me"][1]
                    rr = rom[rec_["variant"]][rec_["recommended_m"]]
                    dem[f"qwen_{ctx}_b{bt}_{m_row['workload'].lower().replace('-', '_')}"] = dict(
                        grade="measured (cited)", source=cal["measured"]["source"], workload=m_row["workload"],
                        tau=m_row["tau"], gpu_ar=m_row["ar"], gpu_spec=m_row["dflash"],
                        rom_ar=cell["ar"]["tokens_s_per_user"], rom_spec_m1=m_row["tau"] / r1["cycle_s"],
                        rom_spec_rec=m_row["tau"] / rr["cycle_s"], rom_ar_rec=rr["ar_tokens_s_per_user"],
                        ratio_ar=cell["ar"]["tokens_s_per_user"] / m_row["ar"],
                        ratio_spec_m1=(m_row["tau"] / r1["cycle_s"]) / m_row["dflash"],
                        ratio_spec_rec=(m_row["tau"] / rr["cycle_s"]) / m_row["dflash"],
                        ratio_best_rec=max(m_row["tau"] / rr["cycle_s"], rr["ar_tokens_s_per_user"]) / m_row["dflash"],
                        per_reticle_note="a B200 is two reticle-class dies; the ROM is one reticle. Halving the "
                                         "measured rate is the iso-area normalisation (bandwidth-bound decode), "
                                         "and the single_die blocks project it from the model",
                        ratio_ar_per_reticle=2 * cell["ar"]["tokens_s_per_user"] / m_row["ar"],
                        ratio_spec_rec_per_reticle=2 * (m_row["tau"] / rr["cycle_s"]) / m_row["dflash"])
        out["demonstrated"] = dem
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=OUT)
    a = ap.parse_args()
    rec = build()
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1, default=float) + "\n")
    s = rec["summary"]
    for blk, v in s["verdict"]["by_gpu_block"].items():
        print(blk, {k: (x["narrowing"], x["not_narrowing"]) for k, x in v.items()})
    for k, v in s["recommendation"].items():
        print(k, {kk: vv for kk, vv in v.items() if kk != "best_option_per_budget"})


if __name__ == "__main__":
    main()
