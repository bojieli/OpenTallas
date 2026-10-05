#!/usr/bin/env python3
"""Source-pinned absolute HBM row versus local KVT row contract."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
RTL = ROOT / "rtl/hdc/v41x/ot_hdc_v41x_window_kv_blocks.sv"
TB = ROOT / "rtl/test/tb_hdc_v41x_window_kv_blocks.sv"
OUT = ROOT / "results/rtl/hdc_v41x_window_kv_blocks.json"
PATTERN = re.compile(r"PASS window KV exact block handoff abs=(\d+) local=(\d+)")


def run(output: Path = OUT):
    cases = [(0, 12345, 12345)] + [(1, row, min(row, 127))
                                    for row in (0, 127, 128, 129, 1048575)]
    covered = []
    with tempfile.TemporaryDirectory(prefix="v41_kv_abs_") as tmp:
        for split in (0, 1):
            exe = Path(tmp) / f"kv_{split}.vvp"
            cmd = ["iverilog", "-g2012", "-s", "tb_hdc_v41x_window_kv_blocks",
                   f"-Ptb_hdc_v41x_window_kv_blocks.SEPARATE_ROWS={split}",
                   "-o", str(exe), str(RTL), str(TB)]
            build = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=30)
            if build.returncode:
                raise RuntimeError(build.stderr[-1000:])
            for mode, row, local in (case for case in cases if case[0] == split):
                sim = subprocess.run(["vvp", "-n", str(exe), f"+ROW={row}"], cwd=ROOT,
                                     capture_output=True, text=True, timeout=30)
                match = PATTERN.search(sim.stdout)
                if sim.returncode or not match or tuple(map(int, match.groups())) != (row, local):
                    raise RuntimeError(f"window KV mismatch {mode=} {row=}: {sim.stdout[-1000:]} {sim.stderr[-1000:]}")
                covered.append({"separate_rows": bool(mode), "absolute_hbm_row": row,
                                "local_kvt_row": local, "blocks": 16, "status": "pass"})
    pins = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (RTL, TB, Path(__file__))}
    record = {"schema": "opentallas.rtl.v41x_window_kv_absolute.v1", "status": "pass",
              "claim_scope": "Standalone 16-block QDQ8 handoff; absolute HBM row and local KVT row remain "
                             "distinct at window saturation. No full die/token or rate claim.",
              "cases": covered, "source_sha256": pins}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(record, indent=2) + "\n")
    return record


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
