"""W11 ring layout at full capacity: writer naming gate and the two-user die gate -- records current (fast)."""

import hashlib
import json
from pathlib import Path

from tools import w11_idx_ring_naming as naming

ROOT = Path(__file__).resolve().parents[1]
MU = ROOT / "results/rtl/w11_die_idx_ring_mu_gate.json"


def test_naming_record_current_and_passing():
    rec = json.loads(naming.OUT.read_text())
    assert rec["status"] == "pass" and rec["sources_sha256"] == naming.sources()
    r, p = rec["result"], rec["parameters"]
    assert rec["ring"]["slots_per_user_per_stack"] == 65568 and rec["ring"]["blocks_per_region"] == 1090
    assert r["steps"] == r["writer_keys"] == r["port_records"] == (p["NA1"] - p["NA0"]) + (p["NB1"] - p["NB0"])
    assert r["final_counts"] == [p["NA1"], p["NB1"]] and p["NB1"] > 65568
    assert r["scans_of_a_wrapped_ring"] > 0 and r["steps_at_slot_past_1024"] > 0 and r["migrations"] >= 4
    assert r["keys_checked"] > 0 and r["scans"] == 2 * r["steps"]
    assert rec["negative_control"]["must_fail"] and not rec["negative_control"]["passed"]


def test_mu_die_gate_current_and_passing():
    rec = json.loads(MU.read_text())
    assert rec["status"] == "pass"
    for path, digest in rec["sources_sha256"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest, path
    cfg = rec["configuration"]
    assert cfg["IDX_RING_RSB"] == 64 and cfg["IDX_RING_RTAIL"] == 32 and cfg["IDX_RING_MU"] == 1
    steps = rec["steps"]
    assert [s["user"] for s in steps] == [1, 2, 1, 2] and [s["position"] for s in steps] == [7, 63, 8, 64]
    for s in steps:
        assert s["verdict"] == "PASS" and s["next_token"] == s["isa_next_token"] and s["fault"] == 0
        assert s["logit_mismatches"] == s["vm_mismatches"] == s["kv_mismatches"] == s["key_carry_mismatches"] == 0
    assert steps[2]["input_token"] == steps[0]["next_token"] and steps[3]["input_token"] == steps[1]["next_token"]
    assert all(s["key_carry"]["keys_checked_cumulative"] > 0 for s in steps[2:])
    assert rec["images_chained"] and rec["rom_images_identical_across_steps"]
