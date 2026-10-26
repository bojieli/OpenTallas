#!/usr/bin/env python3
"""Observe the matched mutant at a control-derived cycle deadline.
This reads existing logs only; it does not stop or modify either simulation.
A bounded failure here is separate from the original binary's terminal verdict.
"""
from pathlib import Path
import json
import re
import sys
root = Path(__file__).resolve().parent
positive = (root / "smoke/run.log").read_text()
negative = (root / "mut_p2l_seg/live_snapshot.log").read_text()
m = re.search(r"^WAVE PASS .*emitted=(\d+) .*cycles=(\d+) errors=0$", positive, re.M)
assert m, "matched positive has no exact PASS"
emitted, cycles = map(int, m.groups())
# The unchanged bench emits progress every 200000 cycles. Use the first
# observable deadline after completion of the matched positive, fixed before
# inspecting negative progress; no wall-clock cutoff is used.
heartbeat = 200000
deadline = ((cycles + heartbeat - 1) // heartbeat) * heartbeat
rows = [tuple(map(int, m.groups())) for m in re.finditer(
    r"^WAVE_HB cyc=(\d+) emitted=(\d+) closes=\d+ seeds=\d+ p2_tx=(\d+)", negative, re.M)]
row = next((r for r in rows if r[0] == deadline), None)
assert row, "negative has not reached the fixed deadline"
result = dict(schema="opentallas.mtp-wave-bounded-progress.v1",
    source_commit="735d2e8e7", positive_case="smoke", mutant_case="mut_p2l_seg",
    matched_params="tools/mtp_wave_bench.py SMOKE", positive_emitted=emitted,
    positive_cycles=cycles, deadline_cycles=deadline, mutant_emitted=row[1],
    mutant_p2_transactions=row[2],
    bounded_verdict="FAIL" if row[1] < emitted else "PASS",
    original_simulator_terminal_verdict="PENDING",
    observation="segmentation corruption fails completion by the matched control deadline")
print(json.dumps(result, indent=2))
sys.exit(1 if result["bounded_verdict"] == "FAIL" else 0)
