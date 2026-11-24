"""DEPTH-PRE-1123 (COORD): generated constructor netlists with flops at logic depth >= the 833 ps budget FAIL in PRE"""
import json
import sys
from pathlib import Path
H = Path(__file__).resolve().parent
sys.path.insert(0, str(H))
import logic_depth as LD  # noqa: E402
import plan_gate_pre as G  # noqa: E402


def chain(n, name="qfd_x", loop=False):
    """module input -> n inverters -> flop u_f; a second flop u_g fed straight by u_f"""
    L = [LD.MARK, f"module {name}(a,clk,y);", "input wire [0:0] a;"]
    prev = "a"
    for i in range(n):
        L.append(f"(* keep *) qfd_bmath_inv u_{i}(.A({prev}),.Y(n{i}));")
        prev = f"n{i}"
    if loop:                                               # a combinational loop must not hang or recurse forever
        L.append(f"(* keep *) qfd_bmath_and2 u_l(.A({prev}),.B(nl),.Y(nl));")
        prev = "nl"
    L.append(f"(* keep *) qfd_bmath_dff #(.W(1)) u_f(.CLK(clk),.D({prev}),.Q(q));")
    L.append("(* keep *) qfd_bmath_dff u_g(.CLK(clk),.D(q),.Q(y));")
    L.append("endmodule")
    return "\n".join(L) + "\n"


def test_census_counts_depth_and_budget(tmp_path):
    p = tmp_path / "g.sv"; p.write_text(chain(20))
    r = LD.census(p, budget=18)
    assert r["module"] == "qfd_x" and r["flops"] == 2 and r["max"] == 20 and r["deep"] == 1 and r["hist"] == {0: 1, 20: 1}
    assert LD.finding(r).startswith("FAIL DEPTH qfd_x: 1 of 2 flops at logic depth >= 18")
    assert LD.census(p, budget=21)["deep"] == 0 and LD.finding(LD.census(p, budget=21)) is None
    p.write_text(chain(3000, loop=True))                   # deep chain + a loop: iterative, terminates
    r = LD.census(p, budget=18)
    assert r["max"] >= 3000 and r["deep"] == 1


def test_pre_depth_fails_on_a_generated_netlist_under_rtl(tmp_path, monkeypatch):
    monkeypatch.delenv("OT_PRE_DEPTH_LEVELS", raising=False)
    (tmp_path / "rtl" / "gen").mkdir(parents=True)
    (tmp_path / "rtl" / "gen" / "deep.sv").write_text(chain(19, "qfd_deep"))
    (tmp_path / "rtl" / "gen" / "ok.sv").write_text(chain(5, "qfd_ok"))
    (tmp_path / "rtl" / "hand.sv").write_text(chain(40, "hand").replace(LD.MARK, "// hand RTL"))   # not generated: not checked
    plan = tmp_path / "plan.json"; plan.write_text(json.dumps({"partition_types": {}}))
    f = G.check_depth(str(tmp_path), str(plan))
    assert [x for x in f if x.startswith("FAIL")] == [x for x in f if x.startswith("FAIL DEPTH qfd_deep: 1 of 2")], f
    assert f[-1].startswith("WARN DEPTH-SUMMARY 2 generated netlist(s)") and "1 over budget" in f[-1]
    monkeypatch.setenv("OT_PRE_DEPTH_LEVELS", "20")
    assert not [x for x in G.check_depth(str(tmp_path), str(plan)) if x.startswith("FAIL")]


def test_pre_depth_follows_the_plan_rtl_with_an_asbuilt(tmp_path):
    (tmp_path / "rtl").mkdir()
    (tmp_path / "rtl" / "deep.sv").write_text(chain(25, "qfd_deep"))
    (tmp_path / "rtl" / "other.sv").write_text(chain(30, "qfd_other"))          # generated but not reached by the plan
    (tmp_path / "rtl" / "top.sv").write_text("module ttop(input wire clk);\n  qfd_deep u_d (.a(1'b0), .clk(clk), .y());\nendmodule\n")
    ab = tmp_path / "ab.json"; ab.write_text(json.dumps({"base": ".", "rtl_roots": ["rtl"]}))
    plan = tmp_path / "plan.json"; plan.write_text(json.dumps({"partition_types": {"t": {"module": "ttop"}}}))
    f = G.check_depth(str(tmp_path), str(plan), str(ab))
    assert any(x.startswith("FAIL DEPTH qfd_deep:") for x in f) and not any("qfd_other" in x for x in f), f
    assert "reached from the plan" in f[-1]


def test_cli_exit(tmp_path):
    p = tmp_path / "g.sv"; p.write_text(chain(18))
    assert LD.main([str(p)]) == 1 and LD.main([str(p), "--levels", "19"]) == 0
    assert "DEPTH" in G.CLASSES
