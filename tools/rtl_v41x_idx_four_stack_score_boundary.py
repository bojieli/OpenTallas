#!/usr/bin/env python3
"""Exact N1040 timed four-stack reader into the current pooled batch scorer."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [ROOT / p for p in (
    "rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_idx_kstream.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_idx_kstream_range.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_idx_range_pc_arb.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_idx_quarter_ranges.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_idx_shard_quarter_collect.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_idx_pool_batch.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_idx_pool_finish.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_idx_pcol.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_idx_hsum.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_idx_arith.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_wgt_tile.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_wgt_mac.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_wgt_bdot.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_wgt_red.sv",
    "rtl/hdc/ot_hdc_fastfp.sv",
    "rtl/hdc/ot_hdc_delay.sv",
    "rtl/test/tb_hdc_v41x_idx_four_stack_score_boundary.sv",
)]
CPP = ROOT / "rtl/test/hdc_v41x_idx_four_stack_score_boundary.cpp"
BASELINE = ROOT / "results/rtl/hdc_v41x_idx_four_stack_pipeline_icarus_short.json"
OUT = ROOT / "results/rtl/hdc_v41x_idx_four_stack_score_boundary.json"
PAT = re.compile(
    r"V41X_SCORE_BOUNDARY_PASS n=(\d+) quantum=(\d+) checked=(\d+) scored=(\d+) "
    r"sectors=(\d+) cycles=(\d+) handoffs=(\d+) collector_stall=(\d+) "
    r"stream_stall=(\d+) collector_empty=(\d+) request_stalls=(\d+) response_stalls=(\d+) "
    r"score_events=(\d+) first_handoff=(-?\d+) last_handoff=(-?\d+) "
    r"first_score=(-?\d+) last_score=(-?\d+) score_span=(\d+)"
)


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="v41-four-score-") as td:
        obj = Path(td) / "obj"
        command = ["verilator", "--cc", "--exe", "--build", "-j", "2",
                   "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNOPTFLAT",
                   "--output-split", "20000", "--output-split-cfuncs", "10000",
                   "--top-module", "tb_hdc_v41x_idx_four_stack_score_boundary",
                   "-GNKEYS=1040", "-GQUANTUM=64", "--Mdir", str(obj),
                   *map(str, SOURCES), str(CPP)]
        started = time.perf_counter()
        build = subprocess.run(command, capture_output=True, text=True, cwd=ROOT, timeout=5400)
        if build.returncode:
            (ROOT / "results/rtl/v41_four_stack_score_boundary_build_failure.log").write_text(
                build.stdout + "\n" + build.stderr)
            raise RuntimeError("Verilator build failed; see results/rtl/v41_four_stack_score_boundary_build_failure.log\n"
                               + build.stderr[-4000:])
        build_wall = round(time.perf_counter() - started, 3)
        binary = obj / "Vtb_hdc_v41x_idx_four_stack_score_boundary"
        started = time.perf_counter()
        run = subprocess.run([str(binary)], capture_output=True, text=True, cwd=ROOT, timeout=600)
        sim_wall = round(time.perf_counter() - started, 3)
        if run.returncode:
            raise RuntimeError(f"N1040 scorer boundary failed:\n{run.stdout[-4000:]}\n{run.stderr[-4000:]}")
        match = PAT.search(run.stdout)
        if not match:
            raise RuntimeError(f"N1040 scorer boundary missing pass marker:\n{run.stdout[-4000:]}")
        vals = list(map(int, match.groups()))
        print(run.stdout.strip(), flush=True)
    (n, quantum, checked, scored, sectors, cycles, handoffs, collector_stall,
     stream_stall, collector_empty, request_stalls, response_stalls, score_events,
     first_handoff, last_handoff, first_score, last_score, score_span) = vals
    assert (n, quantum, checked, scored, sectors, handoffs) == (1040, 64, 1040, 1040, 2210, 17)
    assert first_handoff >= 0 and last_handoff >= first_handoff
    assert first_score >= 0 and last_score >= first_score and score_span == last_score - first_score + 1
    short = json.loads(BASELINE.read_text())
    baseline = next(r for r in short["cases"] if r["keys"] == 1040)
    assert baseline["quantum"] == 64 and baseline["cycles"] == 132
    script = Path(__file__).resolve()
    rec = {
        "schema": "opentallas.hdc-v41x-idx-four-stack-score-boundary.v1",
        "status": "pass", "source_commit": "d1a3d3fc13b47d3e3dea9eca2e44b46b8b617df0",
        "configuration": {"keys": 1040, "quantum": 64, "stacks": 4,
            "quarter_contexts_per_stack": 4, "streamer_WB": 32, "streamer_GA": 24,
            "hbm_QD": 64, "hbm_RQD": 32, "hbm_REFPB": 3,
            "hbm_data": "all-zero 256-bit sector, MEM_MODE=0, MEM_WORDS=1",
            "query_data": "all-zero 264-bit read words, RL=2",
            "head_weights": "32 heads, zero BF16 weights and zero query scales",
            "batch": "current ot_hdc_v41x_idx_pool_batch G4/M2/IH32, b_keep all ones",
            "output_sink": "score output observed every cycle without backpressure"},
        "measurement": {"checked_collector_keys": checked, "keys_scored": scored,
            "hbm_sectors": sectors, "total_cycles": cycles,
            "collector_handoffs": handoffs,
            "collector_output_stall_cycles": collector_stall,
            "stream_output_stall_cycles": stream_stall,
            "collector_no_output_cycles": collector_empty,
            "hbm_request_stall_cycles": request_stalls,
            "hbm_response_stall_cycles": response_stalls,
            "score_output_events_including_padding": score_events,
            "first_collector_handoff_cycle": first_handoff,
            "last_collector_handoff_cycle": last_handoff,
            "first_score_cycle": first_score,
            "last_score_cycle": last_score,
            "score_output_span_cycles": score_span,
            "build_wall_seconds": build_wall, "simulation_wall_seconds": sim_wall},
        "always_ready_comparison": {"source": str(BASELINE.relative_to(ROOT)),
            "keys": 1040, "sectors": baseline["sectors"], "delivery_cycles": baseline["cycles"]},
        "coverage": "Every 64-key collector beat checks exact valid mask, last marker, zero key and refusal bit. Every valid batch score checks its unique global index, zero BF16 score and no fault. Expected HBM sector count is independently calculated from 16 quarter ranges.",
        "limitation": "Deterministic all-zero HBM/query/weight fixture and one current G4/M2 batch tile. The SHARDED=1 pool_adapt wrapper still instantiates the older one-sector serial reader; its query loader and vector-memory writer, selector, KV, weight fetch, physical timing, and model token path are not exercised. This measures only the current scorer service boundary and does not imply 64 scores per cycle or production token rate.",
        "input_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in [*SOURCES, CPP, BASELINE, script]},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rec, indent=2) + "\n")


if __name__ == "__main__":
    main()
