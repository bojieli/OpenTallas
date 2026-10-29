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
