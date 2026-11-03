"""DIE-S81-50 11-03: sign-off face_guard types the flat synth netlist from the hierarchical 1_2_yosys.v beside it
(as the kit face_guard_core.py does), so the land_slot registered one-hot proof sees ot_pl_land_local_kw."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import signoff
from test_face_guard import _flat_like_odb, _registered_onehot_vehicle


def kit(tmp_path, hier_text):
    hier = _registered_onehot_vehicle()
    (tmp_path / "1_synth.v").write_text(_flat_like_odb(hier))
    if hier_text is not None:
        (tmp_path / "1_2_yosys.v").write_text(hier_text)
    (tmp_path / "land_slots.json").write_text(json.dumps(
        {"schema": "opentallas.core_land_slots.v1", "buses": {"d": {"D": 4, "form": "hold_mux"}}}))
    return dict(kit=str(tmp_path), synth=str(tmp_path / "1_synth.v"))


def test_flat_synth_typed_from_hierarchical_netlist(tmp_path):
    disc = kit(tmp_path, _registered_onehot_vehicle())
    r = signoff.run_face_guard(disc, clock_ports=("fclk",))
    assert r["verdict"] == "PASS", r


def test_untyped_or_mistyped_flat_synth_still_fails_closed(tmp_path):
    disc = kit(tmp_path, None)
    r = signoff.run_face_guard(disc, clock_ports=("fclk",))
    assert r["verdict"] == "FAIL" and "land_slot" in r["fail_counts"], r
    (tmp_path / "1_2_yosys.v").write_text(_registered_onehot_vehicle("type"))
    r = signoff.run_face_guard(disc, clock_ports=("fclk",))
    assert r["verdict"] == "FAIL" and "land_slot" in r["fail_counts"], r
    (tmp_path / "1_2_yosys.v").write_text(_registered_onehot_vehicle().replace("module top(", "module other("))
    assert signoff.synth_types(disc["synth"], Path(disc["synth"]).read_text()) is None
