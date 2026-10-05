#!/usr/bin/env python3
"""Timed HBM direct-start range stream gate for compact V4.1 index shards."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [ROOT / p for p in (
    "rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_idx_kstream.sv",  # shared unchanged datapath
    "rtl/hdc/v41x/ot_hdc_v41x_idx_kstream_range.sv",
    "rtl/test/tb_hdc_v41x_idx_kstream_range.sv",
)]
OUT = ROOT / "results/rtl/hdc_v41x_idx_kstream_range.json"
CASES = ((0, 40), (8, 40), (56, 97), (1000, 1050), (1016, 20),
         (1000, 10000), (1000, 100000))
PAT = re.compile(r"V41X_RANGE_PASS skip=(\d+) count=(\d+) checked=(\d+) sectors=(\d+) cycles=(\d+)")


def main() -> None:
    rows = []
    with tempfile.TemporaryDirectory(prefix="v41-range-") as t:
        tmp = Path(t)
        for skip, count in CASES:
            binary = tmp / f"range_{skip}_{count}.vvp"
            subprocess.run(["iverilog", "-g2012", "-s", "tb_hdc_v41x_idx_kstream_range",
                            f"-Ptb_hdc_v41x_idx_kstream_range.SKIP={skip}",
                            f"-Ptb_hdc_v41x_idx_kstream_range.COUNT={count}",
                            "-o", str(binary), *map(str, SOURCES)],
                           check=True, cwd=ROOT)
            run = subprocess.run(["vvp", str(binary)], check=True,
                                 capture_output=True, text=True, timeout=360, cwd=ROOT)
            match = PAT.search(run.stdout)
            assert match, run.stdout
            s, n, checked, sectors, cycles = map(int, match.groups())
            expected = 2 * n + (s + n + 7) // 8 - s // 8
            assert (s, n, checked, sectors) == (skip, count, count, expected)
            rows.append({"skip": s, "keys": n, "sectors": sectors,
                         "cycles": cycles,
                         "sectors_per_cycle": round(sectors / cycles, 6)})
    long = rows[-1]
    assert long["sectors_per_cycle"] > 29.0, long
    script = Path(__file__).resolve()
    rec = {
        "schema": "opentallas.hdc-v41x-idx-kstream-range.v1", "status": "pass",
        "cases": rows,
        "long_range_stack_peak_sector_per_cycle": 31.25,
        "long_range_fraction_of_raw_peak": round(long["sectors_per_cycle"] / 31.25, 6),
        "coverage": "Every wanted key bit-exact against timed HBM sector pattern; skips 0, 8, 56, 1000 and 1016, intra-column starts, 1024-key boundary, exact sector count with no prefix rereads, and sustained 100k-key scan.",
        "limitation": "One range on one stack, raw stream includes unrequested prefix placeholders. No stack/quarter multi-context arbiter, quarter-order collector, array token, or physical closure. Four-stack rate is not measured here.",
        "input_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in [*SOURCES, script]},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rec, indent=2) + "\n")
    print("PASS 7 direct-start ranges; 100k keys: "
          f"{long['sectors']}/{long['cycles']}={long['sectors_per_cycle']} sectors/cycle")


if __name__ == "__main__":
    main()
