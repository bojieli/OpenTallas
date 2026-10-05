#!/usr/bin/env python3
"""Gate C7 step K3: the plesiochronous crossing of a package-to-package link, under two clocks (Verilator).

The rack has no rack-wide synchronous clock: every package runs its own PLL, so a board or cable link crosses two
clocks that differ by up to +-100 ppm (IEEE 802.3 PHY tolerance).  rtl/rom/ot_rom_link_cdc.sv is the crossing: an
asynchronous FIFO with Gray pointers, fed OPEN LOOP by a transmitter that leaves one idle slot every SKIP_EVERY
cycles (a fixed-rate PHY cannot see the far buffer).  This campaign runs it with a C++ harness that toggles the two
clocks at their own periods -- the design-point clock on TX and TX x (1 + ppm) on RX -- and checks, for each case:

  * every flit arrives exactly once and in order (sequence numbers), zero overflow, zero underflow;
  * the crossing latency in RX cycles, against the 4 clock-crossing cycles the 130 ns / 209 ns hop budgets
    (configs/hardware/technology.json links.rom_board_serdes.latency_components_s.cdc);
  * a NEGATIVE case: an idle rate too low for the offset MUST overflow and latch `ovf` (fail closed).

Output: results/rtl/v41_link_cdc_campaign.json.  Run through remote_gate from a pinned clean worktree.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/rtl/v41_link_cdc_campaign.json"
LADDER = ROOT / "results/arch/v41_latency_ladder.json"
DUT = ROOT / "rtl/rom/ot_rom_link_cdc.sv"
TB = ROOT / "rtl/test/tb_rom_link_cdc.sv"
CDC_BUDGET_CYCLES = 4

RES = re.compile(r"LINKCDC skip_every=(\d+) aw=(\d+) sync=(\d+) flits=(\d+) mismatches=(\d+) ovf=(\d+) unf=(\d+) "
                 r"lat_min_fs=(\d+) lat_max_fs=(\d+) lat_mean_fs=(\d+) rx_period_fs=(\d+)")

HARNESS = r'''
#include "Vtb_rom_link_cdc.h"
#include "verilated.h"
#include <cstdint>
#include <cstdlib>
#include <cstring>
int main(int argc, char** argv) {
  Verilated::commandArgs(argc, argv);
  int64_t tx_period = 919963;  // fs
  double ppm = 0;
  for (int i = 1; i < argc; i++) {
    if (!strncmp(argv[i], "+TXFS=", 6)) tx_period = atoll(argv[i] + 6);
    if (!strncmp(argv[i], "+PPM=", 5)) ppm = atof(argv[i] + 5);
  }
  int64_t rx_period = (int64_t)(tx_period * (1.0 + ppm * 1e-6) + 0.5);
  auto* t = new Vtb_rom_link_cdc;
  int64_t now = 0, next_tx = tx_period / 2, next_rx = rx_period / 2 + 137;  // arbitrary initial phase
  t->clk_tx = 0; t->clk_rx = 0; t->time_fs = 0; t->rx_period_fs = rx_period; t->eval();
  while (!Verilated::gotFinish()) {
    if (next_tx <= next_rx) { now = next_tx; t->clk_tx = !t->clk_tx; next_tx += tx_period / 2; }
    else { now = next_rx; t->clk_rx = !t->clk_rx; next_rx += rx_period / 2; }
    t->time_fs = now;
    t->eval();
  }
  t->final(); delete t; return 0;
}
'''


def sh(cmd, **kw) -> str:
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode:
        raise RuntimeError(f"{cmd[0]} failed ({r.returncode}):\n{r.stdout[-3000:]}\n{r.stderr[-3000:]}")
    return r.stdout


def build(scratch: Path, skip: int, aw: int, sync: int) -> Path:
    obj = scratch / f"obj_s{skip}_a{aw}_y{sync}"
    h = scratch / "harness.cpp"
    h.write_text(HARNESS)
    sh(["verilator", "--cc", "--exe", "--build", "-O2", "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNUSED", "-Wno-BLKSEQ",
        "-Wno-SYNCASYNCNET", "--top-module", "tb_rom_link_cdc", f"-GSKIP_EVERY={skip}", f"-GAW={aw}",
        f"-GSYNC={sync}", "-Mdir", str(obj), str(DUT), str(TB), str(h), "-CFLAGS", "-O2", "-j", "8"])
    return obj / "Vtb_rom_link_cdc"


# name, ppm (RX slower when positive), skip_every, aw, sync, flits, expect_overflow
CASES = [
    ("same_clock", 0, 1024, 4, 2, 10_000_000, False),
    ("rx_slow_100ppm", 100, 1024, 4, 2, 100_000_000, False),
    ("rx_fast_100ppm", -100, 1024, 4, 2, 100_000_000, False),
    ("rx_slow_200ppm_1e9", 200, 1024, 4, 2, 1_000_000_000, False),
    ("rx_fast_200ppm", -200, 1024, 4, 2, 100_000_000, False),
    ("rx_slow_200ppm_sync3", 200, 1024, 4, 3, 100_000_000, False),
    ("negative_rx_slow_200ppm_skip_65536", 200, 65536, 4, 2, 100_000_000, True),
]


def run(scratch: Path) -> dict:
    f = json.loads(LADDER.read_text())["ladder"][-1]["clock_hz"]
    tx_fs = int(round(1e15 / f))
    exes, out = {}, []
    for name, ppm, skip, aw, sync, flits, neg in CASES:
        key = (skip, aw, sync)
        if key not in exes:
            exes[key] = build(scratch, *key)
        txt = sh([str(exes[key]), f"+PPM={ppm}", f"+TXFS={tx_fs}", f"+FLITS={flits}"])
        m = RES.search(txt)
        if not m:
            raise RuntimeError(f"{name}: no result\n{txt[-2000:]}")
        g = list(map(int, m.groups()))
        rx_fs = g[10]
        lat_max_cyc = g[8] / rx_fs
        rec = dict(case=name, ppm_rx_vs_tx=ppm, skip_every=skip, buffer_flits=1 << aw, sync_stages=sync,
                   flits_requested=flits, flits_received=g[3], mismatches=g[4], overflow=bool(g[5]),
                   underflow=bool(g[6]), latency_rx_cycles=dict(min=g[7] / rx_fs, max=lat_max_cyc, mean=g[9] / rx_fs),
                   latency_ns_max=g[8] / 1e6, expect_overflow=neg,
                   idle_rate_ppm=1e6 / skip, margin_vs_offset=(1e6 / skip) / max(1, abs(ppm)))
        if neg:
            rec["pass"] = rec["overflow"]            # fail closed: the latch must fire
        else:
            rec["pass"] = (g[4] == 0 and not rec["overflow"] and not rec["underflow"] and g[3] >= flits)
            rec["within_cdc_budget"] = lat_max_cyc <= CDC_BUDGET_CYCLES + 1   # +1: the RX output register
        out.append(rec)
    return dict(clock_hz=f, tx_period_fs=tx_fs, cases=out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scratch", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=OUT)
    a = ap.parse_args()
    a.scratch = a.scratch.resolve()
    a.scratch.mkdir(parents=True, exist_ok=True)
    rec = run(a.scratch)
    pos = [c for c in rec["cases"] if not c["expect_overflow"]]
    rec.update(schema="v41_link_cdc_campaign/1", tool="tools/rtl_v41_link_cdc_campaign.py",
               gate="C7 / K3 (results/arch/v41_rack.json demonstration_plan)",
               sources=[str(p.relative_to(ROOT)) for p in (DUT, TB)],
               cdc_budget_cycles=CDC_BUDGET_CYCLES,
               summary=dict(all_pass=all(c["pass"] for c in rec["cases"]),
                            worst_latency_rx_cycles=max(c["latency_rx_cycles"]["max"] for c in pos),
                            all_within_cdc_budget=all(c.get("within_cdc_budget") for c in pos),
                            flits_checked=sum(c["flits_received"] for c in pos)),
               claim_boundary="RTL of the digital crossing (async FIFO, Gray pointers, open-loop idle insertion) under "
                              "two simulated clocks; no PHY, no CDR, no metastability model (synchronisers are ideal "
                              "flops in simulation)")
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(rec["summary"], indent=1))


if __name__ == "__main__":
    main()
