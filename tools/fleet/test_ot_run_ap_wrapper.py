"""KW-FIX-44 11-10 (COORD 09:4x, OWNER 11-09 "remove the second disk check of the jobs"): the autopilot ot-run backend
wrapper (deployed as ~/.local/lib/kw10/ot-run on the hub) has no client-side disk-wait loop.  ot-run's own per-disk
admission floor is the only disk check."""
import os
import stat
import subprocess
from pathlib import Path

W = Path(__file__).resolve().parent / "ot-run-ap"


def code_lines():
    return [l for l in W.read_text().splitlines() if l.strip() and not l.lstrip().startswith("#")]


def test_wrapper_parses_and_is_executable():
    subprocess.run(["bash", "-n", str(W)], check=True)
    assert W.stat().st_mode & stat.S_IXUSR


def test_no_second_disk_check():
    code = "\n".join(code_lines())
    assert "--pick" not in code                      # no re-asking admission from the client
    assert "KW12_DISK_WAIT" not in code
    assert "OT_RUN_SCRATCH_DISK_FLOOR_GB=" not in code  # no stricter global floor than the admission's own
    assert "21600" not in code and "sleep $((" not in code


def test_admission_keeps_per_host_floors_and_execs_base():
    code = code_lines()
    assert any("OT_RUN_SCRATCH_DISK_FLOOR_GB_HOSTS=epyc4=50,intel1=50,epyc2=50" in l for l in code)
    assert code[-1] == 'exec /home/ubuntu/.local/lib/kw42/ot-run-base "$@"'


def test_runs_through_to_base_without_waiting(tmp_path):
    """the wrapper with a fake base: scratch --dir + --mem goes straight to exec, env carries only the per-host floors"""
    fake = tmp_path / "base"
    fake.write_text('#!/bin/bash\necho "FLOOR=${OT_RUN_SCRATCH_DISK_FLOOR_GB-unset} HOSTS=$OT_RUN_SCRATCH_DISK_FLOOR_GB_HOSTS ARGS=$*"\n')
    fake.chmod(0o755)
    src = W.read_text().replace("/home/ubuntu/.local/lib/kw42/ot-run-base", str(fake))
    w = tmp_path / "ot-run"
    w.write_text(src)
    w.chmod(0o755)
    env = {k: v for k, v in os.environ.items() if not k.startswith("OT_RUN_")}
    r = subprocess.run([str(w), "--mem", "19", "--threads", "2", "--dir", "/srv/opentallas-scratch2/claude/autopilot/review/x",
                        "--no-spill", "--direct", "--", "true"], capture_output=True, text=True, env=env, timeout=30)
    assert r.returncode == 0, r.stderr
    assert "FLOOR=unset" in r.stdout and "HOSTS=epyc4=50,intel1=50,epyc2=50" in r.stdout
    assert "ARGS=--mem 19 --threads 2 --dir /srv/opentallas-scratch2/claude/autopilot/review/x" in r.stdout
    assert "KW12_DISK_WAIT" not in r.stderr
