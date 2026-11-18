"""FACE-GUARD-ADVISORY 11-17 (S81-FIX-OPUS, COORD): R-MINIMAL lists only DRC 0 / TT >= -42 / internal FF hold >= 0 /
bind + LATCHECK as blocking, so the kit face_guard (pin registration) and face_guard_odb results are a WARN line by
default; `export OT_FACE_GUARD_GATE = 1` in config.mk restores the FAIL_PREFLOOR stop.  The test runs the generated
RUN_KIT face_guard lines in bash with stub tools (python3 -> exit FG_RC, openroad -> exit 0)."""
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_phys  # noqa: E402


def _block():
    lines = gen_phys.RUN_KIT.splitlines()
    i = next(k for k, x in enumerate(lines) if "OT_FACE_GUARD_GATE = 1' /work/config.mk" in x)
    j = next(k for k, x in enumerate(lines) if k > i and "face_guard_odb ADVISORY" in x)
    keep = [lines[i], lines[i + 1]]
    d0 = next(k for k in range(i, j) if "1_synth.odb" in lines[k])
    keep += lines[d0:j + 1]
    # drop the reg_fanout / merge_census lines between the two face_guard steps; un-escape the docker string
    body = "\n".join(x.rstrip().removesuffix("\\").rstrip() for x in keep)
    return body.replace("\\$", "$").replace("\\\\n", "\\n")


def _run(tmp, gate, fg_rc):
    w = tmp / "work"
    (w / "run/results/asap7/x/base").mkdir(parents=True, exist_ok=True)
    (w / "run/results/asap7/x/base/1_synth.odb").write_text("")
    (w / "config.mk").write_text("export OT_FACE_GUARD_GATE = 1\n" if gate else "export X = 1\n")
    bin_ = tmp / "bin"
    bin_.mkdir(exist_ok=True)
    (bin_ / "python3").write_text(f"#!/bin/sh\nexit {fg_rc}\n")
    (bin_ / "openroad").write_text("#!/bin/sh\nexit 0\n")
    for f in bin_.iterdir():
        f.chmod(0o755)
    script = "rc=0; N=n.v\n" + _block().replace("/work", str(w)) + "\necho RC=$rc\n"
    env = dict(os.environ, PATH=f"{bin_}:/usr/bin:/bin")
    r = subprocess.run(["bash", "-c", script], capture_output=True, text=True, env=env)
    assert r.returncode == 0, r.stderr
    return r.stdout, (w / "FAIL_PREFLOOR").exists()


def test_face_guard_fail_is_advisory_by_default(tmp_path):
    out, failed = _run(tmp_path, gate=False, fg_rc=1)
    assert "WARN face_guard ADVISORY" in out and "WARN face_guard_odb ADVISORY" in out
    assert "RC=0" in out and not failed


def test_gate_restores_stop(tmp_path):
    out, failed = _run(tmp_path, gate=True, fg_rc=1)
    assert "FAIL_PREFLOOR face_guard" in out and failed
    assert "RC=1" in out


def test_pass_is_silent(tmp_path):
    for gate in (False, True):
        out, failed = _run(tmp_path / str(gate), gate=gate, fg_rc=0)
        assert "ADVISORY" not in out and "FAIL_PREFLOOR" not in out and "RC=0" in out and not failed


def test_run_kit_bash_syntax():
    r = subprocess.run(["bash", "-n"], input=gen_phys.RUN_KIT, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
