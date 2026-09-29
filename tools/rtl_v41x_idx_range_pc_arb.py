#!/usr/bin/env python3
"""Timed one-stack four-context index range arbitration gate."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [ROOT / p for p in (
    "rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_idx_kstream.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_idx_kstream_range.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_idx_quarter_ranges.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_idx_range_pc_arb.sv",
    "rtl/test/tb_hdc_v41x_idx_range_pc_arb.sv",
)]
SINGLE_SOURCES = [ROOT / p for p in (
    "rtl/test/tb_hdc_v41x_idx_kstream_range.sv",
    "rtl/test/tb_hdc_v41x_idx_single_diag.sv",
)]
OUT = ROOT / "results/rtl/hdc_v41x_idx_range_pc_arb.json"
PAT = re.compile(r"V41X_RANGE_ARB_PASS n=(\d+) wb=(\d+) ga=(\d+) quantum=(\d+) qd=(\d+) rw=(\d+) checked=(\d+) sectors=(\d+) cycles=(\d+) grants=(\d+)")
DIAG = re.compile(r"V41X_RANGE_ARB_DIAG idle_pc_slots=(\d+) blocked_req_slots=(\d+) blocked_rsp_slots=(\d+) context_switches=(\d+)")
HBM = re.compile(r"V41X_RANGE_ARB_HBM act=(\d+) hit=(\d+) conf=(\d+) ref=(\d+) bp=(\d+) rd_lat_sum_ps=(\d+) rd_lat_max_ps=(\d+)")
SINGLE = re.compile(r"V41X_RANGE_PASS skip=0 count=65536 checked=65536 sectors=(\d+) cycles=(\d+)")
SINGLE_DIAG = re.compile(r"V41X_SINGLE_DIAG act=(\d+) hit=(\d+) conf=(\d+) ref=(\d+) idle_pc_slots=(\d+) blocked_req_slots=(\d+) bp=(\d+) rd_lat_sum_ps=(\d+) rd_lat_max_ps=(\d+)")
CASES = ((65, 32, 24, 1, 64, 16), (1040, 32, 24, 1, 64, 16),
         *((262144, 32, 24, q, 64, 16) for q in (8, 16, 64, 128)))


def run_case(tmp: Path, n: int, wb: int, ga: int, quantum: int, qd: int, rw: int) -> dict:
    binary = tmp / f"range_arb_{n}_{wb}_{quantum}_{qd}_{rw}.vvp"
    subprocess.run(["iverilog", "-g2012", "-s", "tb_hdc_v41x_idx_range_pc_arb",
                    f"-Ptb_hdc_v41x_idx_range_pc_arb.NKEYS={n}",
                    f"-Ptb_hdc_v41x_idx_range_pc_arb.WB={wb}",
                    f"-Ptb_hdc_v41x_idx_range_pc_arb.GA={ga}",
                    f"-Ptb_hdc_v41x_idx_range_pc_arb.QUANTUM={quantum}",
                    f"-Ptb_hdc_v41x_idx_range_pc_arb.QD={qd}",
                    f"-Ptb_hdc_v41x_idx_range_pc_arb.RW={rw}",
                    "-o", str(binary), *map(str, SOURCES)], check=True, cwd=ROOT)
    run = subprocess.run(["vvp", str(binary)], check=True, capture_output=True,
                         text=True, timeout=900, cwd=ROOT)
    m = PAT.search(run.stdout)
    assert m, run.stdout
    got_n, got_wb, got_ga, got_q, got_qd, got_rw, checked, sectors, cycles, grants = map(int, m.groups())
    assert (got_n, got_wb, got_ga, got_q, got_qd, got_rw) == (n, wb, ga, quantum, qd, rw)
    assert checked == (n // 64) * 16 + min(n % 64, 16), (n, checked)
    d = DIAG.search(run.stdout)
    h = HBM.search(run.stdout)
    assert d and h, run.stdout
    idle, blocked_req, blocked_rsp, switches = map(int, d.groups())
    act, hit, conf, ref, bp, lat_sum, lat_max = map(int, h.groups())
    return {"global_keys": n, "stack_keys": checked, "wb_blocks_per_context": wb,
            "ga_blocks_per_context": ga, "quantum_grants": quantum,
            "hbm_queue_depth_sectors_per_pc": qd,
            "hbm_frfcfs_window": rw,
            "sectors": sectors, "cycles": cycles,
            "sectors_per_cycle": round(sectors / cycles, 6), "arb_grants": grants,
            "idle_pc_slots": idle, "blocked_req_slots": blocked_req,
            "blocked_rsp_slots": blocked_rsp, "context_switches": switches,
            "hbm_act": act, "hbm_hit": hit, "hbm_conf": conf,
            "hbm_ref": ref, "hbm_backpressure_pc_cycles": bp,
            "hbm_read_latency_sum_ps": lat_sum, "hbm_read_latency_max_ps": lat_max,
            "rob_bytes_per_stack": 4 * wb * 4096,
            "rob_bytes_four_stacks": 16 * wb * 4096}


def run_single(tmp: Path) -> dict:
    binary = tmp / "single_65536.vvp"
    subprocess.run(["iverilog", "-g2012", "-s", "tb_hdc_v41x_idx_single_diag",
                    "-o", str(binary), *map(str, [*SOURCES[:3], *SINGLE_SOURCES])],
                   check=True, cwd=ROOT)
    run = subprocess.run(["vvp", str(binary)], check=True, capture_output=True,
                         text=True, timeout=900, cwd=ROOT)
    m = SINGLE.search(run.stdout)
    d = SINGLE_DIAG.search(run.stdout)
    assert m and d, run.stdout
    sectors, cycles = map(int, m.groups())
    act, hit, conf, ref, idle, blocked, bp, lat_sum, lat_max = map(int, d.groups())
    assert sectors == 65536 * 2 + 65536 // 8
    return {"keys": 65536, "sectors": sectors, "cycles": cycles,
            "sectors_per_cycle": round(sectors / cycles, 6),
            "hbm_act": act, "hbm_hit": hit, "hbm_conf": conf, "hbm_ref": ref,
            "idle_pc_slots": idle, "blocked_req_slots": blocked,
            "hbm_backpressure_pc_cycles": bp,
            "hbm_read_latency_sum_ps": lat_sum, "hbm_read_latency_max_ps": lat_max}


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="v41-range-arb-") as d:
        with ThreadPoolExecutor(max_workers=2) as pool:
            cases = list(pool.map(lambda case: run_case(Path(d), *case), CASES))
        single = run_single(Path(d))
    script = Path(__file__).resolve()
    record = {
        "schema": "opentallas.hdc-v41x-idx-range-pc-arb.v1",
        "status": "pass",
        "tools": {
            "iverilog": subprocess.run(["iverilog", "-V"], capture_output=True, text=True,
                                      check=True).stdout.splitlines()[0],
            "vvp": subprocess.run(["vvp", "-V"], capture_output=True, text=True,
                                 check=True).stderr.splitlines()[0],
        },
        "cases": cases,
        "single_range_reference": single,
        "one_stack_raw_peak_sectors_per_cycle": 31.25,
        "one_stack_adopted_effective_cap_sectors_per_cycle": 25.875,
        "four_stack_raw_peak_sectors_per_cycle": 125.0,
        "coverage": "Four concurrent quarter ranges on one 32-PC stack through one timed HBM3E model; every wanted key exact against sector pattern and every needed sector read once. Sticky grant quantum8/16/64/128 at fixed WB32/GA24 and HBM QD64/RW16; irregular 65-key and 262144-global-key scans. A separate matched one-range baseline is included.",
        "limitation": "One-stack source-pinned correctness and rate gate only. Raw range outputs are consumed independently with no quarter-order collector backpressure. No four-stack measured rate, array token, physical SRAM implementation, or die route. Partitioned ROB area is a design cost, not an adopted capacity budget.",
        "input_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in [*SOURCES, *SINGLE_SOURCES, script]},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(record, indent=2) + "\n")
    for row in cases:
        print(f"PASS N={row['global_keys']} WB={row['wb_blocks_per_context']} GA={row['ga_blocks_per_context']} Q={row['quantum_grants']} QD={row['hbm_queue_depth_sectors_per_pc']} RW={row['hbm_frfcfs_window']}: "
              f"{row['sectors']}/{row['cycles']}={row['sectors_per_cycle']} sectors/cycle")


if __name__ == "__main__":
    main()
