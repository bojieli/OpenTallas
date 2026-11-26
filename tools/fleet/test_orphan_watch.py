"""P-ORPHAN-PROCESS: report-only orphan list: ppid-1 processes in silent lanes' dirs; active lanes and non-lane processes are not listed."""
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import orphan_watch as W

CMD_A = "/srv/opentallas-scratch2/claude/LANE-A/run.sh"


def probe_text(*rows):
    return "\n".join("\t".join(map(str, r)) for r in rows)


def test_lane_of_skips_infra_and_non_lane_paths():
    assert W.lane_of("/srv/opentallas-scratch2/claude/LANE-A/x", "") == "LANE-A"
    assert W.lane_of("/", "bash /srv/opentallas-scratch2/claude/rt/abc/tools/x.sh /srv/opentallas-scratch3/claude/LANE-B/y") == "LANE-B"
    assert W.lane_of("/srv/opentallas-scratch2/claude/rt/abc/x", "python3 /usr/bin/x") is None
    assert W.lane_of("/home/ubuntu", "sshd") is None


def test_only_silent_lanes_are_listed(tmp_path, monkeypatch):
    posts = tmp_path / "posts"
    posts.mkdir()
    (posts / "LANE-A.md").write_text("x")
    old = time.time() - 20 * 3600
    os.utime(posts / "LANE-A.md", (old, old))                     # silent 20 h
    (posts / "LANE-B.md").write_text("x")                         # fresh
    monkeypatch.setattr(W, "POSTS", str(posts))
    text = probe_text((11, 9.0, "/srv/opentallas-scratch2/claude/LANE-A/w", CMD_A),
                      (12, 9.0, "/srv/opentallas-scratch2/claude/LANE-B/w", "bash x"),
                      (13, 9.0, "/srv/opentallas-scratch2/claude/LANE-C/w", "bash y"),      # no post file at all = silent
                      (14, 9.0, "/home/ubuntu", "sleep 1"))
    rows = W.parse("h1", text, 12)
    assert sorted(r[1] for r in rows) == [11, 13]
    assert "REPORT ONLY" in W.render(rows, 12) and "never" in W.render(rows, 12)


def test_post_once_per_changed_set_and_nothing_is_killed(tmp_path, monkeypatch):
    monkeypatch.setattr(W, "POSTS", str(tmp_path))
    monkeypatch.setattr(W, "STATE", str(tmp_path / "state.json"))
    sent = []
    killed = []
    monkeypatch.setattr(os, "kill", lambda *a: killed.append(a))
    fake = lambda h, age: probe_text((21, 7.0, "/srv/opentallas-scratch2/claude/LANE-Z/", "bash z"))
    assert W.main(["--hosts", "h1", "--post"], probe_fn=fake, post_fn=sent.append) == 0
    assert W.main(["--hosts", "h1", "--post"], probe_fn=fake, post_fn=sent.append) == 0
    assert len(sent) == 1 and "h1 pid 21" in sent[0] and killed == []
    assert json.load(open(tmp_path / "state.json")) == ["h1:21"]


def test_probe_runs_on_a_real_host_shape():
    """the probe snippet itself must be valid python and print nothing for an unreachable host"""
    compile(W.PROBE, "probe", "exec")
    assert W.probe("h", 6, run=lambda *a, **k: (_ for _ in ()).throw(OSError("x"))) == ""
