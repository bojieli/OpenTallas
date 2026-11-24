"""UNIT-HYGIENE-1124: ot-unit-hygiene resets only FAILED user units whose failure is older than --min-age-s; active / young failed units stay."""
import os
import subprocess
from pathlib import Path

TOOL = Path(__file__).resolve().with_name("ot-unit-hygiene")

FAKE = r"""#!/bin/bash
# fake systemctl: units old.service (failed long ago), young.service (failed now), live.service (active)
up=$(cut -d' ' -f1 /proc/uptime | cut -d. -f1)
case "$*" in
  *"list-units --state=failed"*) printf 'old.service loaded failed failed x\nyoung.service loaded failed failed y\nlive.service loaded active running z\n';;
  *"list-units --all"*) printf 'a\nb\nc\n';;
  *"show"*old.service*) printf 'ActiveState=failed\nInactiveEnterTimestampMonotonic=1000000\n';;
  *"show"*young.service*) printf 'InactiveEnterTimestampMonotonic=%s000000\nActiveState=failed\n' "$up";;
  *"show"*live.service*) printf 'ActiveState=active\nInactiveEnterTimestampMonotonic=0\n';;
  *"reset-failed"*) echo "$*" >> "$LOG";;
esac
"""


def test_resets_only_old_failed_units(tmp_path):
    b = tmp_path / "bin"
    b.mkdir()
    (b / "systemctl").write_text(FAKE)
    (b / "systemctl").chmod(0o755)
    log = tmp_path / "reset.log"
    env = dict(os.environ, PATH=f"{b}:{os.environ['PATH']}", LOG=str(log))
    r = subprocess.run(["bash", str(TOOL), "--min-age-s", "3600"], capture_output=True, text=True, env=env, timeout=60)
    assert r.returncode == 0, r.stderr
    assert "reset=1 kept_young=1" in r.stdout
    assert log.read_text().split() == ["--user", "reset-failed", "old.service"]
    log.unlink()
    r = subprocess.run(["bash", str(TOOL), "--dry-run"], capture_output=True, text=True, env=env, timeout=60)
    assert "dry_run=1" in r.stdout and not log.exists()
