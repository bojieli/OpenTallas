"""FLOW-FIX-2045 (S81-GEOM-OPUS 39ed0e56): run_kit.sh writes its own resume file for an in-place restart: newest valid stage result, inputs not newer, OT_RESUME=0 opts out"""
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit_resume as KR  # noqa: E402

T0 = 1_700_000_000


def put(p, t, txt="x"):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(txt)
    os.utime(p, (t, t))


def kit(tmp, upto="cts"):
    k = Path(tmp)
    put(k / "config.mk", T0, "export POST_CTS_TCL = /work/cts_post.tcl\nexport PRE_GLOBAL_ROUTE_TCL = /work/grt_pre.tcl\n")
    put(k / "cts_post.tcl", T0, "# cts hook\n"); put(k / "grt_pre.tcl", T0, "# grt hook\n")
    base = k / "run" / "results" / "asap7" / "dp_x" / "base"; logs = k / "run" / "logs" / "asap7" / "dp_x" / "base"
    t = T0 + 100
    for s in KR.STEPS[:-1]:
        for n in KR.STEP_OUT[s]:
            put(base / n, t)
        for n in KR.STEP_LOGS[s]:
            put(logs / n, t, "all good\n")
        if s == upto:
            break
        t += 100
    return k


def test_failed_grt_restart_resumes_at_grt_from_the_newest_valid_step(tmp_path):
    k = kit(tmp_path, "cts")
    r = KR.auto_write(str(k), "route")
    assert r["start"] == "grt" and r["reused_steps"] == ["synth", "floorplan", "place", "cts"] and r["auto"]
    j = json.loads((k / "resume.json").read_text())
    assert j["start"] == "grt" and j["source"]["kit"] == str(k) and j["links"] == []          # fields run_kit.sh reads (start, reused_steps, source host / kit)


def test_an_input_newer_than_a_step_invalidates_that_step_and_later_ones(tmp_path):
    k = kit(tmp_path, "cts")
    os.utime(k / "cts_post.tcl", (T0 + 900, T0 + 900))            # the CTS hook was edited after CTS ran
    r = KR.auto_write(str(k), "route")
    assert r["start"] == "cts" and r["reused_steps"] == ["synth", "floorplan", "place"] and "cts_post.tcl" in r["why"]
    os.utime(k / "config.mk", (T0 + 900, T0 + 900))                # a synth-class input newer than synth: nothing past synth is reusable
    assert KR.auto_write(str(k), "route") is None and not (k / "resume.json").exists()


def test_a_failed_stage_is_not_reused_and_synth_only_gives_no_file(tmp_path):
    k = kit(tmp_path, "cts")
    put(k / "run" / "logs" / "asap7" / "dp_x" / "base" / "4_1_cts.log", T0 + 450, "[ERROR RSZ-0074] boom\n")
    assert KR.auto_write(str(k), "route")["start"] == "cts"       # CTS failed: its start step, place is the newest valid
    k2 = kit(tmp_path / "b", "synth")
    assert KR.auto_write(str(k2), "route") is None


def test_a_wave_resume_plan_is_never_overwritten_and_an_auto_one_is_recomputed(tmp_path):
    k = kit(tmp_path, "cts")
    (k / "resume.json").write_text(json.dumps({"start": "place", "reused_steps": ["synth", "floorplan"], "source": {"host": "h", "kit": "/x"}}))
    assert KR.auto_write(str(k), "route") is None and json.loads((k / "resume.json").read_text())["start"] == "place"
    (k / "resume.json").unlink()
    KR.auto_write(str(k), "route")
    base = k / "run" / "results" / "asap7" / "dp_x" / "base"
    put(base / "5_1_grt.odb", T0 + 600); put(k / "run" / "logs" / "asap7" / "dp_x" / "base" / "5_1_grt.log", T0 + 600, "ok\n")
    assert KR.auto_write(str(k), "route")["reused_steps"][-1] == "grt"                      # the next restart sees the new result (route has no reusable step)
    assert json.loads((k / "resume.json").read_text())["start"] == "route"


def test_goal_before_the_start_step_and_the_cli(tmp_path):
    k = kit(tmp_path, "cts")
    assert KR.auto_plan(str(k), "cts")["start"] == "cts"                                    # goal cts, results through cts: nothing left but the goal step itself
    r = subprocess.run([sys.executable, "-I", str(Path(KR.__file__)), "auto", str(k), "route"], capture_output=True, text=True)
    assert r.returncode == 0 and "KW_RESUME_AUTO" in r.stderr and (k / "resume.json").exists()


def test_run_kit_calls_it_first_and_honours_the_opt_out():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "die_plan"))
    import gen_phys
    t = gen_phys.RUN_KIT
    i = t.index("AUTO-RESUME block")
    assert i < t.index("RESYNTH-GUARD block") and "OT_RESUME:-1}\" != 0" in t[i:i + 900] and ".no_auto_resume" in t[i:i + 900] and 'kit_resume.py" auto "$K" "$GOAL"' in t[i:i + 900]
    assert 'shutil.copyfile(Path(__file__).resolve().parents[1] / "autopilot" / "kit_resume.py", kd / "kit_resume.py")' in (Path(gen_phys.__file__)).read_text()


def test_hooks_that_name_config_mk_stay_at_their_own_step(tmp_path):
    """FLOW-OPS-R3 11-24 (QC STB dff1e9a2ad86): a CTS hook that mentions config.mk made config.mk a synth producer, and
    config.mk's text then made every CTS/GRT hook synth: six hooks rewritten after place forced a full rerun"""
    k = kit(tmp_path, "place")
    put(k / "cts_post.tcl", T0 + 900, "# cts hook\nset f [open $::env(WORK)/config.mk]\nsource $::env(WORK)/tap_balance.tcl\n")
    put(k / "tap_balance.tcl", T0 + 900, "proc tb {} {}\n")
    put(k / "grt_pre.tcl", T0 + 900, "source hold_guard_grt.tcl\n"); put(k / "hold_guard_grt.tcl", T0 + 900, "proc g {} {}\n")
    r = KR.auto_plan(str(k), "route")
    assert r and r["start"] == "cts" and r["reused_steps"] == ["synth", "floorplan", "place"]
    os.utime(k / "config.mk", (T0 + 900, T0 + 900))                # config.mk itself is still a synth input
    assert KR.auto_plan(str(k), "route") is None


def test_hdl_identifiers_are_not_reads_but_includes_are(tmp_path):
    k = kit(tmp_path, "place")
    with open(k / "config.mk", "a") as f:
        f.write("export VERILOG_FILES = /work/rtl/top.sv\n")
    put(k / "rtl" / "top.sv", T0, "`include \"defs.svh\"\n// clock_taps drive this\nwire tap_reset_split;\nmodule top; endmodule\n")
    put(k / "rtl" / "defs.svh", T0, "`define X 1\n")
    put(k / "pre_cts.tcl", T0 + 900, "source clock_taps.tcl\n"); put(k / "clock_taps.tcl", T0 + 900, "proc t {} {}\n")
    put(k / "tap_reset_split.tcl", T0 + 900, "proc s {} {}\n")
    with open(k / "config.mk", "a") as f:
        f.write("export PRE_CTS_TCL = /work/pre_cts.tcl\n")
    os.utime(k / "config.mk", (T0, T0))
    put(k / "cts_post.tcl", T0, "source tap_reset_split.tcl\n")
    r = KR.auto_plan(str(k), "route")
    assert r and r["start"] == "cts", r
    os.utime(k / "rtl" / "defs.svh", (T0 + 900, T0 + 900))         # the included header is a synth input
    assert KR.auto_plan(str(k), "route") is None
