"""kit_contract.macro_instances: every instance path in the static macro placement resolves in the staged RTL
(measured failure 10-28: qcore_r13 kit _k3mp5 placed u_fcore.u_fcore.u_red.m{a,b}, double face-shell prefix)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_contract as KC  # noqa: E402
from test_kit_contract import write_kit, _sub  # noqa: E402

RTL = """
`ifdef SYNTHESIS
`define CVP(X)
`else
`define CVP(X) #(.N(X))
`endif
`define EA(Q) \\
    sram u_e``Q ( .a(x[Q]) );
module core #(parameter P = 1) (input [3:0] x);
    generate if (P == 1) begin : g_one
        sram u_w (.a(x[0]));
    end else begin : g_two
        sram2 u_w (.a(x[0]));
    end endgenerate
    for (genvar i = 0; i < 2; i++) begin : g_bank
        sram #(.W(8)) u_s (.a(x[i]));
    end
    sram `CVP(3) u_m (.a(x[1]));
    `EA(0)
    `EA(1)
endmodule
module top(input clk, input [3:0] a, output y);
    core #(.P(1)) u_fcore (.x(a));
    assign y = a[0];
endmodule
"""


def _kit(tmp_path, names):
    kd = write_kit(tmp_path / "kit")
    (kd / "rtl/top.sv").write_text(RTL)
    (kd / "macro_place.tcl").write_text("foreach {inst master x y orient} {\n" +
                                        "".join(f"  {{{n}}} {m} 40 10 R0\n" for n, m in names) +
                                        "} {\n  place_macro -macro_name $inst -location [list $x $y] -orientation $orient -exact\n}\n")
    return kd


def test_resolved_paths_pass(tmp_path):
    kd = _kit(tmp_path, [("u_fcore.g_one.u_w", "sram"), ("u_fcore.g_two.u_w", "sram2"),
                         ("u_fcore.g_bank\\[1\\].u_s", "sram"), ("u_fcore.u_m", "sram"),
                         ("u_fcore.u_e0", "sram"), ("u_fcore.u_e1", "sram")])
    err, info = KC.macro_instances(kd)
    assert err == [] and info == dict(applies=True, placed=6, resolved=6), err


def test_double_prefix_fails(tmp_path):
    kd = _kit(tmp_path, [("u_fcore.u_fcore.u_m", "sram")])
    err, info = KC.macro_instances(kd)
    assert len(err) == 1 and "'u_fcore' is neither an instance nor a generate block of module core" in err[0], err
    assert KC.run_all(kd)["macro_instances"]["verdict"] == "FAIL"


def test_wrong_master_and_missing_leaf_fail(tmp_path):
    kd = _kit(tmp_path, [("u_fcore.u_m", "sram2"), ("u_fcore.u_e2", "sram"), ("u_fcore.g_one", "sram")])
    err, _ = KC.macro_instances(kd)
    assert len(err) == 3, err
    assert "instance of sram, placed as master sram2" in err[0]


def test_escaped_flat_name_and_place_macro_line(tmp_path):
    kd = write_kit(tmp_path / "kit")
    (kd / "rtl/top.sv").write_text("module top(input clk, a, output y);\n  sram \\u_c.u_b.g_w[1].u_m  (.a(a));\n"
                                   "  assign y = a;\nendmodule\n")
    (kd / "macro_place.tcl").write_text("place_macro -macro_name {u_c.u_b.g_w\\[1\\].u_m} -location {40 10} "
                                        "-orientation R0 -exact\n")
    assert KC.macro_instances(kd)[0] == []
    _sub(kd / "macro_place.tcl", "g_w\\[1\\]", "g_w\\[2\\]")
    assert KC.macro_instances(kd)[0]


def test_master_form_is_na(tmp_path):
    kd = write_kit(tmp_path / "kit")          # foreach {master sites}: placed by master, no instance paths
    err, info = KC.macro_instances(kd)
    assert err == [] and info["applies"] is False
