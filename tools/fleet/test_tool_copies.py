"""FLOW-FLEET-R1 11-22 (FABLE-FLOW-0000 F3): cron / timer entries running copied tools are listed; rt/current is fine."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tool_copies as TC  # noqa: E402

DUMP = """### CRON
7 * * * * cd / && /usr/bin/flock -n /tmp/f.lock /usr/bin/python3 -I /home/ubuntu/.local/lib/fleet/flowhealth1-20b88ef3834/flow_health.py >> x.log
*/15 * * * * /usr/bin/python3 -I /srv/opentallas-scratch2/claude/rt/d0ee4a2afb10/tools/autopilot/limit_outage.py --coord /home/ubuntu/coord
*/10 * * * * /usr/bin/python3 -I /srv/opentallas-scratch2/claude/rt/current/tools/fleet/disk_rate.py
5 * * * * /usr/bin/timeout 600 /srv/opentallas-scratch2/claude/fleet-ops-r/host_report.sh
### UNIT --user codex-grt.service ExecStart="/usr/bin/python3" "-I" "/srv/opentallas-scratch2/claude/wt/codex-x/shadow_collect.py" "--watch"
### UNIT --user fail_route.service ExecStart=/bin/sh -c "exec /usr/bin/timeout 300 /usr/bin/python3 -I %h/coord/tools/fail_route.py"
### UNIT --system ot-reaper.service ExecStart=/home/ubuntu/.local/lib/kw44/ot-run --mem 1
"""


def test_entries_classify():
    got = {(w, k, p.rsplit("/", 1)[-1]) for w, p, k in TC.entries(DUMP)}
    assert ("cron", "COPY", "flow_health.py") in got
    assert ("cron", "PINNED-RT", "limit_outage.py") in got
    assert ("user:codex-grt.service", "WORKTREE", "shadow_collect.py") in got
    assert ("system:ot-reaper.service", "COPY", "ot-run") in got
    assert not any(p.endswith("disk_rate.py") or p.endswith("host_report.sh") or p.endswith("fail_route.py") for _, p, _ in TC.entries(DUMP))


def test_report_alerts_after_24h():
    e = [("cron", "/home/u/.local/lib/fleet/x/a.py", "COPY"), ("cron", "/home/u/.local/lib/fleet/y/b.py", "COPY")]
    lines, fl, al = TC.report("intel2", e, {e[0][1]: 1000.0 - 25 * 3600, e[1][1]: 1000.0 - 3600}, 1000.0)
    assert al == 1 and lines[0].startswith("TOOL-COPY ALERT intel2 cron COPY") and lines[1].startswith("TOOL-COPY copy")


def test_main_last_line(tmp_path, capsys):
    f = tmp_path / "d"
    f.write_text(DUMP)
    TC.main(["--file", str(f), "--host", "intel2"])
    last = capsys.readouterr().out.splitlines()[-1]
    assert last.startswith("TOOL-COPY 4 copies") and "intel2:flow_health.py[COPY" in last
