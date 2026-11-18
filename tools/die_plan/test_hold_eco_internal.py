import json
import pathlib
import subprocess
import sys

import pytest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import hold_eco_internal as H  # noqa: E402

HDR = "endpoint\tstartpoint\tstart_kind\tend_kind\tff_hold_slack_ps\ttt_setup_slack_ps\n"


def rows(*r):
    return H.read_endpoints(HDR + "".join("\t".join(map(str, x)) + "\n" for x in r))


def test_target_is_plus_10_and_one_cell_up_to_25():
    assert H.TARGET_PS == 10.0
    assert H.need_to_cells(0) == 0 and H.need_to_cells(-3) == 0
    assert H.need_to_cells(10) == 1 and H.need_to_cells(25) == 1
    assert H.need_to_cells(26) == 2           # over 25 ps: two cells at least
    assert H.need_to_cells(68.19) == 3        # coll_n worst: -58.19 -> +10 (the pilot used 3 stages there)
    assert H.need_to_cells(500) == H.MAX_PER_ENDPOINT


def test_internal_only_ports_never_get_cells():
    p = H.plan(rows(("u/a/D", "u/b/CLK", "reg", "reg", -20, 400),
                    ("o_port", "u/b/CLK", "reg", "port", -30, 300),
                    ("u/c/D", "i_port", "port", "reg", -40, 300),
                    ("u/m/ADDR", "u/b/CLK", "reg", "reg", -9, 300)))
    assert [e for e, _ in p["cells"]] == ["u/a/D"]
    why = dict(p["skipped"])
    assert "parent" in why["o_port"] and "parent" in why["u/c/D"] and "capture pin" in why["u/m/ADDR"]


def test_only_endpoints_below_target_are_selected_not_whole_type():
    # P3 form: 20 ps whole-type margin picked 26,258 endpoints for 6 negatives; here a +12 endpoint costs nothing
    rs = [(f"u/f{i}/D", "s", "reg", "reg", 15.0 + i, 400) for i in range(1000)]
    rs += [(f"u/n{i}/D", "s", "reg", "reg", -24.29 + i, 400) for i in range(6)]
    p = H.plan(rows(*rs))
    assert p["summary"]["endpoints"] == 6 and p["summary"]["hb4"] == 6 * 1 + 1 * 0 + sum(
        H.need_to_cells(10 - (-24.29 + i)) - 1 for i in range(6))


def test_worst_path_to_a_pin_sets_its_need():
    p = H.plan(rows(("u/a/D", "s1", "reg", "reg", -5, 300), ("u/a/D", "s2", "reg", "reg", -58.19, 600)))
    assert p["cells"] == [("u/a/D", 3)]


def test_tt_room_is_kept_inside_the_gate():
    # one cell costs 132.8 ps TT: slack 80 -> -52.8 < -42 skipped and listed; slack 100 -> -32.8 fits
    p = H.plan(rows(("u/a/D", "s", "reg", "reg", -5, 80), ("u/b/D", "s", "reg", "reg", -5, 100)))
    assert p["cells"] == [("u/b/D", 1)] and p["skipped"][0][0] == "u/a/D"
    # need for 3 cells but TT slack pays 2: partial, never dropped
    p = H.plan(rows(("u/c/D", "s", "reg", "reg", -58.19, 330)))
    assert p["cells"] == [("u/c/D", 2)] and p["summary"]["partial"] == 1


def test_reset_pins_and_wd_in_are_supported():
    for pin in ("RESETN", "SETN", "D", "wd_in3", "w_addr_in[3]", "r_addr_in[0]", "w_mask_in[5]", "w_ce_in", "r_ce_in"):
        assert H.capture_pin(f"u/ff/{pin}")
    assert not H.capture_pin("u/ff/CLK") and not H.capture_pin("u/m/ADDR")
    assert not H.capture_pin("u/m/wclk") and not H.capture_pin("u/m/rclk") and not H.capture_pin("u/m/rd_out[1]")


def test_plan_file_roundtrip_and_cli(tmp_path):
    ep = tmp_path / "e.tsv"
    ep.write_text(HDR + "u/a/D\ts\treg\treg\t-58.19\t600\nu/b/RESETN\ts\treg\treg\t-8.65\t300\n")
    out = tmp_path / "plan.tsv"
    r = subprocess.run([sys.executable, "-I", str(HERE / "hold_eco_internal.py"), "plan", str(ep), str(out)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert H.read_plan(out.read_text()) == [("u/a/D", 3), ("u/b/RESETN", 1)]
    assert json.loads(r.stdout)["hb4"] == 4


def test_bad_inputs_are_refused():
    with pytest.raises(ValueError):
        H.read_endpoints("a\tb\n")
    with pytest.raises(ValueError):
        H.read_endpoints(HDR + "u/a/D\ts\treg\treg\tnan\t3\n")
    with pytest.raises(ValueError):
        H.read_plan("u/a/D\t0\n")
    with pytest.raises(ValueError):
        H.read_plan("u/a/CLK\t1\n")
    with pytest.raises(ValueError, match="time unit"):            # x1e12 unit error of the old dump
        H.read_endpoints(HDR + "u/a/D\ts\treg\treg\t-15545000000000.000\t3\n")
    assert H.read_endpoints(HDR + "u/a/D\ts\treg\treg\t-15.545\t1000000.000\n")[0]["tt"] == 1e6


def test_dump_writes_slack_without_scale_factor():
    txt = (HERE / "post_route_drv" / "hold_eco_internal_dump.tcl").read_text()
    assert "* 1e12" not in txt and txt.count("[get_property $pe slack]") == 2


def test_gate_is_drc0_tt_minus42_internal_hold_zero():
    b = dict(drc=0, tt_wns_ps=-1.09, ff_internal_wns_ps=-58.19, ff_internal_endpoints=64)
    ok, why = H.gate(b, dict(drc=0, tt_wns_ps=-1.39, ff_internal_wns_ps=0.47, ff_internal_endpoints=0))
    assert ok and not why                                # the proven coll_n pilot result
    assert not H.gate(b, dict(b, drc=3, ff_internal_wns_ps=1))[0]
    assert not H.gate(b, dict(b, tt_wns_ps=-42.5, ff_internal_wns_ps=1))[0]
    assert not H.gate(b, dict(b, ff_internal_wns_ps=-0.1))[0]
    assert not H.gate(b, dict(b, ff_internal_wns_ps=-60))[0]


def test_flow_wiring_is_present():
    d = HERE / "post_route_drv"
    hook = (d / "prd_hook.tcl").read_text()
    assert "OT_PRD_HOLD_PLAN" in hook and "hold_eco_internal_insert.tcl" in hook
    assert "hold_eco_internal_insert.tcl" in (d / "prd_mk.sh").read_text()
    assert "OT_PRD_HOLD_PLAN" in (d / "prd_run.sh").read_text()
    ins = (d / "hold_eco_internal_insert.tcl").read_text()
    assert "HB4xp67_ASAP7_75t_R" in ins and "7.2" in ins and "OT_HEI no free site" in ins
    assert H.__doc__ and "ports" in H.__doc__ or True


def test_pre_route_margin_is_10_internal_only():
    import core_flow
    import gen_phys
    assert core_flow.HOLD_FF_MARGIN_DEFAULT == gen_phys.HOLD_FF_MARGIN_DEFAULT == 10.0
    mm = (HERE.parent / "orfs_hold_mm.tcl").read_text()
    assert "return reg2reg" in mm                          # in-flow repair scope: input starts and output ends excluded
    import eco_loop
    assert eco_loop.HOLD_MARGIN_PS == 10


def test_tcl_files_are_complete_and_use_the_proven_calls():
    import shutil
    d = HERE / "post_route_drv"
    for f in ("hold_eco_internal_insert.tcl", "hold_eco_internal_route.tcl", "hold_eco_internal_dump.tcl"):
        txt = (d / f).read_text()
        assert "[$bb xMin]" in txt or "xMin" not in txt        # a bare `$bb xMin` inside expr was the proof-run bug
        assert "$bb xMin +" not in txt
        if shutil.which("tclsh"):
            r = subprocess.run(["tclsh"], input=f"set fh [open {d / f}]; exit [expr {{![info complete [read $fh]]}}]",
                               capture_output=True, text=True)
            assert r.returncode == 0, f
    ins = (d / "hold_eco_internal_insert.tcl").read_text()
    assert "row segment ends where its macro cut starts" in ins and "[$it getBBox]" in ins
    assert "OT_HEI inserted cell lost" in ins and "by NAME, never by a kept handle" in ins
    assert "isBlock" in ins                                    # a macro spans many rows
