"""FACEHOLD-S81 11-10: ft OUT-FACE lockup latch (plan clock.ft_face_lockup, gen_rtl/bind ot_dp_lk u_fl_<o>_<n-1> after
the last station) and its per-item event (changes only clock.ft_face_lockup, names only the given types).  Bind end to
end (strict bind + bind_verify, 0 transport stages) needs Yosys like test_ft_hop_lockup.py."""
import json
import shutil
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bind  # noqa: E402
import ft_face_lockup_item_event as E  # noqa: E402
import gen_rtl  # noqa: E402

EX = HERE / "examples" / "bind_tiny"


def _slot(name, k, w=8):
    return dict(name=name, width=w, stations=k, regs_um=[[100.0 * j, 0.0] for j in range(k)])


def _plan():
    return dict(partition_types=dict(a=dict(ft_slots=[_slot("ft0", 3), _slot("ft1", 1)]),
                                     b=dict(ft_slots=[]),
                                     c=dict(ft_slots=[_slot("ft0", 4, 16)])),
                clock=dict(tap_window=dict(window_ps=140), ft_hop_lockup=dict(types=["c"]), x=1), reset=dict(y=2),
                lanes=[1])


def test_plan_switch():
    f = gen_rtl.ft_face_lockup
    assert not f({}, "t") and not f({"clock": {}}, "t") and not f({"clock": {"ft_hop_lockup": {"types": ["t"]}}}, "t")
    assert f({"clock": {"ft_face_lockup": {"types": ["t"]}}}, "t")
    assert not f({"clock": {"ft_face_lockup": {"types": ["u"]}}}, "t")
    assert bind.ft_face_lockup({"clock": {"ft_face_lockup": {"types": ["t"]}}}, "t")
    # the two switches are independent
    assert not gen_rtl.ft_hop_lockup({"clock": {"ft_face_lockup": {"types": ["t"]}}}, "t")


def test_census_one_latch_per_slot_with_epoch():
    c = E.face_census(_plan(), "a")
    assert (c["slots"], c["latches"], c["latch_bits"]) == (2, 2, 2 * 9)
    assert [r["latch_inst"] for r in c["per_slot"]] == ["u_fl_ft0_o_2", "u_fl_ft1_o_0"]
    assert E.face_census(_plan(), "b")["latches"] == 0


def test_apply_changes_only_the_face_list():
    p = _plan()
    out = E.apply(p, ["c", "a", "a"])
    assert out["clock"]["ft_face_lockup"] == {"types": ["a", "c"]}
    assert out["partition_types"] == p["partition_types"] and out["reset"] == p["reset"] and out["lanes"] == p["lanes"]
    assert {k: v for k, v in out["clock"].items() if k != "ft_face_lockup"} == p["clock"]
    assert "ft_face_lockup" not in p["clock"]
    assert out["clock"]["ft_hop_lockup"] == {"types": ["c"]}      # hop list untouched
    assert [t for t in out["partition_types"] if gen_rtl.ft_face_lockup(out, t)] == ["a", "c"]


def test_apply_refuses():
    with pytest.raises(ValueError):
        E.apply(_plan(), ["zz"])
    with pytest.raises(ValueError):
        E.apply(_plan(), ["b"])                                   # no ft slot: no out face
    with pytest.raises(ValueError):
        E.apply(_plan(), [])


def test_fragment_refuses_existing_item_inputs(tmp_path):
    cfg = {"dies": {"s81": {"item_inputs": {"a": {"plan": "x"}}}}}
    (tmp_path / "c.json").write_text(json.dumps(cfg))
    with pytest.raises(ValueError):
        E.main(["fragment", str(tmp_path / "f.json"), "--die", "s81", "--items", "a", "--plan", "p", "--kit-rtl-script",
                "s", "--cfg", str(tmp_path / "c.json")])
    assert E.main(["fragment", str(tmp_path / "f.json"), "--die", "s81", "--items", "b", "--plan", "p",
                   "--kit-rtl-script", "s", "--cfg", str(tmp_path / "c.json")]) == 0
    f = json.loads((tmp_path / "f.json").read_text())
    assert list(f["set"]) == ["item_inputs"] and list(f["set"]["item_inputs"]) == ["b"] and f["applied"] is False


HAVE_YOSYS = bool(shutil.which("docker")) or bool(__import__("os").environ.get("OT_BIND_YOSYS"))


@pytest.mark.skipif(not HAVE_YOSYS, reason="no Yosys")
@pytest.mark.parametrize("hop,face", [(False, False), (False, True), (True, True)])
def test_bind_ft_face_latch_proves(tmp_path, hop, face):
    P = json.loads((EX / "die_plan_lanes.json").read_text())
    P["partition_types"]["tf"]["ft_slots"][0]["stations"] = 3
    P["latency"]["lanes"]["a0y"].update(cycles=5, stations=3)
    if hop:
        P.setdefault("clock", {})["ft_hop_lockup"] = {"types": ["tf"]}
    if face:
        P.setdefault("clock", {})["ft_face_lockup"] = {"types": ["tf"]}
    P["asbuilt"]["base"] = str(EX)
    pf = tmp_path / "p.json"
    pf.write_text(json.dumps(P))
    out = tmp_path / "o"
    for c in ("elab", "bind", "verify"):
        rc = bind.main([c, str(pf), "--out", str(out), "--mem", "4"])
        if rc:
            break
    ft = (out / "rtl" / "bt_tf.sv").read_text()
    cells = (out / "rtl" / "bind_cells.sv").read_text()
    n_lk = (2 if hop else 0) + (1 if face else 0)
    assert ft.count("ot_dp_lk #(.W(9))") == n_lk, ft
    assert ("u_fl_y_o_2" in ft) == face                          # the out-face latch after the last station
    if face:
        assert "u_fl_y_o_2 (.clk(clk), .d(y_o_s2), .q(y_o));" in ft, ft
    assert ("module ot_dp_lk" in cells) == bool(n_lk)
    assert ft.count("ot_dp_st #(.W(8))") == 3
    v = json.loads((out / "verify_report.json").read_text())
    assert rc == 0 and v["verdict"] == "PASS" and v["counts"]["mismatched"] == 0, v.get("mismatches", [])[:3]
