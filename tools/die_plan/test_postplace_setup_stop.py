"""FLOW-NOADV-R3 11-20 (owner rule, FLEET-WATCH-1630): PLACE-SETUP-STOP, the kit ends after detail place when TT setup WNS < -300 ps."""
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "autopilot"))
import gen_phys as G  # noqa: E402
import postplace_setup_stop as PS  # noqa: E402

TCLSH = shutil.which("tclsh")

LOG = ("OT_TT_SETUP_REPAIR rc basis placement\nOT_TT_SETUP_REPAIR measure TT setup wns %s tns -90000.00\n"
       "OT_POSTPLACE_WORST start=u_a/q_reg[3] end=u_b/d_reg[9] hop_um=412.6\n")


def test_below_the_stop_ends_the_kit_with_wns_endpoints_and_hop(tmp_path):
    log = tmp_path / "postplace_setup.log"
    log.write_text(LOG % "-412.30")
    marker, js = tmp_path / "FAIL_POSTCTS", tmp_path / "stop.json"
    rc = PS.main(["--log", str(log), "--stop", "-300", "--marker", str(marker), "--json", str(js)])
    assert rc == 6
    line = marker.read_text().strip()
    assert "PLACE-SETUP-STOP" in line and "wns -412.30" in line and "start=u_a/q_reg[3]" in line and "end=u_b/d_reg[9]" in line and "hop_um=412.6" in line
    assert '"stopped": true' in js.read_text()


def test_at_or_above_the_stop_or_no_measurement_continues(tmp_path):
    log = tmp_path / "l"
    for wns in ("-299.99", "-300.00", "-12.0", "35.5"):
        log.write_text(LOG % wns)
        assert PS.main(["--log", str(log), "--stop", "-300"]) == 0, wns
    log.write_text("openroad crashed\n")                               # no measurement never stops a flow
    assert PS.main(["--log", str(log), "--stop", "-300"]) == 0
    assert PS.main(["--log", str(tmp_path / "missing"), "--stop", "-300"]) == 0


def test_only_kit_wave_gens_stop_and_exemptions():
    W = {"OT_KIT_WAVE": "1"}
    assert G.postplace_stop_ps(W) == -300.0
    assert G.postplace_stop_ps(dict(W, OT_POSTPLACE_SETUP_STOP_PS="-250")) == -250.0
    assert G.postplace_stop_ps({}) is None                                        # a kit run by hand (private kit, lane proof) is not a wave gen
    assert G.postplace_stop_ps({"OT_LANE": "X"}) is None
    for extra in ({"OT_POSTPLACE_SETUP_STOP": "0"}, {"OT_LANE": "FABLE-FIX-X"}, {"OT_RESIGN": "1"}, {"OT_KEEP_GOING": "1"}):
        assert G.postplace_stop_ps(dict(W, **extra)) is None, extra
    assert G.postplace_stop_ps(dict(W, OT_RESIGN="0")) == -300.0


def test_wave_run_item_exports_the_wave_marker_and_resign_pick_is_tagged():
    src = (HERE.parent / "autopilot" / "kit_wave.py").read_text()
    assert 'genv += "export OT_KIT_WAVE=1; " + ("export OT_RESIGN=1; " if sp.get("resign") else "")' in src
    assert 'sp["resign"] = True' in src and 'r.get("_resign")' in src


def test_run_script_measures_place_odb_and_classifier_names_the_class():
    src = (HERE / "gen_phys.py").read_text()
    assert "postplace_setup_stop.py --log /work/postplace_setup.log" in src and "3_place.odb" in src
    import kit_wave as KW
    why_line = ("FAIL_POSTPLACE PLACE-SETUP-STOP wns -412.30 ps < -300 ps (TT, post-place; routing cannot close it) start=a end=b hop_um=412.6")
    cls, why = KW.classify("place", why_line)
    assert cls == "PLAN" and "PLACE-SETUP-STOP" in why
    assert KW.typed_class(cls, "place", why_line) == "design:place_setup_stop"



def test_postplace_attribution_selects_complete_worst_group():
    source = (HERE / "tt_setup_repair.tcl").read_text()
    proc = "proc ot_postplace_worst_report " + source.split("proc ot_postplace_worst_report ", 1)[1].split("\n}\n", 1)[0] + "\n}\n"
    script = proc + """
lassign [ot_postplace_worst_report {
Startpoint: async_source
Endpoint: async_sink
Path Group: asynchronous
 0.0  0.0 ^ async_site/Y (DFF)
 -6400.25 slack (VIOLATED)

Startpoint: real_source
Endpoint: real_sink
Path Group: clk
 0.0  0.0 ^ real_site/Y (DFF)
 -187714.01 slack (VIOLATED)
}] slack path
puts $slack
puts [join $path \\n]
"""
    result = subprocess.run(["tclsh"], input=script, text=True, capture_output=True, check=True)
    assert result.stderr == ""
    assert result.stdout.splitlines()[0] == "-187714.01"
    assert "Startpoint: real_source" in result.stdout and "Endpoint: real_sink" in result.stdout
    assert "async" not in result.stdout


def test_recovery_is_reported_but_never_stops_the_kit(tmp_path):
    """FLOW-PLACEMEAS-1121: QC x_fe_o reset recovery -176.66 at place (+551.17 post-hook CTS) and the -30k..-400k reset-relay stops."""
    log = tmp_path / "l"
    log.write_text(LOG % "-41.20" + "OT_POSTPLACE_RECOVERY wns -131707.67 start=u_rl.rst_n[3]$_DFF_PN0_ end=u_x/rn (reset recovery, reported only; not in the setup stop)\n")
    js = tmp_path / "s.json"
    assert PS.main(["--log", str(log), "--stop", "-300", "--json", str(js)]) == 0
    import json
    d = json.loads(js.read_text())
    assert d["stopped"] is False and d["wns"] == -41.2 and d["recovery_wns"] == -131707.67 and d["recovery_end"] == "u_x/rn"
    log.write_text(LOG % "-412.30" + "OT_POSTPLACE_RECOVERY wns 12.00 start=a end=b (x)\n")   # data setup still stops at -300
    assert PS.main(["--log", str(log), "--stop", "-300"]) == 6
    log.write_text(LOG % "-12.0" + "OT_POSTPLACE_RECOVERY wns ? (read failed: x)\n")
    assert PS.read_log(log.read_text())["recovery_wns"] is None


def _pp_stub(nets, recovery_report, path_rows="", db_stubs="", odb="stub.odb"):
    """tclsh frame for tt_setup_repair.tcl with OT_POSTPLACE_WORST=1: clocks clk (std-cell tree) and fclk_in_a (port -> macro pin)."""
    return f"""
namespace eval sta {{}}
namespace eval ord {{}}
set ::sta_recovery_removal_checks_enabled 1
proc sta::worst_slack {{args}} {{ return [expr {{$::sta_recovery_removal_checks_enabled ? -131707.67 : -41.25}}] }}
proc sta::total_negative_slack {{args}} {{ return -20.0 }}
proc sta::redirect_string_begin {{}} {{ set ::rs {{}} }}
proc sta::redirect_string_end {{}} {{ return $::rs }}
proc report_checks {{args}} {{
  if {{[lsearch $args asynchronous] >= 0}} {{ append ::rs "{recovery_report}" ; return }}
  append ::rs "Startpoint: d_src\\nEndpoint: d_end\\nPath Group: clk\\n{path_rows} -41.25 slack (VIOLATED)\\n"
}}
rename exec actual_exec
proc exec {{args}} {{ return "TC_LIB_FILES = stub.lib" }}
rename source actual_source
proc source {{path}} {{ if {{[file tail $path] eq "tt_setup_repair.tcl"}} {{ uplevel 1 [list actual_source $path] }} }}
proc read_liberty {{args}} {{}}
proc read_db {{args}} {{}}
proc read_sdc {{sdc}} {{ puts "SDC $sdc" }}
proc all_clocks {{}} {{ return {{clk fclk_in_a vclk}} }}
proc get_property {{obj property}} {{ return [dict get {{clk clk_port fclk_in_a fclk_in_a_port vclk {{}}}} $obj] }}
proc get_full_name {{o}} {{ return $o }}
proc get_name {{o}} {{ return $o }}
proc set_clock_latency {{args}} {{}}
proc set_propagated_clock {{clocks}} {{ puts "PROPAGATED $clocks" }}
proc estimate_parasitics {{basis}} {{}}
set ::nets [dict create {nets}]
proc ord::get_db_block {{}} {{ return blk }}
proc blk {{m args}} {{
  switch $m {{
    findBTerm {{ return [expr {{[dict exists $::nets [lindex $args 0]] ? "bt:[lindex $args 0]" : "NULL"}}] }}
    getDbUnitsPerMicron {{ return 1000 }}
    findInst {{ return NULL }}
  }}
}}
proc unknown {{cmd args}} {{
  if {{[string match bt:* $cmd]}} {{ return "net:[string range $cmd 3 end]" }}
  if {{[string match net:* $cmd]}} {{ set r {{}}; foreach m [dict get $::nets [string range $cmd 4 end]] {{ lappend r "it:$m" }}; return $r }}
  if {{[string match it:* $cmd]}} {{ return "inst:[string range $cmd 3 end]" }}
  if {{[string match inst:* $cmd]}} {{ return "mst:[string range $cmd 5 end]" }}
  if {{[string match mst:* $cmd]}} {{ return [string match *macro* $cmd] }}
  error "unknown $cmd"
}}
{db_stubs}
set ::env(OT_POSTPLACE_WORST) 1
set ::env(OT_TT_SETUP_MEASURE) 1
set ::env(ODB) {{{odb}}}
source {{{HERE / 'tt_setup_repair.tcl'}}}
"""


@pytest.mark.skipif(not TCLSH, reason="tclsh")
def test_postplace_propagates_only_port_direct_macro_clocks_and_drops_recovery():
    """FLOW-PLACEMEAS-1121: fclk_in_* -> sta_cland fclk read -112.90 ideal vs +39.12 propagated (QC slw_st_a_v2__cl9f076a5c a3)."""
    rec = "Startpoint: u_rrl_128/q\\nEndpoint: u_bout_x_fe_o/eq\\nPath Group: asynchronous\\n -176.66 slack (VIOLATED)\\n"
    nets = "clk_port {ff1 macro_core buf3} fclk_in_a_port {macro_cland}"
    r = subprocess.run([TCLSH], input=_pp_stub(nets, rec), text=True, capture_output=True, check=True)
    out = r.stdout
    assert "PROPAGATED fclk_in_a" in out and "PROPAGATED clk" not in out
    assert "OT_POSTPLACE_CLOCKS propagated 1 port-direct macro clocks, ideal 1: fclk_in_a" in out
    assert "OT_POSTPLACE_RECOVERY wns -176.66 start=u_rrl_128/q end=u_bout_x_fe_o/eq" in out
    assert "OT_TT_SETUP_REPAIR measure TT setup wns -41.25" in out            # recovery switched off before the stop's number
    assert "start=d_src end=d_end" in out
    rec_line, meas_line = out.index("OT_POSTPLACE_RECOVERY"), out.index("measure TT setup wns")
    assert rec_line < meas_line
    d = PS.read_log(out)
    assert d["wns"] == -41.25 and d["recovery_wns"] == -176.66


@pytest.mark.skipif(not TCLSH, reason="tclsh")
def test_postplace_keeps_a_clock_with_a_buffer_or_flop_sink_ideal():
    nets = "clk_port {ff1 macro_core} fclk_in_a_port {macro_cland buf9}"
    r = subprocess.run([TCLSH], input=_pp_stub(nets, ""), text=True, capture_output=True, check=True)
    assert "PROPAGATED" not in r.stdout and "OT_POSTPLACE_CLOCKS propagated 0" in r.stdout
    assert "OT_POSTPLACE_RECOVERY wns none" in r.stdout


@pytest.mark.skipif(not TCLSH, reason="tclsh")
def test_postplace_reads_the_placed_checkpoint_sdc(tmp_path):
    odb = tmp_path / "3_place.odb"
    sdc = odb.with_suffix(".sdc")

    r = subprocess.run([TCLSH], input=_pp_stub("", "", odb=odb), text=True, capture_output=True, check=True)
    assert "SDC /work/constraint.sdc" in r.stdout

    sdc.write_text("create_clock -period 833 clk\n")
    r = subprocess.run([TCLSH], input=_pp_stub("", "", odb=odb), text=True, capture_output=True, check=True)
    assert f"SDC {sdc}" in r.stdout
    assert "SDC /work/constraint.sdc" not in r.stdout


@pytest.mark.skipif(not TCLSH, reason="tclsh")
def test_postplace_path_geometry_uses_buffer_pins_macro_pin_and_port():
    rows = r""" 0.00 0.00 ^ input (in)\n 1.00 1.00 ^ u_buf/A (BUF)\n 2.00 3.00 ^ u_buf/Y (BUF)\n 3.00 6.00 ^ u_macro/d\[347\] (MACRO)\n 6.00 data arrival time\n"""
    stubs = r"""
rename blk clock_block
proc blk {method args} {
    set name [lindex $args 0]
    if {$method eq "findITerm"} {
        return [dict get {u_buf/A pin_a u_buf/Y pin_y {u_macro/d\[347\]} pin_d u_macro/d[347] NULL} $name]
    }
    if {$method eq "findBTerm" && $name eq "input"} { return port_d }
    return [clock_block $method {*}$args]
}
proc pin_a {method} { return [dict get {getAvgXY {1 10000 0} getInst buffer} $method] }
proc pin_y {method} { return [dict get {getAvgXY {1 20000 2000} getInst buffer} $method] }
proc pin_d {method} { return [dict get {getAvgXY {1 100000 2000} getInst macro} $method] }
proc port_d {method} { return [dict get {getBPins {pin} getBBox port_rect} $method] }
proc port_rect {method} { return 0 }
"""
    r = subprocess.run([TCLSH], input=_pp_stub("", "", rows, stubs), text=True, capture_output=True, check=True)
    d = PS.read_log(r.stdout)
    assert (d["hop_um"], d["path_um"], d["span_um"], d["stages"]) == (80.0, 90.0, 102.0, 2)


@pytest.mark.skipif(not TCLSH, reason="tclsh")
@pytest.mark.parametrize("has_pin", [True, False])
def test_postplace_path_keeps_endpoints_and_resolves_mixed_bus_escaping(has_pin):
    rows = r""" 0.00 0.00 ^ u_src/Q (DFF)\n 1.00 1.00 ^ top/u_macro\[0\]/d\[347\] (MACRO)\n 1.00 data arrival time\n"""
    stubs = r"""
rename blk clock_block
proc blk {method args} {
    set name [lindex $args 0]
    if {$method eq "findITerm"} {
        return [expr {$name eq "u_src/Q" ? "pin_q" : "NULL"}]
    }
    if {$method eq "findInst" && $name eq {top/u_macro\[0\]}} { return macro }
    return [clock_block $method {*}$args]
}
proc macro {method pin} {
    if {$method eq "findITerm" && $pin eq {d[347]} && @HAS_PIN@} { return pin_d }
    return NULL
}
proc pin_q {method} { return [dict get {getAvgXY {1 10000 0} getInst source_ff} $method] }
proc pin_d {method} { return [dict get {getAvgXY {1 100000 2000} getInst macro} $method] }
""".replace("@HAS_PIN@", "1" if has_pin else "0")
    r = subprocess.run([TCLSH], input=_pp_stub("", "", rows, stubs), text=True, capture_output=True, check=True)
    rec = PS.read_log(r.stdout)
    assert (rec["wns"], rec["start"], rec["end"]) == (-41.25, "d_src", "d_end")
    assert rec["hop_um"] == (92.0 if has_pin else None)
    assert ("no instance terminal" in r.stdout) is not has_pin


def test_path_length_span_and_stage_count_reach_the_marker(tmp_path):
    """FABLE-FIX-S81-STROBE 11-21: S81 serdes t16 START wavefront: hop 115.9 um but 2.8 mm / 27 repeaters in one cycle (-1252 ps)."""
    log = tmp_path / "l"
    log.write_text("OT_TT_SETUP_REPAIR measure TT setup wns -1252.45 tns -68858.48\n"
                   "OT_POSTPLACE_WORST start=u_o/s2 end=u_r/q hop_um=115.9 path_um=2901.3 span_um=2837.2 stages=34\n")
    marker, js = tmp_path / "m", tmp_path / "j"
    assert PS.main(["--log", str(log), "--stop", "-300", "--marker", str(marker), "--json", str(js)]) == 6
    line = marker.read_text().strip()
    assert "hop_um=115.9 path_um=2901.3 span_um=2837.2 stages=34;" in line
    import json
    d = json.loads(js.read_text())
    assert d["path_um"] == 2901.3 and d["span_um"] == 2837.2 and d["stages"] == 34 and d["hop_um"] == 115.9
    import kit_wave as KW
    assert KW.classify("place", line)[0] == "PLAN"
    old = PS.read_log(LOG % "-412.30")                                   # logs of older kits keep reading
    assert old["hop_um"] == 412.6 and old["path_um"] is None and old["stages"] is None
    src = (HERE / "tt_setup_repair.tcl").read_text()
    assert "path_um=%.1f span_um=%.1f stages=%d" in src
