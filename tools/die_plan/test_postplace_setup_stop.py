"""FLOW-NOADV-R3 11-20 (owner rule, FLEET-WATCH-1630): PLACE-SETUP-STOP, the kit ends after detail place when TT setup WNS < -300 ps."""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "autopilot"))
import gen_phys as G  # noqa: E402
import postplace_setup_stop as PS  # noqa: E402

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
