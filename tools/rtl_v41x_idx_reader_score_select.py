#!/usr/bin/env python3
"""Timed four-stack reader into a finite full-dimension score slice and top-K."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [
    "rtl/test/tb_hdc_v41x_idx_reader_score_select.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_idx_kstream.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_idx_kstream_range.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_idx_range_pc_arb.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_idx_quarter_ranges.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_idx_shard_quarter_collect.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_idx_score_slice.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_idx.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_idx_arith.sv",
    "rtl/hdc/ot_hdc_fastfp.sv",
    "rtl/hdc/ot_hdc_delay.sv",
    "rtl/hdc/v41/ot_hdc_tselect.sv",
    "rtl/hdc/v41/ot_hdc_tselect_q.sv",
    "tools/rtl_v41x_idx_reader_score_select.py",
]
PAT = re.compile(r"V41X_READER_SCORE_SELECT_PASS n=(\d+) checked=(\d+) scored=(\d+) "
                 r"selected=(\d+) sectors=(\d+) cycles=(\d+) handoffs=(\d+) "
                 r"collector_stall=(\d+) stream_stall=(\d+) first_score=(\d+) "
                 r"last_score=(\d+) last_select=(\d+)")


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="v41-reader-score-select-") as td:
        exe = Path(td) / "tb"
        subprocess.run(["iverilog", "-g2012", "-s",
                        "tb_hdc_v41x_idx_reader_score_select_runner", "-o", str(exe),
                        *[str(ROOT / p) for p in SOURCES if p.endswith(".sv")]], check=True)
        sim = subprocess.run(["vvp", str(exe)], capture_output=True, text=True, timeout=600)
    if sim.returncode:
        raise RuntimeError(sim.stdout[-4000:] + sim.stderr[-1000:])
    m = PAT.search(sim.stdout)
    assert m, sim.stdout
    values = list(map(int, m.groups()))
    assert values[:5] == [1040, 1040, 256, 8, 2210]
    rec = {
        "schema": "opentallas.v41-idx-reader-score-select.v1",
        "status": "pass_exact_bounded_one_quarter",
        "source_sha256": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in SOURCES},
        "measurement": dict(zip(("global_keys_read", "global_keys_checked", "quarter0_keys_scored",
                                 "quarter0_topk", "hbm_sectors", "cycles", "collector_handoffs",
                                 "collector_stall_cycles", "stream_stall_cycles", "first_score_cycle",
                                 "last_score_cycle", "last_select_cycle"), values)),
        "configuration": {"timed_hbm_stacks": 4, "pseudochannels_per_stack": 32,
                          "global_keys": 1040, "quarter0_keys": 256,
                          "key_dim": 128, "heads": 32, "score_slice_keys_per_cycle": 4,
                          "selector_lanes": 4, "selector_topk": 8,
                          "hbm_fixture": "all-zero sector, scale and FP4 codes; zero query and head weights",
                          "score_fixture": "golden BF16 +0 for all 256 quarter0 keys",
                          "topk_fixture": "eight lowest global indices, 0..7"},
        "scope": "Four-stack timed reader and quarter collector read/check all 1040 global keys; one finite NK4 full-dimension score slice scores quarter0's 256 keys in four subbeats per 16-key collector beat, then a W4 threshold selector chooses exact top8. Other three quarters are checked at reader output but not scored/selected. No full-die index rate or chip token claim.",
        "comparison_caution": "The prior 132-cycle always-ready reader and 4621-cycle old scorer gates have different sink widths and coverage; this quarter0 gate is not a like-for-like full-1040 speedup.",
    }
    out = ROOT / "results/rtl/v41_idx_reader_score_select.json"
    out.write_text(json.dumps(rec, indent=2) + "\n")
    print(out)


if __name__ == "__main__":
    main()
