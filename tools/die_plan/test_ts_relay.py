"""TYPE-SAFE-2 11-08: relay constructor pieces -- wiring-only core connectivity from a bound module, and the bound-RTL
latency miter (only declared stages change, stage delta per lane == declared pin cycles)."""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import core_conns_from_bind as CCB  # noqa: E402

PLAN_T = dict(buses=[dict(name="i_a", dir="in", width=4), dict(name="o_b", dir="out", width=4)],
              hard_cores=[dict(inst="u_c.u_x", module="cx"), dict(inst="u_c.u_y", module="cy")])


def bound(D):
    return f"""module t_bound (input wire clk, input wire rst_n, input wire [4:0] i_a, output wire [4:0] o_b);
    wire [3:0] i_a_b; wire i_a_eb; wire [3:0] i_a_q; wire i_a_eq;
    ot_dp_st #(.W(4)) u_bin_i_a (.clk(clk), .rst_n(rst_n), .d(i_a[3:0]), .ea(i_a[4]), .q(i_a_b), .eq(i_a_eb));
    ot_dp_dly #(.W(5), .D({D})) u_lpad_i_a (.clk(clk), .d({{i_a_eb, i_a_b}}), .q({{i_a_eq, i_a_q}}));
    wire [3:0] w_x_a;
    assign w_x_a = {{i_a_q[1:0], i_a_q[3:2]}};
    wire [3:0] w_x_z;
    cx u_u_x (.ck(clk), .a(w_x_a), .z(w_x_z));
    wire [3:0] w_y_m;
    assign w_y_m = w_x_z ^ 4'h1;
    cy u_u_y (.ck(clk), .m(w_y_m), .p(w_x_z));
    ot_dp_st #(.W(4)) u_bout_o_b (.clk(clk), .rst_n(rst_n), .d(w_x_z), .ea(1'b1), .q(o_b[3:0]), .eq(o_b[4]));
endmodule
"""


def _lef(tmp, name, ports):
    rows = ["MACRO " + name]
    for pin, (direction, width) in ports.items():
        for i in range(width):
            rows += [f" PIN {pin}[{i}]", f" DIRECTION {direction} ;", f" END {pin}[{i}]"]
    p = tmp / (name + ".lef")
    p.write_text("\n".join(rows + ["END " + name]) + "\n")
    return str(p)


def test_trace_wiring_only(tmp_path):
    # The tracer takes core pin directions from the actual LEF (unknown directions fail closed), so give the fixture's
    # hard cores real LEF views; the wiring expectations below are unchanged.
    lefs = dict(cx=_lef(tmp_path, "cx", dict(ck=("INPUT", 1), a=("INPUT", 4), z=("OUTPUT", 4))),
                cy=_lef(tmp_path, "cy", dict(ck=("INPUT", 1), m=("INPUT", 4), p=("INPUT", 4))))
    plan_t = dict(PLAN_T, hard_cores=[dict(hc, lef=lefs[hc["module"]]) for hc in PLAN_T["hard_cores"]])
    res = CCB.trace(dict(partition_types=dict(t=plan_t)), "t", bound(3))
    cc = res["core_conns"]["t"]
    assert cc["u_c.u_x"]["a"] == ["bus:i_a"]
    assert "bus:o_b" in cc["u_c.u_x"]["z"]
    p = next(p for p in res["paths"] if p.get("bus") == "i_a")
    assert p["stages_existing"] == 3 and p["dir"] == "in"
    # u_y.p reads u_x.z by wiring -> core:core path; u_y.m goes through an XOR -> no wiring path
    assert "core:u_c.u_x.z" in cc["u_c.u_y"]["p"]
    assert "m" not in cc.get("u_c.u_y", {})


def _plan():
    return dict(
        partitions=[dict(name="pa", type="s"), dict(name="pb", type="t")],
        ports=[dict(id="p0", src=dict(part="pa", bus="o_q"), dst=dict(part="pb", bus="i_a"))],
        lanes=[dict(id="L0", ports=["p0"], fixed_cycles=3)],
        partition_types=dict(t=PLAN_T))


def _run(tmp_path, old, new, delta):
    od, nd = tmp_path / "old", tmp_path / "new"
    od.mkdir()
    nd.mkdir()
    (od / "t.sv").write_text(old)
    (nd / "t.sv").write_text(new)
    pf, ef = tmp_path / "plan.json", tmp_path / "ev.json"
    pf.write_text(json.dumps(_plan()))
    ef.write_text(json.dumps(dict(edits=[dict(type="t", bus="i_a", lanes=dict(L0=dict(delta=delta)))])))
    r = subprocess.run([sys.executable, str(HERE / "ts_relay_miter.py"), str(pf), str(ef), str(od), str(nd),
                        str(tmp_path / "out.json")], capture_output=True, text=True)
    return r.returncode, json.loads((tmp_path / "out.json").read_text())


def test_miter_pass_on_declared_pad(tmp_path):
    rc, rec = _run(tmp_path, bound(1), bound(3), 2)
    assert rc == 0 and rec["verdict"] == "PASS", rec


def test_miter_fails_on_wrong_delta(tmp_path):
    rc, rec = _run(tmp_path, bound(1), bound(3), 1)
    assert rc == 1 and rec["n_mismatch"] == 1


def test_miter_fails_on_undeclared_change(tmp_path):
    rc, rec = _run(tmp_path, bound(1), bound(3).replace("4'h1", "4'h2"), 2)
    assert rc == 1 and rec["n_undeclared"] >= 1


def test_station_sites_leave_core_keepouts():
    import ts_relay_event as TE
    t = dict(outline_um=[1000.0, 200.0], hard_cores=[dict(origin_um=[100.0, 0.0], outline_um=[300.0, 150.0])])
    regs = TE.sites(t, (0.0, 50.0), (900.0, 50.0), 3)
    for x, y in regs:
        assert not (100.0 - TE.HALO < x < 400.0 + TE.HALO and 0.0 - TE.HALO < y < 150.0 + TE.HALO)
        assert 0.0 <= x <= 1000.0 and 0.0 <= y <= 200.0
    assert regs[1] == [450.0, 50.0]          # outside: unchanged


def test_regen_latency_checks_declared_deltas(tmp_path, monkeypatch):
    import subprocess as sp
    import pytest
    import ts_relay_event as T
    base = dict(latency=dict(lanes=dict(L1=dict(cycles=4), L2=dict(cycles=7))))
    out = tmp_path / "p.json"
    out.write_text(json.dumps(dict(latency=dict(lanes=dict(L1=dict(cycles=5), L2=dict(cycles=7))))))
    monkeypatch.setattr(sp, "run", lambda *a, **k: None)
    assert T.regen_latency(out, base, {"L1": 1}) == dict(lanes_changed=1, sum=1)
    with pytest.raises(SystemExit):
        T.regen_latency(out, base, {"L1": 2})
    with pytest.raises(SystemExit):
        T.regen_latency(out, base, {"L2": 1})


def _native_stub(rows, fixed):
    from types import SimpleNamespace as NS
    src = dict(buses=[dict(name="o", dir="out", width=4)],
               internal_stations=[dict(conn="bus:o", regs_um=[[1, 1]], from_um=[0, 0], to_um=[2, 2])])
    L = dict(oname="o", iname="i", lane="L", dst="d", cycles=9, ft=[], width=4)
    return NS(ab=dict(internal_stations_types=["s"]), types=dict(s=src, t=dict(internal_stations=rows)),
              plan=dict(lanes=[dict(id="L", fixed_cycles=fixed)]), parts=dict(p=dict(type="s"), d=dict(type="t")),
              out_bus=dict(p=[L]))


def test_receiver_depth_is_the_deepest_entry():
    import pytest
    import native_istations as NI
    import ts_relay_event as T
    rows = [dict(conn="bus:i", regs_um=[[0, 0]]), dict(conn="bus:i", regs_um=[[0, 0], [1, 1]])]
    assert T._depth(dict(internal_stations=rows), "i") == 2 and T._depth(dict(internal_stations=rows), "x") is None
    NI.annotate(_native_stub(rows, 3))                  # 1 source + deepest receiver 2
    with pytest.raises(ValueError, match="fixed_cycles must equal"):
        NI.annotate(_native_stub(rows, 2))              # first-row depth 1 is not the realised depth
    exact = [dict(rows[0], bit_route=[1]), rows[1]]     # exact-site rows are not merged by the kit: still refused
    with pytest.raises(ValueError, match="conflicting destination"):
        NI.annotate(_native_stub(exact, 3))


def test_miter_src_hash_rename_is_no_change():
    A = ["ot_x g_src_%s (.Y(w_src_%s_Y));" % ("a" * 20, "a" * 20), "assign w_src_%s_Y = k;" % ("a" * 20)]
    B = ["assign w_src_%s_Y = k;" % ("b" * 20), "ot_x g_src_%s (.Y(w_src_%s_Y));" % ("b" * 20, "b" * 20)]
    sys.path.insert(0, str(HERE))
    import ts_relay_miter as M
    assert sorted(M.rename_src_names(A, B)) == sorted(B)


def test_miter_src_hash_with_changed_wiring_stays_different():
    A = ["assign w_src_%s_Y = k;" % ("a" * 20)]
    B = ["assign w_src_%s_Y = j;" % ("b" * 20)]
    sys.path.insert(0, str(HERE))
    import ts_relay_miter as M
    assert sorted(M.rename_src_names(A, B)) != sorted(B)


def test_r8_pad_split_reads_pad_output_as_the_delayed_bit():
    sys.path.insert(0, str(HERE))
    import ts_relay_miter as M
    lines = ["wire [0:0] pd7_x_i_0;", "ot_dp_dly #(.W(1), .D(7)) u_pd7_x_i_0 (.clk(clk), .d(x_i_q[0]), .q(pd7_x_i_0));",
             ".a({pd7_x_i_0[0], y});"]
    assert M.split_r8_pads(lines) == ([".a({x_i_q[0], y});"], {("x_i", 0): 7})


def test_r8_pad_on_a_different_bit_is_not_a_pad():
    sys.path.insert(0, str(HERE))
    import ts_relay_miter as M
    line = "ot_dp_dly #(.W(1), .D(7)) u_pd7_x_i_0 (.clk(clk), .d(x_i_q[1]), .q(pd7_x_i_0));"
    assert M.split_r8_pads([line])[1] == {}


def test_r8_pad_split_expands_a_bus_range_like_its_bit_list():
    sys.path.insert(0, str(HERE))
    import ts_relay_miter as M
    assert M.split_r8_pads([".d({x_q[1:0], y});"])[0] == M.split_r8_pads([".d({x_q[1], x_q[0], y});"])[0]
