"""KW-FIX-17 11-05 GRT-STALL (COORD 17:4x): grt183_make.sh stops a 5_1_grt stage whose log is flat on
'global_route -end_incremental' and re-runs it once in a fresh process from the design saved after repair_design.
Local, no Docker/OpenROAD.
    python3 -m pytest -q tools/die_plan/test_grt_stall_kit.py"""
import json
import time

from test_grt183_kit import GRT, ROOT, calls, fake, kit, run

FAST = {"OT_GRT_STALL_S": "2", "OT_GRT_STALL_POLL": "1", "OT_GRT_STALL_KILL_WAIT": "1"}
STALL1 = ('if [ $N = 1 ]; then echo resized > $R/5_1_grt.stall_resume.odb; echo "{O M5 0 0 10 10}" > $R/5_1_grt.stall_resume.shapes; '
          'printf "repair_design\\nglobal_route -end_incremental -resistance_aware -congestion_report_file x\\n" > $L/5_1_grt.tmp.log; '
          'sleep 60; exit 0; fi\n')
OK2 = 'ls $R > $K/ls$N.txt; echo ok > $L/5_1_grt.log; exit 0\n'


def test_stall_stops_and_resumes_once_from_saved_design(tmp_path):
    k, r, l, s = kit(tmp_path)
    t = time.time()
    p = run(k, s, fake(tmp_path, STALL1 + OK2), "grt", env=FAST)
    assert p.returncode == 0, p.stdout + p.stderr
    assert time.time() - t < 30                                     # the stalled process group was stopped
    assert calls(k) == ["cts grt", "resized grt"]
    assert "OT_GRT_STALL 5_1_grt.tmp.log flat" in p.stdout and "OT_GRT_STALL_RESUME attempt 2 rc 0" in p.stdout
    assert "5_1_grt.stall_strip.shapes" in (k / "ls2.txt").read_text()   # the resumed run's hook drops the PRE shapes
    assert (r / "4_cts.odb").read_text() == "cts" and (r / "4_cts.odb").stat().st_mtime == 1000
    for f in ("4_cts.pre_grt183.odb", "5_1_grt.stall_resume.odb", "5_1_grt.stall_resume.shapes", "5_1_grt.stall_strip.shapes"):
        assert not (r / f).exists(), f
    rec = json.loads((r / "5_1_grt.grt183_recovered.json").read_text())
    assert rec["kind"] == "grt_stall" and rec["attempt1_lines"][0].startswith("global_route -end_incremental")
    assert (l / "5_1_grt.log.stall_attempt1").is_file()


def test_second_stall_is_not_resumed(tmp_path):
    k, r, l, s = kit(tmp_path)
    (r / "5_1_grt.grt183_recovered.json").write_text("{}")
    p = run(k, s, fake(tmp_path, 'echo r > $R/5_1_grt.stall_resume.odb; printf "global_route -end_incremental\\n" > $L/5_1_grt.tmp.log; sleep 5; exit 3\n'),
            "grt", env=FAST)
    assert p.returncode == 3 and len(calls(k)) == 1 and "OT_GRT_STALL" not in p.stdout
    assert not (r / "5_1_grt.stall_resume.odb").exists()


def test_other_last_line_is_not_a_stall(tmp_path):
    k, r, l, s = kit(tmp_path)
    p = run(k, s, fake(tmp_path, 'echo r > $R/5_1_grt.stall_resume.odb; printf "global_route -end_incremental\\nrepair_timing\\n" > $L/5_1_grt.tmp.log; sleep 5; exit 0\n'),
            "grt", env=FAST)
    assert p.returncode == 0 and len(calls(k)) == 1 and "OT_GRT_STALL" not in p.stdout
    assert not (r / "5_1_grt.stall_resume.odb").exists()          # the save is removed after a finished stage


def test_save_from_an_earlier_run_does_not_trigger(tmp_path):
    k, r, l, s = kit(tmp_path)
    import os
    (r / "5_1_grt.stall_resume.odb").write_text("old"); os.utime(r / "5_1_grt.stall_resume.odb", (1000, 1000))
    p = run(k, s, fake(tmp_path, 'printf "global_route -end_incremental\\n" > $L/5_1_grt.tmp.log; sleep 5; exit 0\n'), "grt", env=FAST)
    assert p.returncode == 0 and len(calls(k)) == 1 and "OT_GRT_STALL" not in p.stdout


def test_opt_out(tmp_path):
    for how in ("env", "config"):
        k, r, l, s = kit(tmp_path / how, "export OT_GRT_STALL_RESUME = 0\n" if how == "config" else "")
        env = dict(FAST, **({"OT_GRT_STALL_RESUME": "0"} if how == "env" else {}))
        p = run(k, s, fake(tmp_path / how, STALL1.replace("sleep 60", "sleep 5") + OK2), "grt", env=env)
        assert p.returncode == 0 and len(calls(k)) == 1 and "OT_GRT_STALL" not in p.stdout, how


def test_stall_hook_goes_before_grt183_hook_once(tmp_path):
    k, r, l, s = kit(tmp_path)
    (k / "grt_stall_resume.tcl").write_text("# stall hook\n")
    f = fake(tmp_path, "exit 0\n")
    run(k, s, f, "grt"); run(k, s, f, "grt")
    assert (s / "global_route.tcl").read_text() == ("  source /work/grt_stall_resume.tcl\n  source /work/grt183_resume.tcl\n" + GRT)


def test_stage_and_kit_resume_carry_the_hook(tmp_path):
    import core_flow
    import kit_resume as KR
    core_flow.stage_grt183(tmp_path)
    assert (tmp_path / "grt_stall_resume.tcl").read_bytes() == (ROOT / "physical/common_flow/grt_stall_resume.tcl").read_bytes()
    assert KR.is_gate_root("grt_stall_resume.tcl")
