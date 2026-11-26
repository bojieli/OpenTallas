import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import evidence_check as ev  # noqa: E402


def test_classify_and_scan(tmp_path):
    assert ev.classify("/tmp/x/west.json") == "VOLATILE"
    assert ev.classify("/srv/opentallas-scratch2/claude/a/b.md") == "OK"
    assert ev.classify("/home/ubuntu/coord/lanes/x.md") == "OK"
    p = tmp_path / "posts"
    p.mkdir()
    (p / "L.md").write_text("- 2026-11-26 08:30 PST REVIEW [L -> X] see /tmp/west-request.json and /srv/opentallas-scratch2/claude/n.md 0123456789ab\n"
                            "- 2026-11-26 08:31 PST DONE [L] /tmp/ignored\n"
                            "- 2026-11-26 08:32 PST GOOD [L] /srv/opentallas-scratch2/claude/m.md\n")
    rows = ev.scan_posts(str(p), "2026-11-26 00:00", {"REVIEW", "GOOD"})
    assert [(r[3], r[4]) for r in rows] == [("VOLATILE", "/tmp/west-request.json"), ("NO-SHA", "/srv/opentallas-scratch2/claude/m.md")]
