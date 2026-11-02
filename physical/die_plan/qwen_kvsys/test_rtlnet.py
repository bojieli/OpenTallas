from rtlnet import Net

def test_current_multiline_named_ports_preserve_following_bus_width(tmp_path):
    p = tmp_path / "native.sv"
    p.write_text("module p;\nwire [38:0] d;\nwire [38:0] q;\n"
                 "landing #(.W(39)) u_l (\n .d(d), .q(q), .clk(clk),\n .fault(fault));\n"
                 "wire [304:0] o_grp;\nleaf u_leaf (\n .o_grp(o_grp),\n .q(q)\n);\nendmodule\n")
    n = Net(p)
    assert n.width["o_grp"] == 305
    assert n.insts["u_l"] == ("landing", dict(d="d", q="q", clk="clk", fault="fault"))
    assert n.insts["u_leaf"][1]["o_grp"] == "o_grp"
    assert len(n.bits("o_grp")) == 305


def test_multiline_explicit_empty_port_matches_single_line(tmp_path):
    p = tmp_path / "empty.sv"
    p.write_text("module p;\nwire d;\ncore u_a (.real(d), .pc__land_er_259());\n"
                 "core u_b (\n .real(d),\n .pc__land_er_259()\n);\nendmodule\n")
    n = Net(p)
    assert n.insts["u_a"] == n.insts["u_b"] == ("core", {"real": "d"})
    assert all(e[1] != "pc__land_er_259" for es in n.graph().values() for e in es)


def test_multiline_malformed_named_port_still_rejected(tmp_path):
    import pytest
    p = tmp_path / "bad.sv"
    p.write_text("module p;\ncore u_a (\n .real(d),\n malformed()\n);\nendmodule\n")
    with pytest.raises(ValueError, match="unparsed named port"):
        Net(p)
