#!/usr/bin/env python3
"""Gate C7 / O2 levers: what realistic microarchitecture recovers of the measured collective exposure (Verilator).

The O2 bench (tools/rtl_v41_stage_collective_campaign.py, results/rtl/v41_stage_collective_campaign.json) measured
the exposed tail after the producer's last output on the real one-shot engine.  This campaign runs the SAME producer
schedules, output queues, links (latency, byte rate, credits) and bit-for-bit checks with the changes below, each
case against its own golden (tools/hdc_golden.fold for an all-reduce, the senders' words for an all-gather, every
residual word for the hop).  No link gets bandwidth, no package changes:

  relay      rtl/rom/ot_rom_oneshot_px.sv RELAY=1: the one-shot sends every word to BOTH dies of the partner package,
             so each T1 link (13 lanes per die pair) carries the whole partial; with the receive-side relay each T1
             link carries the words of one index parity and the receiving die forwards them to its package peer over
             UCIe the cycle they land (same rank-order fold, same bits);
  add3       ADD_LAT=3: ot_hdc_fp32_add_fast (the spec's 3-cycle binary32 add) in the fold instead of the 5-stage pipe;
  gw         the all-gather emits GW words per cycle with no bubble between indices (the one-shot emits one word per
             cycle and waits a cycle per index: 5 cycles per 4 words, engine-bound for the 53.8 KB KV rows);
  hop        rtl/test/tb_v41_stage_hop_px.sv on the PHYSICAL stage lanes (docs/ARCH_V41_RACK.md 2: 7 lanes per die,
             same-position package): per-die halves + UCIe swap (full payload per package), and the split in which
             u words ride one package's cables only and cross to the other package over T1.

The rank-order fold chasing arrivals stage by stage (p0 + p1 before p2 lands) is not built: on the critical die of
a package pair (ranks 2 and 3, whose LAST-arriving partials are p0 and p1) all N - 1 adds still follow the last
arrival, so it moves no critical-path cycle (summary.fold_chase).

    python3 tools/rtl_v41_collective_levers_campaign.py --scratch <dir> [--out results/rtl/v41_collective_levers_campaign.json] [--clean]

Run through remote_gate from a pinned clean worktree.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import hashlib
import json
import math
import shutil
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden as G  # noqa: E402
import rtl_v41_stage_collective_campaign as B  # noqa: E402

OUT = ROOT / "results/rtl/v41_collective_levers_campaign.json"
BASE_REC = ROOT / "results/rtl/v41_stage_collective_campaign.json"
FAST = ROOT / "rtl/hdc/ot_hdc_fastfp.sv"
ENGINE = ROOT / "rtl/rom/ot_rom_oneshot_px.sv"
TB = ROOT / "rtl/test/tb_v41_stage_collective_px.sv"
TB_HOP = ROOT / "rtl/test/tb_v41_stage_hop_px.sv"
N, MAXW, LANES, WORD_B, CLOCK = B.N, B.MAXW, B.LANES, B.WORD_B, B.CLOCK
HOP_WORDS = 81                                  # 40,976 B residual in 512-B words
LANE_BPC = B.LANE_NET_BPS / CLOCK               # one 112G lane, bytes per cycle


def sources():
    return [B.ADDER, FAST, ENGINE, TB, TB_HOP]


def source_sha256():
    """SHA-256 of every source the result depends on: the RTL and benches, this driver, the O2 driver it imports
    (patterns, schedules, link parameters) and the golden (tools/audit_source_currency_drift.py re-hashes them)."""
    pins = sources() + [Path(__file__).resolve(), Path(B.__file__).resolve(), ROOT / "tools/hdc_golden.py"]
    return {str(q.relative_to(ROOT)): hashlib.sha256(q.read_bytes()).hexdigest() for q in pins}


def build(scratch: Path, top: str, params: dict) -> Path:
    tag = top + "_" + "_".join(f"{k}{v}" for k, v in sorted(params.items()))
    obj = scratch / f"obj_{tag}"
    exe = obj / f"V{top}"
    if exe.exists():
        return exe
    obj.mkdir(parents=True, exist_ok=True)
    h = obj / "harness.cpp"
    h.write_text(f'#include "V{top}.h"\n#include "verilated.h"\n'
                 "int main(int argc, char** argv) { Verilated::commandArgs(argc, argv);\n"
                 f"  auto* t = new V{top}; t->clk = 0;\n"
                 "  while (!Verilated::gotFinish()) { t->clk = !t->clk; t->eval(); }\n"
                 "  t->final(); delete t; return 0; }\n")
    B.sh(["verilator", "--cc", "--exe", "--build", "-O2", "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNUSED", "-Wno-BLKSEQ",
          "-Wno-MULTIDRIVEN", "-Wno-MULTITOP", "--top-module", top, *[f"-G{k}={v}" for k, v in params.items()],
          "-Mdir", str(obj), *map(str, sources()), str(h), "-CFLAGS", "-O1", "-j", "4"])
    # keep the executable, drop the objects (disk)
    for f in obj.iterdir():
        if f.name != exe.name:
            (shutil.rmtree if f.is_dir() else Path.unlink)(f)
    return exe


# -- cases -------------------------------------------------------------------------------------------------------------
LEVERS = {   # name: (RELAY, ADD_LAT, GW)
    "base_nobubble": (0, 5, 1), "add3": (0, 3, 1), "relay": (1, 5, 1), "relay_add3": (1, 3, 1),
    "gw2": (0, 5, 2), "gw4": (0, 5, 4), "relay_gw1": (1, 5, 1), "relay_gw2": (1, 5, 2), "relay_gw4": (1, 5, 4),
}
# ot_hdc_fp32_add_fast elaborates to ~100 MB per instance in Verilator 4.038 (its Kogge-Stone loops), 40+ GB for the
# 1,536 adders of 4 dies x 3 stages x 128 lanes.  The engine moves one word per cycle whatever its width, so the
# ADD_LAT = 3 cases carry ADD3_LANES data lanes per word while every link still charges the full 512-B word
# (FLIT_OVH pads the record's link cost): the same cycle schedule, bit-exact on the lanes carried.  The
# relay_l8_control case runs the 128-lane relay case at 8 lanes to show the tails agree.
ADD3_LANES = 8


def data_lanes(case):
    if case["pattern"] == "stage_hop":
        return LANES
    return case.get("lanes", ADD3_LANES if LEVERS[case["lever"]][1] == 3 else LANES)


def cases():
    out = []
    for pat in ("allreduce_wo_b", "allreduce_down"):
        for lv in ("base_nobubble", "add3", "relay", "relay_add3"):
            out.append(dict(name=f"{pat}_{lv}_d64_q64", pattern=pat, lever=lv, depth=64, qtx=64))
        for depth in (16, 32, 128):
            out.append(dict(name=f"{pat}_relay_add3_d{depth}_q64", pattern=pat, lever="relay_add3", depth=depth,
                            qtx=64))
        for q in (8, 16, 32):
            out.append(dict(name=f"{pat}_relay_add3_d64_q{q}", pattern=pat, lever="relay_add3", depth=64, qtx=q))
    out.append(dict(name="allreduce_wo_b_relay_l8_control_d64_q64", pattern="allreduce_wo_b", lever="relay",
                    depth=64, qtx=64, lanes=ADD3_LANES))
    for order in ("blocked", "uniform"):
        out.append(dict(name=f"allreduce_wo_b_relay_add3_{order}_d64_q64", pattern="allreduce_wo_b",
                        lever="relay_add3", depth=64, qtx=64, order=order))
    out.append(dict(name="allreduce_wo_b_relay_add3_skew5_d64_q64", pattern="allreduce_wo_b", lever="relay_add3",
                    depth=64, qtx=64, skew=5))
    out.append(dict(name="allreduce_wo_b_relay_add3_ovh32_d64_q64", pattern="allreduce_wo_b", lever="relay_add3",
                    depth=64, qtx=64, ovh=32))
    for pat in ("gather_router", "gather_topk"):
        for lv in ("base_nobubble", "gw4", "relay_gw1", "relay_gw4"):
            out.append(dict(name=f"{pat}_{lv}_d16_q16", pattern=pat, lever=lv, depth=16, qtx=16))
    for lv in ("base_nobubble", "gw2", "gw4", "relay_gw1", "relay_gw2", "relay_gw4"):
        out.append(dict(name=f"gather_rows_{lv}_d128_q128", pattern="gather_rows", lever=lv, depth=128, qtx=128))
    for depth in (32, 64, 256):
        out.append(dict(name=f"gather_rows_relay_gw4_d{depth}_q128", pattern="gather_rows", lever="relay_gw4",
                        depth=depth, qtx=128))
    out.append(dict(name="gather_rows_relay_gw4_d128_q32", pattern="gather_rows", lever="relay_gw4", depth=128,
                    qtx=32))
    # stage hop on the physical lanes
    out.append(dict(name="hop_onedie14_full", pattern="stage_hop", scheme="onedie", u=0, lanes=14))
    out.append(dict(name="hop_perdie7_full", pattern="stage_hop", scheme="perdie", u=0, lanes=7))
    for u in (8, 12, 14, 16, 18, 20, 24, 40):
        out.append(dict(name=f"hop_perdie7_split{u}", pattern="stage_hop", scheme="perdie", u=u, lanes=7))
    for depth in (32, 64):
        out.append(dict(name=f"hop_perdie7_split16_d{depth}", pattern="stage_hop", scheme="perdie", u=16, lanes=7,
                        depth=depth))
    return out


def hop_lists(scheme, u, W=HOP_WORDS):
    """Per sender die (A0, A1, B0, B1): word indices in send order; per word: carried by one package only."""
    uniq = [1 if k < 2 * u else 0 for k in range(W)]
    pk = {0: list(range(0, u)) + list(range(2 * u, W)), 1: list(range(u, 2 * u)) + list(range(2 * u, W))}
    lists = []
    for p in (0, 1):
        if scheme == "onedie":
            lists += [pk[p], []]
        else:
            lists += [pk[p][0::2], pk[p][1::2]]
    return lists, uniq


def top_params(case, lp):
    if case["pattern"] == "stage_hop":
        num = int(round(case["lanes"] * LANE_BPC * 100))
        return "tb_v41_stage_hop_px", dict(
            LANES=LANES, DEPTH=case.get("depth", 128), DEPTH_F=64, QTX=128, LAT_C=lp["LAT_C"], BPC_C=num,
            BPC_C_DEN=100, LAT_X=lp["LAT_X"], BPC_X=lp["BPC_X"], BPC_X_DEN=100, LAT_U=lp["LAT_U"], BPC_U=lp["BPC_U"])
    relay, add, gw = LEVERS[case["lever"]]
    return "tb_v41_stage_collective_px", dict(
        LANES=data_lanes(case), DEPTH=case["depth"], QTX=case["qtx"], PKG_DIES=2, RELAY=relay, ADD_LAT=add, GW=gw,
        LAT_U=lp["LAT_U"], BPC_U=lp["BPC_U"], LAT_X=lp["LAT_X"], BPC_X=lp["BPC_X"], BPC_X_DEN=100,
        FLIT_OVH=WORD_B - 4 * data_lanes(case) + case.get("ovh", 0))


def hop_vectors(path: Path, sched, lists, uniq, seed):
    rng = np.random.default_rng(seed)
    part = B.rand_f32(rng, HOP_WORDS * LANES).reshape(HOP_WORDS, LANES)
    path.mkdir(parents=True, exist_ok=True)
    (path / "part.hex").write_text("\n".join(B.hexw(part[k]) for k in range(HOP_WORDS)) + "\n")
    (path / "ready.hex").write_text("\n".join(f"{sched[k]:08x}" for k in range(HOP_WORDS)) + "\n")
    ll = []
    for d, lst in enumerate(lists):
        ll.append(f"@{d * MAXW:x}")
        ll += [f"{w:08x}" for w in lst]
    (path / "list.hex").write_text("\n".join(ll) + "\n")
    (path / "uniq.hex").write_text("\n".join(str(x) for x in uniq) + "\n")


def coll_vectors(path: Path, words, sched, mode, seed, lanes):
    """B.vectors at `lanes` data lanes per word (every die on the same producer schedule)."""
    rng = np.random.default_rng(seed)
    part = B.rand_f32(rng, N * words * lanes).reshape(N, words, lanes)
    path.mkdir(parents=True, exist_ok=True)
    pl, rl = [], []
    for d in range(N):
        pl.append(f"@{d * MAXW:x}")
        rl.append(f"@{d * MAXW:x}")
        pl += [B.hexw(part[d, k]) for k in range(words)]
        rl += [f"{sched[k]:08x}" for k in range(words)]
    if mode == 0:
        sums = G.bits(G.fold([G.from_bits(part[d]) for d in range(N)]))
        el = [B.hexw(sums[k]) for k in range(words)]
    else:
        el = ["0" * (lanes * 8)]
    (path / "part.hex").write_text("\n".join(pl) + "\n")
    (path / "ready.hex").write_text("\n".join(rl) + "\n")
    (path / "exp.hex").write_text("\n".join(el) + "\n")


def run_case(scratch: Path, case: dict, lp: dict) -> dict:
    p = B.PATTERNS[case["pattern"]]
    hop = case["pattern"] == "stage_hop"
    words = HOP_WORDS if hop else p["words"]
    sch = B.schedule(dict(p, words=words), case.get("order"))
    vec = scratch / f"vec_{case['name']}"
    exe = build(scratch, *top_params(case, lp))
    start = 20
    args = [str(exe), f"+VEC={vec}", f"+WORDS={words}", f"+START={start}", "+TIMEOUT=60000"]
    if hop:
        lists, uniq = hop_lists(case["scheme"], case["u"])
        hop_vectors(vec, sch, lists, uniq, 101 + len(case["name"]))
        args += [f"+LN{d}={len(lst)}" for d, lst in enumerate(lists)]
    else:
        coll_vectors(vec, words, sch, p["mode"], 11 + len(case["name"]), data_lanes(case))
        args += [f"+MODE={p['mode']}", f"+SKEW={case.get('skew', 0)}"]
    txt = B.sh(args, timeout=3600)
    shutil.rmtree(vec, ignore_errors=True)
    arr = [tuple(map(int, m.groups())) for m in B.ARR.finditer(txt)]
    sbs = {int(m.group(1)): dict(zip(("start", "ref", "pushed_last", "stall", "hold", "qmax", "first", "last",
                                      "fault", "code"), map(int, m.groups()[1:]))) for m in B.SB.finditer(txt)}
    dn = B.DONE.search(txt)
    if not dn:
        raise RuntimeError(f"{case['name']}: no result\n{txt[-2000:]}")
    prod = [sbs[d] for d in sbs if sbs[d]["pushed_last"] >= 0]
    ref = max(x["ref"] for x in prod)
    pushed = max(x["pushed_last"] for x in prod)
    recv = sorted({a[0] for a in arr})
    last = max(a[2] for a in arr)
    first = min(a[2] for a in arr)
    per_die_last = {d: max(a[2] for a in arr if a[0] == d) for d in recv}
    per_die_first = {d: min(a[2] for a in arr if a[0] == d) for d in recv}
    needs_all = case["pattern"] in ("gather_router", "gather_topk")
    first_useful = max(per_die_last.values()) if needs_all else max(per_die_first.values())
    rec = dict(case=case["name"], pattern=case["pattern"], lever=case.get("lever", case.get("scheme")),
               node=p["node"], words_per_die=words, bytes_per_die=words * WORD_B,
               order=case.get("order", p["order"]), skew_cycles=case.get("skew", 0),
               flit_overhead_bytes=case.get("ovh", 0))
    if hop:
        rec.update(scheme=case["scheme"], lanes_per_cable=case["lanes"], one_package_words=case["u"],
                   cable_words_per_die=[len(x) for x in lists], rx_depth_words=case.get("depth", 128),
                   forward_credits=64, tx_queue_words=128,
                   t1_words_per_link=case["u"] // 2 + (case["u"] % 2),
                   receive_buffer_max=max(sbs[d]["qmax"] for d in range(4)))
    else:
        relay, add, gw = LEVERS[case["lever"]]
        rec.update(relay=relay, add_lat=add, gather_words_per_cycle=gw, data_lanes=data_lanes(case),
                   link_bytes_per_word=WORD_B + case.get("ovh", 0), rx_depth_words=case["depth"],
                   tx_queue_words=case["qtx"])
    rec.update(producer_first_word_cycle=start + min(sch), producer_ref_last_cycle=ref,
               producer_actual_last_cycle=pushed, producer_stall_cycles=max(x["stall"] for x in prod),
               producer_queue_max=max(x["qmax"] for x in prod),
               consumer_first_word_cycle=first, consumer_last_word_cycle=last,
               consumer_first_useful_cycle=first_useful,
               exposed_first_useful_cycles=first_useful - ref,
               exposed_tail_cycles=last - ref, exposed_tail_ns=(last - ref) / CLOCK * 1e9,
               per_die_tail_cycles={str(d): per_die_last[d] - ref for d in recv},
               producer_delay_cycles=pushed - ref, model_exposed_cycles=p["model_exposed"],
               mismatches=int(dn.group(2)), out_err=int(dn.group(3)), timeout=int(dn.group(4)),
               faults=[sbs[d]["fault"] for d in sorted(sbs)], passed=dn.group(5) == "PASS")
    return rec


# -- queue and area cost -------------------------------------------------------------------------------------------------
BITCELL_UM2 = 0.021          # configs/hardware/technology.json nodes.N5.sram_hd_bitcell_um2 (the analytical envelope)
RF_OVERHEAD = 2.5            # 1R1W register-file macro area per bit / HD 6T bitcell (ASSUMPTION: periphery + 8T cell)
FLOP_UM2 = 0.5               # N5-class scan flop incl. local routing (ASSUMPTION)
DIE_MM2 = 815.0              # docs/ARCH_V41_RACK.md 3: 815 mm2 dies


def queue_cost(depth, qtx, add_lat, gw, relay, lanes=LANES):
    fw = 32 * lanes
    pw = fw + (3 if relay is not None else 2) + 32
    rx_bits = N * depth * pw                             # N source FIFOs (the local one included), DEPTH words each
    tx_bits = qtx * fw
    heads = N * fw                                       # popped words (both engines)
    delay = sum((g - 1) * add_lat for g in range(2, N)) * fw
    gout = gw * fw
    sram_bits = rx_bits + tx_bits
    flop_bits = heads + delay + gout
    mm2 = sram_bits * BITCELL_UM2 * RF_OVERHEAD * 1e-6 + flop_bits * FLOP_UM2 * 1e-6
    return dict(rx_fifo_bits=rx_bits, tx_queue_bits=tx_bits, sram_KiB=sram_bits / 8 / 1024,
                head_flops=heads, delay_line_flops=delay, gather_out_flops=gout, flop_bits=flop_bits,
                area_mm2=round(mm2, 4), die_fraction=mm2 / DIE_MM2)


def summarise(rec, base):
    by = {c["case"]: c for c in rec["cases"]}
    bp = base["summary"]["patterns"]
    out = {}
    std = [c for c in rec["cases"] if "control" not in c["case"] and c.get("order") == B.PATTERNS[c["pattern"]]["order"] and not c["skew_cycles"]
           and not c["flit_overhead_bytes"]]
    for pat in ("allreduce_wo_b", "allreduce_down", "gather_router", "gather_topk", "gather_rows", "stage_hop"):
        rows = [c for c in std if c["pattern"] == pat]
        if not rows:
            continue
        lv = {}
        for c in rows:
            key = c["lever"] if pat != "stage_hop" else c["case"]
            best = lv.get(key)
            if best is None or (c["exposed_tail_cycles"], c.get("rx_depth_words", 0), c.get("tx_queue_words", 0)) < \
                    (best["exposed_tail_cycles"], best.get("rx_depth_words", 0), best.get("tx_queue_words", 0)):
                lv[key] = c
        levers = {k: dict(case=c["case"], exposed_tail_cycles=c["exposed_tail_cycles"],
                          exposed_first_useful_cycles=c["exposed_first_useful_cycles"],
                          producer_stall_cycles=c["producer_stall_cycles"],
                          per_die_tail_cycles=c["per_die_tail_cycles"])
                  for k, c in sorted(lv.items(), key=lambda kv: kv[1]["exposed_tail_cycles"])}
        before = bp[pat]["measured_exposed_tail_cycles"]
        best_key = min(levers, key=lambda k: levers[k]["exposed_tail_cycles"])
        entry = dict(before_tail_cycles=before, before_first_useful_cycles=None,
                     model_exposed_cycles=B.PATTERNS[pat]["model_exposed"], levers=levers, best_lever=best_key,
                     best_tail_cycles=levers[best_key]["exposed_tail_cycles"],
                     recovered_cycles=before - levers[best_key]["exposed_tail_cycles"])
        bc = [c for c in base["cases"] if c["case"] == bp[pat].get("best_case")]
        if bc:
            entry["before_first_useful_cycles"] = bc[0]["exposed_first_useful_cycles"]
        if pat != "stage_hop":
            best = lv[best_key]
            sweep = sorted((c for c in rows if c["lever"] == best_key), key=lambda c: (c["rx_depth_words"],
                                                                                       c["tx_queue_words"]))
            ok = [c for c in sweep if c["exposed_tail_cycles"] <= best["exposed_tail_cycles"]]
            ok_ns = [c for c in ok if c["producer_stall_cycles"] == 0]
            entry["depth_sweep"] = {f"d{c['rx_depth_words']}_q{c['tx_queue_words']}":
                                    dict(tail=c["exposed_tail_cycles"], stall=c["producer_stall_cycles"])
                                    for c in sweep}
            entry["min_rx_depth_words"] = min(c["rx_depth_words"] for c in ok)
            entry["min_tx_queue_words"] = min((c["tx_queue_words"] for c in ok_ns), default=None)
            relay, add, gw = LEVERS[best_key]
            entry["queue_cost_per_die"] = queue_cost(entry["min_rx_depth_words"], entry["min_tx_queue_words"] or
                                                     best["tx_queue_words"], add, gw, relay)
            b0 = [c for c in base["cases"] if c["case"] == bp[pat].get("best_case")]
            if b0:
                entry["queue_cost_per_die_before"] = queue_cost(bp[pat]["min_rx_depth_for_best_tail"],
                                                                bp[pat]["min_tx_queue_without_producer_stall"] or
                                                                b0[0]["tx_queue_words"], 5, 1, None)
        else:
            entry["t1_words_per_link"] = lv[best_key]["t1_words_per_link"]
            entry["receive_buffer_words"] = lv[best_key]["rx_depth_words"]
        out[pat] = entry
    # the fold chasing arrivals: with the relay, the critical die of the pair is rank 2 or 3, whose last partials
    # (p0, p1) come from the other package; N - 1 adds follow them either way
    fold = dict(critical_ranks=[2, 3], adds_after_last_arrival_all_at_once=N - 1,
                adds_after_last_arrival_chased=N - 1, cycles_saved=0,
                note="ranks 0 and 1 would save one add (their last partials are p2, p3), but the collective ends "
                     "when its slowest die ends")
    return dict(all_pass=all(c["passed"] for c in rec["cases"]),
                bit_exact=all(c["mismatches"] == 0 for c in rec["cases"]), patterns=out, fold_chase=fold)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scratch", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--jobs", type=int, default=1, help="parallel Verilator builds (a 128-lane build is ~3 GB)")
    ap.add_argument("--only", default="")
    ap.add_argument("--clean", action="store_true")
    a = ap.parse_args()
    a.scratch = a.scratch.resolve()
    a.scratch.mkdir(parents=True, exist_ok=True)
    lp = B.link_params()
    cs = [c for c in cases() if a.only in c["name"]]
    tops = {}
    for c in cs:
        t, prm = top_params(c, lp)
        tops[(t, tuple(sorted(prm.items())))] = (t, prm)
    with cf.ThreadPoolExecutor(a.jobs) as ex:
        list(ex.map(lambda tp: build(a.scratch, *tp), tops.values()))
    with cf.ThreadPoolExecutor(4) as ex:
        res = list(ex.map(lambda c: run_case(a.scratch, c, lp), cs))
    base = json.loads(BASE_REC.read_text())
    rec = dict(schema="v41_collective_levers_campaign/1", tool="tools/rtl_v41_collective_levers_campaign.py",
               gate="C7 / O2 levers", baseline=str(BASE_REC.relative_to(ROOT)), link_parameters=lp,
               lane_bytes_per_cycle=LANE_BPC, levers={k: dict(relay=v[0], add_lat=v[1], gather_words_per_cycle=v[2])
                                                      for k, v in LEVERS.items()},
               sources=[str(p.relative_to(ROOT)) for p in sources()], source_sha256=source_sha256(),
               area_assumptions=dict(bitcell_um2=BITCELL_UM2, rf_overhead=RF_OVERHEAD, flop_um2=FLOP_UM2,
                                     die_mm2=DIE_MM2,
                                     note="receive FIFOs and producer queues as 1R1W register-file macros; head, "
                                          "delay-line and gather-output registers as flops"),
               claim_boundary=("RTL of the lever engine (ot_rom_oneshot_die_px) with the O2 bench's behavioural links "
                               "(flight ring + token-bucket rate + credit lane) and producer / consumer stubs; the "
                               "relay channels are UCIe flight only (at most 3 x 512 B per cycle leave a die on UCIe, "
                               "40% of its 3,864 B/cycle); single clock, no PHY, no FEC, no retries"),
               cases=res)
    rec["summary"] = summarise(rec, base)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps({k: dict(before=v["before_tail_cycles"], best=v["best_tail_cycles"], lever=v["best_lever"])
                      for k, v in rec["summary"]["patterns"].items()}, indent=1))
    print("all_pass", rec["summary"]["all_pass"], "bit_exact", rec["summary"]["bit_exact"])
    if a.clean:
        for d in a.scratch.glob("obj_*"):
            shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    main()
