#!/usr/bin/env python3
"""Gate C7 step O2: producer -> collective -> consumer of one V4.1 layer stage, in RTL (Verilator).

The V4.1 design point (docs/ARCH_V41_RACK.md, results/arch/v41_lanes.json best_split on v41-rack-gates) prices a
collective as STREAMING behind its producer: decode_critical_path.Graph.solve starts the collective's bytes at the
producer's START (+ control) and ends it at max(start + bytes, producer finish) + hop + fold.  The bytes therefore
overlap the producer's whole issue AND its pipeline depth, before any output exists.  This campaign measures, on
the real one-shot engine (rtl/rom/ot_rom_oneshot_allreduce.sv ot_rom_oneshot_die, unchanged) with credit-based
bounded queues, backpressure onto the producer and behavioural links at the validated latencies and rates, what
is actually exposed after the producer's last output, for the patterns that dominate the critical path by
count x size (tools/decode_critical_path.py v41_graph at the design point, 1M context, batch 1):

  allreduce_wo_b     attn.out_allreduce, 20,480 B FP32 partial per die after the row-parallel wo_b (13 full
                     board all-reduces on the path; 27 more end at a group boundary, direct_to_next_stage)
  allreduce_down     ffn.combine_allreduce after the MoE down projection (39 full on the path)
  gather_router      ffn.router_allgather, 384 B per die (40 on the path; latency-bound)
  gather_topk        attn.idx.topk_merge, 4 KB per die (8 on the path)
  gather_rows        attn.rows_allgather, 53,760 B per die of HBM-gathered KV rows (8 on the path)
  stage_hop          substage/head hop: the 40,976-B residual on the rack cable (28 on the path)

Clock 1.087 GHz (the spec).  Links (configs/hardware/technology.json, results/arch/v41_rack.json lanes):
UCIe 10 ns / 4.2 TB/s; T1 board 130 ns (light FEC, incl. CDC and endpoint) at 13 lanes x 13.18 GB/s per die pair;
T2 rack cable 209 ns (full KP4) at 14 lanes x 13.18 GB/s per package.  Latencies are rounded UP to whole cycles.

Producer schedules (the cycle, from the producer's start, at which each 512-B word is complete) come from the
design point's own producer node (issue and depth, dumped from the solved DAG) and the weight array's row
mapping (tools/rtl_hdc_v41x_wgt_campaign.py die_mapping: row groups scheduled round-robin onto the tiles, so rows
complete in WAVES in index order, one wave per row's beat count).  `blocked` (rows contiguous per tile: every word
completes at the end) and `uniform` are the order sensitivities.

    python3 tools/rtl_v41_stage_collective_campaign.py --scratch <dir> [--out results/rtl/v41_stage_collective_campaign.json]

Run through remote_gate from a pinned clean worktree.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import math
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden as G  # noqa: E402

OUT = ROOT / "results/rtl/v41_stage_collective_campaign.json"
ADDER = ROOT / "rtl/proto/ot_fp32_add_rne_pipe.sv"
ENGINE = ROOT / "rtl/rom/ot_rom_oneshot_allreduce.sv"
TB = ROOT / "rtl/test/tb_v41_stage_collective.sv"
N, MAXW = 4, 512
LANES = int(__import__("os").environ.get("OT_SB_LANES", 128))   # 128 FP32 lanes (R-U3); smaller only for a smoke run
WORD_B = 4 * LANES
CLOCK = 1.087e9
LANE_NET_BPS = 13176470588.235294            # results/arch/v41_rack.json lanes.lane_net_Bps
LINKS = dict(
    ucie=dict(lat_s=10e-9, Bps=4.2e12, src="technology.json links.rom_package_ucie"),
    t1=dict(lat_s=130e-9, Bps=13 * LANE_NET_BPS,
            src="T1 on-module board link: 130 ns light-FEC hop (arch_budget_v41.BASELINE board_hop_s), R-L9 13 lanes "
                "per die pair"),
    t2=dict(lat_s=209e-9, Bps=14 * LANE_NET_BPS,
            src="T2 rack cable: technology.json links.rom_rack_cable_serdes 209 ns (full KP4), R-L9 14 stage lanes "
                "per package"),
)


def cyc(s):
    return math.ceil(s * CLOCK - 1e-9)


def bpc(Bps):
    return int(round(Bps / CLOCK * 100)), 100


# -- the design point's producers (decode_critical_path DAG at the design point, 1M, batch 1: issue / depth cycles,
#    and the model's exposed time fin(collective) - fin(producer)); dumped from v41-rack-gates@0facdc17 by
#    tools/v41_collective_exposure.py --dump -------------------------------------------------------------------------
PATTERNS = {
    "allreduce_wo_b": dict(node="attn.out_allreduce", mode=0, words=40, prod="attn.wo_b", issue=39, depth=51,
                           rows=5120, beats=8, order="waves", link="t1", model_exposed=152.87, on_path=13,
                           on_path_direct=27, consumer="attn.hc_post: elementwise in index order (streams)"),
    "allreduce_down": dict(node="ffn.combine_allreduce", mode=0, words=40, prod="ffn.down", issue=39, depth=67,
                           rows=5120, beats=8, order="waves", link="t1", model_exposed=163.84, on_path=39,
                           on_path_direct=1, consumer="ffn.hc_post: elementwise in index order (streams)"),
    "gather_router": dict(node="ffn.router_allgather", mode=1, words=1, prod="ffn.softplus_sqrt", issue=1,
                          depth=170, order="uniform", link="t1", model_exposed=141.31, on_path=40,
                          consumer="ffn.bias -> top-6 of 384: needs every score (no overlap possible)"),
    "gather_topk": dict(node="attn.idx.topk_merge", mode=1, words=8, prod="attn.idx.topk_local (tail)", issue=8,
                        depth=163, order="uniform", link="t1", model_exposed=141.31, on_path=8,
                        consumer="attn.idx.topk_final: a 4-way tselect over all 2,048 candidates (needs every word)"),
    "gather_rows": dict(node="attn.rows_allgather", mode=1, words=105, prod="attn.gather (HBM round trip)",
                        issue=17, depth=272, order="uniform", link="t1", model_exposed=212.71, on_path=8,
                        consumer="attn.scores: streams rows (position order if the dies' shares interleave)"),
    "stage_hop": dict(node="substage_hop0 / head.hop", mode=None, words=81, prod="hc_post", issue=10, depth=33,
                      order="uniform", link="t2", model_exposed=328.38, on_path=28,
                      consumer="hc_pre of the next group: elementwise over the 4 copies (streams)"),
}


def schedule(p, order=None):
    order = order or p["order"]
    W, dep, iss = p["words"], p["depth"], p["issue"]
    if order == "blocked":
        return [dep + iss] * W
    if order == "waves":
        rpw = math.ceil(p["rows"] * p["beats"] / iss)          # rows completing per wave (one wave per row's beats)
        per = LANES
        return [dep + p["beats"] * math.ceil((k + 1) * per / rpw) for k in range(W)]
    return [dep + math.ceil(iss * (k + 1) / W) for k in range(W)]


def rand_f32(rng, n):
    e = rng.integers(100, 150, n)
    m = rng.integers(0, 1 << 23, n)
    s = rng.integers(0, 2, n)
    return ((s << 31) | (e << 23) | m).astype(np.uint32)


def hexw(row):
    return "".join(f"{int(x):08x}" for x in row[::-1])


def vectors(path: Path, words, sched_per_die, mode, seed, ndie=N):
    rng = np.random.default_rng(seed)
    part = rand_f32(rng, N * words * LANES).reshape(N, words, LANES)
    path.mkdir(parents=True, exist_ok=True)
    pl, rl, el = [], [], []
    for d in range(ndie):
        pl.append(f"@{d * MAXW:x}")
        rl.append(f"@{d * MAXW:x}")
        for k in range(words):
            pl.append(hexw(part[d, k]))
            rl.append(f"{sched_per_die[d][k]:08x}")
    if mode == 0:
        sums = G.bits(G.fold([G.from_bits(part[d]) for d in range(N)]))
        el = [hexw(sums[k]) for k in range(words)]
    else:
        el = ["0" * (LANES * 8)]
    (path / "part.hex").write_text("\n".join(pl) + "\n")
    (path / "ready.hex").write_text("\n".join(rl) + "\n")
    (path / "exp.hex").write_text("\n".join(el) + "\n")


def sh(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode:
        raise RuntimeError(f"{cmd[0]} failed ({r.returncode}):\n{r.stdout[-3000:]}\n{r.stderr[-3000:]}")
    return r.stdout


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
    sh(["verilator", "--cc", "--exe", "--build", "-O2", "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNUSED", "-Wno-BLKSEQ",
        "-Wno-MULTIDRIVEN", "--top-module", top, *[f"-G{k}={v}" for k, v in params.items()], "-Mdir", str(obj),
        str(ADDER), str(ENGINE), str(TB), str(h), "-CFLAGS", "-O1", "-j", "4"])
    return exe


ARR = re.compile(r"ARR die=(\d+) word=(\d+) cyc=(\d+)")
SB = re.compile(r"SB die=(\d+) start=(-?\d+) ref=(-?\d+) pushed_last=(-?\d+) stall=(\d+) hold=(\d+) qmax=(\d+) "
                r"first=(-?\d+) last=(-?\d+) fault=(\d+) code=(\d+)")
DONE = re.compile(r"SBDONE done=(\d+) mismatches=(\d+) out_err=(\d+) timeout=(\d+) (PASS|FAIL)")


def link_params():
    u, x, c = LINKS["ucie"], LINKS["t1"], LINKS["t2"]
    return dict(clock_hz=CLOCK, word_bytes=WORD_B,
                LAT_U=cyc(u["lat_s"]), BPC_U=int(round(u["Bps"] / CLOCK)),
                LAT_X=cyc(x["lat_s"]), BPC_X=bpc(x["Bps"])[0], BPC_X_DEN=100,
                LAT_C=cyc(c["lat_s"]), BPC_C=bpc(c["Bps"])[0], BPC_C_DEN=100,
                bytes_per_cycle=dict(ucie=u["Bps"] / CLOCK, t1=x["Bps"] / CLOCK, t2=c["Bps"] / CLOCK),
                sources={k: v["src"] for k, v in LINKS.items()})


def top_params(case: dict, lp: dict):
    if case["pattern"] == "stage_hop":
        return "tb_v41_stage_hop", dict(
            LANES=LANES, DEPTH=case["depth"], DEPTH_U=case.get("depth_u", 16), QTX=case["qtx"], LAT_C=lp["LAT_C"],
            BPC_C=lp["BPC_C"], BPC_C_DEN=100, LAT_U=lp["LAT_U"], BPC_U=lp["BPC_U"], FLIT_OVH=case.get("ovh", 0))
    return "tb_v41_stage_collective", dict(
        LANES=LANES, DEPTH=case["depth"], QTX=case["qtx"], PKG_DIES=2, LAT_U=lp["LAT_U"], BPC_U=lp["BPC_U"],
        LAT_X=lp["LAT_X"], BPC_X=lp["BPC_X"], BPC_X_DEN=100, FLIT_OVH=case.get("ovh", 0))


def run_case(scratch: Path, case: dict, lp: dict) -> dict:
    p = PATTERNS[case["pattern"]]
    words = case.get("words", p["words"])
    pp = dict(p, words=words)
    sch = schedule(pp, case.get("order"))
    skew = case.get("skew", 0)
    vec = scratch / f"vec_{case['name']}"
    hop = case["pattern"] == "stage_hop"
    # the hop bench reads producer 0's block (address k): the die-0 block of the vectors
    vectors(vec, words, [sch] * N, 1 if hop else p["mode"], 11 + len(case["name"]), 1 if hop else N)
    exe = build(scratch, *top_params(case, lp))
    start = 20
    args = [str(exe), f"+VEC={vec}", f"+WORDS={words}", f"+START={start}", f"+SKEW={skew}", "+TIMEOUT=60000"]
    if not hop:
        args.append(f"+MODE={p['mode']}")
    txt = sh(args, timeout=3600)
    arr = [tuple(map(int, m.groups())) for m in ARR.finditer(txt)]
    sbs = {int(m.group(1)): dict(zip(("start", "ref", "pushed_last", "stall", "hold", "qmax", "first", "last",
                                      "fault", "code"), map(int, m.groups()[1:]))) for m in SB.finditer(txt)}
    dn = DONE.search(txt)
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
    # consumer's first useful cycle: a streaming consumer starts on the first word it receives; one that needs the
    # whole vector (router top-6, topk final) on the last
    needs_all = case["pattern"] in ("gather_router", "gather_topk")
    first_useful = max(per_die_last.values()) if needs_all else min(per_die_first.values())
    rec = dict(case=case["name"], pattern=case["pattern"], node=p["node"], words_per_die=words,
               bytes_per_die=words * WORD_B, order=case.get("order", p["order"]), rx_depth_words=case["depth"],
               tx_queue_words=case["qtx"], skew_cycles=skew, flit_overhead_bytes=case.get("ovh", 0),
               producer_first_word_cycle=start + min(sch), producer_ref_last_cycle=ref,
               producer_actual_last_cycle=pushed, producer_stall_cycles=max(x["stall"] for x in prod),
               producer_queue_max=max(x["qmax"] for x in prod),
               consumer_first_word_cycle=first, consumer_last_word_cycle=last,
               consumer_first_useful_cycle=first_useful,
               exposed_first_useful_cycles=first_useful - ref,
               exposed_tail_cycles=last - ref,
               exposed_tail_ns=(last - ref) / CLOCK * 1e9,
               producer_delay_cycles=pushed - ref,
               model_exposed_cycles=p["model_exposed"],
               excess_over_model_cycles=(last - ref) - p["model_exposed"],
               mismatches=int(dn.group(2)), out_err=int(dn.group(3)), timeout=int(dn.group(4)),
               faults=[sbs[d]["fault"] for d in sorted(sbs)], passed=dn.group(5) == "PASS")
    return rec


def cases():
    out = []
    for pat in ("allreduce_wo_b", "allreduce_down"):
        for depth in (8, 16, 32, 64, 128):          # the engine's FIFO depth is a power of two
            out.append(dict(name=f"{pat}_d{depth}_q64", pattern=pat, depth=depth, qtx=64))
        for q in (4, 8, 16, 32):
            out.append(dict(name=f"{pat}_d64_q{q}", pattern=pat, depth=64, qtx=q))
    for order in ("blocked", "uniform"):
        out.append(dict(name=f"allreduce_wo_b_{order}_d64_q64", pattern="allreduce_wo_b", depth=64, qtx=64,
                        order=order))
    out.append(dict(name="allreduce_wo_b_skew5_d64_q64", pattern="allreduce_wo_b", depth=64, qtx=64, skew=5))
    out.append(dict(name="allreduce_wo_b_ovh32_d64_q64", pattern="allreduce_wo_b", depth=64, qtx=64, ovh=32))
    for depth in (2, 4, 8, 16):
        out.append(dict(name=f"gather_router_d{depth}_q16", pattern="gather_router", depth=depth, qtx=16))
    for depth in (4, 8, 16, 64):
        out.append(dict(name=f"gather_topk_d{depth}_q16", pattern="gather_topk", depth=depth, qtx=16))
    for depth in (16, 32, 64, 128, 256):
        out.append(dict(name=f"gather_rows_d{depth}_q128", pattern="gather_rows", depth=depth, qtx=128))
    for depth in (16, 32, 64, 128, 256):
        out.append(dict(name=f"stage_hop_full_d{depth}_q64", pattern="stage_hop", depth=depth, qtx=64))
    out.append(dict(name="stage_hop_half_d256_q64", pattern="stage_hop", depth=256, qtx=64, words=41))
    for q in (4, 16):
        out.append(dict(name=f"stage_hop_full_d256_q{q}", pattern="stage_hop", depth=256, qtx=q))
    return out


def analytical_tail(p, lp, words=None):
    """What the bench should show if only link serialisation, one hop and the engine's fold are exposed: the
    bytes start at the producer's FIRST output (not its start), then hop + fold (2 + 3 x 5 on the RTL adders)."""
    words = words or p["words"]
    sch = schedule(dict(p, words=words))
    link = LINKS[p["link"]]
    cpw = WORD_B / (link["Bps"] / CLOCK)
    if p["mode"] == 1:
        # the one-shot gathers an index only when every source's word is in; it then emits N words
        drain = words * max(cpw, N + 1)
    else:
        drain = words * cpw
    lat = cyc(link["lat_s"])
    last_send = max(max(sch), min(sch) + drain)
    fold = (2 + 3 * 5 + 1) if p["mode"] == 0 else (N + 2 if p["mode"] == 1 else cyc(LINKS["ucie"]["lat_s"]))
    return round(last_send + lat + fold - max(sch), 1)


def summarise(rec, lp):
    by = {c["case"]: c for c in rec["cases"]}
    pats = {}
    for pat, p in PATTERNS.items():
        rows = [c for c in rec["cases"] if c["pattern"] == pat and c["order"] == p["order"] and c["skew_cycles"] == 0
                and c["flit_overhead_bytes"] == 0 and c["words_per_die"] == p["words"]]
        if not rows:
            continue
        best = min(c["exposed_tail_cycles"] for c in rows)
        full = [c for c in rows if c["exposed_tail_cycles"] <= best and c["producer_stall_cycles"] == 0]
        min_depth = min((c["rx_depth_words"] for c in rows if c["exposed_tail_cycles"] <= best), default=None)
        min_q = min((c["tx_queue_words"] for c in rows if c["exposed_tail_cycles"] <= best
                     and c["producer_stall_cycles"] == 0), default=None)
        pats[pat] = dict(node=p["node"], on_critical_path=p["on_path"], model_exposed_cycles=p["model_exposed"],
                         measured_exposed_tail_cycles=best, measured_exposed_tail_ns=best / CLOCK * 1e9,
                         excess_over_model_cycles=round(best - p["model_exposed"], 2),
                         excess_over_model_ns=(best - p["model_exposed"]) / CLOCK * 1e9,
                         analytical_tail_cycles=analytical_tail(p, lp),
                         min_rx_depth_for_best_tail=min_depth, min_tx_queue_without_producer_stall=min_q,
                         consumer=p["consumer"],
                         depth_sweep={c["rx_depth_words"]: c["exposed_tail_cycles"] for c in rows
                                      if c["tx_queue_words"] == max(r["tx_queue_words"] for r in rows)},
                         queue_sweep={c["tx_queue_words"]: dict(tail=c["exposed_tail_cycles"],
                                                                producer_stall=c["producer_stall_cycles"])
                                      for c in rows if c["rx_depth_words"] == 64 or pat.startswith("stage")},
                         full_overlap=best <= p["model_exposed"] + 1e-6)
        if full:
            pats[pat]["best_case"] = full[0]["case"]
    return dict(all_pass=all(c["passed"] for c in rec["cases"]),
                bit_exact=all(c["mismatches"] == 0 for c in rec["cases"]),
                patterns=pats)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scratch", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--jobs", type=int, default=6)
    ap.add_argument("--only", default="")
    ap.add_argument("--clean", action="store_true", help="delete the Verilator build directories at the end")
    a = ap.parse_args()
    a.scratch = a.scratch.resolve()
    a.scratch.mkdir(parents=True, exist_ok=True)
    lp = link_params()
    cs = [c for c in cases() if a.only in c["name"]]
    # build every distinct executable first (in parallel), then run
    tops = {}
    for c in cs:
        t, prm = top_params(c, lp)
        tops[(t, tuple(sorted(prm.items())))] = (t, prm)
    with cf.ThreadPoolExecutor(a.jobs) as ex:
        list(ex.map(lambda tp: build(a.scratch, *tp), tops.values()))
    with cf.ThreadPoolExecutor(2 * a.jobs) as ex:
        res = list(ex.map(lambda c: run_case(a.scratch, c, lp), cs))
    rec = dict(schema="v41_stage_collective_campaign/1", tool="tools/rtl_v41_stage_collective_campaign.py",
               gate="C7 / O2 (docs/ARCH_V41_RACK.md 6, results/arch/v41_rack.json demonstration_plan)",
               link_parameters=lp, patterns={k: {kk: vv for kk, vv in v.items()} for k, v in PATTERNS.items()},
               schedules={k: schedule(v) for k, v in PATTERNS.items()},
               sources=[str(p.relative_to(ROOT)) for p in (ADDER, ENGINE, TB)],
               claim_boundary=("RTL of the one-shot engine (ot_rom_oneshot_die, unchanged) with behavioural links "
                               "(flight ring + token-bucket rate + credit lane) and cycle-faithful producer / consumer "
                               "stubs driven from the design point's producer timing and the weight array's row "
                               "mapping; single clock (the plesiochronous crossing is gate K3 and sits inside the "
                               "link latencies); no PHY, no FEC, no link errors or retries"),
               cases=res)
    rec["summary"] = summarise(rec, lp)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(rec["summary"], indent=1))
    if a.clean:
        import shutil
        for d in a.scratch.glob("obj_*"):
            shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    main()
