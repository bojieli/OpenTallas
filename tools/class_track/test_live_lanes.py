import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import live_lanes as ll  # noqa: E402


def test_build_and_resolve(tmp_path):
    posts = tmp_path / "posts"
    posts.mkdir()
    (posts / "QC-INT-R2.md").write_text("- 2026-11-26 09:03 PST x\n- 2026-11-26 09:10 PST y\n")
    rows = ll.build([{"lane": "QC-INT-R2", "die": "QC", "classes": "all", "agent": "a1"}],
                    [{"lane": "QC-ALLFIX", "die": "QC", "owns": "o", "claude_agent": "x"},
                     {"lane": "S81-C9-ROWS", "die": "", "owns": "", "claude_agent": ""},
                     {"lane": "QC-INT-R2", "die": "QC"}], str(posts))
    assert [r["status"] for r in rows] == ["live", "dead", "dead"]
    assert rows[0]["last_post"] == "2026-11-26 09:10"
    assert ll.resolve("QC-ALLFIX", rows) == "QC-INT-R2"
    assert ll.resolve("S81-C9-ROWS", rows) == "S81-INT-R2"      # die inferred from the lane name
    assert ll.resolve("qc-int-r2", rows) == "QC-INT-R2" and ll.resolve("COORD", rows) == "COORD"


def test_active_lanes_added_case_insensitive(tmp_path):
    posts = tmp_path / "posts"
    posts.mkdir()
    (posts / "head-int-r2.md").write_text("- 2026-11-26 10:23 PST DONE x\n")
    (posts / "S81-OLD.md").write_text("- 2026-11-25 10:23 PST DONE x\n")
    (posts / "QC-NEW.md").write_text("- 2026-11-26 10:00 PST DONE x\n")
    rows = ll.build([{"lane": "HEAD-INT-R2", "die": "HEAD", "classes": "", "agent": ""}], [], str(posts), "2026-11-26 06:00")
    by = {r["lane"]: r for r in rows}
    assert by["HEAD-INT-R2"]["last_post"] == "2026-11-26 10:23" and len(rows) == 3
    assert by["QC-NEW"]["status"] == "live" and by["S81-OLD"]["status"] == "dead" and by["S81-OLD"]["integrator"] == "S81-INT-R2"
