"""FAILFAST-1 orphan census (tools/autopilot/orphan_scan.py): row mapping, dead-row leak, lane ownership.  Local, no ssh.
    python3 -m pytest -q tools/autopilot/test_orphan_scan.py"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import orphan_scan as O  # noqa: E402

NOW = time.time()
KIT = "/srv/opentallas-scratch2/claude/kw43-wave-1109/runs/hbm/kit-wave/hbm/d44v/items/q_su31/attempt_11/gen/q_su31"


def cont(origin=KIT, work=None):
    return {"name": "dpkit-q_su31-1", "origin": origin, "work": work or origin, "age_h": 5, "threads": 8, "rss_gb": 10}


def wave(att, status, q=None):
    return ["hbm", "d44v", "q_su31", att, status, q, "", 0]


def test_live_row_is_not_a_candidate():
    assert O.classify(cont(), {}, [], NOW, wave=[wave(11, "ENQUEUED", "RUNNING")])[0] == "LIVE"
    assert O.classify(cont(), {}, [], NOW, wave=[wave(11, "RUNNING")])[0] == "LIVE"


def test_cancelled_row_with_running_queue_job_is_a_leak_even_if_a_lane_posted():
    q = [(NOW - 600, "- [HBM-COMPOSE-2 -> COORD] q_su31 looked at")]
    v, status, owner = O.classify(cont(), {}, q, NOW, wave=[wave(11, "CANCELLED", "RUNNING")])
    assert v == "ORPHAN" and "CANCELLED/RUNNING" in status and "HBM-COMPOSE-2" in owner


def test_older_attempt_whose_row_moved_on_is_a_leak():
    v, status, _ = O.classify(cont(), {}, [], NOW, wave=[wave(12, "ENQUEUED", "RUNNING")])
    assert v == "ORPHAN" and "no a11 row" in status and "now a12" in status


def test_no_row_is_lane_owned_only_with_a_recent_post():
    lane = "/srv/opentallas-scratch2/claude/hbm-cores-b/kits/opsa0_B"
    q = [(NOW - 600, "[HBM-CORES-B -> COORD] opsa0_B running")]
    assert O.classify(cont(lane), {}, q, NOW)[0] == "LANE"
    assert O.classify(cont(lane), {}, [(NOW - 5 * 3600, q[0][1])], NOW)[0] == "ORPHAN"
    assert O.classify(cont(lane), {}, [], NOW)[1] == "no row"


def test_census_posts_are_not_ownership_claims():
    cs = [cont("/srv/opentallas-scratch2/claude/x/kit_item%d" % i) for i in range(8)]
    text = " ".join("kit_item%d" % i for i in range(8))
    assert O.census_lines(cs, [(NOW, "[LAND-RING-2 -> COORD] " + text), (NOW, "[A-LANE -> COORD] kit_item1")]) == {0}


def test_scratch_aliases_and_job_rows():
    assert O.norm("/srv/opentallas-scratch3/claude/kw/x") == O.norm("/srv/opentallas-scratch2/claude/kw/x") == "kw/x"
    rows = {O.norm(KIT): [["job", KIT, "WAIT-GEOM", "", "id1", 1, ""]]}
    assert O.classify(cont(), rows, [], NOW)[0] == "LIVE"
    rows = {O.norm(KIT): [["job", KIT, "CANCELLED", "cancelled", "id1", 1, ""]]}
    assert O.classify(cont(), rows, [], NOW)[0:2] == ("ORPHAN", "job CANCELLED cancelled")
