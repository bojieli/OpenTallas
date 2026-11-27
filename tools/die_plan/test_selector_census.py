"""pytest: selector_census (C-SELECTOR-NAME-MISS / C-RELAY-SEAT-KEYMISS, report-only) + relay_rank_sites in the kit seat lint."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import selector_census as SC  # noqa: E402
import seat_match as SM  # noqa: E402

NETLIST = r"""module t (clk);
 DFFHQNx1_ASAP7_75t_R \u_bin_a/q[0]$_DFF_P_  (.CLK(clk));
 DFFHQNx1_ASAP7_75t_R \u_bin_a/q[1]$_DFF_P_  (.CLK(clk));
 DFFHQNx1_ASAP7_75t_R \u_bin_a/q[2]$_DFF_P_  (.CLK(clk));
 DFFHQNx1_ASAP7_75t_R \u_u_lf0_u_crr/q[0]$_DFF_P_  (.CLK(clk));
 DFFHQNx1_ASAP7_75t_R \u_cland_unit_i0.dch[0].genblk2.u_dsel/y[0]$_DFF_P_  (.CLK(clk));
 DFFHQNx1_ASAP7_75t_R \u_cland_unit_i0.dch[1].genblk2.u_dsel/y[0]$_DFF_P_  (.CLK(clk));
 NAND2x1_ASAP7_75t_R \u_cland_unit_i0.g1  (.A(a));
 DFFHQNx1_ASAP7_75t_R \u_r.rk[0]$_DFF_P_  (.CLK(clk));
 DFFHQNx1_ASAP7_75t_R \u_r.rk[1]$_DFF_P_  (.CLK(clk));
endmodule
"""


def _cells(tmp_path):
    f = tmp_path / "n.v"
    f.write_text(NETLIST)
    return SC.read_netlist(f)


def test_read_netlist(tmp_path):
    c = _cells(tmp_path)
    assert len(c) == 9 and c[0] == ("DFFHQNx1_ASAP7_75t_R", "u_bin_a/q[0]$_DFF_P_")


def test_seat_ladder_zero_under_over(tmp_path):
    d = [dict(kind="seat", source="s", key=k) for k in ("u_bin_a/q[0]", "u_bin_a.q[1]", "u_u_crr/q[0]", "u_gone/q[0]", "u_r.rk[0]")]
    r = SC.census(d, _cells(tmp_path))
    zero = {x["key"] for x in r["rows"] if x["verdict"] == "ZERO"}
    assert zero == {"u_gone/q[0]"}                       # '.', first-component strip and image-flat lf prefix all resolve
    grp = {x["key"]: x for x in r["rows"] if x["kind"] == "seat-group"}
    assert grp["u_bin_a.q"]["verdict"] == "OVER" and grp["u_bin_a.q"]["flops"] == 3 and grp["u_bin_a.q"]["keys"] == 2
    assert grp["u_r.rk"]["verdict"] == "OVER"


def test_list_regex_zero_and_shadowed(tmp_path):
    d = [dict(kind="list", source="w", key=r"u_cland_unit_i0\.dch\[\d+\]\.u_dsel/y", regex=True),    # no genblk2 segment: matches zero
         dict(kind="list", source="w", key=r"u_cland_unit_i0\.dch\[\d+\]\.genblk2\.u_dsel/y", regex=True),
         dict(kind="list", source="w", key=r"u_dsel/y", regex=True),                                 # all covered by the previous rule
         dict(kind="list", source="p", key="u_cland_unit_i0"), dict(kind="list", source="p", key="u_missing")]
    r = SC.census(d, _cells(tmp_path))
    v = {x["key"]: x["verdict"] for x in r["rows"]}
    assert v[d[0]["key"]] == "ZERO" and v["u_dsel/y"] == "SHADOWED" and v["u_missing"] == "ZERO"
    assert d[1]["key"] not in v and "u_cland_unit_i0" not in v


def test_rank_directive(tmp_path):
    d = [dict(kind="rank", source="r", key="u_r.rk", alts=["u_r.rk"]), dict(kind="rank", source="r", key="u_none.q", alts=["u_none.q"])]
    r = SC.census(d, _cells(tmp_path))
    assert [x["key"] for x in r["rows"] if x["verdict"] == "ZERO"] == ["u_none.q"]


def test_kit_directives_and_main_exit0(tmp_path, capsys):
    kit = tmp_path / "kit"
    kit.mkdir()
    (kit / "istations.tcl").write_text("rs_place_all [dict create {u_bin_a/q[0]} {1.0 2.0} {u_gone/q[0]} {3.0 4.0}]\n"
                                       "rs_rank_line {u_none.q} 0.000 1.000 2.000 3.000 asc\n")
    (kit / "landing_placement.tcl").write_text("set cland_dsel_cone {u_cland_unit_i0 u_nope}\nset other_var {zzz}\n")
    (kit / "1_synth_odb.v").write_text(NETLIST)
    ds = SC.kit_directives(kit)
    assert [x["kind"] for x in ds] == ["seat", "seat", "rank", "list", "list"]
    assert SC.main(["--kit", str(kit), "--json", str(tmp_path / "o.json")]) == 0
    out = capsys.readouterr().out
    assert "SELECTOR-CENSUS WARN 3 zero-match" in out and "REPORT ONLY" in out
    rec = json.loads((tmp_path / "o.json").read_text())
    assert rec["report_only"] is True
    assert SC.main(["--kit", str(tmp_path / "empty")]) == 0


def test_main_never_raises_on_bad_kit(tmp_path, capsys):
    (tmp_path / "1_synth.v").write_text("")
    assert SC.main(["--kit", str(tmp_path), "--plan", str(tmp_path / "nope.json"), "--type", "x"]) == 0
    assert "not checked" in capsys.readouterr().out


def test_plan_regex_directives():
    t = {"relay_sites": {"u_a/q[0]": [1, 2]}, "budgets": {"unit_write_patterns": [r"u_x\.g_b\[\d+\]"]}, "other": {"note": "(a|b)"}}
    ds = SC.kit_directives(Path("/nonexistent-kit"), t)
    assert {(x["kind"], x["key"]) for x in ds} == {("seat", "u_a/q[0]"), ("plan", r"u_x\.g_b\[\d+\]")}


def test_gen_lint_seat_miss_reads_relay_rank_sites(tmp_path):
    (tmp_path / "rtl").mkdir()
    (tmp_path / "rtl" / "t_bound.sv").write_text(
        "module t_part (input wire clk);\n  ot_dp_dly #(.W(8), .D(3)) u_lpad (.clk(clk), .d(d), .q(q));\nendmodule\n")
    (tmp_path / "istations.tcl").write_text("rs_rank_line {u_lpad.q} 0.000 1.000 2.000 3.000 asc\n")
    assert SM.kit_lines(tmp_path) == []
    (tmp_path / "istations.tcl").write_text("rs_rank_line {u_lpad.q} 0.000 1.000 2.000 3.000 asc\n"
                                            "rs_rank_line {u_dead_rank.q} 0.000 1.000 2.000 3.000 desc\n")
    ln = SM.kit_lines(tmp_path)
    assert len(ln) == 1 and "SEAT-MISS WARN 1 of 2" in ln[0]
