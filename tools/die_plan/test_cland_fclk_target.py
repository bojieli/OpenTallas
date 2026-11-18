"""FABLE-FIX-QC-N N4.1 (D) 11-18: hard cland write clock insertion target (cland_fclk_target.py / .tcl, gen_phys hook).

QC sle_st_a_v1 4_cts.odb: three ft-hop rings (input max 350 ps, falling-edge writers, T 833) missed the cland d setup by
-50..-66 ps because the one-sink forwarded clock is a bare wire.  Target = input max + 45 + lib setup; the kit pads the
port -> pin clock delay up to target - capture edge, raise only.
    python3 -m pytest -q tools/die_plan/test_cland_fclk_target.py"""
import re
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

import cland_fclk_target as C
import gen_phys as G

HERE = Path(__file__).resolve().parent
SRC = (HERE / "cland_fclk_target.tcl").read_text()
needs_tclsh = pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh")

LIB = """library (x) {
  time_unit : "1ps";
  cell (sta_cland_w4) {
    pin("fclk") { direction : input; clock : true;
      timing() { timing_sense : positive_unate; timing_type : max_clock_tree_path;
        cell_rise(scalar) { values("116.6"); } } }
    pin("d[1]") { direction : input;
      timing() { related_pin : "fclk"; timing_type : hold_falling;
        rise_constraint(scalar) { values("-36.9"); } }
      timing() { related_pin : "fclk"; timing_type : %(kind)s;
        rise_constraint(scalar) { values("58.8"); }
        fall_constraint(scalar) { values("92.7"); } } }
    pin("d[0]") { direction : input;
      timing() { related_pin : "fclk"; timing_type : %(kind)s;
        rise_constraint(scalar) { values("54.0, 61.5"); } } }
    pin("t_rst_n") { direction : input;
      timing() { related_pin : "fclk"; timing_type : %(kind)s;
        rise_constraint(scalar) { values("300.0"); } } }
    pin("q[0]") { direction : output;
      timing() { related_pin : "clk"; timing_type : rising_edge;
        cell_rise(scalar) { values("500.0"); } } }
  }
}
"""
SDC = ("# OT_FWD_RING_INPUTS fclk_in_ft_i ft_i[*] cland_fstart_in_ft_i\n"
       "set_input_delay -max 350.0000 -clock fclk_in_ft_i [get_ports {ft_i[*]}]\n"
       "set_input_delay -min -85.0000 -clock fclk_in_ft_i [get_ports {ft_i[*]}]\n"
       "set_input_delay -max 166.6000 -clock fclk_in_ft_i [get_ports {cland_fstart_in_ft_i}]\n"
       "set_input_delay -max 166.6000 -clock fclk_in_bus [get_ports {bus[*]}]\n")


def _lib(tmp_path, name="c_tt.lib", kind="setup_falling", text=LIB):
    f = tmp_path / name
    f.write_text(text.replace("\n", "\n".join(["", ""])).replace("{ ", "{\n").replace("; ", ";\n") % dict(kind=kind))
    return f


def _slots(*buses):
    return dict(buses={b: dict(form="hard_child", D=4, instance=f"u_bound.u_cland_{b}", master=f"m_{b}", port="d",
                               width=4, clock_pin="fclk", clock_port=f"fclk_in_{b}") for b in buses})


def _cores(*buses, lib="c_tt.lib", **params):
    return [dict(inst=f"cl_{b}", physical_inst=f"u_bound.u_cland_{b}", lib=f"views/x/{lib}",
                 param_wrap=dict(base="ot_dp_clk_landing_cas", params=dict(W=4, DEPTH=4, WREG=1, **params))) for b in buses]


def test_lib_setup_is_the_largest_d_vs_fclk_setup_and_names_the_edge(tmp_path):
    assert C.lib_setup(_lib(tmp_path)) == (92.7, "fall")            # d pins only: t_rst_n 300 and the clk arcs ignored
    assert C.lib_setup(_lib(tmp_path, kind="setup_rising")) == (92.7, "rise")
    ns = tmp_path / "ns.lib"
    ns.write_text(_lib(tmp_path).read_text().replace('"1ps"', '"1ns"').replace("92.7", "0.0927").replace("58.8", "0.05")
                  .replace("54.0, 61.5", "0.05"))
    assert C.lib_setup(ns)[0] == pytest.approx(92.7)
    assert C.lib_setup(tmp_path / "missing.lib") == (None, None)
    assert C.lib_setup(_lib(tmp_path), clock_pin="wck") == (None, None)


def test_target_is_input_max_plus_45_plus_setup_and_the_delay_is_what_the_capture_edge_lacks():
    tgt, need = C.target(350.0, 92.7, "fall", 833.0)
    assert tgt == pytest.approx(487.7) and need == pytest.approx(71.2)   # the measured st_a rings: 2.2 ps today
    assert C.target(166.6, 92.7, "fall", 833.0)[1] < 0                   # IO-budget ring: the T/2 edge is enough
    assert C.target(350.0, 92.7, "rise", 833.0)[1] < 0                   # rise writer captures a full cycle later


def test_rows_read_the_kit_lib_else_95_and_only_a_short_ring_gets_a_table_row(tmp_path):
    _lib(tmp_path)
    rs = C.rows(_slots("ft_i", "bus"), _cores("ft_i", "bus"), SDC, 833.0, tmp_path)
    by = {r["inst"]: r for r in rs}
    assert by["u_bound.u_cland_ft_i"] == dict(inst="u_bound.u_cland_ft_i", pin="fclk", port="fclk_in_ft_i", target_ps=487.7,
                                              pin_delay_ps=71.2, in_max_ps=350.0, setup_ps=92.7, edge="fall", basis="lib")
    assert by["u_bound.u_cland_bus"]["pin_delay_ps"] < 0 and by["u_bound.u_cland_bus"]["target_ps"] == 304.3
    t = C.table(rs)
    assert [l for l in t.splitlines() if not l.startswith("#")] == ["u_bound.u_cland_ft_i fclk fclk_in_ft_i 71.2 487.7 fall"]
    # no readable lib: 95 ps, edge from the wrapper params (WFALL / WNEG = fall writer, else rise)
    rs = C.rows(_slots("ft_i"), _cores("ft_i", lib="gone.lib", WFALL=1), SDC, 833.0, tmp_path)
    assert (rs[0]["setup_ps"], rs[0]["basis"], rs[0]["edge"], rs[0]["pin_delay_ps"]) == (95.0, "default", "fall", 73.5)
    rs = C.rows(_slots("ft_i"), _cores("ft_i", lib="gone.lib"), SDC, 833.0, tmp_path)
    assert rs[0]["edge"] == "rise" and C.table(rs) == ""
    # soft rings / ring_start copies / a bus the SDC does not time on its forwarded clock: no row
    soft = dict(buses=dict(ft_i=dict(D=4, form="hold_mux"),
                           st=dict(_slots("ft_i")["buses"]["ft_i"], port="t_rst_n", width=1)))
    assert C.rows(soft, _cores("ft_i"), SDC, 833.0, tmp_path) == []
    assert C.rows(_slots("other"), _cores("other"), SDC, 833.0, tmp_path) == []


def test_wire_sources_the_hook_once_before_the_pg_connect():
    post = (HERE / "cts_post.tcl").read_text()
    out = C.wire(post)
    assert out.count("cland_fclk_target.tcl]]") == 1 and C.wire(out) == out
    assert out.index("cland_fclk_target.tcl]]") < out.index("ot_pg_connect_all cts_post")       # new cells get supplies
    assert out.index("tap_balance.tcl]]") < out.index("cland_fclk_target.tcl]]")                # tb_* procs are loaded
    assert out.replace(C.HOOK_LINES, "") == post
    with pytest.raises(ValueError, match="PG connect marker"):
        C.wire("puts hi\n")


def _plan(tmp_path, monkeypatch, sdc=SDC, cores=None):
    import landing_contract as LC
    monkeypatch.setattr(LC, "ring_input_sdc", lambda P, tn: sdc)
    kd = tmp_path / "kit"
    (kd / "macros").mkdir(parents=True)
    _lib(kd / "macros")
    shutil.copyfile(HERE / "cts_post.tcl", kd / "cts_post.tcl")
    P = SimpleNamespace(types={"ty": dict(hard_cores=_cores("ft_i", "bus") if cores is None else cores)},
                        die=dict(period_ps=833.0))
    return P, kd


def test_emit_prints_one_line_per_cland_and_wires_the_kit_only_when_a_delay_is_needed(tmp_path, monkeypatch):
    P, kd = _plan(tmp_path, monkeypatch)
    before = (kd / "cts_post.tcl").read_text()
    lines = []
    rs = C.emit(P, "ty", _slots("ft_i", "bus"), kd, log=lines.append)
    assert len(rs) == 2 and len(lines) == 2
    assert lines[1].startswith("OT_CLAND_FCLK_TARGET u_bound.u_cland_ft_i 487.7 pin_delay=71.2 in_max=350.0 setup=92.7(lib) edge=fall")
    assert lines[0].startswith("OT_CLAND_FCLK_TARGET u_bound.u_cland_bus 304.3 pin_delay=0.0 ")
    assert (kd / C.TABLE).read_text().splitlines()[1] == "u_bound.u_cland_ft_i fclk fclk_in_ft_i 71.2 487.7 fall"
    assert (kd / C.HOOK).read_text() == SRC and C.HOOK in (kd / "cts_post.tcl").read_text()
    # nothing to pad (IO-budget ring only) and no hard cland at all: the kit files stay byte-identical
    for slots in (_slots("bus"), dict(buses=dict(bus=dict(D=4, form="hold_mux"))), None):
        P, kd2 = _plan(tmp_path / f"k{len(list(tmp_path.iterdir()))}", monkeypatch)
        C.emit(P, "ty", slots, kd2, log=lines.append)
        assert sorted(p.name for p in kd2.iterdir()) == ["cts_post.tcl", "macros"] and (kd2 / "cts_post.tcl").read_text() == before


def test_gen_phys_calls_the_hook_right_after_the_hard_landing_rows_and_after_cts_post_is_staged():
    src = (HERE / "gen_phys.py").read_text()
    i = src.index("land_slots = hard_landing.emit(")
    j = src.index("cland_fclk_target.emit(P, tn, land_slots, kd, unit_ps=LIB_TIME_UNIT_PS)")
    assert 0 < j - i < 700 and src.index('"cts_post.tcl"') < i and G.LIB_TIME_UNIT_PS == 1.0
    assert src.count("cland_fclk_target.emit(") == 1


def proc(name):
    m = re.search(r"^proc " + re.escape(name) + r"\s+\{[^\n]*?\}\s+\{", SRC, re.M)
    i, d = m.end(), 1
    while d:
        c = SRC[i]
        i += 1
        if c == "\\":
            i += 1
            continue
        d += (c == "{") - (c == "}")
    return SRC[m.start():i]


def tcl(tmp_path, names, body):
    f = tmp_path / "t.tcl"
    f.write_text("\n".join(proc(n) for n in names) + "\n" + body)
    return subprocess.run(["tclsh", str(f)], capture_output=True, text=True, check=True).stdout.split("\n")


@needs_tclsh
def test_tcl_reads_the_generated_table_and_sizes_the_chain_up_never_down(tmp_path):
    rs = [dict(inst="u_bound.u_cland_ft_i", pin="fclk", port="fclk_in_ft_i", target_ps=487.7, pin_delay_ps=71.2, edge="fall"),
          dict(inst="u_bound.u_cland_bus", pin="fclk", port="fclk_in_bus", target_ps=304.3, pin_delay_ps=-112.2, edge="fall")]
    (tmp_path / "t.txt").write_text(C.table(rs))
    out = tcl(tmp_path, ["cft_rows", "cft_cells", "cft_stage"],
              f"puts [cft_rows {tmp_path / 't.txt'}]\nputs [cft_rows {tmp_path / 'none.txt'}]\n"
              "puts [list [cft_cells 69.0 30.0] [cft_cells 9.0 30.0] [cft_cells 60.0 30.0]]\n"
              "puts [list [cft_stage 54.0 3 30.0] [cft_stage 0.0 3 30.0] [cft_stage 5.0 0 30.0] [cft_stage 900.0 3 30.0] [cft_stage 3.0 3 30.0]]\n")
    assert out[0] == "{u_bound.u_cland_ft_i fclk fclk_in_ft_i 71.2 487.7 fall}" and out[1] == ""
    assert out[2] == "3 1 2"
    assert out[3] == "18.0 30.0 30.0 60.0 10.0"


def test_tcl_pads_in_front_of_the_pin_with_the_tap_balance_helpers_and_never_removes_a_cell():
    run = proc("cft_run")
    assert "tb_hang $it [$it getNet] $nb $tag $x $y" in run and "tb_outside $it" in run and "tb_end $todo" in run
    assert "if {$d <= $tol} continue" in run and "set_propagated_clock [all_clocks]" in run
    assert not re.search(r"dbInst_destroy|dbNet_destroy|\bdisconnect\b", SRC)
    assert 'puts "OT_CLAND_FCLK_TARGET $inst [format %.1f $target] ' in run
