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


# DIE-KV-51 10-31: hard (macro) clock pins + kit-time refresh
HNET = NET.replace("endmodule", r""" SRAM \u.m[0].u_s  (.clk(ck), .d(a));
 SRAM \u.m[1].u_s  (.clk(ck), .d(a));
endmodule""")


def hsl(extra_leaves=()):
    return sl([("L0", ["u.r\\[0\\]$_DFF_P_/CLK", "u.r\\[1\\]$_DFF_P_/CLK", "u.s\\[3\\]$_DFF_N_/CLK"]),
               ("M0", ["u.m\\[0\\].u_s/clk"]), ("M1", ["u.m\\[1\\].u_s/clk"])] + list(extra_leaves))


def test_hard_pins_kept_and_leaf_with_only_hard_pins_not_empty():
    out, rep = S.rebind_netlist(hsl(), HNET)
    assert rep["verdict"] == "PASS", rep
    assert rep["hard"] == 2 and rep["exact"] == 3 and rep["removed"] == 0
    assert out["core_tree"]["leaves"][1]["sinks"] == ["u.m\\[0\\].u_s/clk"]


def test_planned_hard_pin_off_port_fails():
    out, rep = S.rebind_netlist(hsl(), HNET.replace(r"\u.m[1].u_s  (.clk(ck)", r"\u.m[1].u_s  (.clk(gck)"))
    assert out is None and any("not on the clock port" in e for e in rep["errors"])


def test_unplanned_hard_pin_fails_when_plan_lists_hard_pins():
    s = hsl(); s["core_tree"]["leaves"] = s["core_tree"]["leaves"][:2]
    out, rep = S.rebind_netlist(s, HNET)
    assert out is None and any("not in the plan" in e for e in rep["errors"])


def test_legacy_plan_without_hard_pins_ignores_macros():
    out, rep = S.rebind_netlist(sl([("L0", ["u.r\\[0\\]$_DFF_P_/CLK", "u.r\\[1\\]$_DFF_P_/CLK",
                                             "u.s\\[3\\]$_DFF_N_/CLK"])]), HNET)
    assert rep["verdict"] == "PASS" and rep["hard_unplanned"] == 2


def _kit(tmp_path, s):
    (tmp_path / "n.v").write_text(HNET)
    sp = tmp_path / "core_infra_slice.json"; sp.write_text(json.dumps(s, indent=1))
    return sp


def test_refresh_exact_writes_nothing(tmp_path, monkeypatch):
    import core_infra
    monkeypatch.setattr(core_infra, "install", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no install")))
    sp = _kit(tmp_path, hsl()); before = sp.read_bytes()
    assert S.refresh(tmp_path, sp, tmp_path / "n.v", tmp_path / "r.json") == 0
    assert sp.read_bytes() == before and not (tmp_path / "r.json").exists()


def test_refresh_removed_register_recompiles(tmp_path, monkeypatch):
    import core_infra
    seen = {}
    monkeypatch.setattr(core_infra, "install", lambda kd, sl, copy_support=True: seen.update(sl=sl, cs=copy_support) or True)
    s = hsl(); s["core_tree"]["leaves"][0]["sinks"].append("u.gone\\[9\\]$_DFF_P_/CLK")
    sp = _kit(tmp_path, s)
    assert S.refresh(tmp_path, sp, tmp_path / "n.v", tmp_path / "r.json") == 0
    assert seen["cs"] is False and seen["sl"]["core_tree"]["sink_census"]["removed"] == 1
    assert json.loads((tmp_path / "r.json").read_text())["action"] == "refreshed"
    assert "u.gone" not in sp.read_text()


def test_refresh_fail_writes_nothing(tmp_path):
    s = hsl(); s["core_tree"]["leaves"][0]["sinks"] = ["u.r\\[0\\]$_DFF_P_/CLK"]   # u.r[1], u.s[3] unplanned
    sp = _kit(tmp_path, s); before = sp.read_bytes()
    assert S.main(["refresh", str(tmp_path), "--slice", str(sp), "--netlist", str(tmp_path / "n.v"),
                   "--report", str(tmp_path / "r.json")]) == 1
    assert sp.read_bytes() == before and json.loads((tmp_path / "r.json").read_text())["action"] == "FAIL"


def test_stage_sink_refresh(tmp_path):
    import master_slice as MS
    assert MS.stage_sink_refresh(tmp_path, {"core_tree": {}}) is False and not list(tmp_path.iterdir())
    assert MS.stage_sink_refresh(tmp_path, hsl()) is True
    assert (tmp_path / "core_infra_slice.json").is_file() and (tmp_path / "core_sink_census.py").is_file()
