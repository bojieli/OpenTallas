"""HOLD-PAD-FLOW 11-24: the wave puts rt/current's pre-GRT hold build (planned hold pad) into a kit made from a pinned snapshot."""
import shlex
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "die_plan"))
import kit_wave as KW          # noqa: E402
import pregrt_ff_hold as PG    # noqa: E402


def test_refresh_command_regenerates_the_kit_file_on_a_host_without_a_checkout(tmp_path):
    kd = tmp_path / "kit dir"
    kd.mkdir()
    hg = (HERE.parent / "die_plan" / "hold_gate.tcl").read_text()
    (kd / "hold_gate.tcl").write_text(hg)
    (kd / "pregrt_ff_hold.tcl").write_text(hg.split(PG.MARK)[0] + "set pg_auto -1\nrepair_timing -hold -hold_margin 40\n")
    cmd = KW.pregrt_refresh_cmd(kd)
    assert len("bash -c " + shlex.quote(cmd)) < KW.FLOW_REFRESH_CMD_MAX
    r = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True, cwd=tmp_path)
    assert r.returncode == 0 and "OT_PREGRT_REFRESH refreshed" in r.stdout, r.stdout + r.stderr
    assert "proc ot_hold_pad" in (kd / "pregrt_ff_hold.tcl").read_text()
    assert sorted(p.name for p in kd.iterdir()) == ["hold_gate.tcl", "pregrt_ff_hold.tcl"]
    # a kit without the build: nothing is created
    bare = tmp_path / "bare"
    bare.mkdir()
    r = subprocess.run(["bash", "-c", KW.pregrt_refresh_cmd(bare)], capture_output=True, text=True)
    assert r.returncode == 0 and "absent" in r.stdout and not any(bare.iterdir())


def test_option_is_off_by_default_and_takes_true_or_patterns():
    cfg = {"dies": {"qwen_compute": {"pregrt_refresh": ["slw_st_b_v1__*", "sle_st_b_v2__cl14c98df5__pv41c959f3"]}, "s81": {}}}
    assert not KW.pregrt_refresh_on(cfg, "s81", "slw_st_b_v1__cle6023ec2")
    assert KW.pregrt_refresh_on(cfg, "qwen_compute", "slw_st_b_v1__cle6023ec2")
    assert KW.pregrt_refresh_on(cfg, "qwen_compute", "sle_st_b_v2__cl14c98df5__pv41c959f3")
    assert not KW.pregrt_refresh_on(cfg, "qwen_compute", "sle_st_b_v2__clfde1249e")
    cfg["dies"]["s81"]["pregrt_refresh"] = True
    assert KW.pregrt_refresh_on(cfg, "s81", "anything")


def test_run_item_refreshes_before_the_inputs_are_fingerprinted():
    src = (HERE / "kit_wave.py").read_text()
    i = src.index('run("pregrt_refresh", remote(pregrt_refresh_cmd(K)), idempotent=True)')
    assert src.index("flow_files_refresh_cmd(K, None if core else W, [_ent])") < i < src.index('run("resume_inputs"')
