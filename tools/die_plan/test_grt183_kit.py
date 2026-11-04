"""FLOW-28 GRT-0183 fresh-process re-run in the kit runners (physical/common_flow/grt183_make.sh): local, no Docker/OpenROAD."""
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "autopilot"))
import core_flow  # noqa: E402
import gen_phys  # noqa: E402
import kit_resume as KR  # noqa: E402

W = ROOT / "physical/common_flow/grt183_make.sh"
GRT = "  source_step_tcl PRE GLOBAL_ROUTE\n  set x 1\n"
SAVED = ("OT_GRT183_RESUME_SAVED helper=repair_design_helper\n[ERROR GRT-0183] Net n: maze\n")


def kit(tmp_path, cfg=""):
    k = tmp_path / "work"; r = k / "run/results/asap7/t/base"; l = k / "run/logs/asap7/t/base"; s = tmp_path / "scripts"
    for d in (r, l, s):
        d.mkdir(parents=True)
    (s / "global_route.tcl").write_text(GRT)
    (k / "config.mk").write_text(cfg)
    (k / "grt183_resume.tcl").write_text("# hook\n")
    (r / "4_cts.odb").write_text("cts")
    os.utime(r / "4_cts.odb", (1000, 1000))
    return k, r, l, s


def fake(tmp_path, body):
    """fake make: appends each call's 4_cts.odb content to calls.txt, then runs body with $N = the call number"""
    f = tmp_path / "fake_make.sh"
    f.write_text('#!/bin/bash\nK=$OT_GRT183_WORK; R=$K/run/results/asap7/t/base; L=$K/run/logs/asap7/t/base\n'
                 'echo "$(cat $R/4_cts.odb 2>/dev/null) $*" >> $K/calls.txt; N=$(wc -l < $K/calls.txt)\n' + body)
    return f


def run(k, s, f, *args, env=None):
    e = dict(os.environ, OT_GRT183_WORK=str(k), OT_GRT183_SCRIPTS=str(s), **(env or {}))
    return subprocess.run(["bash", str(W), "bash", str(f), *args], env=e, capture_output=True, text=True)


def calls(k):
    p = k / "calls.txt"
    return p.read_text().splitlines() if p.exists() else []


SAVE_THEN = ('if [ $N = 1 ]; then printf "%s" "' + SAVED.replace("\n", "\\n") + '" > $L/5_1_grt.log; echo resized > $R/5_1_grt.grt183_resume.odb; exit 2; fi\n')


def test_resume_once_then_restores_cts_and_receipt(tmp_path):
    k, r, l, s = kit(tmp_path)
    p = run(k, s, fake(tmp_path, SAVE_THEN + 'echo ok > $L/5_1_grt.log; exit 0\n'), "grt", "HOLD_SLACK_MARGIN=0")
    assert p.returncode == 0, p.stdout + p.stderr
    assert calls(k) == ["cts grt HOLD_SLACK_MARGIN=0", "resized grt HOLD_SLACK_MARGIN=0"]    # same goal + vars, fresh process, new input
    assert (r / "4_cts.odb").read_text() == "cts" and (r / "4_cts.odb").stat().st_mtime == 1000
    assert not (r / "4_cts.pre_grt183.odb").exists() and not (r / "5_1_grt.grt183_resume.odb").exists()
    rec = json.loads((r / "5_1_grt.grt183_recovered.json").read_text())
    assert rec["schema"] == "opentallas.grt183_resume.v1" and rec["rc_attempt1"] == 2
    assert rec["cts_odb_sha256"] == hashlib.sha256(b"cts").hexdigest()
    assert rec["resume_odb_sha256"] == hashlib.sha256(b"resized\n").hexdigest()
    assert "OT_GRT183_RESUME_SAVED" in (l / "5_1_grt.log.grt183_attempt1").read_text()
    assert "attempt 2 rc 0" in p.stdout


def test_second_failure_is_final(tmp_path):
    k, r, l, s = kit(tmp_path)
    p = run(k, s, fake(tmp_path, SAVE_THEN + 'echo "[ERROR GRT-0183] Net n" > $L/5_1_grt.log; exit 2\n'), "grt")
    assert p.returncode == 2 and len(calls(k)) == 2
    assert (r / "4_cts.odb").read_text() == "cts"
    # the same kit run again: marker present, no third route from the wrapper
    p = run(k, s, fake(tmp_path, 'echo "OT_GRT183_RESUME_SAVED x GRT-0183" > $L/5_1_grt.log; echo r > $R/5_1_grt.grt183_resume.odb; exit 2\n'), "grt")
    assert p.returncode == 2 and len(calls(k)) == 3


def test_first_full_route_failure_is_not_rerun(tmp_path):
    """q2n2 / hd_turn_a / bf_col3 C class: GRT-0183 in the first full route: no saved design, nothing to resume"""
    k, r, l, s = kit(tmp_path)
    p = run(k, s, fake(tmp_path, 'echo "[ERROR GRT-0183] Net n" > $L/5_1_grt.log; exit 2\n'), "grt")
    assert p.returncode == 2 and len(calls(k)) == 1 and not (r / "5_1_grt.grt183_recovered.json").exists()


def test_other_failure_and_stale_save_not_rerun(tmp_path):
    k, r, l, s = kit(tmp_path)
    (r / "5_1_grt.grt183_resume.odb").write_text("stale")
    p = run(k, s, fake(tmp_path, 'echo "[ERROR GRT-0116] congestion" > $L/5_1_grt.log; exit 2\n'), "grt")
    assert p.returncode == 2 and len(calls(k)) == 1 and (r / "4_cts.odb").read_text() == "cts"


@pytest.mark.parametrize("how", ["env", "config"])
def test_opt_out(tmp_path, how):
    k, r, l, s = kit(tmp_path, "export OT_GRT183_RESUME = 0\n" if how == "config" else "")
    p = run(k, s, fake(tmp_path, SAVE_THEN), "grt", env={"OT_GRT183_RESUME": "0"} if how == "env" else None)
    assert p.returncode == 2 and len(calls(k)) == 1
    assert (s / "global_route.tcl").read_text() == GRT


def test_hook_before_kit_hook_once(tmp_path):
    k, r, l, s = kit(tmp_path)
    f = fake(tmp_path, "exit 0\n")
    run(k, s, f, "grt"); run(k, s, f, "grt")
    assert (s / "global_route.tcl").read_text() == ("  source /work/grt183_resume.tcl\n" + GRT)


def test_print_targets_pass_through(tmp_path):
    k, r, l, s = kit(tmp_path)
    p = run(k, s, fake(tmp_path, "echo X: y\n"), "print-X")
    assert p.stdout == "X: y\n" and (s / "global_route.tcl").read_text() == GRT


def test_stage_resume_hardlink_not_written_through_and_do_grt_runs_again(tmp_path):
    k, r, l, s = kit(tmp_path)
    prev = tmp_path / "prev_4_cts.odb"
    os.link(r / "4_cts.odb", prev)
    done = k / "done.txt"; done.write_text("do-cts\ndo-grt\n")
    p = run(k, s, fake(tmp_path, SAVE_THEN + "exit 0\n"), "grt", env={"KWRS_DONE": str(done)})
    assert p.returncode == 0 and prev.read_text() == "cts"
    assert os.path.samefile(prev, r / "4_cts.odb")          # the same inode is back, never rewritten
    assert done.read_text() == "do-cts\n"


def test_killed_rerun_swap_is_undone(tmp_path):
    k, r, l, s = kit(tmp_path)
    (r / "4_cts.odb").write_text("resized"); (r / "4_cts.pre_grt183.odb").write_text("cts")
    (r / "5_1_grt.grt183_recovered.json").write_text("{}")
    run(k, s, fake(tmp_path, "exit 0\n"), "grt")
    assert calls(k) == ["cts grt"]


def test_hook_is_abi3s_unchanged():
    assert hashlib.sha256((ROOT / "physical/common_flow/grt183_resume.tcl").read_bytes()).hexdigest() == \
        "50d43e568486b97feb7896397e525bfbf1c9779e820f622fb0870c35864f853d"


def test_stage_copies_both(tmp_path):
    core_flow.stage_grt183(tmp_path)
    assert (tmp_path / "grt183_make.sh").read_bytes() == W.read_bytes()
    assert (tmp_path / "grt183_resume.tcl").is_file()
    subprocess.run(["bash", "-n", str(tmp_path / "grt183_make.sh")], check=True)


LINE = "if [ '${OT_GRT183_RESUME:-1}' != 0 ] && [ -f /work/grt183_make.sh ]; then M=\\\"bash /work/grt183_make.sh \\$M\\\"; fi;"
RUNNERS = ["physical/die_plan/hbm_arch_cores/run_kit_hbm.sh", "physical/die_plan/qwen_kvsys/cores/harden/run_kit_kv.sh",
           "physical/die_plan/qwen_compute/cores/legacy/gen_core_kit_qc.py", "physical/die_plan/s81/cores/legacy/gen_core_kit_legacy.py"]


@pytest.mark.parametrize("rel", RUNNERS)
def test_runner_wraps_make_right_after_m(rel):
    t = (ROOT / rel).read_text()
    assert t.count(LINE) == 1
    m = t.index("M='make DESIGN_CONFIG=/work/config.mk")
    assert m < t.index(LINE) < t.index("\\$M ", m)


@pytest.mark.parametrize("rel", RUNNERS[:2])
def test_shell_runner_parses(rel):
    subprocess.run(["bash", "-n", str(ROOT / rel)], check=True)


def test_gen_phys_runner_fingerprint_unchanged():
    """stage-resume compares runner_norm: the wrapper is a '# KWRS' edit, so relaunching a kit on this source reuses its stages"""
    t = gen_phys.RUN_KIT
    assert "${KWRS_F}${KWRS_M}${KWRS_G}rc=0;" in t
    n = KR.runner_norm(t)
    assert "KWRS_G" not in n and "grt183" not in n
    # exact: the host shell turns the definition into the same inner statement as the other runners
    d = re.search(r'^KWRS_G=(".*")  # KWRS$', t, re.M).group(1)
    out = subprocess.run(["bash", "-c", f'CPUS=1; KWRS_G={d}; printf %s "$KWRS_G"'], capture_output=True, text=True).stdout
    assert out == """if [ '1' != 0 ] && [ -f /work/grt183_make.sh ]; then M="bash /work/grt183_make.sh $M"; fi; """


def test_kit_resume_new_files_are_gate_class():
    assert KR.is_gate_root("grt183_make.sh") and KR.is_gate_root("grt183_resume.tcl")
    st = KR.classify({"run_kit.sh": "bash /work/grt183_make.sh\n"}, ["grt183_make.sh", "grt183_resume.tcl"], {})
    assert st == {"grt183_make.sh": KR.GATE, "grt183_resume.tcl": KR.GATE}
