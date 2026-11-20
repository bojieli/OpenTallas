"""FLOW-FIX-2045 (FABLE-FIX-S81-SERDES): a report copied from another kit (H21's tt_setup_repair_grt.log in H23 / H25) is not this kit's own"""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import kit_reports as KR  # noqa: E402

T0 = 1_700_000_000


def put(p, t, txt="x"):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(txt)
    os.utime(p, (t, t))


def kit(tmp, synth_t=None, own=(), copied=()):
    k = Path(tmp)
    base = k / "run" / "logs" / "asap7" / "dp_x" / "base"
    if synth_t is not None:
        put(base / "1_2_yosys.log", synth_t); put(base / "1_1_yosys_canonicalize.log", synth_t + 5)
    for n, t in own:
        put(k / n, t, "H23 own")
    for n, t in copied:
        put(k / n, t, "H21 copy")
    return k


def test_copied_report_older_than_the_kits_own_synth_is_stale_and_own_is_not(tmp_path):
    k = kit(tmp_path, T0, own=[("tt_setup_repair_grt.log", T0 + 900)], copied=[("tt_setup_measure_grt.log", T0 - 5000)])
    assert KR.synth_start(str(k)) == T0
    assert not KR.is_stale(str(k), str(k / "tt_setup_repair_grt.log"))
    assert KR.is_stale(str(k), str(k / "tt_setup_measure_grt.log"))
    assert subprocess.run([sys.executable, "-I", str(HERE / "kit_reports.py"), "stale", str(k), str(k / "tt_setup_measure_grt.log")]).returncode == 0
    assert subprocess.run([sys.executable, "-I", str(HERE / "kit_reports.py"), "stale", str(k), str(k / "tt_setup_repair_grt.log")]).returncode == 1


def test_quarantine_moves_only_stale_reports_and_a_fresh_kit_starts_with_none(tmp_path):
    k = kit(tmp_path, None, copied=[("tt_setup_repair_grt.log", T0 - 9000), ("postcts_gate_TT.log", T0 - 9000), ("FAIL_POSTCTS", T0 - 9000)])
    (k / "config.mk").write_text("export CORNER = TC\n")                                  # the kit's own input is no report
    assert KR.synth_start(str(k)) is None
    moved = KR.quarantine(str(k), lambda m: None)
    assert len(moved) == 3 and not list(k.glob("tt_setup_repair*.log")) and (k / "stale_reports" / "tt_setup_repair_grt.log").read_text() == "H21 copy"
    assert (k / "config.mk").exists()
    # a kit that has synthesised: older reports go, newer ones stay
    k2 = kit(tempfile.mkdtemp(), T0, own=[("hold_gate.log", T0 + 50)], copied=[("pregrt_ff_hold.log", T0 - 10)])
    assert [os.path.basename(a) for a, _ in KR.quarantine(str(k2), lambda m: None)] == ["pregrt_ff_hold.log"] and (k2 / "hold_gate.log").exists()
    assert KR.quarantine(str(k2), lambda m: None) == []                                   # idempotent


def test_relayed_kit_keeps_its_internal_order(tmp_path):
    """rsync -a keeps every mtime: the kit's own reports stay newer than its own synth after a relay, so nothing is quarantined"""
    src = kit(tmp_path / "a", T0, own=[("tt_setup_repair_grt.log", T0 + 700), ("run_route.log", T0 + 800)])
    dst = tmp_path / "b"
    subprocess.run(["rsync", "-a", str(src) + "/", str(dst) + "/"], check=True) if shutil.which("rsync") else shutil.copytree(src, dst, copy_function=shutil.copy2)
    assert KR.quarantine(str(dst), lambda m: None) == [] and (dst / "tt_setup_repair_grt.log").exists()


def test_run_kit_quarantines_first_and_gen_ships_the_helper():
    import gen_phys
    t = gen_phys.RUN_KIT
    assert t.index('kit_reports.py" quarantine "$K"') < t.index("RESYNTH-GUARD block") + 5000 and t.index('kit_reports.py" quarantine "$K"') < t.index("STAGE-CAP block (COORD 11-17")
    assert 'kit_reports.py").exists' not in t
    src = (HERE / "gen_phys.py").read_text()
    assert 'with_name("kit_reports.py"), kd / "kit_reports.py"' in src


def test_route_results_ignores_a_stage_result_and_a_signoff_older_than_the_kits_synth(tmp_path):
    sys.path.insert(0, str(HERE.parent))
    import route_results as RR
    k = tmp_path / "kit"; base = k / "run" / "logs" / "asap7" / "dp_t1" / "base"
    put(base / "1_2_yosys.log", T0)
    put(base / "4_1_cts.json", T0 - 4000, "{}"); put(base / "4_1_cts.log", T0 - 4000)           # copied from another kit
    put(base / "5_1_grt.json", T0 + 600, "{}"); put(base / "5_1_grt.log", T0 + 600)             # this kit's own
    put(k / "signoff" / "signoff.json", T0 - 3000, '{"verdict": "PASS", "checks": {"setup_tt": {"wns_ps": -73.5}}}')
    rec = RR.record(str(base))
    assert "cts" not in rec["t"] and "grt" in rec["t"] and "signoff" not in rec["t"] and "signoff" not in rec["res"]
    put(k / "signoff" / "signoff.json", T0 + 900, '{"verdict": "PASS", "checks": {"setup_tt": {"wns_ps": -12.0}}}')
    assert RR.record(str(base))["res"]["signoff"]["setup"] == -12.0
