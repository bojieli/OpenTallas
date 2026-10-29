import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import clock_duty as C
import die_sta_related as D


def raw(tmp_path, text):
    p = tmp_path / "arr.txt"
    p.write_text(text)
    return p


def test_same_physical_edges_legacy_v1(tmp_path):
    p = raw(tmp_path, "T t_a 100 90 20\nF t_a 140.544 100 21\n")
    legacy = C.report(p, "FF", "inv2", "legacy")
    assert legacy["duty_max"] == pytest.approx((416.5+D.SPICE_CLOCK_CAL_INV["FF"]*40.544)/833)
    p.write_text("# OT_EDGES v1\nT t_a 100 90 20\nF t_a 140.544 130.544 21\n")
    v1 = C.report(p, "FF", "inv2")
    assert v1["duty_max"] == legacy["duty_max"]
    assert v1["outside_45_55"] == 0
    assert C.report(p, "FF", "buf")["outside_45_55"] == 1


def test_shared_factor_is_not_copied(tmp_path, monkeypatch):
    p = raw(tmp_path, "# OT_EDGES v1\nT t_a 100 90 20\nF t_a 110 99 21\n")
    monkeypatch.setitem(D.SPICE_CLOCK_CAL_INV, "TT", 2.)
    assert C.report(p, "TT", "inv")["duty_max"] == pytest.approx((416.5+20)/833)


def test_ambiguity_controls(tmp_path):
    p = raw(tmp_path, "T t_a 100 90 20\nF t_a 140 130 21\n")
    with pytest.raises(ValueError, match="ambiguous"):
        C.report(p, "TT", "inv")
    with pytest.raises(ValueError, match="disagrees"):
        C.report(p, "TT", "inv", "legacy")
    with pytest.raises(ValueError, match="requires OT_EDGES"):
        C.report(p, "TT", "inv", "v1")
    p.write_text("# OT_EDGES v1\nT t_a 100 90 20\nF t_a 140 130 21\n")
    with pytest.raises(ValueError, match="conflicts"):
        C.report(p, "TT", "inv", "legacy")


@pytest.mark.parametrize("text", [
    "T t_a 100 90 20\n", "T t_a 100 90 20\nF t_b 110 99 21\n",
    "T t_a 100 90 20\nF t_a nan 99 21\n", "T t_a 100 90\nF t_a 110 99\n",
    "T t_a 100 90 20\nT t_a 100 90 20\nF t_a 110 99 21\n"])
def test_incomplete_or_invalid_readout_fails(tmp_path, text):
    with pytest.raises(ValueError):
        C.report(raw(tmp_path, "# OT_EDGES v1\n"+text), "TT", "inv")


def test_mixed_requires_decomposition(tmp_path):
    p = raw(tmp_path, "# OT_EDGES v1\nT t_a 100 90 20\nF t_a 110 99 21\n")
    with pytest.raises(ValueError, match="components"):
        C.report(p, "TT", "mixed")


def test_ot_clk_duty_entrypoint(tmp_path):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "clk"))
    import ot_clk
    p = raw(tmp_path, "# OT_EDGES v1\nT t_a 100 90 20\nF t_a 110 99 21\n")
    out = tmp_path / "duty.json"
    assert ot_clk.main(["duty", str(p), str(p), str(out), "--clock-cell", "inv2"]) == 0
    assert json.loads(out.read_text())["corners"]["FF"]["clock_cell"] == "inv2"


def test_proof_wrong_corner_is_rejected(tmp_path):
    p = tmp_path / "proof.json"
    p.write_text(json.dumps(dict(corner="TT", taps=[])))
    with pytest.raises(ValueError, match="corner differs"):
        C.report(p, "FF", "mixed")


def test_mixed_uses_shared_component_local_parity(tmp_path):
    from clock_components import scaled
    keys = ("late_ps", "early_ps", "fall_late_ps", "fall_early_ps")
    part = dict(zip(keys, (100., 90., 110., 99.)), master="BUFx24_ASAP7_75t_R", source_rise_input_edge="fall")
    tap = dict(part, port="t_a", slew_ps=20, clock_components=[part])
    p = tmp_path / "proof.json"
    p.write_text(json.dumps(dict(clock_components_basis="measured", taps=[tap])))
    v = scaled([part], tap, "FF", "spice_edge")
    assert C.report(p, "FF", "mixed")["duty_max"] == pytest.approx((416.5+v["fall_late_ps"]-v["late_ps"])/833)
    tap["clock_components"][0]["late_ps"] += 1
    p.write_text(json.dumps(dict(clock_components_basis="measured", taps=[tap])))
    # Mutant: total no longer matches raw arrival; no factor fallback.
    tap["late_ps"] -= 1
    p.write_text(json.dumps(dict(clock_components_basis="measured", taps=[tap])))
    with pytest.raises(ValueError, match="sum"):
        C.report(p, "FF", "mixed")
