"""tests for die_sta.py: netlist parse, ILM extraction, SPEF filter, seam discovery, flat == ilm on a tiny pair."""
import json
import shutil
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import die_sta as D  # noqa: E402

TD = HERE / "testdata" / "die_sta"

# a liberty stand-in for the cells of testdata/die_sta (directions, clock pins, sequential)
FAKE = {
    "BUFx2_ASAP7_75t_R": dict(pins={"A": "input", "Y": "output"}, clock=set(), seq=False),
    "INVx1_ASAP7_75t_R": dict(pins={"A": "input", "Y": "output"}, clock=set(), seq=False),
    "NAND2xp33_ASAP7_75t_R": dict(pins={"A": "input", "B": "input", "Y": "output"}, clock=set(), seq=False),
    "DFFHQNx1_ASAP7_75t_R": dict(pins={"CLK": "input", "D": "input", "QN": "output"}, clock={"CLK"}, seq=True),
}


def _part():
    return D.read_verilog(TD / "part_a.v")["part_a"]


def test_read_verilog():
    nl = _part()
    assert [p[1] for p in nl.ports] == ["clk", "a_i", "a_o", "x_i", "x_o"]
    assert ("input", "a_i", 1, 0) in nl.ports
    assert len(nl.insts) == 14 and nl.assigns == [("x_o", "x_i")]
    top = D.read_verilog(TD / "die_top.v")["pair_top"]
    conns = dict(top.insts[0][2])
    assert conns["a_o"] == ["w_a[1]", "w_a[0]"]          # whole-bus reference expanded msb first


def test_ilm_cones():
    red, kept, wires, st = D.extract_ilm(_part(), FAKE, {"clk"})
    keep = {i for _, i, c in red.insts if len(c) > 1 or i in ("ckb1", "g1")}
    names = {i: c for _, i, c in red.insts}
    # interface registers + output buffers + the clock buffer of the interface registers
    for i in ("s0_0", "s0_1", "s2_0", "s2_1", "ob0", "ob1", "ckb1", "g1"):
        assert i in names
    # internal register stage and its logic are gone, except as side loads (one input pin)
    assert "mid_0" not in names and "i0" not in names
    assert [p for p, _ in names["b0"]] == ["A"] and [p for p, _ in names["ckb2"]] == ["A"]
    # a kept gate's input from removed logic is left open
    assert [p for p, _ in names["g1"]] == ["B", "Y"]
    assert [p for p, _ in names["s2_0"]] == ["CLK", "QN"]
    assert red.assigns == [("x_o", "x_i")]
    assert {"s1q[0]", "ck1", "m1[1]"} <= kept and "m0[0]" not in kept and "n_int" not in kept
    assert st["ilm_cells"] == 8 and st["cells"] == 14 and keep


def test_filter_spef(tmp_path):
    _, kept, _, _ = D.extract_ilm(_part(), FAKE, {"clk"})
    n, tot = D.filter_spef(TD / "part_a.spef", tmp_path / "f.spef", kept)
    assert (n, tot) == (1, 3)
    t = (tmp_path / "f.spef").read_text()
    assert "*D_NET *2 " in t and "*D_NET *1 " not in t and "*4 mid_0" not in t and "*5 s2_0" in t


def test_seams(tmp_path):
    p = tmp_path / "parts" / "a"
    p.mkdir(parents=True)
    shutil.copy(TD / "part_a.v", p / "6_final.v")
    top = D.read_verilog(TD / "die_top.v")["pair_top"]
    s = D.die_seams(top, D.find_parts(tmp_path / "parts"))
    got = sorted((x["src"], x["dst"], x["dst_pin"]) for x in s)
    assert got == [("u0", "u1", "a_i[0]"), ("u0", "u1", "a_i[1]"), ("u0", "u1", "x_i")]


def test_liberty_parse(tmp_path):
    lib = tmp_path / "x.lib"
    lib.write_text('library (x) { cell (DFF) { ff (IQ, IQN) { next_state : "D"; } pin (CLK) { direction : input; '
                   'clock : true; } pin (D) { direction : input; } pin (Q) { direction : output; } } '
                   'cell (BUF) { pin (A) { direction : input; } pin (Y) { direction : output; } } }')
    c = D.read_liberty_cells([lib])
    assert c["DFF"]["seq"] and c["DFF"]["clock"] == {"CLK"} and not c["BUF"]["seq"]
    assert c["BUF"]["pins"] == {"A": "input", "Y": "output"}


def _have_sta():
    try:
        D._sta_bin()
        D.lib_dir(None) if any(Path(x).expanduser().is_dir() for x in D.LIB_DIRS) else (_ for _ in ()).throw(SystemExit)
        return True
    except SystemExit:
        return False


@pytest.mark.skipif(not _have_sta(), reason="needs OpenSTA `sta` and the ASAP7 NLDM libs")
def test_flat_equals_ilm(tmp_path):
    p = tmp_path / "parts" / "part_a"
    p.mkdir(parents=True)
    shutil.copy(TD / "part_a.v", p / "6_final.v")
    shutil.copy(TD / "part_a.spef", p / "6_final.spef")
    res = {}
    for mode in ("flat", "ilm"):
        D.main(["run", "--top", str(TD / "die_top.v"), "--parts", str(tmp_path / "parts"), "--out",
                str(tmp_path / mode), "--mode", mode, "--corner", "TT", "--corner", "FF", "--period-ps", "300"])
        res[mode] = json.loads((tmp_path / mode / "die_sta.json").read_text())
    seam = "u0->u1/a_i"
    for corner, dly in (("TT", "max"), ("FF", "min")):
        f = res["flat"]["corners"][corner]["seams"][seam][dly]
        i = res["ilm"]["corners"][corner]["seams"][seam][dly]
        assert f["paths"] == i["paths"] == 2
        assert abs(f["worst"] - i["worst"]) < 0.01
    assert res["flat"]["verdict"]["status"] in ("PASS", "FAIL")
    assert D.main(["compare", str(tmp_path / "flat" / "die_sta.json"), str(tmp_path / "ilm" / "die_sta.json")]) == 0


def test_verdict_tt_ff():
    seams = {"a": {"max": dict(worst=5.0, neg=0), "min": dict(worst=3.0, neg=0)}}
    res = dict(mode="ilm", corners={"TT": dict(exit=0, seams=seams, ffspread={"u0": dict(spread=40.0)}),
                                    "FF": dict(exit=0, seams=seams, ffspread={"u0": dict(spread=30.0)}),
                                    "SS": dict(exit=0, seams={"a": {"max": dict(worst=-100.0, neg=3)}})})
    assert D.verdict(res)["status"] == "PASS"            # SS never gates
    res["corners"]["TT"]["ffspread"]["u0"]["spread"] = 81.0
    assert D.verdict(res)["status"] == "FAIL"            # spread > 80 at TT
    del res["corners"]["FF"]
    assert D.verdict(res)["status"].startswith("NOT RUN")


@pytest.mark.skipif(not _have_sta(), reason="needs OpenSTA `sta` and the ASAP7 NLDM libs")
def test_spine_models_agree(tmp_path):
    p = tmp_path / "parts" / "part_a"
    p.mkdir(parents=True)
    shutil.copy(TD / "part_a.v", p / "6_final.v")
    sp = tmp_path / "spine_TT.json"
    sp.write_text(json.dumps({"parts": {"u0": {"taps": {"clk": {"offset_ps": 20.0}}},
                                        "u1": {"taps": {"clk": {"offset_ps": 0.0}}}}}))
    w = {}
    for m in ("ports", "gclk"):
        D.main(["run", "--top", str(TD / "die_top.v"), "--parts", str(tmp_path / "parts"), "--out", str(tmp_path / m),
                "--mode", "flat", "--corner", "TT", "--spine-branch", str(tmp_path / "spine_{c}.json"),
                "--spine-model", m])
        w[m] = json.loads((tmp_path / m / "die_sta.json").read_text())["corners"]["TT"]["seams"]["u0->u1/a_i"]
    assert abs(w["ports"]["max"]["worst"] - w["gclk"]["max"]["worst"]) < 0.01
    assert abs(w["ports"]["min"]["worst"] - w["gclk"]["min"]["worst"]) < 0.01
