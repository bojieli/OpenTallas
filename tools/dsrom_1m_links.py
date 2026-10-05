#!/usr/bin/env python3
"""DS-ROM S81 links in RTL at 1.2 GHz: the stage hop, the token return and the TP4 collectives.

Replaces the per-token composition's modelled link terms (tools/dsrom_1m_measure.py, graph s58_graph()) by RTL
measurements at the S81 shapes and the 1.2 GHz streaming clock (T_CORE 0.8333 ns):

  hop   rtl/test/dsrom_sys/tb_dsrom_1m_hop.sv (Icarus): the 40,976-B residual (641 flits of 64 B) through the S81
        link endpoint rtl/dsrom_sys/ot_dsrom_link_rt.sv on an idle link with full-rate credits (CREDITS 512,
        SEQW 10), the board leg's CHANNEL_CYCLES = the light-FEC PHY budget (130 ns = 156 cycles, a VENDOR
        budget carried as a delay line), optionally chained cut-through into a second ot_dsrom_link_rt for the
        in-package UCIe fan-out leg of the graph's hop ('board mesh x1 + UCIe fan-out'); one 8-B flit for the
        token return.  The endpoint on-die wire stages (2 x 45, routed die geometry) are added in cycles.
  coll  rtl/test/tb_w15b_v41_tp4.sv (Verilator 5.050) via tools/w15_collectives.py: the TP4 group (2 packages x
        2 dies, per-die clocks, UCIe-A and 112G light-FEC link layers, deterministic release) at T_CORE 0.8333 ns,
        one descriptor per S81 collective at its exact payload, golden-checked on every VM write.

Subcommands: hop, coll, record (merge the two into results/rtl/dsrom_1m_allmeasured_20261004/links.json), all.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
OUT = ROOT / "results/rtl/dsrom_1m_allmeasured_20261004/links.json"

CLK = 1.2e9
T_CORE_NS = 0.8333

# ------------------------------------------------------------------------------------------------------- budgets
# Board light-FEC hop (tools/sync_cost_table.py hop_decomp.on_module_light_fec_130ns point_ns 130; arch_budget_v41
# BASELINE board_hop_s 130 ns): PHY Tx+Rx, RS(272,257) accumulate + decode, PCS, flight, CDC, endpoint.
LFEC_NS = 130.0
# Rack cable full KP4 (technology.json links.rom_rack_cable_serdes hop 209 ns): what ArrayFabric.alpha_stage charges
# for the stage hop and the token return in the S58 graph (sensitivity only).
KP4_NS = 209.0
# In-package UCIe fan-out leg: technology.json links.rom_package_ucie hop 10 ns, less the 1.5 ns on-die routing proxy
# it embeds (uarch_model.UCIE_LEGACY_ONDIE_S), which the routed-geometry wire stages replace.
UCIE_NS = 10.0 - 1.5
# Endpoint on-die wire stages: uarch_model.DIE_SHRUNK_INTERIM serdes_stages 45 (collective/hub -> SerDes edge at the
# SS 504 um/stage reach), paid at both ends (uarch_model.hub_edge_hop_wire_s).
SERDES_STAGES = 45
# PHY lane rate per die pair: R-L9 13 lanes x 13.18 GB/s (tools/rtl_v41_stage_collective_campaign.LINKS t1).
T1_LANES = 13
RESIDUAL_B = 40976
RETURN_B = 8
RETURN_TRAVERSALS = 8          # decode_critical_path.ArrayFabric.hop('return'): 'board x8 (token id back to the first stage)'


def cyc(ns):
    return math.ceil(ns * CLK * 1e-9 - 1e-9)


CH_LFEC, CH_KP4, CH_UCIE = cyc(LFEC_NS), cyc(KP4_NS), cyc(UCIE_NS)

HOP_RTL = ["rtl/test/dsrom_sys/tb_dsrom_1m_hop.sv", "rtl/dsrom_sys/ot_dsrom_link_rt.sv",
           "rtl/dsrom_sys/ot_dsrom_link_chan.sv", "rtl/link/ot_link_crc32.sv"]
# name, defines, bytes, role
HOP_CASES = [
    ("hop_lfec_board", dict(FB=64, CH=CH_LFEC, CHU=0), RESIDUAL_B, "board leg alone (light-FEC)"),
    ("hop_lfec_fanout", dict(FB=64, CH=CH_LFEC, CHU=CH_UCIE), RESIDUAL_B,
     "HEADLINE stage hop: board leg (light-FEC) + cut-through UCIe fan-out leg"),
    ("ret_lfec_flit", dict(FB=64, CH=CH_LFEC, CHU=0), RETURN_B, "HEADLINE token return: one 8-B flit, one board traversal"),
    ("hop_kp4_fanout", dict(FB=64, CH=CH_KP4, CHU=CH_UCIE), RESIDUAL_B,
     "sensitivity: the 209 ns full-KP4 cable tier the S58 graph's alpha_stage charges"),
    ("ret_kp4_flit", dict(FB=64, CH=CH_KP4, CHU=0), RETURN_B, "sensitivity: token return traversal on the 209 ns tier"),
    ("lever_fb160_lfec_fanout", dict(FB=160, CH=CH_LFEC, CHU=CH_UCIE), RESIDUAL_B,
     "INFORMATIVE lever, not the S81 endpoint: 160-B flits (192 GB/s) so the PHY lane rate, not the endpoint, binds"),
]


def sha(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def tool_version(cmd):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True)
        return (r.stdout + r.stderr).strip().splitlines()[0]
    except Exception as e:  # pragma: no cover
        return f"unavailable: {e}"


def phy_Bps():
    import rtl_v41_stage_collective_campaign as SC
    return T1_LANES * SC.LANE_NET_BPS


def run_hop_case(work: Path, case):
    name, defs, nbytes, role = case
    vvp = work / f"{name}.vvp"
    cmd = ["iverilog", "-g2012", "-o", str(vvp)] + [f"-D{k}={v}" for k, v in sorted(defs.items())] + \
        [str(ROOT / s) for s in HOP_RTL]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"compile {name}: {r.stderr[-2000:]}")
    r = subprocess.run(["vvp", "-n", str(vvp), f"+bytes={nbytes}", "+seed=81", f"+case={name}"],
                       capture_output=True, text=True)
    m = re.search(r"HOP_SUMMARY (.*)", r.stdout)
    if not m:
        raise SystemExit(f"{name}: no summary\n{r.stdout[-2000:]}{r.stderr[-2000:]}")
    f = {}
    for kv in m.group(1).split():
        k, v = kv.split("=", 1)
        f[k] = int(v) if re.fullmatch(r"-?\d+", v) else v
    return dict(case=name, role=role, defines=defs, bytes=nbytes, summary=m.group(0), fields=f,
                mismatch_lines=[l for l in r.stdout.splitlines() if l.startswith("MISMATCH")][:5],
                exact=f["result"] == "PASS")


def cmd_hop(a):
    work = Path(a.work) / "hop"
    work.mkdir(parents=True, exist_ok=True)
    runs = {c[0]: run_hop_case(work, c) for c in HOP_CASES}
    for r in runs.values():
        print(r["summary"], flush=True)
    phy = phy_Bps()
    ep_Bps = 64 * CLK
    wire = 2 * SERDES_STAGES

    def hop_row(r, vendor_ch, vendor_chu):
        f = r["fields"]
        total = f["last_flit"]
        fb = f["fb"]
        ser_ep = f["flits"] - 1                                  # measured: the endpoint takes one flit a cycle
        phy_ns = r["bytes"] / phy * 1e9
        phy_cyc = phy_ns * CLK * 1e-9
        binding = "phy" if phy_cyc > f["flits"] else "endpoint"
        # cut-through: the PHY serialisation overlaps the endpoint's; it adds only when it is the slower rate
        phy_extra = max(0, math.ceil(phy_cyc - f["flits"] - 1e-9)) if binding == "phy" else 0
        cycles = total + phy_extra + wire
        return dict(
            exact=r["exact"], payload_B=r["bytes"], flit_bytes=fb, payload_flits=f["flits"],
            link_rt_first_to_last_cycles=total, first_flit_cycles=f["first_flit"],
            board_leg_last_flit_cycles=f["leg1_last_flit"], board_leg_first_flit_cycles=f["leg1_first_flit"],
            vendor_channel_cycles=dict(board=vendor_ch, ucie_fanout=vendor_chu),
            measured_endpoint_cycles=total - vendor_ch - vendor_chu,
            endpoint_serialization_cycles=ser_ep, endpoint_rate_GBps=round(fb * CLK / 1e9, 1),
            in_ready_stalls=f["credit_stalls1"] + f["credit_stalls2"], sustained_1_flit_per_cycle=f["in_span"] == f["flits"] - 1,
            phy_lane_rate_GBps=round(phy / 1e9, 2), phy_serialization_ns=round(phy_ns, 2),
            phy_serialization_binding=binding == "phy", phy_serialization_extra_cycles=phy_extra,
            wire_stage_cycles=wire, total_cycles=cycles, us=round(cycles / CLK * 1e6, 4))
    hop = hop_row(runs["hop_lfec_fanout"], CH_LFEC, CH_UCIE)
    board = hop_row(runs["hop_lfec_board"], CH_LFEC, 0)
    kp4 = hop_row(runs["hop_kp4_fanout"], CH_KP4, CH_UCIE)
    lever = hop_row(runs["lever_fb160_lfec_fanout"], CH_LFEC, CH_UCIE)

    def ret_row(r, ch):
        f = r["fields"]
        per = f["first_flit"]
        cycles = RETURN_TRAVERSALS * per + wire
        return dict(exact=r["exact"], payload_B=RETURN_B, traversals=RETURN_TRAVERSALS,
                    per_traversal_cycles=per, measured_endpoint_cycles_per_traversal=per - ch,
                    vendor_channel_cycles_per_traversal=ch, wire_stage_cycles=wire, total_cycles=cycles,
                    us=round(cycles / CLK * 1e6, 4))
    ret = ret_row(runs["ret_lfec_flit"], CH_LFEC)
    ret_kp4 = ret_row(runs["ret_kp4_flit"], CH_KP4)
    out = dict(
        clock_hz=CLK, simulator=tool_version(["iverilog", "-V"]),
        convention="cycles from the first input handshake to the cycle the last flit is delivered (out_valid & "
                   "out_ready at the far end), idle link, out_ready = 1; first_flit: to the first out_valid",
        budgets=dict(
            light_fec_ns=LFEC_NS, light_fec_cycles=CH_LFEC, kp4_cable_ns=KP4_NS, kp4_cycles=CH_KP4,
            ucie_fanout_ns=UCIE_NS, ucie_fanout_cycles=CH_UCIE, serdes_wire_stages_per_end=SERDES_STAGES,
            phy_lanes_per_die_pair=T1_LANES, phy_lane_net_Bps=phy / T1_LANES,
            labels=dict(
                vendor="VENDOR BUDGET (not RTL): light-FEC PHY 130 ns (tools/sync_cost_table.py "
                       "on_module_light_fec_130ns: PHY Tx+Rx 20-60, RS(272,257) accumulate 25.6 + decode 25-50, PCS "
                       "3-5, flight 0.9, CDC 4, endpoint 5 ns; band 89-185) and the UCIe hop 10 ns "
                       "(technology.json rom_package_ucie) less its 1.5 ns on-die proxy; both carried as the "
                       "link_rt channel delay line ot_dsrom_link_chan",
                measured="RTL: ot_dsrom_link_rt TX stages + CRC + RX stages + receive FIFO + output register "
                         "+ the flit serialisation at 64 B/cycle, and the cut-through hand-off into the fan-out leg",
                wire="ROUTED-GEOMETRY WIRE STAGES (not simulated): 2 x 45 SerDes endpoint stages, "
                     "uarch_model.DIE_SHRUNK_INTERIM serdes_stages (W18b shrunk die at the SS 504 um/stage reach)")),
        hop=dict(headline_case="hop_lfec_fanout", **hop, per_hop_us=hop["us"]),
        hop_board_leg_only=board, hop_kp4_sensitivity=kp4, hop_lever_fb160=lever,
        token_return=dict(headline_case="ret_lfec_flit", **ret, token_return_us=ret["us"]),
        token_return_kp4_sensitivity=ret_kp4,
        runs=runs,
        sources={p: sha(ROOT / p) for p in HOP_RTL})
    (Path(a.work) / "hop.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(dict(per_hop_us=hop["us"], hop_cycles=hop["total_cycles"], token_return_us=ret["us"]),
                     indent=1))
    return out


# ------------------------------------------------------------------------------------------------- collectives
# (graph node, op, payload bytes): the S81 graph's collective payloads (tools/dsrom_1m_measure.s58_graph())
S81_COLL = [
    ("attn.a_allgather", "all_gather", 3648),
    ("attn.idx.topk_merge", "all_gather", 16384),
    ("attn.cand.merge", "all_gather", 65536),
    ("attn.rows_allgather", "all_gather", 67584),
    ("attn.out_allreduce", "all_reduce", 20480),
    ("ffn.router_allgather", "all_gather", 1536),
    ("ffn.combine_allreduce", "all_reduce", 20480),
    ("head.argmax_merge", "all_gather", 32),
]
# the bench issues 12 descriptors: the 8 above in layer order, then 4 repeats (op-position independence check)
S81_OPS = S81_COLL + [S81_COLL[3], S81_COLL[4], S81_COLL[0], S81_COLL[7]]
LANES, RANKS, MAXW, NOPS = 16, 4, 320, 12
WORD_B = 4 * LANES


def words_of(op, payload):
    return math.ceil(payload / WORD_B) if op == "all_reduce" else math.ceil(payload / RANKS / WORD_B)


def s81_fixture(outdir: Path, seed: int = 81) -> dict:
    """Operands and golden for the 12 S81 descriptors.  Reduces: FP32 partial sums over ~40 binades with exact and
    near cancellations, signed zeros and the pairwise-vs-linear cancellation case; result FP32 (rnd 0), golden
    ((r0 + r1) + (r2 + r3)) in hdc_golden.add (binary32 RNE, +0 canonical), the engine's fixed order.  Gathers:
    random bit patterns over the payload bytes of each rank (zero beyond them), rank-major result."""
    import hdc_golden as G
    outdir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    part = np.zeros((NOPS, RANKS, MAXW, LANES), np.uint32)
    exp = np.zeros((NOPS, RANKS * MAXW, LANES), np.uint32)
    desc = []
    for oi, (name, op, payload) in enumerate(S81_OPS):
        n = words_of(op, payload)
        assert 1 <= n <= MAXW, (name, n)
        if op == "all_reduce":
            E = payload // 4
            v = (np.exp2(rng.uniform(-20, 20, (RANKS, E))) * rng.choice([-1, 1], (RANKS, E))).astype(np.float32)
            c = rng.random(E) < 0.125
            v[1, c] = -v[0, c]                                                   # exact cancellation in (r0 + r1)
            c2 = rng.random(E) < 0.125
            v[3, c2] = (-v[2, c2] * (1 + rng.integers(-4, 5, c2.sum()) * 2.0 ** -23)).astype(np.float32)
            # rank x element: pairwise 0 vs linear 1 (1e10 absorption), exact zero sums, signed zeros, a tie
            v[:, :4] = np.array([[1e10, 1.0, -0.0, 2.0 ** 24], [1.0, -1.0, 0.0, 1.0],
                                 [-1e10, 2.0 ** -24, -0.0, 1.0], [1.0, 1.0, -0.0, 1.0]], np.float32)
            flat = np.zeros((RANKS, MAXW * LANES), np.uint32)
            flat[:, :E] = G.bits(v)
            part[oi] = flat.reshape(RANKS, MAXW, LANES)
            s = G.add(G.add(v[0], v[1]), G.add(v[2], v[3]))
            ef = np.zeros(MAXW * LANES, np.uint32)
            ef[:E] = G.bits(s)
            exp[oi, :MAXW] = ef.reshape(MAXW, LANES)
            desc.append((0 << 31) | (0 << 30) | (oi << 15) | n)
        else:
            per = payload // RANKS // 4                                         # 32-bit elements per rank
            for r in range(RANKS):
                flat = np.zeros(n * LANES, np.uint32)
                flat[:per] = rng.integers(0, 2 ** 32, per, dtype=np.uint64).astype(np.uint32)
                part[oi, r, :n] = flat.reshape(n, LANES)
                exp[oi, r * n:(r + 1) * n] = part[oi, r, :n]
            desc.append((1 << 31) | (oi << 15) | n)

    def wr(path, arr):
        with path.open("w") as f:
            for lanes in arr.reshape(-1, LANES):
                f.write("".join(f"{int(x):08x}" for x in lanes[::-1]) + "\n")
    wr(outdir / "part.hex", part)
    wr(outdir / "expected.hex", exp)
    (outdir / "desc.hex").write_text("".join(f"{x:08x}\n" for x in desc))
    meta = dict(schema="dsrom_s81_collective_fixture_v1", seed=seed, lanes=LANES, word_bytes=WORD_B,
                ops=[dict(op_index=i, node=nm, op=op, payload_B=p, words_per_rank=words_of(op, p))
                     for i, (nm, op, p) in enumerate(S81_OPS)],
                reference="all_reduce: hdc_golden.add((r0 + r1), (r2 + r3)), FP32 result (rnd 0); all_gather: "
                          "rank-major copy",
                images_sha256={p: sha(outdir / p) for p in ("part.hex", "expected.hex", "desc.hex")},
                golden_sha256=sha(ROOT / "tools/hdc_golden.py"))
    (outdir / "manifest.json").write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n")
    return meta


# S81 configurations of tb_w15b_v41_tp4.  The model's config is v41p17_r0d1024 (RELAY 0, DEPTH 1024, 17 wire stages
# each side, T_CORE 0.92, ADD_LAT 3 adder) plus 2 x (coll_stages 45 - 17) stages in uarch_model._cons_adjust.
COLL_CONFIGS = {
    # HEADLINE: the S81 die: U_WIRE = DIE_SHRUNK_INTERIM ucie_stages 34 (collective -> UCIe), X_WIRE = serdes_stages
    # = coll_stages 45 (collective -> SerDes); the LAT-7 adder tree (ot_hdc_fp32_add_lat) that the 1.2 GHz SS
    # configs of w15_collectives (v41ss_*) use, since the LAT-3 pipe does not close at 0.833 ns
    "s81_r0d1024": ("tb_w15b_v41_tp4", dict(RELAY=0, DEPTH=1024, U_WIRE=34, X_WIRE=45, T_CORE=T_CORE_NS,
                                            FPLAT=1, ADD_LAT=7), "s81"),
    # re-clock only: the model's config verbatim at 0.8333 ns (17/17 wires, LAT-3 adder) -- separates the clock
    # from the die's wire stages
    "s81rc_r0d1024": ("tb_w15b_v41_tp4", dict(RELAY=0, DEPTH=1024, U_WIRE=17, X_WIRE=17, T_CORE=T_CORE_NS), "s81"),
}


def cmd_coll(a):
    work = Path(a.work)
    os.environ["W15_BUILD"] = str(work / "w15b")
    os.environ["W15_VEC"] = str(work / "w15v")
    import w15_collectives as W
    W.BUILD, W.VEC = Path(os.environ["W15_BUILD"]), Path(os.environ["W15_VEC"])
    W.CONFIGS.update(COLL_CONFIGS)
    W.BUILD.mkdir(parents=True, exist_ok=True)       # verilator -Mdir creates only the last path level
    meta = s81_fixture(W.VEC / "s81")
    out = dict(simulator=W.verilator_version(), verilator_flags=W.VFLAGS, fixture=meta, configs={})
    names = a.configs.split(",") if a.configs else list(COLL_CONFIGS)
    for name in names:
        t0 = time.time()
        c = W.campaign_config(name, a.ncal, a.nmeas, a.jobs)
        rec = W.config_record(c)
        rec["wall_s"] = round(time.time() - t0, 1)
        meas = c["measured"]
        rec["all_runs_passed"] = all(r["passed"] for r in c["calibration"] + meas)
        rec["vm_hash_distinct_all_runs"] = len({r["vm_sha256"] for r in c["calibration"] + meas})
        per = {}
        for row in rec["collectives"]:
            nm, op, p = S81_OPS[row["op"]]
            assert row["mode"] == op and row["words_per_rank"] == words_of(op, p), (row, nm)
            per.setdefault(nm, []).append(row)
        rec["by_collective"] = {
            nm: dict(op=op, payload_B=p, words_per_rank=words_of(op, p),
                     cycles=max(r["issue_to_last_commit_cycles"] for r in per[nm]),
                     cycles_each_issue=[r["issue_to_last_commit_cycles"] for r in per[nm]],
                     per_die_cycles=per[nm][0]["per_die_issue_to_last_commit"],
                     us=round(max(r["issue_to_last_commit_cycles"] for r in per[nm]) * T_CORE_NS / 1e3, 4),
                     free_running_cycles=[min(rec["free_running_latency_range"][r["op"]][0] for r in per[nm]),
                                          max(rec["free_running_latency_range"][r["op"]][1] for r in per[nm])],
                     exact=rec["all_runs_passed"])
            for nm, op, p in S81_COLL}
        out["configs"][name] = rec
        (work / "coll.json").write_text(json.dumps(out, indent=1, default=str) + "\n")
        print(name, json.dumps({k: (v["cycles"], v["us"]) for k, v in rec["by_collective"].items()}),
              "passed", rec["all_runs_passed"], flush=True)
    out["sources"] = {p: sha(ROOT / p) for p in sorted(set(W.TB_SRC["tb_w15b_v41_tp4"]) |
                                                      {"tools/w15_collectives.py", "tools/hdc_golden.py"})}
    (work / "coll.json").write_text(json.dumps(out, indent=1, default=str) + "\n")
    return out


# ------------------------------------------------------------------------------------------------------ model
def model_terms():
    """The S58 graph's priced link nodes (us, issue + depth + ctrl) at the S81 baseline settings."""
    import dsrom_1m_measure as M
    g, T, _ = M.s58_graph()
    tot = lambda n: (g.nodes[n]["issue"] + g.nodes[n]["depth"] + g.nodes[n]["ctrl"]) * 1e6
    out = dict(T_us=T * 1e6, hop_us_extra_S81=M.HOP_US, extra_hops=M.S81_EXTRA_HOPS)
    hops = [n for n in g.nodes if g.nodes[n]["kind"] == "hop" and g.nodes[n]["hop_kind"] != "return"]
    out["graph_hops"] = len(hops)
    out["hop_node_us"] = {n: round(tot(n), 4) for n in ("L0.substage_hop0", "head.hop")}
    out["hop_link"] = g.nodes["head.hop"].get("_hub_edge_link")
    out["token_return_us"] = round(tot("token.return"), 4)
    reps = {"attn.a_allgather": "L0.attn.a_allgather", "attn.rows_allgather": "L0.attn.rows_allgather",
            "attn.out_allreduce": "L0.attn.out_allreduce", "ffn.router_allgather": "L0.ffn.router_allgather",
            "ffn.combine_allreduce": "L0.ffn.combine_allreduce", "attn.idx.topk_merge": "L2.attn.idx.topk_merge",
            "attn.cand.merge": "L20.attn.cand.merge", "head.argmax_merge": "head.argmax_merge"}
    out["collective_node_us"] = {k: dict(node=v, us=round(tot(v), 4), payload_B=g.nodes[v]["payload"],
                                         op=g.nodes[v]["op"]) for k, v in reps.items()}
    out["collective_counts"] = {k: sum(1 for n in g.nodes if n.endswith("." + k) or n == k) for k in reps}
    return out


def cmd_record(a):
    work = Path(a.work)
    hop = json.loads((work / "hop.json").read_text())
    coll = json.loads((work / "coll.json").read_text())
    model = model_terms()
    head = coll["configs"].get("s81_r0d1024")
    collectives = {}
    if head:
        for nm, r in head["by_collective"].items():
            mt = model["collective_node_us"][nm]
            collectives[nm] = dict(op=r["op"], payload_B=r["payload_B"], words_per_rank=r["words_per_rank"],
                                   cycles=r["cycles"], us=r["us"], exact=r["exact"],
                                   cycles_each_issue=r["cycles_each_issue"], free_running_cycles=r["free_running_cycles"],
                                   model_us=mt["us"],
                                   reclock_only_cycles=coll["configs"].get("s81rc_r0d1024", {}).get(
                                       "by_collective", {}).get(nm, {}).get("cycles"))
    exact_all = all(r["exact"] for r in hop["runs"].values()) and all(
        c.get("all_runs_passed") for c in coll["configs"].values())
    rec = dict(
        schema="opentallas.dsrom-1m.links.v1",
        generated_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        scope="DS-ROM S81 (TP4 = 2 packages x 2 dies, 1.2 GHz, 81 stage hops): the stage hop, the token return and "
              "the TP4 collectives measured in RTL at the S81 payloads and clock; replaces the modelled link terms "
              "of tools/dsrom_1m_measure.py compose",
        status="pass" if exact_all else "FAIL",
        clock_hz=CLK, t_core_ns=T_CORE_NS,
        hop=dict(
            measured_endpoint_cycles=hop["hop"]["measured_endpoint_cycles"],
            link_rt_first_to_last_cycles=hop["hop"]["link_rt_first_to_last_cycles"],
            first_flit_cycles=hop["hop"]["first_flit_cycles"], payload_flits=hop["hop"]["payload_flits"],
            payload_B=RESIDUAL_B,
            vendor_phy_ns=dict(board_light_fec=LFEC_NS, ucie_fanout=UCIE_NS,
                               cycles=hop["hop"]["vendor_channel_cycles"]),
            phy_serialization_ns=hop["hop"]["phy_serialization_ns"],
            phy_serialization_binding=hop["hop"]["phy_serialization_binding"],
            endpoint_rate_GBps=hop["hop"]["endpoint_rate_GBps"], phy_lane_rate_GBps=hop["hop"]["phy_lane_rate_GBps"],
            wire_stage_cycles=hop["hop"]["wire_stage_cycles"], total_cycles=hop["hop"]["total_cycles"],
            per_hop_us=hop["hop"]["per_hop_us"], exact=hop["hop"]["exact"],
            split_us=dict(measured_rtl=round(hop["hop"]["measured_endpoint_cycles"] / CLK * 1e6, 4),
                          vendor_phy=round(sum(hop["hop"]["vendor_channel_cycles"].values()) / CLK * 1e6, 4),
                          wire_stages=round(hop["hop"]["wire_stage_cycles"] / CLK * 1e6, 4)),
            token_return_us=hop["token_return"]["token_return_us"],
            token_return=hop["token_return"],
            model=dict(graph_hop_node_us=model["hop_node_us"], graph_hop_link=model["hop_link"],
                       extra_S81_hop_us=model["hop_us_extra_S81"], token_return_us=model["token_return_us"]),
            board_leg_only=hop["hop_board_leg_only"], kp4_sensitivity=hop["hop_kp4_sensitivity"],
            token_return_kp4_sensitivity=hop["token_return_kp4_sensitivity"], lever_fb160=hop["hop_lever_fb160"],
            labels=hop["budgets"]["labels"], budgets=hop["budgets"], convention=hop["convention"],
            simulator=hop["simulator"], runs=hop["runs"]),
        collectives=collectives,
        collective_detail=dict(
            headline_config="s81_r0d1024", convention="issue -> last VM commit on the slowest die, deterministic "
            "release (det=1), max over repeated issues; us at T_CORE 0.8333 ns",
            model_basis="uarch_model: W15 v41p17_r0d1024_sweep linear fit at 0.92 ns + 2 x (45 - 17) S81 wire stages "
                        "at 0.833 ns + VMC_FUSED coll_write 13 cycles at 0.9 GHz + ctrl; the bench's behavioural VM "
                        "is always ready, so the VM lane-group write (13 slow cycles = 14.4 ns) is NOT in the "
                        "measured cycles and stays modelled",
            graph_instances=model["collective_counts"],
            configs={k: {kk: vv for kk, vv in v.items() if kk not in ("collectives",)}
                     for k, v in coll["configs"].items()},
            fixture=coll["fixture"], simulator=coll["simulator"], verilator_flags=coll["verilator_flags"]),
        model_reference=model,
        sources={**hop["sources"], **coll.get("sources", {}),
                 **{p: sha(ROOT / p) for p in ("tools/dsrom_1m_links.py", "tools/dsrom_1m_measure.py",
                                                   "tools/uarch_model.py", "tools/decode_critical_path.py",
                                                   "tools/sync_cost_table.py",
                                                   "tools/rtl_v41_stage_collective_campaign.py",
                                                   "tools/dsrom_s82_token_pricing.py",
                                                   "results/rtl/w15_collectives.json",
                                                   "results/rtl/dsrom_system_rtl_20261003/link_rt_bench.json")}},
        simulator=dict(hop=hop["simulator"], collectives=coll["simulator"]),
        command="python3 tools/dsrom_1m_links.py " + " ".join(sys.argv[1:]))
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rec, indent=1, default=str) + "\n")
    print("status", rec["status"], "->", out)
    return rec


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("cmd", choices=("hop", "coll", "record", "all"))
    ap.add_argument("--work", default=os.environ.get("DSROM_LINKS_WORK", "/tmp/claude-1000/dsrom_1m_links"))
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--configs", default="")
    ap.add_argument("--ncal", type=int, default=24)
    ap.add_argument("--nmeas", type=int, default=12)
    ap.add_argument("--jobs", type=int, default=16)
    a = ap.parse_args()
    Path(a.work).mkdir(parents=True, exist_ok=True)
    if a.cmd in ("hop", "all"):
        cmd_hop(a)
    if a.cmd in ("coll", "all"):
        cmd_coll(a)
    if a.cmd in ("record", "all"):
        cmd_record(a)


if __name__ == "__main__":
    main()
