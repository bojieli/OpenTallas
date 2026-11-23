"""PROBE-THROUGH-1122 (COORD 18:5x): OT_PROBE_THROUGH=1 kits run past the triage stops in estimate mode, write PROBE.json, never sign off."""
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_phys as G          # noqa: E402
import probe_report as PR     # noqa: E402
import signoff as S           # noqa: E402

GATES = ("hop census (GENBUG-5.2", "FF structural hold gate", "SETUP_TRIAGE pre-route setup estimate", "FAIL_POSTCTS pre-route insertion gate",
         "final GRT released TT/FF policy", "--json /work/place_setup_stop.json")


def test_probe_flag_is_opt_in():
    assert G.probe_through({"OT_PROBE_THROUGH": "1"}) and not G.probe_through({}) and not G.probe_through({"OT_PROBE_THROUGH": "0"})


def test_every_triage_stop_is_guarded_in_the_run_script():
    for g in GATES:
        lines = [ln for ln in G.RUN_KIT.splitlines() if g in ln and not ln.lstrip().startswith("#")]
        assert lines, g
        for ln in lines:
            assert "probe_through.on" in ln, (g, ln[:200])
            assert not re.search(r"(tee -a|>>) /work/FAIL_POSTCTS; rc=[46]", ln), (g, ln[:200])
    assert re.search(r"if \[ \\\$ppr = 6 \] && \[ ! -f /work/probe_through.on \]; then rc=6", G.RUN_KIT)
    assert 'python3 -I "$K/probe_report.py" "$K" --goal "$GOAL" --rc "$rc"' in G.RUN_KIT


def test_stop_marker_target_follows_the_flag(tmp_path):
    expr = r"\$( [ -f /work/probe_through.on ] && echo /work/PROBE_STOPS.log || echo /work/FAIL_POSTCTS)"
    assert expr in G.RUN_KIT
    sh = expr.replace("\\$", "$").replace("/work", str(tmp_path))
    run = lambda: subprocess.run(["bash", "-c", f"echo {sh}"], capture_output=True, text=True).stdout.strip()
    assert run().endswith("FAIL_POSTCTS")
    (tmp_path / "probe_through.on").write_text("1\n")
    assert run().endswith("PROBE_STOPS.log")


def test_signoff_never_signs_a_probe_kit(tmp_path):
    rec = {"inputs": {"kit": str(tmp_path)}, "verdict": "SIGNED", "reasons": [], "checks": {}, "local_verdict": "SIGNED"}
    assert S.probe_guard(dict(rec))["verdict"] == "SIGNED"
    (tmp_path / "probe_through.on").write_text("1\n")
    r = S.probe_guard(dict(rec, checks={}))
    assert r["verdict"] == "NOT SIGNED" and r["local_verdict"] == "NOT SIGNED" and r["probe"] is True
    assert r["reasons"][-1].startswith("probe_through: FAIL") and r["checks"]["probe_through"]["verdict"] == "FAIL"
    assert len(S.probe_guard(r)["reasons"]) == 1                  # idempotent


STA = """Startpoint: u_bound.u_a.q_reg (rising edge-triggered flip-flop clocked by clk)
Endpoint: u_bound.u_b.d_reg/D (rising edge-triggered flip-flop clocked by clk)
                               -120.50   slack (VIOLATED)

Startpoint: u_bound.u_a.r_reg (rising edge-triggered flip-flop clocked by clk)
Endpoint: u_bound.u_b.e_reg/D (rising edge-triggered flip-flop clocked by clk)
                                -30.00   slack (VIOLATED)

Startpoint: in_x (input port clocked by vclk)
Endpoint: u_bound.u_c.f_reg/D (rising edge-triggered flip-flop clocked by clk)
                                 12.00   slack (MET)
"""
GRT = """[INFO GRT-0096] Final congestion report:
Layer         Resource        Demand        Usage (%)    Max H / Max V / Total Overflow
---------------------------------------------------------------------------------------
M1                   0             0            0.00%             0 /  0 /  0
M2               12345          6789           55.00%             3 /  0 / 40
M3               12345          6789           55.00%             0 /  2 /  0
Total            24690         13578           55.00%             3 /  2 / 40
"""


def test_probe_report_lists_every_class(tmp_path):
    K = tmp_path / "kit"
    base, logs, reps = (K / "run" / x / "asap7" / "d" / "base" for x in ("results", "logs", "reports"))
    for d in (base, logs, reps):
        d.mkdir(parents=True)
    for f in ("3_place.odb", "4_cts.odb", "5_1_grt.odb"):
        (base / f).write_text("x")
    (K / "probe_through.on").write_text("1\n")
    (K / "PROBE_STOPS.log").write_text("FAIL_POSTPLACE PLACE-SETUP-STOP wns -310.00 ps < -300 ps (TT, post-place)\n"
                                        "FAIL_POSTCTS SETUP_TRIAGE pre-route setup estimate below the stop: OT_POSTCTS_GATE TT ...\n")
    (K / "place_setup_stop.json").write_text(json.dumps({"wns": -310.0, "start": "u_bound.u_a.q_reg", "end": "u_bound.u_b.d_reg/D"}))
    (K / "postcts_gate_TT.json").write_text(json.dumps({"pinreg_n": 10, "pinreg_mean_ps": 420.0, "bound_ps": 380.0, "dev_ps": 40.0, "tol_ps": 25.0,
                                                        "setup_wns_est_ps": -180.0, "band_verdict": "ADVISORY", "verdict": "FAIL"}))
    (K / "postcts_gate_FF.json").write_text(json.dumps({"hold_wns_est_ps": -12.5, "band_verdict": "PASS", "verdict": "PASS"}))
    (K / "postplace_setup.log").write_text(STA)
    (logs / "5_1_grt.log").write_text(GRT + "Found 7 slew violations\n")
    (reps / "congestion.rpt").write_text("violation type: Horizontal congestion\n  srcs: net1\n  bbox = ( 10.0, 20.0 ) - ( 12.0, 22.0 ) on Layer M2\n")
    assert PR.main([str(K), "--goal", "route", "--rc", "0"]) == 0
    p = json.loads((K / "PROBE.json").read_text())
    assert p["signoff"] is False and p["deepest"] == "grt" and len(p["stops_passed"]) == 2
    assert p["setup"]["post_place"]["wns"] == -310.0 and p["setup"]["pre_route_est_ps"] == -180.0
    assert p["setup_classes"][0] == {"start_block": "u_a", "end_block": "u_b", "count": 2, "worst_ps": -120.5,
                                     "example": "u_bound.u_a.q_reg -> u_bound.u_b.d_reg/D"}
    assert p["clock_insertion"]["TT"]["dev_ps"] == 40.0 and p["hold"]["ff_est_ps"] == -12.5
    assert p["congestion"]["total_overflow"] == 40 and p["congestion"]["layers"] == {"M2": 40} and p["congestion"]["markers"] == 1
    assert p["drv"]["slew"] == 7
    assert {"PLACE-SETUP-STOP", "SETUP_TRIAGE", "setup", "congestion", "clock_insertion", "hold", "drv"} <= set(p["failing_classes"])


def test_probe_report_of_an_empty_kit_is_not_an_error(tmp_path):
    assert PR.main([str(tmp_path)]) == 0
    p = json.loads((tmp_path / "PROBE.json").read_text())
    assert p["deepest"] is None and p["failing_classes"] == [] and p["signoff"] is False
