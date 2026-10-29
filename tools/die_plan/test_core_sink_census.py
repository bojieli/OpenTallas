import json

import core_sink_census as S

NET = r"""
module t (ck, a, y);
 input ck;
 DFFHQNx1_ASAP7_75t_R \u.r[0]$_DFF_P_  (.CLK(ck),
    .D(a),
    .QN(n1));
 DFFHQNx1_ASAP7_75t_R \u.r[1]$_DFF_P_  (.CLK(ck), .D(a), .QN(n2));
 DFFLQNx1_ASAP7_75t_R \u.s[3]$_DFF_N_  (.CLK(ck), .D(a), .QN(n3));
 INVx1_ASAP7_75t_R _1_ (.A(n1), .Y(y));
endmodule
"""


def sl(leaves):
    return {"core_tree": {"clock_port": "ck", "leaves": [{"node": n, "sinks": s} for n, s in leaves]}}


def test_census_direct_port():
    sinks, other = S.census(NET, "ck")
    assert sorted(sinks) == ["u.r[0]$_DFF_P_", "u.r[1]$_DFF_P_", "u.s[3]$_DFF_N_"] and other == {}


def test_rebind_suffix_change_and_removed_register():
    sinks, _ = S.census(NET, "ck")
    old = sl([("L0", ["u.r\\[0\\]$_SDFF_PN0_/CLK", "u.r\\[1\\]$_DFF_P_/CLK"]),
              ("L1", ["u.s\\[3\\]$_DFF_N_/CLK", "u.gone\\[7\\]$_DFF_P_/CLK"])])
    out, rep = S.rebind(old, sinks)
    assert rep["verdict"] == "PASS", rep
    assert (rep["exact"], rep["renamed"], rep["removed"], rep["missing"], rep["extra"]) == (2, 1, 1, 0, 0)
    assert out["core_tree"]["leaves"][0]["sinks"][0] == "u.r\\[0\\]$_DFF_P_/CLK"
    assert out["core_tree"]["leaves"][1]["sinks"] == ["u.s\\[3\\]$_DFF_N_/CLK"]


def test_unplanned_actual_flop_fails():
    sinks, _ = S.census(NET, "ck")
    out, rep = S.rebind(sl([("L0", ["u.r\\[0\\]$_DFF_P_/CLK", "u.r\\[1\\]$_DFF_P_/CLK"])]), sinks)
    assert out is None and rep["verdict"] == "FAIL" and any("u.s[3]" in e for e in rep["errors"])


def test_ambiguous_key_fails():
    sinks = {"u.r[0]$_DFF_P_": "D", "u.r[0]$_DFF_N_": "D"}
    out, rep = S.rebind(sl([("L0", ["u.r\\[0\\]$_SDFF_PN0_/CLK"])]), sinks)
    assert out is None and rep["verdict"] == "FAIL"


def test_empty_leaf_fails():
    sinks = {"u.r[0]$_DFF_P_": "D"}
    out, rep = S.rebind(sl([("L0", ["u.r\\[0\\]$_DFF_P_/CLK"]), ("L1", ["u.x\\[0\\]$_DFF_P_/CLK"])]), sinks)
    assert out is None and any("no actual sink left" in e for e in rep["errors"])


def test_other_clock_net_reported():
    sinks, other = S.census(NET.replace(r"\u.s[3]$_DFF_N_  (.CLK(ck)", r"\u.s[3]$_DFF_N_  (.CLK(gck)"), "ck")
    assert list(other) == ["u.s[3]$_DFF_N_"] and len(sinks) == 2


def test_cli_rebind(tmp_path):
    (tmp_path / "n.v").write_text(NET)
    (tmp_path / "s.json").write_text(json.dumps(sl([("L0", ["u.r\\[0\\]$_SDFF_PN0_/CLK", "u.r\\[1\\]$_DFF_P_/CLK",
                                                              "u.s\\[3\\]$_DFF_N_/CLK"])])))
    rc = S.main(["rebind", str(tmp_path / "s.json"), str(tmp_path / "n.v"), "--out", str(tmp_path / "o.json"),
                 "--report", str(tmp_path / "r.json")])
    assert rc == 0
    o = json.loads((tmp_path / "o.json").read_text())
    assert o["core_tree"]["sink_census"]["renamed"] == 1
