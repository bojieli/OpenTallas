"""Focused gate of the opt-in local K arbitration partitions (tools/rtl_chip_v41x_karb_local.py)."""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REC = ROOT / "results/rtl/chip_v41x_karb_pipe_equiv.json"


def test_record_pins_current_sources():
    d = json.loads(REC.read_text())
    for p, h in d["sources"].items():
        assert hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == h, p


def test_transaction_equivalence_and_steering():
    d = json.loads(REC.read_text())
    assert all(r["pass"] and r["arms_identical"] for r in d["runs"])
    assert all(r["pass"] for r in d["kv_prefetch_bench"]) and len(d["kv_prefetch_bench"]) == 5
    assert d["added_uncontended_k_round_trip_cycles"] == [4]
    m = re.search(r"n=(\d+) got=(\d+) pipe_got=(\d+) bad=(\d+) .* ingress_stalls=(\d+)", d["hash_steering_exhaustive"]["summary"])
    n, got, pgot, bad, stalls = map(int, m.groups())
    assert n == got == pgot == 131072 and bad == 0 and stalls == 0
