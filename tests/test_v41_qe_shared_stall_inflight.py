"""Record checks for the shared-HBM QE in-flight sweep (tools/v41_qe_shared_stall_inflight.py)."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REC = ROOT / "results/rtl/v41_qe_shared_stall_inflight.json"


def _rec():
    return json.loads(REC.read_text())


def test_sources_pinned():
    for rel, digest in _rec()["source_sha256"].items():
        assert hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() == digest, rel


def test_every_point_exact():
    rec = _rec()
    assert rec["status"] == "pass"
    for c in rec["cases"]:
        assert c["status"] == "pass" and c["errors"] == 0 and c["masked"] == 4 and c["consumed"] == 3840


def test_defaults_reproduce_prior_record():
    reg = _rec()["default_regression_vs_prior_record"]
    assert reg and all(v["identical"] for v in reg.values())


def test_default_geometry_is_room_bound():
    """At the qualified geometry every blocked request cycle is a pseudo-channel room refusal."""
    rec = _rec()
    for c in rec["cases"]:
        if (c["la"], c["w_nd"], c["w_depth"], c["w_room"]) == (8, 8, 16, 16):
            lim = c["limiter"]
            assert lim["la_pc_room"] == lim["la_blocked"] > 0 and lim["adapter_bp"] == 0


def test_room_relief_raises_supply():
    rec = _rec()
    base = next(c for c in rec["cases"] if (c["la"], c["w_nd"], c["w_depth"], c["w_room"], c["k"]) == (8, 8, 16, 16, "noK"))
    assert rec["best"]["bytes_per_cycle_row_phase"] > 5 * base["bytes_per_cycle_row_phase"]
