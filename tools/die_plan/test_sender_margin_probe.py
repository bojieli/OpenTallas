"""Forwarded-clock sender margin probe: single-corner guard, CPPR credit, cross-tap never credited, and the kit SDC form it relies on."""
import os
import pathlib
import shutil
import subprocess

import pytest

HERE = pathlib.Path(__file__).resolve().parent
TCL = HERE / "sender_margin_probe.tcl"
SH = HERE / "sender_margin_probe.sh"

pytestmark = pytest.mark.skipif(not shutil.which("tclsh"), reason="tclsh not installed")


def tcl(body, **env):
    e = {k: v for k, v in os.environ.items() if k != "CORNERS"}
    e.update(SMP_LIB_ONLY="1", **env)
    r = subprocess.run(["tclsh"], input=f"source {{{TCL}}}\n{body}\n", text=True, capture_output=True, env=e)
    return r.stdout.strip(), r.stderr


def test_multi_corner_refused():
    out, _ = tcl("puts [catch {smp_require_single_corner} m]; puts $m", CORNERS="tc bc")
    assert out.startswith("1") and "CORNERS=tc bc" in out


@pytest.mark.parametrize("env", [{}, {"CORNERS": ""}, {"CORNERS": "  "}])
def test_single_corner_accepted(env):
    assert tcl("puts [catch {smp_require_single_corner}]", **env)[0] == "0"


def test_main_refuses_before_loading():
    r = subprocess.run(["tclsh", str(TCL)], text=True, capture_output=True, env={**os.environ, "CORNERS": "tc bc"})
    assert r.returncode != 0 and "multi-corner" in r.stderr


def test_credit_is_the_cppr_remainder():
    # kv3_hgi_v7 ft0 (same tap) and ft10 (clk_t7 data, clk_t1 clock)
    assert float(tcl("puts [smp_credit 119.8 214.8 217.4]")[0]) == pytest.approx(122.4)
    assert float(tcl("puts [smp_credit -115.6 208.8 324.4]")[0]) == pytest.approx(0.0, abs=1e-6)


def test_tap_kinds():
    assert tcl("puts [smp_classify clk_t4 clk_t4]")[0] == "same_tap"
    assert tcl("puts [smp_classify clk_t7 clk_t1]")[0] == "cross_tap"
    assert tcl("puts [smp_classify {} clk_t1]")[0] == "unknown"


def test_sources_from_gen_and_written_sdc():
    sdc = ("create_generated_clock -name fclk_out_a -master_clock clk -source [get_ports clk_t4] -divide_by 1 [get_ports fclk_out_a]\n"
           "create_generated_clock -name fclk_out_b -source [get_ports {clk_t25}] -master_clock [get_clocks {clk}] -divide_by 1 "
           "[get_ports {fclk_out_b[0]}]\ncreate_clock -name fclk_in_a -period 833.0 [get_ports fclk_in_a]\n")
    out, _ = tcl("set d [smp_sources {" + sdc + "}]; puts \"[dict get $d fclk_out_a] [dict get $d fclk_out_b] [dict size $d]\"")
    assert out == "clk_t4 clk_t25 2"


def test_bus_bit_names_also_tried_escaped():
    out, _ = tcl("puts [lindex [smp_odb_names {u/q[13]$_DFF_P_/CLK}] 1]")
    assert out == "u/q\\[13\\]$_DFF_P_/CLK"


def test_runner_clears_corners(tmp_path):
    b = tmp_path / "kit/run/results/asap7/dp_x/base"
    b.mkdir(parents=True)
    (b / "4_cts.odb").write_text("x")
    (b / "4_cts.sdc").write_text("x")
    r = subprocess.run(["bash", str(SH), str(tmp_path / "kit"), str(tmp_path / "o")], text=True, capture_output=True,
                       env={**os.environ, "SMP_DRY": "1"})
    assert r.returncode == 0 and " CORNERS= " in r.stdout and "asap7/dp_x/base" in r.stdout


def test_kit_sdc_exports_are_generated_clocks_of_their_source_tap():
    """Per-tap source, divide by 1, on the export port: what lets STA credit the shared tap. Never a create_clock."""
    import landing_contract as L
    from test_landing_sdc_outputs import fixture
    p, tn = fixture()
    for pin in p.types[tn]["clock"]["landing_contract"]["pins"]:
        if pin["kind"] == "clock":
            pin["source_clock_port"] = "clk_t7"
    text = L.sdc(p, tn, "set x [all_outputs]\n")
    assert ("create_generated_clock -name fclk_out_data -master_clock clk -source [get_ports clk_t7] -divide_by 1 "
            "[get_ports fclk_out_data]") in text
    assert "create_clock -name fclk_out_data" not in text
