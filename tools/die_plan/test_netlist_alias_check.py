"""netlist_alias_check: re-read of an exported netlist fails closed on assign/alias cycles (SPEPRD3 11-16)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import netlist_alias_check as N  # noqa: E402


def spe_like(n, fixed):
    """n padded outputs as write_verilog exported them: the delay buffer input sits on the net that kept the port
    name (fixed=False, SPEPRD3 archived 6_final.v) or on the renamed internal net (fixed=True)."""
    ports = ", ".join(f"xw_o[{i}]" for i in range(n))
    L = [f"module strip (clk, {ports});", " input clk;", f" output [{n - 1}:0] xw_o;"]
    for i in range(n):
        old = f"ot_export_internal_{i}" if fixed else f"xw_o[{i}]"
        L += [f" wire ot_xw_min25_{i}_n;"] + ([f" wire {old};"] if fixed else [])
        L += [f" DFFHQNx1_ASAP7_75t_R r{i} (.CLK(clk), .D(ot_xw_min25_{i}_n), .QN({old}));",
              f" HB4xp67_ASAP7_75t_R ot_xw_min25_{i} (.A({old}),\n    .Y(ot_xw_min25_{i}_n));"]
    L += [f" assign xw_o[{i}] = ot_xw_min25_{i}_n;" for i in range(n)] + ["endmodule"]
    return "\n".join(L) + "\n"


def test_spe_566_alias_cycle_fixture_fails(tmp_path):
    v = tmp_path / "6_final.v"
    v.write_text(spe_like(566, fixed=False))
    probs, st = N.check(v.read_text())
    assert len(probs) == 566 and {p["kind"] for p in probs} == {"alias_cycle"}
    assert probs[0]["nets"][0] == probs[0]["nets"][-1] and any(n.startswith("xw_o[") for n in probs[0]["nets"])
    out = tmp_path / "r.json"
    assert N.main([str(v), "--json", str(out)]) == 1
    assert json.loads(out.read_text())["verdict"] == "FAIL"


def test_spe_fixed_export_passes(tmp_path):
    v = tmp_path / "6_final.v"
    v.write_text(spe_like(566, fixed=True))
    assert N.main([str(v)]) == 0
    probs, st = N.check(v.read_text())
    assert probs == [] and st["assigns"] == 566 and st["buffers"] == 566


def test_assign_cycle_and_self_alias_fail():
    t = "module m (a, b);\n output a; output b;\n assign a = b;\n assign b = a;\nendmodule\n"
    assert [p["kind"] for p in N.check(t)[0]] == ["alias_cycle"]
    t = "module m (a);\n output a;\n assign a = a;\nendmodule\n"
    assert "self_alias" in [p["kind"] for p in N.check(t)[0]]


def test_escaped_names_inverter_chain_and_constants():
    t = ("module m (\\o[0] , i);\n output \\o[0] ; input i;\n wire \\o[0]938 ;\n"
         " INVx1_ASAP7_75t_R u1 (.A(\\o[0] ), .Y(\\o[0]938 ));\n assign \\o[0] = \\o[0]938 ;\nendmodule\n")
    assert len(N.check(t)[0]) == 1                       # escaped identifiers keep their identity
    ok = ("module m (o, p, i);\n output o, p; input i;\n wire n;\n BUFx2_ASAP7_75t_R u1 (.A(i), .Y(n));\n"
          " assign o = n;\n assign p = 1'b0;\nendmodule\n")
    assert N.check(ok)[0] == []                          # a plain feed-forward alias and a constant tie pass
    # feedback through a flop or a multi-input gate is not an alias cycle
    fb = ("module m (o, clk);\n output o; input clk;\n wire q, d;\n DFFHQNx1_ASAP7_75t_R r (.CLK(clk), .D(d), .QN(q));\n"
          " NAND2xp33_ASAP7_75t_R g (.A(q), .B(clk), .Y(d));\n assign o = q;\nendmodule\n")
    assert N.check(fb)[0] == []


def test_zero_modules_and_unreadable_fail(tmp_path):
    v = tmp_path / "empty.v"
    v.write_text("// nothing\n")
    assert N.main([str(v)]) == 1                          # zero objects measured is never a PASS
    assert N.main([str(tmp_path / "missing.v")]) == 2
