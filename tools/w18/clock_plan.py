#!/usr/bin/env python3
"""W18: clock plan of the V4.1 ROM layer die (two domains, one PLL), its CDC points with measured latency,
the rate matching they need, and the clock-tree power of each domain.

Inputs: the ratio-FIFO bench (rtl/test/tb_chip_v41_ratio_fifo.sv, run here), the W10 pair power record
(measured clock-tree + flop-clock + ROM-macro-clock power), the die floorplan (hub partitions), the
connectivity ledger (edge widths) and W11's domain map (root message 2026-09-30).

    python3 tools/w18/clock_plan.py --floorplan F --output results/physical_abi3/asap7/chip/v41_w18/clock_plan.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIFO = ROOT / "rtl/chip/ot_chip_v41_ratio_fifo.sv"
TB = ROOT / "rtl/test/tb_chip_v41_ratio_fifo.sv"
PAIR = ROOT / "results/physical_abi3/asap7/chip/v41_w18/pair_w10p5_abstract.json"
CONN = ROOT / "results/contracts/v41_floorplan_connectivity.json"
F_FAST, F_SLOW, F_MEAS = 1.2e9, 0.9e9, 1.087e9


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def bench() -> dict:
    out = {}
    with tempfile.TemporaryDirectory() as t:
        b = Path(t) / "tb"
        subprocess.run(["iverilog", "-g2012", "-o", str(b), str(FIFO), str(TB)], check=True, capture_output=True)
        for mode in ("sparse", "random_stall"):
            args = ["vvp", "-n", str(b)] + (["+sparse"] if mode == "sparse" else [])
            txt = subprocess.run(args, capture_output=True, text=True, timeout=900).stdout
            m = re.search(r"W18_CDC_RESULT (.*)", txt)
            kv = dict(x.split("=") for x in m.group(1).split()) if m else {}
            out[mode] = dict(result=kv, verdict=txt.strip().splitlines()[-1])
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--floorplan", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args(argv)
    fp = json.loads(a.floorplan.read_text())
    conn = {e["id"]: e for e in json.loads(CONN.read_text())["edges"]}
    pr = json.loads(PAIR.read_text())
    b = bench()
    sp = b["sparse"]["result"]
    f2s = [float(x) for x in sp["f2s_lat_slow_cycles"].split("/")]
    s2f = [float(x) for x in sp["s2f_lat_fast_cycles"].split("/")]
    parts = fp["hub"]["parts"]
    slow_parts = ["HUB_VM", "HUB_SU_VECTOR", "HUB_HC"]
    area = lambda ks: round(sum(parts[k]["w"] * parts[k]["h"] for k in ks) / 1e6, 2)  # noqa: E731
    ratio = F_FAST / F_SLOW
    cdc = [
        dict(point="SU -> attention p-words", from_domain="slow", width_bits=conn["vm_pv_preload"]["data_bits"],
             widened_bits=int(round(conn["vm_pv_preload"]["data_bits"] * ratio)),
             note="W11 is widening the p-word port; 4/3 keeps the fast consumer's rate"),
        dict(point="attention scores and PV -> VM", from_domain="fast", width_bits=512, widened_bits=683,
             note="ASSUMED 512-bit attention output word (W3); the slow VM write side needs 4/3 the width"),
        dict(point="VM x-gather -> field x broadcast", from_domain="slow", width_bits=549,
             widened_bits=732, note="the x root (xcap) is on the fast side: the VM must supply 4/3 x words per "
                                    "slow cycle (64 -> 85.3 elements) or the field idles 25% of x-bound cycles"),
        dict(point="field results -> VM", from_domain="fast", width_bits=4096, widened_bits=5461,
             note="model VM write port 128 FP32 elements per fast cycle; the slow VM needs 171 per slow cycle"),
        dict(point="collective DMA <-> VM", from_domain="fast", width_bits=conn["vm_collective"]["data_bits"],
             widened_bits=int(round(conn["collective_vm"]["data_bits"] * ratio)),
             note=f"vm_collective {conn['vm_collective']['data_bits']} / collective_vm "
                  f"{conn['collective_vm']['data_bits']} bits"),
        dict(point="VM -> indexer query", from_domain="slow", width_bits=conn["vm_he"]["data_bits"],
             widened_bits=int(round(conn["vm_he"]["data_bits"] * ratio)), note="vm_he width"),
        dict(point="index scores -> select", from_domain="fast", width_bits=32, widened_bits=43,
             note="selected_kv/score width 32 (ledger); rate-limited by top-k, width need not grow"),
    ]
    for c in cdc:
        if c["from_domain"] == "fast":
            c["latency"] = dict(slow_cycles_min=f2s[0], slow_cycles_mean=f2s[1], slow_cycles_max=f2s[2],
                                model_cycles=int(-(-f2s[2] // 1)))
        else:
            c["latency"] = dict(fast_cycles_min=s2f[0], fast_cycles_mean=s2f[1], fast_cycles_max=s2f[2],
                                model_cycles=int(-(-s2f[2] // 1)))
        c["fifo"] = "ot_chip_v41_ratio_fifo, depth 4 (covers the 4-fast / 3-slow hyperperiod at full rate)"
    # clock-tree power (the measured pair's clock-related groups at TT, scaled to 1.2 GHz)
    bd = pr["power_w_per_pair"]["breakdown"]
    idle = bd["idle_clock_on"]
    pair_clk_w = (idle["clock"]["total_w"] + idle["sequential"]["internal_w"] + idle["macro"]["internal_w"])
    pair_clk_12 = pair_clk_w * F_FAST / F_MEAS
    pairs = 7102
    # global distribution: an H-tree to the 464 clusters + hub, M8 wire at the platform setRC capacitance
    c_um = 1.03962e-1 * 1e-15            # F/um (setRC M8: 0.104 fF/um)
    htree_um = 28000 * (464 ** 0.5)      # ~ side x sqrt(leaves)
    c_tree = 2.0 * htree_um * c_um       # wire + repeaters (x2, ASSUMED)
    glob_fast = c_tree * 0.7 ** 2 * F_FAST
    hub_model_clock_w = 5.0              # results/uarch/v41_rom.json power.hub (area x constant, UNCALIBRATED)
    slow_frac = area(slow_parts) / area(list(parts))
    rec = dict(
        schema="opentallas.v41.w18_clock_plan.v1",
        pll=dict(vco_ghz=3.6, fast=dict(divide=3, ghz=1.2), slow=dict(divide=4, ghz=0.9),
                 alignment="rising edges coincide every 3.333 ns (4 fast = 3 slow); tightest fast/slow edge "
                           "spacing 278 ps in either direction",
                 basis="one PLL per die, two dividers (AGENTS.md c0894b1c); the clocks are phase-related, so the "
                       "crossings are timed synchronously by STA, not synchronised"),
        domains=dict(
            slow_0p9=dict(units=["SU controller and broadcast tree", "SU light and SFU lanes", "chunk-8 reducer",
                                 "lane-0 side pipe (rsqrt/sqrt/softplus/Engram gate)", "softplus_sqrt",
                                 "VM-H group tiles and rotate network (the whole VM)", "Sinkhorn / mHC (HC)"],
                          placement=dict(hub_partitions=slow_parts, contiguous=True, area_mm2=area(slow_parts),
                                         bbox_um=[min(parts[k]["x"] for k in slow_parts),
                                                  min(parts[k]["y"] for k in slow_parts),
                                                  max(parts[k]["x"] + parts[k]["w"] for k in slow_parts),
                                                  max(parts[k]["y"] + parts[k]["h"] for k in slow_parts)])),
            fast_1p2=dict(units=["ROM field (all pairs)", "indexer score array", "attention tiles, controller, "
                                 "loader, ILV", "ring reader/writer", "CKV path", "HBM service / PHY controllers",
                                 "collective and link ports", "gather"],
                          placement="everything else: the ROM field, HUB_ATTENTION, COLLECTIVE and GATHER (in the VM "
                                    "column, fast islands on the slow region's edge), HBM service bands, link strips"),
            source="W11 domain map (root, 2026-09-30)"),
        cdc=dict(style="synchronous-ratio FIFO (rtl/chip/ot_chip_v41_ratio_fifo.sv): no synchronisers, pointer "
                       "published one source cycle after its entry, one flop-to-flop pointer crossing per direction "
                       "at the domain edge (278 ps worst spacing), 4 entries",
                 bench=b, bench_sources={str(p.relative_to(ROOT)): sha(p) for p in (FIFO, TB)},
                 latency_basis="write edge -> the destination edge that registers the word (sparse traffic, "
                               "every phase of the hyperperiod); replaces the model's ASSUMED 2 cycles",
                 points=cdc,
                 rate_matching="every slow-side port at a crossing must be 4/3 as wide as its fast-side rate, or "
                               "the fast side stalls 25% of the time; the widened_bits column is that width"),
        clock_power=dict(
            fast_domain=dict(pair_clock_w_each_1p2ghz=round(pair_clk_12, 5),
                             pair_clock_basis="W10 p5 measured idle-with-clock groups: clock tree + flop clock pins "
                                              "(sequential internal) + ROM macro clock, x 1.2 / 1.087",
                             field_ungated_w=round(pair_clk_12 * pairs, 1),
                             field_gated_idle_w=0.0, field_per_busy_pair_w=round(pair_clk_12, 5),
                             global_tree_w=round(glob_fast, 3),
                             global_tree_basis="H-tree ~ 28 mm x sqrt(464 clusters) of M8 at 0.104 fF/um, x2 for "
                                               "repeaters (ASSUMED), 0.7 V, 1.2 GHz"),
            slow_domain=dict(hub_clock_w=round(hub_model_clock_w * slow_frac * F_SLOW / 1.034e9, 3),
                             basis="model hub clock 5.0 W (UNCALIBRATED area x constant) x slow-region area share "
                                   f"({slow_frac:.2f}) x 0.9 / 1.034 GHz -- replace with W11's hardened units",
                             global_tree_w=round(c_tree * 0.05 * 0.7 ** 2 * F_SLOW, 4),
                             global_tree_basis="the slow region is ~5% of the fast tree's span (ASSUMED)")),
        inputs=dict(floorplan=str(a.floorplan), floorplan_sha256=sha(a.floorplan), pair_record_sha256=sha(PAIR),
                    connectivity_sha256=sha(CONN)),
        tool_sha256=sha(Path(__file__)))
    a.output.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(dict(cdc=[(c["point"], c["width_bits"], c["widened_bits"], c["latency"]) for c in cdc],
                          power=rec["clock_power"], slow=rec["domains"]["slow_0p9"]["placement"]), indent=1))


if __name__ == "__main__":
    main()
