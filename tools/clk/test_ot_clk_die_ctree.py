"""DIE-PROTO-3 tests for the ot_clk -> die_sta routed-tree adapter (tools/clk/ot_clk_die_ctree.py).
Synthetic 3-cell tree + a die-combo SPEF with a *NAME_MAP, a signal net and a signal port (no fleet inputs)."""
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "die_plan"))
import ot_clk_die_ctree as A  # noqa: E402

CTREE = """// ot_clk ctree (synthetic)
module ctree (root, t_a__clk, t_b__clk);
  input root;
  output t_a__clk;
  output t_b__clk;
  wire n1;
  wire n2;
  wire qn3_t_b__clk;
  CKINVDCx16_ASAP7_75t_R b1 (.A(root), .Y(n1));
  CKINVDCx16_ASAP7_75t_R b2 (.A(n1), .Y(n2));
  CKINVDCx16_ASAP7_75t_R b3 (.A(n1), .Y(qn3_t_b__clk));
  assign t_a__clk = n2;
  assign t_b__clk = qn3_t_b__clk;
endmodule
"""

SPEF = """*SPEF "ieee 1481-1999"
*DESIGN "die_combo"
*DATE "x"
*VENDOR "OpenROAD"
*PROGRAM "OpenROAD"
*VERSION "1"
*DESIGN_FLOW "NAME_SCOPE LOCAL"
*DIVIDER /
*DELIMITER :
*BUS_DELIMITER [ ]
*T_UNIT 1 PS
*C_UNIT 1 FF
*R_UNIT 1 KOHM
*L_UNIT 1 HENRY

*NAME_MAP
*1 ck_n1
*2 ck_n2
*3 ck_qn3_t_b__clk
*4 ck_b1
*5 ck_b2
*6 ck_b3
*7 sig_x
*8 u_sig

*PORTS
root I
t_a__clk O
t_b__clk O
rst_n I

*D_NET root 1.5
*CONN
*P root I
*I *4:A I
*CAP
1 root 0.5
2 *4:A 1.0
*RES
1 root *4:A 0.01
*END

*D_NET *1 3.0
*CONN
*I *4:Y O
*I *5:A I
*I *6:A I
*CAP
1 *4:Y 1.0
2 *1:1 1.0
3 *5:A 0.5
4 *6:A 0.5
*RES
1 *4:Y *1:1 0.02
2 *1:1 *5:A 0.02
3 *1:1 *6:A 0.03
*END

*D_NET t_a__clk 1.2
*CONN
*I *5:Y O
*P t_a__clk O
*CAP
1 *5:Y 0.6
2 t_a__clk 0.6
*RES
1 *5:Y t_a__clk 0.04
*END

*D_NET *3 1.1
*CONN
*I *6:Y O
*P t_b__clk O
*CAP
1 *6:Y 0.5
2 t_b__clk 0.6
*RES
1 *6:Y t_b__clk 0.05
*END

*D_NET *7 2.0
*CONN
*P rst_n I
*I *8:A I
*CAP
1 *7 2.0
*RES
1 rst_n *8:A 0.1
*END
"""

TCL = "read_verilog /out/combo.v\nglobal_route -x\nsource setRC.tcl\nestimate_parasitics -global_routing\nputs OT_DONE\n"


def mk(tmp_path, ctree=CTREE, spef=SPEF):
    (tmp_path / "ctree.v").write_text(ctree)
    (tmp_path / "combo.spef").write_text(spef)
    return tmp_path / "ctree.v", tmp_path / "combo.spef", tmp_path / "out"


def test_build_renames_and_filters(tmp_path):
    v, s, o = mk(tmp_path)
    rec = A.build(v, s, o)
    assert rec["spef_nets_kept"] == 4 and rec["spef_nets_dropped"] == 1
    ov = (o / "ctree.v").read_text()
    assert "module die_ctree (root, t_a__clk, t_b__clk);" in ov
    assert "assign" not in ov and "qn3_t_b__clk" not in ov and "wire n2;" not in ov
    assert "b2 (.A(n1), .Y(t_a__clk))" in ov and "b3 (.A(n1), .Y(t_b__clk))" in ov
    sp = (o / "ctree.spef").read_text()
    assert '*DESIGN "die_ctree"' in sp and '*DESIGN_FLOW "NAME_SCOPE LOCAL"' in sp
    assert "*NAME_MAP" not in sp and "rst_n" not in sp and "sig_x" not in sp and "ck_" not in sp
    for net in ("root", "n1", "t_a__clk", "t_b__clk"):
        assert f"*D_NET {net} " in sp
    assert "*I b1:Y O" in sp and "2 n1:1 1.0" in sp and "3 n1:1 b3:A 0.03" in sp
    assert "1 b3:Y t_b__clk 0.05" in sp


def test_output_reads_as_die_sta_ctree(tmp_path):
    die_sta = pytest.importorskip("die_sta")
    v, s, o = mk(tmp_path)
    A.build(v, s, o)
    mods = die_sta.read_verilog(o / "ctree.v")
    ct = mods[die_sta.CTREE_MODULE]
    bits = list(ct.port_bits())
    assert {b for d, _, b in bits if d == "input"} == {"root"}
    assert {b for d, _, b in bits if d == "output"} == {"t_a__clk", "t_b__clk"}


def test_missing_parasitics_fail_closed(tmp_path):
    spef = SPEF.split("*D_NET *3 1.1")[0] + "*D_NET *7" + SPEF.split("*D_NET *7")[1]
    v, s, o = mk(tmp_path, spef=spef)
    with pytest.raises(A.AdapterError, match="no D_NET"):
        A.build(v, s, o)


def test_reference_leaving_tree_fails(tmp_path):
    spef = SPEF.replace("*I *6:A I\n*CAP", "*I *6:A I\n*I *8:B I\n*CAP")
    v, s, o = mk(tmp_path, spef=spef)
    with pytest.raises(A.AdapterError, match="leave the clock tree"):
        A.build(v, s, o)


def test_bad_ctree_contracts(tmp_path):
    with pytest.raises(A.AdapterError, match="exactly one input"):
        A.read_ctree(CTREE.replace("module ctree (root,", "module ctree (root, en,").replace(
            "  input root;", "  input root;\n  input en;"))
    with pytest.raises(A.AdapterError, match="t_<inst>__<port>"):
        A.read_ctree(CTREE.replace("t_a__clk", "tap_a"))
    with pytest.raises(A.AdapterError, match="exactly one module"):
        A.read_ctree(CTREE + CTREE)
    with pytest.raises(A.AdapterError, match="two ports"):
        A.port_aliases(A.read_ctree(CTREE.replace("assign t_a__clk = n2;", "assign t_a__clk = t_b__clk;")))


def test_patch_tcl():
    p = A.patch_tcl(TCL, "/out/combo_TT.spef")
    assert "estimate_parasitics -global_routing -spef_file /out/combo_TT.spef\n" in p
    with pytest.raises(A.AdapterError, match="exactly one"):
        A.patch_tcl(TCL.replace("estimate_parasitics -global_routing\n", ""), "x")
    with pytest.raises(A.AdapterError, match="exactly one"):
        A.patch_tcl(TCL + "estimate_parasitics -global_routing\n", "x")
    with pytest.raises(A.AdapterError, match="already"):
        A.patch_tcl(TCL.replace("puts OT_DONE", "# -spef_file\nputs OT_DONE"), "x")


def test_cli(tmp_path):
    v, s, o = mk(tmp_path)
    assert A.main(["build", "--ctree-v", str(v), "--spef", str(s), "--out", str(o)]) == 0
    assert (o / "adapter.json").is_file()
    t = tmp_path / "c.tcl"
    t.write_text(TCL)
    assert A.main(["tcl", str(t), "/out/x.spef"]) == 0 and "-spef_file /out/x.spef" in t.read_text()
    assert A.main(["tcl", str(t), "/out/x.spef"]) == 2


def test_restore_pin_cap(tmp_path):
    spef = SPEF.replace("*D_NET t_a__clk 1.2", "*D_NET t_a__clk 2.0")
    v, s, o = mk(tmp_path, spef=spef)
    rec = A.build(v, s, o)
    assert abs(rec["restored_cap_ff"] - 0.8) < 1e-9
    sp = (o / "ctree.spef").read_text()
    blk = sp.split("*D_NET t_a__clk 2.0")[1].split("*END")[0]
    assert "3 b2:Y 0.4" in blk and "4 t_a__clk 0.4" in blk and blk.index("4 t_a__clk 0.4") < blk.index("*RES")
    rec = A.build(v, s, tmp_path / "o2", restore_cap="none")
    assert rec["restored_cap_ff"] == 0.0
    assert "b2:Y 0.4" not in (tmp_path / "o2" / "ctree.spef").read_text()
