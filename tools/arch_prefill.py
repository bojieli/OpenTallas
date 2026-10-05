#!/usr/bin/env python3
"""GPU prefill + KV ingest for the four designs, on the current constants.

    python3 tools/arch_prefill.py [--out results/arch/prefill_ingest.json]

Policy (user decision): every prefill -- cold prompts and agent turns -- runs on GPUs; the decode chips
ingest the KV.  Designs:
  * v41_rom -- DeepSeek-V4.1-Flash ROM array: 188 dies, 28 stages of a 4-die tensor group, 4 HBM3E stacks per
    layer die, replicate-on-write of the owner layers' compressed rows (results/arch/v41_rack.json), 1M / 200K;
  * v41_hbm -- its HBM comparator (results/arch/v41_hbm_switched.json headline);
  * qwen_rom / qwen_hbm -- the Qwen3-8B two-reticle package at 8K (8-bit weights, every layer split across both
    dies), FP8 KV in its 8 HBM3E stacks, and the same package with its weights on HBM.

The model, in order:
  1. BYTES: per user sent over the wire (owner rows 288 + 68 B, window rings 528 B) and written into HBM after
     replication; per die on the busiest die; users held (read from the budget records, recomputed here).
  2. GPU PREFILL: FLOPs per prompt position from the budget record's own per-token MACs (weights, sparse attention,
     the lightning indexer's scan, which is quadratic over a cold prompt), at an EFFECTIVE per-GPU rate calibrated
     to a cited DeepSeek-class prefill throughput (LMSYS, GB200) and scaled to B200 by the FP8 dense-peak ratio.
  3. LINK PATH: GPU (GPUDirect RDMA) -> ConnectX-7 400G -> RoCEv2 -> the rack switch's uplink ports -> switch
     multicast to each reader stage's 4 x 112G package port -> RDMA-write target -> ot_hdc_kv_ingest -> HBM.
  4. INGEST: time bound by the NICs, the busiest package port and the RTL-measured engine rate; HBM share.
  5. TTFT = GPU prefill + exposed transfer + fence + first decode step; two binding options (stream during the
     prefill, or late-bind: the GPU holds the KV and bursts it at the end).
  6. CAPACITY: slots reserved during prefill, and the GPU tier / ingest bandwidth a rack needs at R prompt tokens
     per output token.
Every constant below carries its source; ASSUMED ones are labelled.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "results/arch/prefill_ingest.json"
SCHEMA = "opentallas.arch-prefill-ingest.v2"

CITE = {
    "lmsys_gb200_dsv3": dict(
        url="https://www.lmsys.org/blog/2025-09-25-gb200-part-2/",
        what="DeepSeek-V3/R1 prefill on GB200 NVL72, 2,000-token inputs: 26,156 input tok/s per GPU (FP8 attention, "
             "NVFP4 MoE) and 18,471 (BF16 attention, FP8 MoE)"),
    "gb200_nvl72": dict(url="https://www.nvidia.com/en-us/data-center/gb200-nvl72/",
                        what="GB200 superchip (2 GPUs): FP8 20 PFLOPS sparse; dense = half sparse -> 5 PF per GPU"),
    "dgx_b200": dict(url="https://www.nvidia.com/en-us/data-center/dgx-b200/",
                     what="DGX B200: 8 B200, 1,440 GB HBM3E, FP8 72 PFLOPS (sparse) -> 4.5 PF dense per GPU; "
                          "8 x single-port ConnectX-7 400 Gb/s"),
    "nim_llama8b": dict(url="https://docs.nvidia.com/nim/benchmarking/llm/1.0.0/performance.html",
                        what="Llama-3.1-8B-Instruct FP8 TP1, concurrency 1, 20,000 input tokens: TTFT 403.2 ms (H100), "
                             "408.66 ms (H200)"),
    "cx7_gdr": dict(url="https://github.com/NVIDIA/nccl/issues/2409",
                    what="ib_write_bw ConnectX-7 400G, GPUDirect RDMA from GPU HBM: 391.47 Gb/s (host memory 392.6)"),
    "nixl_llmd": dict(url="https://llm-d.ai/blog/networking-for-distributed-inference-llm-d",
                      what="NIXL (UCX/UCCL) KV transfer between two H200 over 400G IB: ~49.5 GB/s, ~99% of line rate"),
    "deepseek_v4": dict(url="https://arxiv.org/abs/2606.19348",
                        what="DeepSeek-V4-Flash 284B (13B activated), 1M context; V4-Pro needs 27% of V3.2's "
                             "single-token FLOPs at 1M"),
    "deepseek_v3": dict(url="https://arxiv.org/abs/2412.19437",
                        what="DeepSeek-V3: 671B total, 37B activated; 61 layers, 128 heads, MLA q/k head 192 "
                             "(128 + 64 RoPE), v head 128, vocab 129,280 x hidden 7,168"),
}

# -- GPU calibration ---------------------------------------------------------------------------------------
GB200_FP8_DENSE = 5.0e15          # cited gb200_nvl72
B200_FP8_DENSE = 4.5e15           # cited dgx_b200
H100_FP8_DENSE = 1.979e15         # NVIDIA H100 SXM datasheet (dense FP8)
LMSYS_TOK_S = dict(conservative=18471.0, optimistic=26156.0)
V3 = dict(active=37e9, embed=129280 * 7168, layers=61, heads=128, qk=192, v=128, isl=2000)
EP_LAYER_FLOOR_S = 0.2e-3         # ASSUMED (DeepEP low-latency dispatch+combine class): small EP prefills
INDEXER_EFF_SENS = 0.5            # ASSUMED sensitivity: the quadratic indexer at half the calibrated rate

# -- links -------------------------------------------------------------------------------------------------
NIC400_Bps = 391.47e9 / 8         # cited cx7_gdr (GPUDirect RDMA goodput)
FENCE_S = 10e-6                   # ASSUMED: last RDMA completion + descriptor fence + host release
GPU_CHUNK = 8192                  # ASSUMED: chunked-prefill chunk (vLLM/SGLang class) for the exposed tail


def load(p):
    return json.loads((ROOT / p).read_text())


def v3_flops_per_token():
    w = 2 * (V3["active"] - 2 * V3["embed"])                              # no embedding / lm_head per prompt token
    att = 2 * V3["layers"] * V3["heads"] * (V3["qk"] + V3["v"]) * V3["isl"] / 2   # causal MLA, mean position
    return w + att


def gpu_rates():
    f = v3_flops_per_token()
    out = {}
    for k, tok in LMSYS_TOK_S.items():
        gb200 = tok * f
        out[k] = dict(gb200_flops=gb200, b200_flops=gb200 * B200_FP8_DENSE / GB200_FP8_DENSE,
                      b200_mfu_fp8_dense=gb200 / GB200_FP8_DENSE)
    return dict(v3_flops_per_token_2k=f, rates=out,
                basis="LMSYS GB200 DeepSeek-V3 prefill tok/s per GPU x V3's FLOPs per 2K-prompt token (no embedding "
                      "or head, causal MLA at the mean position), x B200/GB200 FP8 dense peak (4.5/5.0). "
                      "Conservative = the BF16-attention/FP8-MoE configuration; optimistic = FP8/NVFP4 (V4.1's routed "
                      "experts are FP4, so the optimistic one is the format match)")


# ======================================================================================================
# V4.1 workload
# ======================================================================================================
class V41:
    def __init__(self):
        b = load("results/arch/arch_budget_v41.json")
        self.budget = b
        self.clock = b["clock_hz"]
        t = b["workload"]["1048576"]["totals"]["macs"]
        self.lm_head = 5120 * 129280
        self.weight_macs = sum(v for k, v in t.items() if k.startswith(("weight", "hc_proj")))
        self.att_macs = sum(v for k, v in t.items() if k.startswith("attention"))
        self.idx_mac_per_key = 32 * 128                                   # index heads x index head dim
        # the indexer's scan per layer as a function of position: linear (a * p) or capped (min(p, cap))
        ctx = 200000                                                     # the record's per-layer table
        self.scan = []
        for L in b["workload"][str(ctx)]["per_layer"]:
            n = L["n_scan"]
            if n:
                self.scan.append(("lin", n / ctx) if n >= ctx // 2 else ("cap", n))
        for c in (200000, 1048576):                                       # reproduces the record's indexer MACs
            rec = b["workload"][str(c)]["totals"]["macs"]["indexer:fp4"]
            assert abs(rec - self.idx_mac_per_key * self.keys(c)) / rec < 1e-9, c
        r = load("results/arch/v41_rack.json")
        self.rack = r
        kr = r["kv_replication"]
        self.row_B = kr["row_bytes"]                                      # 288 main + 68 index key
        self.owners = {int(k): dict(ratio=v["ratio"], replicas=v["replicas"], stage=v["owner_stage"])
                       for k, v in kr["owners"].items()}
        self.win_B, self.win_rows, self.layers = 528, 128, 40
        self.dies_per_stage, self.stacks = 4, b["kv_state"]["stacks_per_die"]
        self.hbm_die_Bps = b["kv_state"]["sustained_Bps_per_die"]
        self.stack_B = 22.5e9                                             # technology.json hbm.hbm3e
        self.port_Bps = r["lanes"]["per_package"]["switch"] * r["lanes"]["lane_net_Bps"]
        self.per_stage_1m = {int(k): v for k, v in kr["per_stage_bytes_per_user_1m"].items()}

    def keys(self, p):
        return sum(a * p if k == "lin" else min(p, a) for k, a in self.scan)

    def keys_sum(self, a, b):
        """sum of keys(p) over p in [a, b)"""
        s = 0.0
        for k, c in self.scan:
            if k == "lin":
                s += c * (b * (b - 1) - a * (a - 1)) / 2
            else:
                lo, hi = min(a, c), min(b, c)
                s += (hi * (hi - 1) - lo * (lo - 1)) / 2 + c * max(0, b - max(a, c))
        return s

    def prefill_flops(self, n_new, ctx0=0):
        w = 2 * (self.weight_macs - self.lm_head) * n_new + 2 * self.lm_head
        att = 2 * self.att_macs * n_new                                    # full 640-row attention at every position:
        idx = 2 * self.idx_mac_per_key * self.keys_sum(ctx0, ctx0 + n_new)  # conservative for early positions
        return dict(total=w + att + idx, weights=w, attention=att, indexer=idx)

    def sent_bytes(self, n, ctx0=0):
        rows = sum(((ctx0 + n) // o["ratio"] - ctx0 // o["ratio"]) for o in self.owners.values())
        win = self.layers * min(ctx0 + n, self.win_rows) * self.win_B
        return dict(owner_rows=rows * self.row_B, window_rings=win, total=rows * self.row_B + win)

    def written_bytes(self, n):
        """replicated rows + every stage's window rings (a layer split over two stages keeps its ring on both,
        as the rack's per-stage table does): the sum of per_stage_bytes"""
        return sum(self.per_stage_bytes(n).values())

    def per_stage_bytes(self, n):
        """HBM bytes per user per stage: the replicated owner rows of every owner the stage reads (owner stage and
        the next replicas - 1 stages) plus the stage's own window rings, which the rack's 1M table carries."""
        def rows(s, ctx):
            return sum(ctx // o["ratio"] * self.row_B for o in self.owners.values()
                       if o["stage"] <= s < o["stage"] + o["replicas"])
        out = {}
        for s, b1m in self.per_stage_1m.items():
            win = b1m - rows(s, 1048576)
            assert win >= 0 and win % (self.win_rows * self.win_B) == 0, (s, win)
            out[s] = rows(s, n) + win * min(n, self.win_rows) / self.win_rows
        return out

    def capacity(self, n):
        c = self.budget["capacity"][str(n)]
        per_die = c["per_user_bytes_busiest_die"]
        return dict(per_user_bytes_busiest_die=per_die, rom_users=c["rom_users"], hbm_users=c["hbm_users"],
                    rom_users_without_reserve=c.get("rom_users_without_reserve"),
                    capacity_efficiency=c.get("capacity_efficiency"),
                    source="results/arch/arch_budget_v41.json capacity (4 x 22.5 GB x technology.json "
                           "efficiencies.hbm_capacity, the reserve the Qwen3 budget also applies)")


# ======================================================================================================
# Qwen3-8B workload
# ======================================================================================================
class Qwen:
    def __init__(self):
        q = load("results/arch/qwen3_budget.json")
        self.budget = q
        w = q["workload"]["8192"]
        self.lm_head = w["macs"]["lm_head"]
        self.weight_macs = w["weight_macs"]
        self.layers, self.kv_heads, self.hd, self.heads = 36, 8, 128, 32
        self.kv_B_per_pos = self.layers * self.kv_heads * self.hd * 2          # FP8 K and V
        self.hbm_Bps = q["hbm_design"]["stacks"] * q["hbm_design"]["stack_bytes_s"] * q["hbm_design"]["efficiency"]
        self.stacks = q["hbm_design"]["stacks"]
        self.clock = q["clock_hz"]

    def prefill_flops(self, n_new, ctx0=0):
        w = 2 * (self.weight_macs - self.lm_head) * n_new + 2 * self.lm_head
        per_pair = 2 * 2 * self.layers * self.heads * self.hd                  # QK and PV
        att = per_pair * (n_new * ctx0 + n_new * (n_new + 1) / 2)
        return dict(total=w + att, weights=w, attention=att)


def dense_rates():
    """Dense 8B FP8 effective rate from the cited NIM TTFT (Llama-3.1-8B, 20K, TP1)."""
    llama_w = 4096 * (6144 + 4096 + 3 * 14336) * 32
    pair = 2 * 2 * 32 * 32 * 128
    isl = 20000
    fl = 2 * llama_w * isl + pair * isl * (isl + 1) / 2
    h100, h200 = fl / 0.4032, fl / 0.40866
    return dict(h100_flops=h100, h200_flops=h200, b200_flops_modelled=h100 * B200_FP8_DENSE / H100_FP8_DENSE,
                h100_mfu_fp8_dense=h100 / H100_FP8_DENSE,
                basis="cited NIM TTFT at 20K over Llama-3.1-8B's prompt FLOPs; B200 = H100 x FP8 dense-peak ratio "
                      "(MODELLED: no cited single-B200 8B prefill)")


# ======================================================================================================
# model
# ======================================================================================================
def ingest_engine():
    """RTL-measured engine rates (results/rtl/hdc_kv_ingest_campaign.json), per die at its clock."""
    p = ROOT / "results/rtl/hdc_kv_ingest_campaign.json"
    rec = json.loads(p.read_text()) if p.exists() else None
    src = str(p.relative_to(ROOT)) if rec else "worktree-agent-ab5912eff5bdb5981 @4abb77bb (not on main)"
    c = rec["cases"] if rec else None
    bpc = dict(qwen_bf16=c["qwen_shipped_geom"]["beats_per_cycle"] if c else 0.9688,
               v41_rows=c["v41_ckv"]["beats_per_cycle"] if c else 0.4999,
               v41_keys=c["v41_ikey"]["beats_per_cycle"] if c else 0.3413,
               v41_win=c["v41_win"]["beats_per_cycle"] if c else 0.4852)
    return dict(record=src, beats_per_cycle=bpc, beat_B=64,
                git_head=rec.get("git_head") if rec else "41259b66",
                qwen_in_Bps=bpc["qwen_bf16"] * 64 * 1.09864e9,
                v41_rows_in_Bps=bpc["v41_rows"] * 64 * 1.0339e9, v41_keys_in_Bps=bpc["v41_keys"] * 64 * 1.0339e9,
                v41_win_in_Bps=bpc["v41_win"] * 64 * 1.0339e9)


def v41_design(m: V41, rates, eng, design, dec_rate, context, n_gpu=8, nics=2, rate_key="conservative"):
    fl = m.prefill_flops(context)
    r = rates["rates"][rate_key]["b200_flops"]
    t_pf = fl["total"] / (r * n_gpu)
    t_pf_sens = (fl["weights"] + fl["attention"] + fl["indexer"] / INDEXER_EFF_SENS) / (r * n_gpu)
    sent = m.sent_bytes(context)
    written = m.written_bytes(context)
    link = nics * NIC400_Bps
    # busiest package port: the stage with the most replicated bytes, half of it per package (2 packages/stage)
    stage_B = max(m.per_stage_bytes(context).values())
    pkg_B = stage_B / 2
    t_nic = sent["total"] / link
    t_port = pkg_B / m.port_Bps
    cap = m.capacity(context)
    die_B = cap["per_user_bytes_busiest_die"]
    # engine time for the busiest die: main rows at the ROWS rate, keys at the IKEY rate (bytes in on the wire)
    main_frac = 288 / 356
    t_eng = die_B * main_frac / eng["v41_rows_in_Bps"] + die_B * (1 - main_frac) / eng["v41_keys_in_Bps"]
    t_burst = max(t_nic, t_port, t_eng)
    binding = ["nic", "package_port", "engine"][[t_nic, t_port, t_eng].index(t_burst)]
    # streaming during a chunked prefill: the link must keep pace, the exposed tail is the last chunk + windows
    pace_Bps = sent["total"] / t_pf
    tail_B = m.sent_bytes(min(GPU_CHUNK, context), context - min(GPU_CHUNK, context))["owner_rows"] + sent["window_rings"]
    tail_pkg = tail_B * (stage_B / sent["owner_rows"] if sent["owner_rows"] else 1) / 2
    t_tail = max(tail_B / link, tail_pkg / m.port_Bps)
    first = 1.0 / dec_rate
    ttft_stream = t_pf + t_tail + FENCE_S + first
    ttft_late = t_pf + t_burst + FENCE_S + first
    return dict(
        design=design, context=context, gpus=f"{n_gpu} x B200 ({n_gpu // 8} DGX B200)", rate_key=rate_key,
        prefill_flops=fl, gpu_rate_flops_per_gpu=r, gpu_prefill_s=t_pf,
        gpu_prefill_s_indexer_at_half_rate=t_pf_sens,
        bytes_sent=sent, bytes_written_hbm_replicated=written, busiest_stage_bytes=stage_B,
        busiest_package_bytes=pkg_B, busiest_die_bytes=die_B,
        link=dict(nics=nics, nic_goodput_Bps=NIC400_Bps, uplink_Bps=link, package_port_Bps=m.port_Bps),
        burst=dict(nic_s=t_nic, package_port_s=t_port, engine_s=t_eng, time_s=t_burst, binding=binding),
        stream=dict(pace_Bps_needed=pace_Bps, link_busy_fraction=pace_Bps / link, exposed_tail_bytes=tail_B,
                    exposed_tail_s=t_tail),
        hbm_share=dict(ingest_die_Bps_during_burst=die_B / t_burst,
                       fraction_of_die_hbm=die_B / t_burst / m.hbm_die_Bps,
                       fraction_stream=die_B / t_pf / m.hbm_die_Bps),
        first_decode_step_s=first, fence_s=FENCE_S,
        ttft_stream_s=ttft_stream, ttft_late_bind_s=ttft_late,
        slot_reserved_s=dict(stream=t_pf + t_tail, late_bind=t_burst),
        capacity=cap)


def v41_turn(m: V41, rates, dec_rate, n_new, ctx0, n_gpu=8, nics=2, rate_key="conservative"):
    fl = m.prefill_flops(n_new, ctx0)
    r = rates["rates"][rate_key]["b200_flops"]
    t_pf = max(fl["total"] / (r * n_gpu), m.layers * EP_LAYER_FLOOR_S)
    link = nics * NIC400_Bps
    ctx_B = m.sent_bytes(ctx0)["total"]
    new_B = m.sent_bytes(n_new, ctx0)["total"]
    readback = ctx_B / link                                               # GPU prefix cache miss: read our HBM back
    first_owner = m.sent_bytes(ctx0)["owner_rows"] / 4 / link             # layer-pipelined readback: layer 2 first
    t_in = new_B / link
    first = 1.0 / dec_rate
    return dict(new_tokens=n_new, resident=ctx0, prefill_flops=fl["total"], gpu_prefill_s=t_pf,
                ep_floor_s=m.layers * EP_LAYER_FLOOR_S, new_bytes_sent=new_B, ingest_s=t_in,
                ttft_prefix_cached_s=t_pf + t_in + FENCE_S + first,
                context_readback_bytes=ctx_B, context_readback_serial_s=readback,
                ttft_readback_serial_s=readback + t_pf + t_in + FENCE_S + first,
                ttft_readback_layer_pipelined_s=first_owner + t_pf + t_in + FENCE_S + first)


def qwen_design(q: Qwen, dr, eng, design, dec_rate, context=8192, gpu="h200"):
    fl = q.prefill_flops(context)
    r = dr[f"{gpu}_flops"] if gpu != "b200" else dr["b200_flops_modelled"]
    t_pf = fl["total"] / r
    B = q.kv_B_per_pos * context
    link = NIC400_Bps
    last_layer = B / q.layers
    t_tail = last_layer / link
    t_burst = 2 * B / min(link, eng["qwen_in_Bps"])                      # BF16 on the wire (vLLM's native pages)
    t_burst_fp8 = B / link                                                # FP8 cast on the GPU (R-P5 RNE from FP32)
    first = 1.0 / dec_rate
    cap_B = q.stacks * 22.5e9
    return dict(design=design, context=context, gpu=f"1 x {gpu.upper()}", prefill_flops=fl, gpu_prefill_s=t_pf,
                kv_bytes_fp8=B, kv_bytes_bf16_on_wire=2 * B,
                link=dict(path="PCIe Gen5 x16 endpoint on die 0 of the package behind the host PCIe switch shared "
                               "with one ConnectX-7 400G (ARCH_SPEC_QWEN3 R-P1); die 1's KV heads cross the "
                               "package's UCIe link (4.2 TB/s, ~80x the endpoint)", goodput_Bps=link),
                stream=dict(pace_Bps_needed=2 * B / t_pf, exposed_last_layer_s=2 * t_tail),
                burst_s_bf16=t_burst, burst_s_fp8=t_burst_fp8,
                hbm_share_at_link_rate=link / q.hbm_Bps,
                first_decode_step_s=first, ttft_stream_s=t_pf + 2 * t_tail + FENCE_S + first,
                ttft_late_bind_s=t_pf + t_burst + FENCE_S + first,
                ttft_late_bind_fp8_wire_s=t_pf + t_burst_fp8 + FENCE_S + first,
                wire_format="BF16 NHD pages (vLLM native); the engine rounds to FP8. FP8 on the wire halves the "
                            "bytes but must be cast from FP32 with RNE for bit-identity (ARCH_SPEC_QWEN3 R-P5)",
                capacity=dict(users_no_efficiency=int(cap_B // B), users_at_0p9=int(0.9 * cap_B // B),
                              note="0.9 x stacks x 22.5 GB / 604 MB of FP8 KV a user at 8K; the V4.1 users held apply the same 0.9"))


def sustained(m: V41, q: Qwen, rates, dr, v41_agg, qwen_agg):
    out = {}
    r = rates["rates"]["conservative"]["b200_flops"]
    for ctx, tag in ((1048576, "1M"), (200000, "200K")):
        per_tok = m.prefill_flops(4096, ctx - 4096)["total"] / 4096
        gpu_tok_s = r / per_tok
        rows = {}
        for bname, agg in v41_agg[str(ctx)].items():
            rows[bname] = {str(R): dict(prompt_tok_s=R * agg, b200_needed=R * agg / gpu_tok_s,
                                        dgx_b200_needed=R * agg / gpu_tok_s / 8,
                                        ingest_sent_Bps=R * agg * m.row_B * 2.5,
                                        uplink_fraction_2x400G=R * agg * m.row_B * 2.5 / (2 * NIC400_Bps))
                           for R in (1, 4, 20)}
            rows[bname]["decode_aggregate_tok_s"] = agg
        out[f"v41_rom@{tag}"] = dict(flops_per_prompt_token_at_context=per_tok, b200_prompt_tok_s=gpu_tok_s,
                                     sent_B_per_prompt_token=m.row_B * 2.5, by_batch=rows)
    per_tok = q.prefill_flops(2048, 6144)["total"] / 2048
    h200 = dr["h200_flops"] / per_tok
    out["qwen_rom@8K"] = dict(flops_per_prompt_token=per_tok, h200_prompt_tok_s=h200, decode_aggregate_tok_s=qwen_agg,
                              by_R={str(R): dict(prompt_tok_s=R * qwen_agg, h200_needed=R * qwen_agg / h200,
                                                 ingest_Bps=R * qwen_agg * q.kv_B_per_pos,
                                                 link_fraction=R * qwen_agg * q.kv_B_per_pos / NIC400_Bps)
                                    for R in (1, 4, 20)})
    return out


def build():
    m, q = V41(), Qwen()
    rates, dr, eng = gpu_rates(), dense_rates(), ingest_engine()
    lanes = load("results/arch/v41_lanes.json")
    hs = load("results/arch/v41_hbm_switched.json")["ratios_batch1"]
    dec = dict(v41_rom={c: lanes["design_point"][c]["ar"] for c in ("1048576", "200000")},
               v41_hbm={c: hs[c]["ar"]["hbm"] for c in ("1048576", "200000")})
    qb = q.budget["batch"]["per_context"]["8192"]
    pp = q.budget["power_production"]["scenarios"]["B_proposed_production"]
    q_rom_b1 = pp["rom"]["ar_batch1"]["tokens_s"]            # the package's autoregressive design rate
    q_hbm_b1 = q.budget["hbm_comparator"]["8192"]["rom_format_int8"]["tokens_s"]
    q_m = q.budget["area"]["lane_multiplier_m"]        # the package's lane multiplier: batch 2 is KV-bound at it
    qwen_agg = next(r["total_tokens_s"] for r in qb["rom"] if r["batch"] == 2 and r["lane_multiplier"] == q_m)
    rec = dict(schema=SCHEMA, tool="tools/arch_prefill.py", policy="GPU prefill for every prompt (cold and agent "
               "turns); the decode chips ingest the KV (user decision)", citations=CITE, gpu_calibration=rates,
               dense_gpu_calibration=dr, ingest_engine=eng,
               decode_rates=dict(v41_rom=dec["v41_rom"], v41_hbm=dec["v41_hbm"], qwen_rom_b1=q_rom_b1,
                                 qwen_hbm_b1_int8=q_hbm_b1,
                                 sources=["results/arch/v41_lanes.json design_point",
                                          "results/arch/v41_hbm_switched.json ratios_batch1",
                                          "results/arch/qwen3_budget.json power_production B rom.ar_batch1 (Qwen ROM)",
                                          "results/arch/qwen3_budget.json hbm_comparator 8192 rom_format_int8"]),
               assumptions=dict(ep_layer_floor_s=EP_LAYER_FLOOR_S, indexer_eff_sensitivity=INDEXER_EFF_SENS,
                                fence_s=FENCE_S, gpu_chunk=GPU_CHUNK,
                                window_rings="shipped (40 x 128 x 528 B = 2.70 MB), not re-derived by replay"))
    rec["v41_workload"] = dict(
        weight_macs_per_token=m.weight_macs, attention_macs_per_token=m.att_macs,
        indexer_scan=[dict(kind=k, coeff=a) for k, a in m.scan],
        bytes={str(c): dict(sent=m.sent_bytes(c), written_replicated=m.written_bytes(c), capacity=m.capacity(c))
               for c in (200000, 1048576)},
        sent_B_per_new_token=m.row_B * 2.5)
    v = []
    for d in ("v41_rom", "v41_hbm"):
        for c in (1048576, 200000):
            for ng, nics, rk in ((8, 2, "conservative"), (8, 2, "optimistic"), (16, 2, "conservative"),
                                 (8, 8, "conservative")):
                if d == "v41_hbm" and (ng, nics, rk) != (8, 2, "conservative"):
                    continue
                v.append(v41_design(m, rates, eng, d, dec[d][str(c)], c, ng, nics, rk))
    rec["v41_cold"] = v
    rec["v41_turns"] = [dict(design="v41_rom", **v41_turn(m, rates, dec["v41_rom"][str(c)], n, c - n))
                        for c in (1048576, 200000) for n in (1024, 4096, 32768)]
    rec["qwen_cold"] = [qwen_design(q, dr, eng, "qwen_rom", q_rom_b1, 8192, g) for g in ("h200", "b200")] + \
                       [qwen_design(q, dr, eng, "qwen_hbm", q_hbm_b1, 8192, "h200")]
    v41_agg = {c: dict(b1=lanes["energy"][c]["b1"]["rom"]["aggregate_tokens_s"],
                       fill28=lanes["energy"][c]["fill28"]["rom"]["aggregate_tokens_s"],
                       sat1024=lanes["energy"][c]["sat1024"]["rom"]["aggregate_tokens_s"])
               for c in ("1048576", "200000")}
    rec["sustained"] = sustained(m, q, rates, dr, v41_agg, qwen_agg)
    # slot-reservation cost vs a session of S output tokens at the saturated per-user rate
    sat = {c: lanes["energy"][c]["sat1024"]["rom"]["tokens_s_per_user"] for c in ("1048576", "200000")}
    base = {(r["design"], r["context"]): r for r in v if r["gpus"].startswith("8 ") and r["rate_key"] == "conservative"
            and r["link"]["nics"] == 2}
    res = {}
    for c in ("1048576", "200000"):
        r = base[("v41_rom", int(c))]
        S = 32768 / sat[c]
        res[c] = dict(session_output_tokens=32768, session_decode_s=S,
                      stream_reserved_fraction=r["slot_reserved_s"]["stream"] / (r["slot_reserved_s"]["stream"] + S),
                      late_bind_reserved_fraction=r["slot_reserved_s"]["late_bind"] /
                      (r["slot_reserved_s"]["late_bind"] + S),
                      users_held=r["capacity"]["rom_users"])
    rec["slot_reservation"] = res
    # rack switch QoS: package-port load during a late-bind burst vs the Engram gather's own load
    t3 = m.rack["traffic"]["rows"]["T3_engram"]
    r1m = base[("v41_rom", 1048576)]
    rec["switch_port_load"] = dict(
        engram_utilisation_fill_mtp=t3["utilisation_fill_mtp"],
        ingest_package_port_utilisation_2x400G=r1m["busiest_package_bytes"] / r1m["burst"]["time_s"] / m.port_Bps,
        ingest_package_port_utilisation_8x400G=1.0,
        requirement="Engram gather in a strict-priority traffic class above KV ingest on the rack switch; ingest "
                    "in a lower class so a burst cannot queue a token-path gather behind it")
    return rec


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=OUT)
    a = ap.parse_args()
    rec = build()
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1, sort_keys=True) + "\n")
    for r in rec["v41_cold"]:
        print(f'{r["design"]} {r["context"]:>8} {r["gpus"]:22s} {r["rate_key"]:12s} nics={r["link"]["nics"]} '
              f'prefill {r["gpu_prefill_s"]:.2f} s  burst {r["burst"]["time_s"]*1e3:.2f} ms ({r["burst"]["binding"]})  '
              f'TTFT stream {r["ttft_stream_s"]:.3f} late {r["ttft_late_bind_s"]:.3f}')
    for r in rec["v41_turns"]:
        print(f'turn +{r["new_tokens"]} on {r["resident"]}: prefill {r["gpu_prefill_s"]*1e3:.1f} ms, TTFT cached '
              f'{r["ttft_prefix_cached_s"]*1e3:.1f} ms, readback {r["ttft_readback_serial_s"]*1e3:.1f} ms')
    for r in rec["qwen_cold"]:
        print(f'{r["design"]} {r["gpu"]}: prefill {r["gpu_prefill_s"]*1e3:.1f} ms TTFT {r["ttft_stream_s"]*1e3:.1f} ms')
    print("->", a.out)


if __name__ == "__main__":
    main()
