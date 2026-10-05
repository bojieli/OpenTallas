#!/usr/bin/env python3
"""W19: architecture feasibility audit of the GPU-organised HBM comparators (analysis only).

    python3 tools/hbm_feasibility_audit.py [--dramsim PATH/TO/dramsim3main] [--out results/uarch/hbm_feasibility_audit.json]

The audit re-walks the V4.1 HBM token exactly as tools/uarch_model.py prices it (v41_hbm_chain: the ROM arch DAG's
critical path at 1M, matvecs re-priced as SM ops on their 1/96 row slice, the switched-fabric terms of W9), moves it
to the 1.2 GHz product clock the way W16 does (cycle terms rescaled, fabric seconds kept), and then applies one
correction at a time.  Each correction is a switch on the same node walk, so every corrected rate names exactly what
changed.  The Qwen3-8B HBM comparator is audited on HBM efficiency and on the DFlash verify.

Nothing here edits the model; the record states what the model should absorb.

With --dramsim, a DRAMsim3 binary (github.com/umd-memsys/DRAMsim3) runs the model's access patterns on an HBM3E
pseudo-channel proxy (configs written by this tool); without it the previous record's DRAM section is kept.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import uarch_model as U          # noqa: E402
import arch_budget_v41 as A      # noqa: E402

SCHEMA = "opentallas.hbm-feasibility-audit.v1"
OUT = ROOT / "results/uarch/hbm_feasibility_audit.json"
CLK_MODEL = 1.0339e9             # hbm_gpu_design("v41") clock: every cycle term in the chain is counted here
CLK = 1.2e9                      # product clock (AGENTS.md, user decision 2026-09-30)
CLK_CHAIN = 0.9e9                # serial-chain domain (AGENTS.md clock domains: SU, SFU, softplus, Sinkhorn, reducers)
CTX = 1048576
TP = 96
HEADS = 64
ROM_TP = 4                       # the arch DAG's dedicated-unit nodes are priced at the ROM layer group (4 dies)
HBM_DIE_BPS = 3.6e12             # 4 HBM3E stacks x 0.9 TB/s sustained (uarch_model.hbm_gpu_design)
PKG_LINK_BPS = 0.9e12            # package switch link payload (tools/arch_hbm_switched_v41.py)
L_COLL_MODEL = 0.668             # us per switched collective in V41_HBM_FABRIC_US (125.9 us / 188)
N_COLL = U.V41_HBM_FABRIC_US["collective_latency"] / L_COLL_MODEL
GATHER_BUDGET_US = A.KV_GATHER_S_REQUIRED * 1e6          # 0.25 us: the DAG's attn.gather depth
TSELECT_KEYS_PER_US = 262144 / 3.962                     # ROM L20 topk_local: 262,144 keys in 3.962 us (DAG issue)
IDX_CAND_B = 8                                           # (score, position) candidate record (W9 prices 96 x 512 x 8 B)

# W16 consolidation headline under audit (branch claude/w16-consolidation 84aa38ce, results/uarch/consolidation.json
# clock_basis / comparison_rule "equal area" row).  Recorded here because the branch is not on main.
W16_HEADLINE = dict(commit="84aa38ce", record="results/uarch/consolidation.json (branch claude/w16-consolidation)",
                    ar_tokens_s=3193.7, mtp_tokens_s=6350.3, chain_us_ar=313.1, weight_sweep_us=37.4,
                    drain_cycles=70, barrier_boundary_cycles=54,
                    note="pre-W13-SS SM constants; main HEAD now carries drain 95 and a 78-cycle boundary")

# W15 NVLS switch bench, TP-12 (P = 6 packages), deterministic release, die clock 1.0339 GHz.  SCRATCH: W15 has not
# committed its HBM configs to results/rtl/w15_collectives.json yet (the P = 48 run is still open).  Parsed from
# /tmp/claude-1000/w15b/runs/hbm_p6/s{1,6,2001}_d1_*/log.txt (OP lines: slowest die last_vm - first issue).
W15_NVLS_SCRATCH = dict(
    bench="rtl/test/tb_w15_v41_hbm_nvls.sv (branch claude/w15-ss 7223e0ea), ot_link_nvls_switch, P = 6 (12 dies)",
    status="SCRATCH (not a committed record)", clock_hz=1.0339e9,
    all_reduce_ns={1: 808.6, 2: 855.0, 4: 856.9, 8: 860.8},
    all_gather_ns={1: 848.2, 2: 854.0, 4: 865.7, 8: 888.9},
    words_bytes=64, release="deterministic (U_DREL 47, X_DREL 240)",
    note="the switch core is held at 250 ns for any P (SW_PIPE = core - (2 + 3 log2 P)), so P = 48 should land "
         "within a few cycles of P = 6; the per-word slope is the bench's 16-lane width, not the product link")
L_COLL_W15 = 0.83                # us: central of 0.81 (1-word all-reduce) .. 0.85 (all-gather)

# W9 G-graph (tools/arch_hbm_best_v41.py price_g / draft_g at G = 96 on the NVLS switch fabric, the adopted ladder
# rung), evaluated 2026-09-30 by this stream: the model the uarch chain replaced.  Its routed experts carry the 1 us
# first access and the union of the pass's experts.
W9_G96 = dict(ar_tokens_s=3580.4, ar_breakdown_us=dict(compute_chain=111.73, weight_sweep=37.37,
                                                        collective_latency=125.87, collective_bytes=1.48),
              mtp_m6_tokens_s=8743.8, verify_us=370.7, draft_us=46.76, distinct_experts_6=34.6,
              mtp_breakdown_us=dict(compute_chain=112.83, weight_sweep=99.65, collective_latency=125.87,
                                    collective_bytes=29.24),
              collectives_issued=250, collectives_on_ar_path=219)
N_DRAFT_COLL = 3 * N_COLL / 40 + 5   # 3 layer spans + 5 Markov steps, one group collective each

FETCH_LAT_US = dict(low=0.25, central=0.5, high=1.0)
FETCH_LAT_SRC = ("low: the DAG's own gather budget (arch_budget_v41.KV_GATHER_S_REQUIRED, 250 ns); central: the "
                 "model's HBM_LOADED_LAT_NS (500 ns, the bulk-copy Little's-law latency); high: "
                 "arch_budget_v41.HBM_LAT_S (1 us, the first access of a data-dependent gather); DRAMsim3 proxy: "
                 "48-56 ns of it is the DRAM row miss, the rest is controller queue, PHY, NoC and SMEM landing")


def sha(p):
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()


# --------------------------------------------------------------------------------------------------------------
# V4.1: the node walk
# --------------------------------------------------------------------------------------------------------------
def _graph():
    if "g" not in _G:
        arch, b = U.arch_graph(CTX)
        _G["g"] = b.g
        _G["path"] = b.g.path(b.sink)
    return _G["g"], _G["path"]


_G = {}


def walk(P=1, fetch_lat=None, expert_eff=None, union=False, coll_L=L_COLL_MODEL, rowsplit_gather=False,
         idx_tp96=False, heads_tp96=False, chain_clock=False, head_align=False, gather_lat=None):
    """The V4.1 HBM chain (us at the 1.2 GHz product clock) with the named corrections.  With every switch off it
    is uarch_model.v41_hbm_chain rescaled as W16 does (_hbm_chain_n with the cycle terms x 1.0339/1.2)."""
    d = U.hbm_gpu_design("v41")
    assert d["clock_hz"] == CLK_MODEL
    drain = d["drain_cycles"]
    g, path = _graph()
    ck = CLK_MODEL / CLK
    parts = defaultdict(float)
    notes = defaultdict(float)
    Ue = A.distinct_experts(P, 384, 6) if union else 6.0
    moe_layers = 0
    idx_layers = 0
    for x in path:
        nd = g.nodes[x]
        kind = nd["kind"]
        t = sum(g.contrib[x].values()) * 1e6            # us at the DAG clock
        issue = nd.get("issue", 0.0) * 1e6
        k = U.node_key(x) if kind == "matvec" else ""
        if kind == "matvec" and k and k != "hc.fn":
            rows = nd["sweep"]["macs"] / U.NODE_K[k] / TP
            if head_align and k == "wq_b":
                rows = 512.0                               # one whole head (512 q rows) on a head die: 64 heads / 96 dies
            routed = 0.0
            if k == "experts_gu":
                routed = rows
            elif k == "down":
                routed = rows * 6 / 7                      # 6 routed + 1 shared expert rows
            if routed:
                rows += routed * (Ue / 6 - 1)
            t_sm = U.sm_op_cycles(rows, U.NODE_K[k], U.NODE_FMT[k], drain, True) / CLK
            t_op = t_sm
            if routed and expert_eff:
                # data-dependent: nothing is prefetched, the op runs at the HBM stream rate once the first byte lands
                by = (routed * Ue / 6) * U.NODE_K[k] * A.FP4
                t_op = max(t_sm, by / (HBM_DIE_BPS / 0.9 * expert_eff))
            parts["sm_matvec"] += t_op * 1e6
            if k == "experts_gu":
                moe_layers += 1
                if fetch_lat:
                    parts["expert_fetch_latency"] += fetch_lat
            parts["x_broadcast_fill"] += math.ceil(U.NODE_K[k] * P * 2 / U.X_BCAST_BPC) / CLK * 1e6
            continue
        if kind in ("collective", "hop"):
            continue
        f = 1.0                                            # issue scale for the TP-96 re-pricing
        extra_add = 0.0
        if idx_tp96 and (x.endswith("idx.score") or x.endswith("idx.topk_local")):
            f = ROM_TP / TP
        if idx_tp96 and x.endswith("idx.topk_final"):
            idx_layers += 1
            # a 96-way merge instead of 4-way: 96 x 512 candidates through the same tselect, and their bytes
            extra_add = (TP - ROM_TP) * 512 / TSELECT_KEYS_PER_US
            notes["idx_merge_bytes"] += TP * 512 * IDX_CAND_B * P / PKG_LINK_BPS * 1e6
        if heads_tp96 and (x.endswith(("attn.scores", "attn.pv", "attn.exp", "attn.normalize", "attn.max"))):
            f = math.ceil(HEADS / TP) / (HEADS / ROM_TP)   # 1 head a die against the DAG's 16
        tc = max(0.0, t - issue * (1 - f))
        ex = (P - 1) * issue * f if P > 1 else 0.0
        serial = kind in ("vector", "reduce", "select")
        s = (CLK_MODEL / CLK_CHAIN) if (chain_clock and serial) else ck
        if kind == "op" and x.endswith(".gather") and gather_lat is not None:
            parts["kv_gather_latency_delta"] += (gather_lat - GATHER_BUDGET_US)
        parts["dedicated_and_su"] += tc * s
        parts["verify_extra_issue"] += ex * s
        parts["dedicated_and_su"] += extra_add * (CLK_MODEL / CLK_CHAIN if chain_clock else ck) * (1 if P == 1 else 1)
        parts["verify_extra_issue"] += extra_add * (P - 1) * (CLK_MODEL / CLK_CHAIN if chain_clock else ck)
    nb = U.v41_boundaries(path, g.nodes)
    parts["barrier"] = nb * d["barrier"]["boundary_cycles"] / CLK * 1e6
    parts["collective_latency"] = N_COLL * coll_L
    parts["collective_bytes"] = U.V41_HBM_FABRIC_US["collective_bytes"] * P + notes["idx_merge_bytes"]
    parts["pipeline_hops"] = U.V41_HBM_FABRIC_US["pipeline_hops"]
    parts["control"] = U.V41_HBM_FABRIC_US["control"]
    if rowsplit_gather:
        parts["rowsplit_intermediate_gather"] = moe_layers * (coll_L + 6 * 2304 * 2 * P / PKG_LINK_BPS * 1e6)
    T = sum(parts.values())
    return T, {k: round(v, 3) for k, v in parts.items()}, dict(boundaries=nb, moe_layers=moe_layers,
                                                              distinct_experts=round(Ue, 2))


def rates(opts_ar, opts_v, draft="model", coll_L=L_COLL_MODEL):
    T_ar, p_ar, _ = walk(1, **opts_ar)
    T_ar = max(T_ar, 37.4)
    T_v, p_v, info = walk(U.V41_POSITIONS, **opts_v)
    if draft == "model":
        Td = U.V41_DRAFT_FRACTION * T_ar
    else:
        Td = W9_G96["draft_us"] + N_DRAFT_COLL * (coll_L - L_COLL_MODEL)
    mtp = U.V41_TAU / (T_v + Td) * 1e6
    return dict(ar_T_us=round(T_ar, 1), ar_tokens_s=round(1e6 / T_ar, 1), verify_T_us=round(T_v, 1),
                draft_us=round(Td, 1), mtp_tokens_s=round(mtp, 1), ar_parts_us=p_ar, verify_parts_us=p_v,
                verify_info=info)


def v41_audit():
    base = rates({}, {})
    L = FETCH_LAT_US
    cases = {}

    def case(key, ar, v, draft="model", coll_L=L_COLL_MODEL):
        r = rates(ar, v, draft, coll_L)
        cases[key] = dict(ar_tokens_s=r["ar_tokens_s"], mtp_tokens_s=r["mtp_tokens_s"],
                          d_ar_us=round(r["ar_T_us"] - base["ar_T_us"], 1),
                          d_verify_us=round(r["verify_T_us"] - base["verify_T_us"], 1),
                          d_draft_us=round(r["draft_us"] - base["draft_us"], 1))
        return r

    eff_c = DRAM_EFF["expert_chunks_refresh"]
    case("1_expert_fetch_latency", dict(fetch_lat=L["central"], gather_lat=L["central"]),
         dict(fetch_lat=L["central"], gather_lat=L["central"]))
    case("1_expert_stream_efficiency", dict(expert_eff=eff_c), dict(expert_eff=eff_c))
    case("2_collective_latency_w15", dict(coll_L=L_COLL_W15), dict(coll_L=L_COLL_W15), coll_L=L_COLL_W15)
    case("3_rowsplit_intermediate_gather", dict(rowsplit_gather=True), dict(rowsplit_gather=True))
    case("3_head_alignment_64_on_96", dict(head_align=True), dict(head_align=True))
    case("4_mtp_expert_union", {}, dict(union=True))
    case("4_mtp_expert_union_streamed", dict(expert_eff=eff_c), dict(union=True, expert_eff=eff_c))
    case("6_indexer_at_tp96_widths", dict(idx_tp96=True), dict(idx_tp96=True))
    case("6_attention_at_tp96_heads", dict(heads_tp96=True), dict(heads_tp96=True))
    case("6_serial_chain_at_0p9ghz", dict(chain_clock=True), dict(chain_clock=True))
    case("6_drafter_w9_g96", {}, {}, draft="w9")

    def combined(lat, collL, chain, eff):
        o = dict(fetch_lat=lat, gather_lat=lat, expert_eff=eff, coll_L=collL, rowsplit_gather=True, idx_tp96=True,
                 heads_tp96=True, chain_clock=chain, head_align=True)
        ov = dict(o, union=True)
        return rates(o, ov, draft="w9", coll_L=collL)

    central = combined(L["central"], L_COLL_W15, True, eff_c)
    low = combined(L["high"], 0.89, True, 0.795)                  # the pessimistic end
    high = combined(L["low"], L_COLL_MODEL, False, 0.9)             # the optimistic end (model fabric, 1.2 GHz chain)
    return dict(baseline_main=base, cases=cases, combined=dict(central=central, pessimistic=low, optimistic=high))


# --------------------------------------------------------------------------------------------------------------
# DRAM proxy (DRAMsim3) of the model's access patterns
# --------------------------------------------------------------------------------------------------------------
# HBM3E pseudo-channel proxy: 32-bit PC, BL8 (32 B a burst), 32 PCs x 31.25 GB/s = 1.0 TB/s a stack (the model's
# 1,024 ps per 32 B burst per PC, uarch_model.HBM_PC_SECTORS_PER_CYCLE).  Timings in ns from HBM3-class datasheet
# ranges (ASSUMED values, recorded below): tRCD 14, tRP 14, tRAS 29, CL 17, tRRD 2/4, tFAW 16, tCCD_L 2,
# tRFCab 350, tREFI 3,900, tRFCpb 200.  Bank groups interleaved at the burst (address map ro-ra-ba-ch-co-bg).
DRAM_TCK_NS = 0.256
DRAM_TIMING_NS = dict(CL=17, CWL=8, tRCDRD=14, tRCDWR=10, tRP=14, tRAS=29, tRFC=350, tRFCb=200, tREFI=3900,
                      tRRD_S=2, tRRD_L=4, tWTR_S=3, tWTR_L=9, tFAW=16, tWR=16, tCCD_S=1.024, tCCD_L=2.048,
                      tRTP_L=7.5, tRTP_S=3.8)
DRAM_EFF = dict(                       # filled from the record (or a --dramsim run): fraction of the PC peak
    weight_stream_refresh=0.899, weight_stream_with_writes_refresh=0.873, expert_chunks_refresh=0.795,
    kv_rows_refresh=0.496, weight_stream_no_refresh=0.997)
PATTERNS = dict(
    A_stream="dense weight prefetch: sequential 32 B bursts",
    B_expert="routed expert slice at TP-96: 1.5 KB contiguous at random 1 KB-aligned rows (1.44 KB a PC an expert)",
    C_kvrow="selected KV / index rows: 288 B at random rows",
    D_stream_wr="weight stream with one 32 B write per 32 reads (KV append, results)",
    E_random="random 32 B reads (bound)")


def _dram_cfg(banks_per_group, policy, refresh=True):
    c = {k: max(1, round(v / DRAM_TCK_NS)) for k, v in DRAM_TIMING_NS.items()}
    if not refresh:
        c["tREFI"] = 10 ** 9
    nb = 4 * banks_per_group
    return f"""[dram_structure]
protocol = HBM
bankgroups = 4
banks_per_group = {banks_per_group}
rows = 32768
columns = 256
device_width = 32
BL = 8
num_dies = 1
[timing]
tCK = {DRAM_TCK_NS}
CL = {c['CL']}
CWL = {c['CWL']}
tRCDRD = {c['tRCDRD']}
tRCDWR = {c['tRCDWR']}
tRP = {c['tRP']}
tRAS = {c['tRAS']}
tRFC = {c['tRFC']}
tRFCb = {c['tRFCb']}
tREFI = {c['tREFI']}
tREFIb = {max(1, c['tREFI'] // nb)}
tRPRE = 1
tWPRE = 1
tRRD_S = {c['tRRD_S']}
tRRD_L = {c['tRRD_L']}
tWTR_S = {c['tWTR_S']}
tWTR_L = {c['tWTR_L']}
tFAW = {c['tFAW']}
tWR = {c['tWR']}
tCCD_S = {c['tCCD_S']}
tCCD_L = {c['tCCD_L']}
tXS = 1400
tCKE = 8
tCKSRE = 10
tXP = 8
tRTP_L = {c['tRTP_L']}
tRTP_S = {c['tRTP_S']}
[power]
VDD = 1.2
IDD0 = 65
IDD2P = 28
IDD2N = 40
IDD3P = 40
IDD3N = 55
IDD4W = 500
IDD4R = 390
IDD5AB = 250
IDD6x = 31
[system]
channel_size = 1024
channels = 2
bus_width = 32
address_mapping = rorabachcobg
queue_structure = PER_BANK
refresh_policy = {policy}
row_buf_policy = OPEN_PAGE
cmd_queue_size = 16
trans_queue_size = 128
unified_queue = False
[other]
epoch_period = 100000000
output_level = 1
"""


def _traces(d: Path, n=200000):
    import random
    rnd = random.Random(20260930)
    cap = 2 * 512 * 2 ** 20

    def w(name, seq):
        with open(d / f"{name}.trc", "w") as f:
            for a, wr in seq:
                f.write(f"0x{a:x} {'WRITE' if wr else 'READ'} 0\n")
    w("A_stream", [(i * 32, False) for i in range(n)])
    out = []
    while len(out) < n:
        base = rnd.randrange(0, cap - 4096) // 1024 * 1024
        out += [(base + j * 32, False) for j in range(48)]
    w("B_expert", out[:n])
    out = []
    while len(out) < n:
        base = rnd.randrange(0, cap // 288 - 1) * 288 // 32 * 32
        out += [(base + j * 32, False) for j in range(9)]
    w("C_kvrow", out[:n])
    out, wa = [], cap // 2
    for i in range(n):
        if i % 33 == 32:
            out.append((wa, True))
            wa += 32
        else:
            out.append((i * 32, False))
    w("D_stream_wr", out)
    w("E_random", [(rnd.randrange(0, cap // 32) * 32, False) for _ in range(n)])
    with open(d / "F_idle.trc", "w") as f:
        for i in range(150):
            f.write(f"0x{rnd.randrange(0, 2 ** 29) // 32 * 32:x} READ {i * 2000}\n")


def dram_proxy(binary: str):
    d = Path(tempfile.mkdtemp(prefix="w19dram_"))
    _traces(d)
    runs = {}
    cfgs = dict(no_refresh=(4, "RANK_LEVEL_STAGGERED", False), all_bank_refresh_16b=(4, "RANK_LEVEL_STAGGERED", True),
                all_bank_refresh_48b=(12, "RANK_LEVEL_STAGGERED", True),
                per_bank_refresh_48b=(12, "BANK_LEVEL_STAGGERED", True))
    procs = []
    for cn, (bpg, pol, ref) in cfgs.items():
        (d / f"{cn}.ini").write_text(_dram_cfg(bpg, pol, ref))
        for t in list(PATTERNS) + (["F_idle"] if cn == "all_bank_refresh_16b" else []):
            o = d / f"{cn}__{t}"
            o.mkdir()
            procs.append((cn, t, o, subprocess.Popen([binary, str(d / f"{cn}.ini"), "-c",
                                                      "300000" if t == "F_idle" else "400000", "-t",
                                                      str(d / f"{t}.trc"), "-o", str(o)],
                                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)))
    for cn, t, o, p in procs:
        p.wait()
        r = json.loads((o / "dramsim3.json").read_text())
        bw = sum(v["average_bandwidth"] for v in r.values())
        runs.setdefault(cn, {})[t] = dict(
            GBps=round(bw, 2), efficiency=round(bw / 62.5, 3),
            read_latency_ns=round(sum(v["average_read_latency"] for v in r.values()) / len(r) * DRAM_TCK_NS, 1),
            activates=sum(v["num_act_cmds"] for v in r.values()))
    try:
        commit = subprocess.run(["git", "-C", str(Path(binary).resolve().parents[1]), "rev-parse", "HEAD"],
                                capture_output=True, text=True).stdout.strip()
    except Exception:
        commit = "unknown"
    return dict(tool="DRAMsim3", commit=commit, proxy="2 HBM3E pseudo-channels (32 bit, BL8), 62.5 GB/s peak",
                timing_ns=DRAM_TIMING_NS, tck_ns=DRAM_TCK_NS, patterns=PATTERNS, runs=runs,
                caveats=["DRAMsim3 has no HBM3 protocol: the HBM (2) protocol with HBM3E-class timings in ns",
                         "saturated injection: read latencies are queueing, not first access (F_idle is first access)",
                         "no ECC, no controller or PHY overhead: an upper bound on the achievable fraction",
                         "per-bank refresh in DRAMsim3 is pessimistic against the repository's RTL REFpb study "
                         "(results/rtl/hdc_hbm_campaign.json refresh_study, cited in arch_budget_v41.hbm_requirements: "
                         "0.965-0.993 of refresh-free)"])


# --------------------------------------------------------------------------------------------------------------
# Qwen3-8B HBM comparator
# --------------------------------------------------------------------------------------------------------------
def qwen_audit(dram):
    rec = json.loads((ROOT / "results/uarch/hbm_gpu.json").read_text())
    rows = {r["design"]: r for r in rec["rows"]}
    spec = {r["design"]: r for r in rec["speculation"]}
    ar = rows["qwen_hbm_gpu"]["tokens_s"]
    out = dict(model_ar_tokens_s=ar, model_sustained_fraction=0.90)
    effs = dict(proxy_stream_refresh=dram["weight_stream_refresh"],
                proxy_stream_writes_refresh=dram["weight_stream_with_writes_refresh"], low=0.85)
    out["ar_at_efficiency"] = {k: dict(fraction=v, tokens_s=round(ar * v / 0.90, 1)) for k, v in effs.items()}
    # DFlash verify: GQA 4 query heads per KV head x b positions share each K/V element; the SM has 16 columns
    dq = U.hbm_gpu_design("qwen")
    clock = dq["clock_hz"]
    n_sm, ingest = dq["sm_count"], dq["element"]["ingest_Bpc"]
    cols = dq["element"]["cols"]
    kv_die_layer = 2 * 4 * 128 * 8192                      # FP8 K and V, this die's 4 KV heads, 8K (qwen_hbm_ops)
    simt = n_sm * dq["element"]["simt_lanes"]
    acc = json.loads((ROOT / "results/speculative/dflash_block_acceptance.json").read_text())["blocks"]
    blocks = []
    for name, r in spec.items():
        if not name.startswith("qwen_hbm_dflash_b"):
            continue
        b = r["block"]
        passes = math.ceil(4 * b / cols)
        t_sm = passes * kv_die_layer / (n_sm * ingest)
        t_hbm = kv_die_layer / dq["hbm_Bpc"]
        attn_extra = max(0.0, t_sm - max(t_hbm, kv_die_layer / (n_sm * ingest)))
        # softmax on the SIMT lanes: max, exp-sum, scale over 16 heads x 8K keys a position (3 passes)
        smx_extra = 3 * (b - 1) * 16 * 8192 / simt
        extra = 36 * (attn_extra + smx_extra)
        step = r["step_cycles"] + extra
        blocks.append(dict(block=b, tau=r["tau"], model_tokens_s=r["tokens_s"], model_step_cycles=r["step_cycles"],
                           kv_passes=passes, attn_extra_cycles_per_layer=round(attn_extra),
                           softmax_extra_cycles_per_layer=round(smx_extra), corrected_step_cycles=round(step),
                           corrected_tokens_s=round(r["tau"] * clock / step, 1),
                           corrected_tokens_s_at_proxy_eff=round(r["tau"] * clock / (
                               r["step_cycles"] * 0.90 / dram["weight_stream_with_writes_refresh"] + extra), 1)))
    blocks.sort(key=lambda x: x["block"])
    best = max(blocks, key=lambda x: x["corrected_tokens_s"])
    best_e = max(blocks, key=lambda x: x["corrected_tokens_s_at_proxy_eff"])
    out["dflash"] = dict(model_best=spec["qwen_hbm_dflash_best"]["tokens_s"], model_best_block=spec["qwen_hbm_dflash_best"]["block"],
                         blocks=blocks, corrected_best=dict(block=best["block"], tokens_s=best["corrected_tokens_s"]),
                         corrected_best_at_proxy_eff=dict(block=best_e["block"], tokens_s=best_e["corrected_tokens_s_at_proxy_eff"]),
                         mma_columns=cols, gqa_q_per_kv=4, clock_hz=clock,
                         basis="the model prices the verify as the AR stream plus the draft bytes (hbm_speculation_rows): "
                               "the in-block attention adds no bytes, but at GQA 4 a b-position block needs 4b query "
                               "columns on each K/V element and the SM has 16, so K and V pass the MMA ceil(4b/16) "
                               "times; softmax runs on the 4,096 SIMT lanes")
    return out


# --------------------------------------------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dramsim", default=None)
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args()
    prev = json.loads(Path(a.out).read_text()) if Path(a.out).exists() else None
    if a.dramsim:
        dram = dram_proxy(a.dramsim)
    elif prev and "dram_proxy" in prev:
        dram = prev["dram_proxy"]
    else:
        dram = None
    if dram:
        r = dram["runs"]
        DRAM_EFF.update(weight_stream_refresh=r["all_bank_refresh_16b"]["A_stream"]["efficiency"],
                        weight_stream_with_writes_refresh=r["all_bank_refresh_16b"]["D_stream_wr"]["efficiency"],
                        expert_chunks_refresh=r["all_bank_refresh_16b"]["B_expert"]["efficiency"],
                        kv_rows_refresh=r["all_bank_refresh_16b"]["C_kvrow"]["efficiency"],
                        weight_stream_no_refresh=r["no_refresh"]["A_stream"]["efficiency"])
    v = v41_audit()
    q = qwen_audit(DRAM_EFF)
    srcs = ["tools/uarch_model.py", "tools/arch_budget_v41.py", "tools/arch_hbm_best_v41.py",
            "tools/arch_hbm_switched_v41.py", "tools/hbm_feasibility_audit.py", "results/uarch/hbm_gpu.json",
            "results/rtl/gpu_sm_exact.json", "results/rtl/gpu_sm_blockdot_exact.json",
            "results/rtl/gpu_supply_barrier.json", "results/floorplan/hbm_gpu/v41_hbm_die.json",
            "results/speculative/dflash_block_acceptance.json", "results/arch/v41_latency_ladder.json"]
    C = v["cases"]

    def cr(key):
        return dict(ar_tokens_s=C[key]["ar_tokens_s"], mtp_tokens_s=C[key]["mtp_tokens_s"])
    verdicts = [
        dict(assumption="1a sustained HBM3E bandwidth (weight stream)", model="0.90 of 1.0 TB/s a stack, 3.6 TB/s a die; "
             "weight sweep 37.4 us under a 313-326 us chain", evidence=f"DRAMsim3 proxy, all-bank refresh: stream "
             f"{DRAM_EFF['weight_stream_refresh']}, stream + writes {DRAM_EFF['weight_stream_with_writes_refresh']}; "
             "the sweep is 12% of the chain, so AR at batch 1 is not bandwidth-bound", verdict="SOUND",
             corrected=dict(ar_tokens_s=v["baseline_main"]["ar_tokens_s"], mtp_tokens_s=v["baseline_main"]["mtp_tokens_s"])),
        dict(assumption="1b data-dependent routed-expert fetch", model="omitted: matvecs priced with weights resident "
             "(W9's G-graph carried +1 us a layer; the uarch chain dropped it)", evidence="expert ids exist only after "
             "top-6; DRAMsim3 first access 53 ns in the DRAM + controller/PHY/NoC; 0.5 us central, 40 layers",
             verdict="OPTIMISTIC", corrected=cr("1_expert_fetch_latency")),
        dict(assumption="2a switched collective latency", model=f"{L_COLL_MODEL} us x {N_COLL:.0f} on the path = 125.9 us",
             evidence="W15 NVLS bench (TP-12, deterministic, SCRATCH): 0.81 us all-reduce, 0.85-0.89 us all-gather",
             verdict="OPTIMISTIC", corrected=cr("2_collective_latency_w15")),
        dict(assumption="2b collective count vs exact row split", model="188 on the path (W9 K-split down/wo_b) while "
             "sm_op_cycles keeps a row's whole K in one SM", evidence="exact golden order needs the 6 x 2,304 expert "
             "intermediate gathered before down: +1 collective a MoE layer", verdict="OPTIMISTIC",
             corrected=cr("3_rowsplit_intermediate_gather")),
        dict(assumption="3 MoE at TP-96 (384 experts, top-6, 2,304 x 5,120 FP4)", model="every die 1/96 of every "
             "expert: 48 gate/up rows, 184 KB a die an expert", evidence="balanced by construction (no routing "
             "imbalance); EP at batch 1 puts 6 experts on <= 6 of 96 dies at 4.9 us each (E[max load] 1.15): "
             "~+200 us/token; 64 heads on 96 dies need head alignment (+2 us)", verdict="SOUND (TP beats EP at B = 1)",
             corrected=cr("3_head_alignment_64_on_96")),
        dict(assumption="4a MTP: dense matrices on the 8 MMA columns", model="one weight pass for 6 positions",
             evidence="SM_ELEM v41 cols 8, x store sized for 8 columns; RTL exactness cases are 2 columns",
             verdict="SOUND (8-column SM not yet measured)", corrected=None),
        dict(assumption="4b MTP: routed experts ride the columns", model="6 experts a layer for 6 positions",
             evidence=f"each position routes its own top-6: union U(6) = {A.distinct_experts(6, 384, 6):.1f} experts, "
             "fetched after the router (W9 prices the union)", verdict="OPTIMISTIC",
             corrected=cr("4_mtp_expert_union_streamed")),
        dict(assumption="4c MTP: per-position KV rows (W11: 6 x 645 rows)", model="kvscan issue repeated per position, "
             "collective bytes x 6", evidence="W11 forward_positions: own window + own selection per position; the "
             "HBM chain assumes no shared rows", verdict="SOUND", corrected=None),
        dict(assumption="5 KV capacity/bandwidth at 1M", model=f"{U._v41_state_user() / 1e9 if hasattr(U, '_v41_state_user') else 0.936:.3f} GB a user; "
             "~7,760 users a TP-96 group", evidence="0.183 GB index keys + 6 MB rows a token a user; 346 TB/s a group",
             verdict="SOUND", corrected=None),
        dict(assumption="6a indexer at ROM TP-4 widths", model="262,144 keys a die (the ROM DAG)",
             evidence="TP-96 holds 1/96 of the keys; the merge becomes 96 x 512", verdict="PESSIMISTIC",
             corrected=cr("6_indexer_at_tp96_widths")),
        dict(assumption="6b attention at 16 heads a die", model="the ROM DAG's 16 heads", evidence="<= 1 head a die at TP-96",
             verdict="PESSIMISTIC", corrected=cr("6_attention_at_tp96_heads")),
        dict(assumption="6c serial units at 1.2 GHz", model="dedicated_and_su cycles rescaled to 1.2 GHz",
             evidence="AGENTS.md clock domains: SU/SFU/reducers/select at 0.9 GHz", verdict="OPTIMISTIC",
             corrected=cr("6_serial_chain_at_0p9ghz")),
        dict(assumption="6d drafter", model="3/40 of an AR token (ASSUMED)", evidence="W9 draft_g at G = 96: 46.8 us "
             "(3 layer spans + 5 Markov steps, each with a collective)", verdict="OPTIMISTIC",
             corrected=cr("6_drafter_w9_g96")),
        dict(assumption="6e barriers / kernel boundaries", model="329 boundaries x 78 cycles (RTL-measured 62 + 16)",
             evidence="tb_gpu_barrier; a persistent hardware-sequenced program, not GPU kernels (V100 grid.sync would "
             "give 1,246 tok/s)", verdict="SOUND for the custom machine; idealised as a 'GPU'", corrected=None),
        dict(assumption="Qwen 1: HBM efficiency", model="0.90 of 8 x 1.0 TB/s", evidence="proxy 0.873-0.898",
             verdict="SOUND (0-3%)", corrected=dict(ar_tokens_s=q["ar_at_efficiency"]["proxy_stream_writes_refresh"]["tokens_s"])),
        dict(assumption="Qwen 4: DFlash b16 on 16 columns", model="verify = AR bytes + draft bytes",
             evidence="GQA 4 x 16 positions = 64 query columns: K/V pass the MMA 4 times; softmax on SIMT",
             verdict="OPTIMISTIC", corrected=dict(dflash_tokens_s=q["dflash"]["corrected_best"]["tokens_s"])),
    ]
    cc = v["combined"]
    summary = dict(
        w16_headline=dict(ar=W16_HEADLINE["ar_tokens_s"], mtp=W16_HEADLINE["mtp_tokens_s"]),
        main_model_at_1p2=dict(ar=v["baseline_main"]["ar_tokens_s"], mtp=v["baseline_main"]["mtp_tokens_s"]),
        realistic_range=dict(ar=[cc["pessimistic"]["ar_tokens_s"], cc["central"]["ar_tokens_s"], cc["optimistic"]["ar_tokens_s"]],
                             mtp=[cc["pessimistic"]["mtp_tokens_s"], cc["central"]["mtp_tokens_s"], cc["optimistic"]["mtp_tokens_s"]],
                             order="pessimistic, central, optimistic"),
        blockers="none architectural; every gap is a latency term with a known build",
    )
    build_plan = [
        "B1 program: the TP-96 V4.1 token as an SM/dedicated-unit program with row-split exact matvecs (whole K "
        "per SM), head-aligned wq_b (64 heads on 64 of 96 dies), sequence-sharded KV and index keys; golden-checked "
        "per layer (extends the W17 TP-4 ISA executor to TP-96 ranks)",
        "B2 expert fetch path: router top-6 -> descriptor -> bulk copy of 6 (or U(6)) expert slices from 128 "
        "pseudo-channels into SMEM, measured first-byte latency in RTL against a DRAM model (closes 1b and 4b)",
        "B3 collectives at P = 48: commit W15's tb_w15_v41_hbm_nvls P = 6 and P = 48 records; add the 27.6 KB "
        "expert-intermediate all-gather and the 96 x 512 index merge to the collective list",
        "B4 8-column SM exactness and timing (the RTL cases are 2 columns): the MTP column claim",
        "B5 dedicated units on the HBM die at TP-96 widths in the 0.9 GHz serial domain (indexer 1/96 keys, "
        "96-way top-k merge, 1-head attention with per-position rows)",
        "B6 runtime composition: one full-shape token over 96 ranks (runtime composition, not a flat netlist), "
        "one layer cycle-accurate per rank class, collectives from B3's record, token checked against the 1M "
        "reference token (21946)",
        "B7 re-price the model from B1-B6 and restate the HBM headline; DSpark drafter priced on the G = 96 graph",
    ]
    rec = dict(schema=SCHEMA, tool="tools/hbm_feasibility_audit.py", stream="W19", date="2026-09-30",
               verdicts=verdicts, summary=summary, build_plan=build_plan,
               status="analysis (no P&R, no RTL); corrections are estimates on the model's own node walk",
               headline_under_audit=W16_HEADLINE, w15_nvls_scratch=W15_NVLS_SCRATCH, w9_g96_reference=W9_G96,
               fetch_latency_us=dict(FETCH_LAT_US, source=FETCH_LAT_SRC),
               collective_latency_us=dict(model=L_COLL_MODEL, w15_scratch_central=L_COLL_W15,
                                          collectives_on_path=round(N_COLL, 1)),
               dram_efficiency_used=dict(DRAM_EFF), dram_proxy=dram, v41=v, qwen=q,
               source_sha256={s: sha(s) for s in srcs if (ROOT / s).exists()})
    Path(a.out).write_text(json.dumps(rec, indent=1) + "\n")
    b = v["baseline_main"]
    print(f"baseline main @1.2 GHz: AR {b['ar_tokens_s']}  MTP {b['mtp_tokens_s']}")
    for k, c in v["cases"].items():
        print(f"  {k:36s} AR {c['ar_tokens_s']:8.1f} (dT {c['d_ar_us']:+6.1f})  MTP {c['mtp_tokens_s']:8.1f} "
              f"(dV {c['d_verify_us']:+6.1f}, dD {c['d_draft_us']:+5.1f})")
    for k, c in v["combined"].items():
        print(f"  combined {k:12s} AR {c['ar_tokens_s']:8.1f}  MTP {c['mtp_tokens_s']:8.1f}  T_ar {c['ar_T_us']}  "
              f"verify {c['verify_T_us']} draft {c['draft_us']}")
    print("qwen", json.dumps({k: q[k] for k in ("ar_at_efficiency",)}), q["dflash"]["corrected_best"],
          q["dflash"]["corrected_best_at_proxy_eff"])


if __name__ == "__main__":
    main()
