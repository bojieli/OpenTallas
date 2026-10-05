#!/usr/bin/env python3
"""Tagged per-PC sharded index reader: exact timed gate and measured gap."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RTL = ROOT / "rtl/hdc/v41x/ot_hdc_v41x_idx_shard_reader_pc.sv"
HBM = ROOT / "rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv"
TIMED_TB = ROOT / "rtl/test/tb_hdc_v41x_idx_shard_reader_pc_timed.sv"
PAIRED_TB = ROOT / "rtl/test/tb_hdc_v41x_idx_shard_roundtrip_pc.sv"
WRITER = ROOT / "rtl/hdc/v41x/ot_hdc_v41x_idx_pool_kwr.sv"
BRIDGE = ROOT / "rtl/hdc/v41x/ot_hdc_v41x_idx_pool_hbm_bridge.sv"
OUT = ROOT / "results/rtl/hdc_v41x_idx_shard_reader_pc.json"


def run_case(tmp: Path, top: str, sources: list[Path]) -> str:
    binary = tmp / f"{top}.vvp"
    subprocess.run(["iverilog", "-g2012", "-s", top, "-o", str(binary),
                    *map(str, sources)], check=True, cwd=ROOT)
    return subprocess.run(["vvp", str(binary)], check=True, capture_output=True,
                          text=True, timeout=120, cwd=ROOT).stdout


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="v41-shard-pc-") as t:
        tmp = Path(t)
        paired = run_case(tmp, "tb_hdc_v41x_idx_shard_roundtrip_pc",
                          [WRITER, BRIDGE, HBM, RTL, PAIRED_TB])
        timed = run_case(tmp, "tb_hdc_v41x_idx_shard_reader_pc_timed",
                         [HBM, RTL, TIMED_TB])
    assert "V41X_SHARD_ROUNDTRIP_PASS rows=65 records=65 writes=195" in paired, paired
    assert "V41X_SHARD_READER_PC_TIMED_PASS scans=1" in timed, timed
    rows = [tuple(map(int, m.groups())) for m in re.finditer(
        r"ROUNDTRIP n=(\d+) keys=(\d+) sectors=(\d+) cycles=(\d+)", paired)]
    assert [n for n, _, _, _ in rows] == [1, 40, 65], paired
    match = re.search(r"SCAN n=(\d+) keys=(\d+) sectors=(\d+) beats=(\d+) ref=(\d+) cycles=(\d+)", timed)
    assert match, timed
    n, keys, sectors, beats, refs, cycles = map(int, match.groups())
    assert (n, keys, sectors, beats, refs, cycles) == (1040, 1040, 2210, 17, 1, 1026)
    target = 125.0
    measured = sectors / cycles
    script = Path(__file__).resolve()
    rec = {
        "schema": "opentallas.hdc-v41x-idx-shard-reader-pc.v1", "status": "pass_exact_below_bandwidth_target",
        "paired_roundtrip": [{"keys": a, "sectors": c, "cycles": d} for a, _, c, d in rows],
        "timed_1040_key_scan": {"keys": keys, "sectors": sectors, "cycles": cycles,
                                "sectors_per_cycle": round(measured, 6)},
        "target_sectors_per_cycle": target,
        "fraction_of_target": round(measured / target, 6),
        "architecture": "Two in-flight 64-key beats, one tagged request per pseudo-channel per cycle, 128 PC ports across four stacks, 192 descriptor positions per beat.",
        "coverage": "Writer/bridge/four timed-HBM exact N=1/40/65; independent four-stack NPC32 timed-HBM exact N=1040, 2210 unique sectors and all 1040 keys/code/scale/refusal/last checked.",
        "limitation": "Measured at 2.154 sectors/cycle, far below the 125 target. The two-beat window cannot hide HBM latency; descriptor priority and wide output mux are not placed/routed. This is negative throughput evidence, not an adopted design or full-token gate.",
        "input_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in [WRITER, BRIDGE, HBM, RTL, TIMED_TB, PAIRED_TB, script]},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rec, indent=2) + "\n")
    print(paired.strip())
    print(timed.strip())


if __name__ == "__main__":
    main()
