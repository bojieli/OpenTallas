#!/usr/bin/env python3
"""W11: the V4.1 index-key reader against the four-stack HBM rate.

Builds and runs, in Verilator, every key of every beat checked exactly:

* the LEGACY layout (keys interleaved over the four stacks in 16-key groups,
  four quarter streams per stack sharing its 32 pseudo-channels through
  ot_hdc_v41x_idx_range_pc_arb, 16-way shard collector) at N = 65, 1,040 and
  262,144 -- cycle-equal to the committed gate records -- plus three
  diagnostic variants at 262,144 that locate the loss;
* the QUARTER-PER-STACK layout (stack q holds position quarter q; one
  ot_hdc_v41x_idx_kstream_range per stack straight into its HBM model; the
  four streams joined by ot_hdc_v41x_idx_quarter_join) at the spec
  configuration, N = 65, 1,040, 262,144 (two placements), 1,048,576, and at
  the legacy 1 GHz core clock for a same-clock comparison.

The HBM model (ot_hdc_v41x_idx_hbm) keeps every timing and controller
parameter of the gate (QD 64, RQD 32, RW 16, MAXSKIP 16, REFPB 3); the core
clock of the spec runs is 1.0339 GHz (CLK_PS 967, the nearest integer
picosecond, 0.02% fast).  Writes results/rtl/w11_idx_reader_rate.json.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import hashlib
import json
import math
import re
import subprocess
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/rtl/w11_idx_reader_rate.json"
V = "rtl/hdc/v41x/"
LEGACY_SOURCES = [V + f for f in (
    "ot_hdc_v41x_idx_hbm.sv", "ot_hdc_v41x_idx_kstream.sv",
    "ot_hdc_v41x_idx_kstream_range.sv", "ot_hdc_v41x_idx_range_pc_arb.sv",
    "ot_hdc_v41x_idx_quarter_ranges.sv", "ot_hdc_v41x_idx_shard_quarter_collect.sv",
    "ot_hdc_v41x_idx_quarter_collect_pipe.sv")] + ["rtl/test/tb_w11_idx_reader_rate.sv"]
LEGACY_CPP = "rtl/test/w11_idx_reader_rate.cpp"
QS_SOURCES = [V + f for f in (
    "ot_hdc_v41x_idx_hbm.sv", "ot_hdc_v41x_idx_kstream.sv",
    "ot_hdc_v41x_idx_kstream_range.sv", "ot_hdc_v41x_idx_quarter_join.sv")] + [
    "rtl/test/tb_w11_idx_quarter_stack.sv"]
QS_CPP = "rtl/test/w11_idx_quarter_stack.cpp"
LEGACY_RECORD = "results/rtl/hdc_v41x_idx_four_stack_verilator_collector_pipeline.json"
LEGACY_SHORT_RECORD = "results/rtl/hdc_v41x_idx_four_stack_pipeline_icarus_short.json"

NPC, STACKS, DW, KEY_BYTES, SECTOR_BYTES, BURST_PS = 32, 4, 256, 68, 32, 1024
TARGET_SECTORS_PER_CYCLE = 108.8        # 3,482 B/cycle per die (the root's figure)
SPEC = {"CLK_PS": 967, "WB": 128, "GA": 120}
HBM_GATE = {"QD": 64, "RQD": 32, "RW": 16, "MAXSKIP": 16, "REFPB": 3}

PASS = re.compile(r"V41X_FOUR_STACK_PASS n=(\d+) quantum=(\d+) checked=(\d+) sectors=(\d+) "
                  r"cycles=(\d+) stalled=(\d+) request_stalls=(\d+) output_stalls=(\d+)")
STACK = re.compile(r"W11_STACK s=(\d+) rd=(\d+) act=(\d+) hit=(\d+) conf=(\d+) ref=(\d+) bp=(\d+) "
                   r"lat_sum_ps=(\d+) lat_max_ps=(\d+) pc_rd_min=(\d+) pc_rd_max=(\d+)")
FIRST = re.compile(r"W11_FIRST_OUT cycle=(-?\d+)")

# (name, layout, N, parameters, role)
RUNS = [
    ("legacy_n65", "legacy", 65, {"QUANTUM": 64}, "before"),
    ("legacy_n1040", "legacy", 1040, {"QUANTUM": 64}, "before"),
    ("legacy_n262144", "legacy", 262144, {"QUANTUM": 64}, "before"),
    ("legacy_pipe_collector", "legacy", 262144, {"QUANTUM": 64, "COLLECT": 1}, "diagnostic"),
    ("legacy_pipe_collector_quantum1", "legacy", 262144, {"QUANTUM": 1, "COLLECT": 1}, "diagnostic"),
    ("legacy_pipe_collector_no_refresh", "legacy", 262144,
     {"QUANTUM": 64, "COLLECT": 1, "REFI_PS": 10**12}, "diagnostic"),
    ("quarter_stack_n65", "quarter_stack", 65, dict(SPEC), "after"),
    ("quarter_stack_n1040", "quarter_stack", 1040, dict(SPEC), "after"),
    ("quarter_stack_n262144", "quarter_stack", 262144, dict(SPEC), "after"),
    ("quarter_stack_n262144_placement2", "quarter_stack", 262144,
     dict(SPEC, BASE=123, BSTEP=777, OSTEP=8), "after"),
    ("quarter_stack_n1048576", "quarter_stack", 1048576, dict(SPEC), "after"),
    ("quarter_stack_n1048576_placement2", "quarter_stack", 1048576,
     dict(SPEC, BASE=123, BSTEP=4099, OSTEP=8), "after"),
    ("quarter_stack_n262144_clk1000", "quarter_stack", 262144, {"WB": 128, "GA": 120}, "after"),
    ("sensitivity_ga96_n1048576", "quarter_stack", 1048576, dict(SPEC, GA=96), "sensitivity"),
    ("sensitivity_wb64_ga60_n262144", "quarter_stack", 262144, dict(SPEC, WB=64, GA=60), "sensitivity"),
    ("sensitivity_wb64_ga60_n1048576", "quarter_stack", 1048576, dict(SPEC, WB=64, GA=60), "sensitivity"),
]
QS_DEFAULTS = {"BASE": 0, "BSTEP": 1000, "OSTEP": 136, "CLK_PS": 1000, "WB": 32, "GA": 24}
LEGACY_DEFAULTS = {"CLK_PS": 1000, "WB": 32, "GA": 24, "COLLECT": 0}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sources() -> dict[str, str]:
    paths = sorted({*LEGACY_SOURCES, LEGACY_CPP, *QS_SOURCES, QS_CPP,
                    "tools/w11_idx_reader_rate.py", LEGACY_RECORD, LEGACY_SHORT_RECORD})
    return {p: sha(ROOT / p) for p in paths}


def rank(x: int, s: int) -> int:
    full, rem = divmod(x, 64)
    return 16 * full + max(0, min(16, rem - 16 * s))


def legacy_sectors(n: int) -> int:
    qs = 8 * (n // 32)
    total = 0
    for s in range(4):
        for q in range(4):
            lo, hi = rank(q * qs, s), rank(n if q == 3 else (q + 1) * qs, s)
            if hi > lo:
                total += 2 * (hi - lo) + (hi + 7) // 8 - lo // 8
    return total


def qs_sectors(n: int, ostep: int) -> int:
    qs = 8 * (n // 32)
    total = 0
    for q in range(4):
        lo = (q * ostep) % 1024
        hi = lo + (n - 3 * qs if q == 3 else qs)
        if hi > lo:
            total += 2 * (hi - lo) + (hi + 7) // 8 - lo // 8
    return total


def bank_in_group(block: int) -> int:
    """Bank address above the bank group of ot_hdc_v41x_idx_hbm (NPC 32) for a block's sectors."""
    s = block * 128
    row = s >> 15
    return ((s >> 12) ^ (row >> 2)) & 7


def legacy_collision_fraction(n: int) -> float:
    """Legacy layout, stack 0: fraction of 16-key scan steps at which two of the four
    quarter streams sit in the same bank (same bank-in-group, different rows: their
    starts are >= one row apart), i.e. must share one bank with two open rows."""
    qs = 8 * (n // 32)
    ranges = [(rank(q * qs, 0), rank(n if q == 3 else (q + 1) * qs, 0)) for q in range(4)]
    length = min(hi - lo for lo, hi in ranges)
    steps = hits = 0
    for t in range(0, max(length, 1), 16):
        banks = []
        for lo, hi in ranges:
            if lo + t < hi:
                sb, pos = divmod(lo + t, 1024)
                banks.append(bank_in_group(17 * sb + 1 + pos // 64))
        steps += 1
        hits += len(set(banks)) < len(banks)
    return round(hits / steps, 4)


def build_and_run(run, build_root: Path) -> dict:
    name, layout, n, params, role = run
    if layout == "legacy":
        srcs, cpp, top = LEGACY_SOURCES, LEGACY_CPP, "tb_w11_idx_reader_rate"
        cfg = dict(LEGACY_DEFAULTS, **params)
    else:
        srcs, cpp, top = QS_SOURCES, QS_CPP, "tb_w11_idx_quarter_stack"
        cfg = dict(QS_DEFAULTS, **params)
    obj = build_root / name
    cmd = ["verilator", "--cc", "--exe", "--build", "-j", "4", "-Wno-fatal", "-Wno-WIDTH",
           "-Wno-UNOPTFLAT", "-Wno-WIDTHCONCAT", "--output-split", "20000",
           "--output-split-cfuncs", "10000", "--top-module", top, f"-GNKEYS={n}",
           *[f"-G{k}={v}" for k, v in params.items()], "--Mdir", str(obj),
           *[str(ROOT / s) for s in srcs], str(ROOT / cpp)]
    t0 = time.perf_counter()
    b = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT, timeout=7200)
    if b.returncode:
        raise RuntimeError(f"{name}: Verilator build failed\n{b.stdout[-2000:]}\n{b.stderr[-3000:]}")
    build_s = time.perf_counter() - t0
    t0 = time.perf_counter()
    r = subprocess.run([str(obj / f"V{top}")], capture_output=True, text=True, cwd=ROOT, timeout=7200)
    sim_s = time.perf_counter() - t0
    m = PASS.search(r.stdout)
    if r.returncode or not m:
        raise RuntimeError(f"{name}: simulation failed\n{r.stdout[-4000:]}\n{r.stderr[-2000:]}")
    keys, quantum, checked, sectors, cycles, empty, req_stall, rsp_stall = map(int, m.groups())
    stacks = []
    for sm in STACK.finditer(r.stdout):
        s, rd, act, hit, conf, ref, bp, lat_sum, lat_max, rmin, rmax = map(int, sm.groups())
        stacks.append({"stack": s, "hbm_reads": rd, "activates": act, "row_hits": hit,
                       "row_conflicts": conf, "refreshes": ref, "request_backpressure_pc_cycles": bp,
                       "mean_read_latency_ns": round(lat_sum / rd / 1000, 2) if rd else None,
                       "max_read_latency_ns": round(lat_max / 1000, 2),
                       "reads_per_pc_min": rmin, "reads_per_pc_max": rmax})
    first = int(FIRST.search(r.stdout).group(1))
    expected = legacy_sectors(n) if layout == "legacy" else qs_sectors(n, cfg["OSTEP"])
    assert (keys, checked, sectors) == (n, n, expected), (name, keys, checked, sectors, expected)
    peak = STACKS * NPC * cfg["CLK_PS"] / BURST_PS
    return {
        "name": name, "role": role, "layout": layout, "keys": n, "parameters": cfg,
        "checked_keys": checked, "sectors": sectors, "cycles": cycles,
        "sectors_per_cycle": round(sectors / cycles, 3),
        "bytes_per_cycle": round(sectors * SECTOR_BYTES / cycles, 1),
        "first_output_cycle": first,
        "sustained_sectors_per_cycle": round(sectors / (cycles - first), 3) if cycles > first else None,
        "hbm_peak_sectors_per_cycle": round(peak, 3),
        "hbm_efficiency": round(sectors / cycles / peak, 4),
        "stalls": {"collector_empty_cycles": empty, "hbm_request_stall_cycles": req_stall,
                   "hbm_response_stall_cycles": rsp_stall},
        "hbm_per_stack": stacks,
        "build_wall_seconds": round(build_s, 1), "simulation_wall_seconds": round(sim_s, 2),
    }


def element(wb: int, ga: int) -> dict:
    rob_bits = wb * 4 * DW
    return {
        "name": "per-pseudo-channel reader element (quarter-per-stack layout)",
        "count_per_die": STACKS * NPC,
        "contents": "request generator (next block, super-block key count, prepared request) + "
                    "reorder slice (one ROB bank: WB entries x one 4-sector column) + per-entry beat "
                    "counters and completion bit",
        "rob_entries": wb, "lookahead_blocks": ga,
        "rob_bits": rob_bits, "rob_kib": rob_bits / 8192,
        "rob_macro": f"1W1R, {wb} x {4 * DW}: write {DW} b (one HBM beat/cycle), read {4 * DW} b",
        "control_register_bits_approx": wb * 3 + wb + (20 + 5 + 30 + 20) + (20 + 3 + 2 + 28 + 1) + (28 + 4 + 16 + 1),
        "ports": {"hbm_request": "valid/ready + addr 28 + len 4 + tag 16",
                  "hbm_response": "valid/ready + data 256 + tag 16 + beat 4",
                  "drain_read": f"{4 * DW} b (one 128-B column: 2 keys' codes, or 32 scales)"},
        "die_rob_mib": STACKS * NPC * rob_bits / 8 / 2**20,
        "per_stack_shared": {"drain_control": 1, "scale_buffer_bits": 64 * 512,
                             "output_queue_bits": 2 * (16 * 544 + 16)},
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=6)
    ap.add_argument("--build-dir", default=None)
    args = ap.parse_args()
    head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True,
                          cwd=ROOT).stdout.strip()
    pins_before = sources()
    with tempfile.TemporaryDirectory(prefix="w11-idx-rate-", dir=args.build_dir) as td:
        with cf.ThreadPoolExecutor(args.jobs) as ex:
            rows = list(ex.map(lambda r: build_and_run(r, Path(td)), RUNS))
    assert sources() == pins_before, "a source changed while the campaign ran"
    by = {r["name"]: r for r in rows}
    for row in rows:
        print(f'{row["name"]:40s} cycles={row["cycles"]:6d} sectors/cycle={row["sectors_per_cycle"]:7.2f} '
              f'first={row["first_output_cycle"]}', flush=True)

    # the instrumented legacy bench is the committed gate, cycle for cycle
    gate = json.loads((ROOT / LEGACY_RECORD).read_text())
    short = json.loads((ROOT / LEGACY_SHORT_RECORD).read_text())
    gate_cycles = {c["keys"]: c["cycles"] for c in gate["cases"]}
    short_cycles = {c["keys"]: c["cycles"] for c in short["cases"]}
    for n in (65, 1040, 262144):
        assert by[f"legacy_n{n}"]["cycles"] == gate_cycles[n], (n, by[f"legacy_n{n}"]["cycles"])
    for n in (65, 1040):
        assert by[f"legacy_n{n}"]["cycles"] == short_cycles[n]

    spec = by["quarter_stack_n262144"]
    target_cycles = math.ceil(legacy_sectors(262144) / TARGET_SECTORS_PER_CYCLE)
    before = by["legacy_n262144"]
    long = by["quarter_stack_n1048576"]
    long_target = math.ceil(long["sectors"] / TARGET_SECTORS_PER_CYCLE)
    diag = {k: by[k] for k in ("legacy_pipe_collector", "legacy_pipe_collector_quantum1",
                               "legacy_pipe_collector_no_refresh")}
    rec = {
        "schema": "opentallas.w11-idx-reader-rate.v1",
        "status": "pass",
        "git_head": head,
        "simulator": "Verilator " + subprocess.run(["verilator", "--version"], capture_output=True,
                                                   text=True).stdout.split()[1],
        "target": {"sectors_per_cycle": TARGET_SECTORS_PER_CYCLE,
                   "bytes_per_cycle": round(TARGET_SECTORS_PER_CYCLE * SECTOR_BYTES, 1),
                   "keys": 262144, "sectors": legacy_sectors(262144),
                   "max_cycles_after_fill": target_cycles,
                   "core_clock_ghz": round(1000 / SPEC["CLK_PS"], 4),
                   "hbm_peak_sectors_per_cycle": round(STACKS * NPC * SPEC["CLK_PS"] / BURST_PS, 3)},
        "hbm_model_parameters": dict(HBM_GATE, note="unchanged gate values; timing parameters are the "
                                     "module defaults (HBM3E 1,024 ps burst per pseudo-channel)"),
        "spec_configuration": {"layout": "quarter_stack", **SPEC,
                               "collector": "ot_hdc_v41x_idx_quarter_join (1 beat/cycle, 64 x 544 b)"},
        "summary": {
            "before": {"cycles": before["cycles"], "sectors_per_cycle": before["sectors_per_cycle"],
                       "clock_ps": 1000},
            "after": {"cycles": spec["cycles"], "sectors_per_cycle": spec["sectors_per_cycle"],
                      "first_output_cycle": spec["first_output_cycle"],
                      "cycles_after_fill": spec["cycles"] - spec["first_output_cycle"],
                      "clock_ps": SPEC["CLK_PS"]},
            "after_same_clock": {"cycles": by["quarter_stack_n262144_clk1000"]["cycles"],
                                 "sectors_per_cycle": by["quarter_stack_n262144_clk1000"]["sectors_per_cycle"],
                                 "clock_ps": 1000},
            "after_n1048576": {"cycles": long["cycles"], "sectors_per_cycle": long["sectors_per_cycle"],
                               "cycles_after_fill": long["cycles"] - long["first_output_cycle"],
                               "max_cycles_after_fill": long_target},
            "meets_target": (spec["cycles"] - spec["first_output_cycle"] <= target_cycles and
                             long["cycles"] - long["first_output_cycle"] <= long_target),
            "sensitivity": {k: {"cycles": by[k]["cycles"], "sectors_per_cycle": by[k]["sectors_per_cycle"],
                                "WB": by[k]["parameters"]["WB"], "GA": by[k]["parameters"]["GA"]}
                            for k in by if k.startswith("sensitivity_")},
        },
        "diagnosis": {
            "collector_cap": "the legacy shard collector drops o_valid for a cycle after every beat: at most "
                             "one 64-key beat per 2 cycles = 32 keys = 68 sectors/cycle; a 1-beat/cycle "
                             f"collector alone gives {diag['legacy_pipe_collector']['cycles']} cycles (no gain): "
                             "the HBM side binds first",
            "bank_collisions": "legacy layout: every stack runs four quarter streams in lockstep over the same "
                               "32 pseudo-channels; each holds one bank per bank group, chosen by its block "
                               "address, so for some N two streams need different rows of one bank for long "
                               "stretches. Fraction of the scan with such a pair, by N (stack 0): "
                               + json.dumps({str(n): legacy_collision_fraction(n) for n in
                                             (65536, 131072, 200000, 262144, 524288, 777777, 1048576)})
                               + ". Long per-context grant runs (QUANTUM 64) hide part of it at the price of "
                               "fill and deep ROBs; request-by-request interleave (QUANTUM 1) makes the pair "
                               f"alternate rows: {diag['legacy_pipe_collector_quantum1']['cycles']} cycles, "
                               f"{diag['legacy_pipe_collector_quantum1']['hbm_per_stack'][0]['row_conflicts']} "
                               "row conflicts on stack 0",
            "refresh": "with QUANTUM runs a paused context's bank has no queued burst, so the refresh-aware "
                       "REFpb chooser refreshes it and the resuming context's oldest burst blocks its "
                       "pseudo-channel once MAXSKIP (16) bypasses are spent. Refresh disabled (diagnostic "
                       f"only): {diag['legacy_pipe_collector_no_refresh']['cycles']} cycles",
            "fix": "quarter-per-stack placement: stack q holds position quarter q, so each stack runs ONE "
                   "sequential stream -- no two streams share a bank, no per-channel context arbitration "
                   "(the range_pc_arb and the 16-way shard collector go away), and the refresh chooser always "
                   "finds banks the stream has left. The single stream's per-channel lookahead must cover the "
                   "other channels' refresh stalls (the drain waits for the slowest of 32 channels): GA 120 "
                   "blocks over a WB 128-entry ROB per channel -- the same ROB storage as the legacy 4 x 32 "
                   "entries. The rate is sensitive to GA (refresh phase; see summary.sensitivity): WB 64 "
                   "halves the storage and meets the 262,144-key budget but not the 1M-key sustained rate. Keys, lane masks, last flags, refusal bits and position order to "
                   "the selector are unchanged and checked on every beat. Cost outside the reader: as N "
                   "grows the quarter boundaries move 8 q positions per 32 keys, so 48 keys (3.3 KB) migrate "
                   "stack q -> q-1 per 32 decode steps (a ring per stack; the join realigns heads at 8 mod "
                   "16 with an 8-key carry).",
        },
        "element": element(SPEC["WB"], SPEC["GA"]),
        "legacy_element": {"count_per_die": STACKS * NPC,
                           "rob_bits": 4 * 32 * 4 * DW,
                           "note": "4 contexts x (WB 32 x 1,024 b) per physical pseudo-channel + 4:1 arbiter slice",
                           "die_rob_mib": STACKS * NPC * 4 * 32 * 4 * DW / 8 / 2**20},
        "collector": {"module": "ot_hdc_v41x_idx_quarter_join", "output_bits": 64 * 544 + 64 + 64 + 4,
                      "key_bits": 64 * 544, "inputs": "4 x (16 x 544 b + 16 kv)",
                      "carry_bits": 4 * 8 * 544, "beats_per_cycle": 1,
                      "feeds": "64 keys/cycle = 16 NK=4 score slices"},
        "cases": rows,
        "short_case_check": "legacy layout N=65/1,040/262,144 reproduce the committed gate cycles "
                            f"({gate_cycles[65]}, {gate_cycles[1040]}, {gate_cycles[262144]}); quarter-stack N=65 and "
                            "1,040 pass the exact per-beat key/mask/last/refusal checks",
        "limitation": "Behavioural timed HBM model (simulation only); core clock 967 ps for 1.0339 GHz. The "
                      "ring migration and the writer's quarter placement are specified, not built. Not a "
                      "physical or token-rate claim.",
        "sources_sha256": pins_before,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    if OUT.exists():
        raise SystemExit(f"{OUT} exists; records are never overwritten")
    OUT.write_text(json.dumps(rec, indent=2) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
