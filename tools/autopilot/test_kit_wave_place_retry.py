"""KW-FIX-17 11-05: async PLACE service retries an ot-run NOT RUN (sshd drop on the gen-host probe)."""
import subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as KW  # noqa: E402


def _run(tmp_path, script):
    log = tmp_path / "place.live.log"
    fake = tmp_path / "fake.sh"
    fake.write_text(script)
    inner = f"bash {fake} {tmp_path}"
    body = f"exec >> {log} 2>&1; " + KW.place_retry_sh(inner, str(log)).replace("sleep $((20*(i+1)+RANDOM%20))", "true") + "; echo KW_PLACE_RC=$rc"
    subprocess.run(["bash", "-c", body], check=True)
    return log.read_text()


def test_not_run_is_retried_then_runs(tmp_path):
    # first call: NOT RUN (probe drop); second: RAN on, rc 0
    txt = _run(tmp_path, 'n=$(cat $1/n 2>/dev/null || echo 0); echo $((n+1)) > $1/n\n'
                         'if [ $n -eq 0 ]; then echo "ot-run: NOT RUN: no host qualifies (epyc4: SSH probe exit 255)"; exit 3; fi\n'
                         'echo "ot-run: RAN on epyc4 (unit u): exit 0"; exit 0\n')
    assert txt.count("KW_PLACE_TRY") == 2 and "KW_SSH_RETRY place try 2" in txt and txt.strip().endswith("KW_PLACE_RC=0")


def test_design_failure_not_retried(tmp_path):
    txt = _run(tmp_path, 'echo "ot-run: RAN on epyc4 (unit u): exit 1"; exit 1\n')
    assert txt.count("KW_PLACE_TRY") == 1 and txt.strip().endswith("KW_PLACE_RC=1")


def test_not_run_gives_up_after_retries(tmp_path):
    txt = _run(tmp_path, 'echo "ot-run: NOT RUN: no host qualifies"; exit 3\n')
    assert txt.count("KW_PLACE_TRY") == KW.SSH_RETRIES + 1 and txt.strip().endswith("KW_PLACE_RC=3")


def test_place_rc_regex_reads_last_line(tmp_path):
    txt = _run(tmp_path, 'echo "ot-run: NOT RUN: x"; exit 3\n')
    import re
    assert re.findall(r"(?m)^KW_PLACE_RC=(-?\d+)\s*$", txt) == ["3"]
