"""tests for waiter_fail_relay.py (PLAN-GATE-PRE-1115): fake queue, fake poster, no hub access."""
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import waiter_fail_relay as R  # noqa: E402


def stamp(age_min):
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo
    t = datetime.now(ZoneInfo("America/Los_Angeles")) - timedelta(minutes=age_min)
    return t.strftime("%Y-%m-%d %H:%M %Z")


def q(age, lane, text, to="COORD", tag="RESULT", cc=""):
    return f"- {stamp(age)} {tag} [{lane} -> {to}{'; cc ' + cc if cc else ''}] {text}"


class Poster:
    def __init__(self, ok=True, queue=None):
        self.posts, self.ok, self.queue = [], ok, queue

    def __call__(self, post_sh, text):
        if self.ok:
            self.posts.append(text)
            if self.queue:   # the post lands in the queue view like post.sh does
                with open(self.queue, "a") as f:
                    f.write(f"- {stamp(0)} {text}\n")
        return self.ok


def setup(tmp_path, lines):
    qf = tmp_path / "queue.md"
    qf.write_text("\n".join(lines) + "\n")
    return qf, tmp_path / "state.json"


def test_matches_and_skips():
    assert R.parse(q(1, "DIE-S81-92", "G1d bind did NOT pass: G0 17 errors"))
    assert R.parse(q(1, "DIE-S81-92", "Traceback (most recent call last) in elab"))
    assert R.parse(q(1, "DIE-S81-92", "REFUSE: input missing"))
    assert R.parse(q(1, "DIE-S81-92", "G1d passed, adopted")) is None
    assert R.parse(q(1, "DIE-S81-92", "ok " + "x" * 400 + " did NOT pass late")) is None          # verdict window is the head
    assert R.parse(q(1, "FABLE-FLOW-1800", "FAIL: 86 before P&R")) is None                  # reviews are not waiter results
    assert R.parse(q(1, "DIE-S81-92", "FAIL", tag="LAUNCH")) is None                        # only RESULT lines
    assert R.parse(q(1, "PLAN-GATE-PRE-1115", "FAIL")) is None
    assert R.parse("- 2026 NEEDS-ACTION [X -> Y] RESULT [DIE-A -> COORD] FAIL") is None


def test_post_addresses_owner_and_coord(tmp_path):
    qf, st = setup(tmp_path, [q(5, "DIE-QC-103", "REBINDS FAILED: S4q6b do NOT pass", to="QC-SC-ROWS-1115, COORD",
                                cc="KIT-OPS-5")])
    p = Poster()
    posted, _, failed = R.run(qf, st, "post.sh", poster=p)
    assert len(posted) == 1 and not failed
    t = p.posts[0]
    assert t.startswith("NEEDS-ACTION [PLAN-GATE-PRE-1115 -> DIE-QC-103, QC-SC-ROWS-1115, COORD; cc KIT-OPS-5]")
    assert f"WAITER-FAIL {posted[0]}" in t


def test_idempotent_by_state_and_by_queue(tmp_path):
    qf, st = setup(tmp_path, [q(5, "DIE-S81-92", "G1d did NOT pass")])
    p = Poster(queue=qf)
    assert len(R.run(qf, st, "x", poster=p)[0]) == 1
    assert R.run(qf, st, "x", poster=p)[0] == []                  # state
    st.unlink()
    p2 = Poster(queue=qf)
    assert R.run(qf, st, "x", poster=p2)[0] == [] and p2.posts == []   # state lost: the queue still holds the key
    assert len(p.posts) == 1


def test_new_line_new_key_and_same_text_other_time(tmp_path):
    qf, st = setup(tmp_path, [q(30, "DIE-S81-92", "G1d did NOT pass")])
    p = Poster()
    R.run(qf, st, "x", poster=p)
    with open(qf, "a") as f:
        f.write(q(0, "DIE-S81-92", "G1d did NOT pass") + "\n")                     # same text, new stamp: new event
        f.write(q(0, "KV-102", "FAIL: kit_rtl again") + "\n")
    posted, _, _ = R.run(qf, st, "x", poster=p)
    assert len(posted) in (1, 2)
    assert len(p.posts) == 3 or len(p.posts) == 2     # stamp has minute resolution: identical minute = same key
    assert len({x.split("WAITER-FAIL ")[1][:12] for x in p.posts}) == len(p.posts)


def test_first_run_relays_only_recent(tmp_path):
    qf, st = setup(tmp_path, [q(600, "DIE-S81-92", "old did NOT pass"), q(10, "DIE-QC-103", "new did NOT pass")])
    p = Poster()
    posted, noted, _ = R.run(qf, st, "x", max_age_min=120, poster=p)
    assert len(posted) == 1 and len(noted) == 1 and "DIE-QC-103" in p.posts[0]
    # later runs relay any new line however old its stamp says
    with open(qf, "a") as f:
        f.write(q(600, "KV-102", "FAIL: late") + "\n")
    assert len(R.run(qf, st, "x", max_age_min=120, poster=p)[0]) == 1


def test_failed_post_is_retried(tmp_path):
    qf, st = setup(tmp_path, [q(5, "DIE-S81-92", "did NOT pass")])
    posted, _, failed = R.run(qf, st, "x", poster=Poster(ok=False))
    assert posted == [] and len(failed) == 1
    assert json.loads(st.read_text())["seen"] == {}
    p = Poster()
    assert len(R.run(qf, st, "x", poster=p)[0]) == 1


def test_max_posts_defers_rest(tmp_path):
    qf, st = setup(tmp_path, [q(5, f"DIE-{i}", f"did NOT pass {i}") for i in range(5)])
    p = Poster()
    assert len(R.run(qf, st, "x", max_posts=2, poster=p)[0]) == 2
    assert len(R.run(qf, st, "x", max_posts=10, poster=p)[0]) == 3


def test_dry_does_not_write_state(tmp_path, capsys):
    qf, st = setup(tmp_path, [q(5, "DIE-S81-92", "did NOT pass")])
    R.run(qf, st, "x", dry=True)
    assert not st.exists() and "NEEDS-ACTION" in capsys.readouterr().out


def test_real_post_sh_contract(tmp_path):
    fake = tmp_path / "post.sh"
    fake.write_text('#!/bin/bash\necho "$1|$2" >> "$(dirname "$0")/got.txt"\n')
    qf, st = setup(tmp_path, [q(5, "DIE-S81-92", "did NOT pass")])
    assert len(R.run(qf, st, str(fake))[0]) == 1
    lane, text = (tmp_path / "got.txt").read_text().split("|", 1)
    assert lane == "PLAN-GATE-PRE-1115" and text.startswith("NEEDS-ACTION")


XTAP_TEXT = 'class_id=C-XTAP-HOLD A arm DONE: base c085ccb76d2e (lag row in base), col_h9_r2__t1__clce45cab5__pv9e92407b, place->CTS (goal cts, no route), epyc8, rt b521092f9e17, place svc kwp-678f021e2d50774e99dc, 3_place sha 47354d1381b4 (Fable GOOD, plan-visual GOOD, AUTO-GEOM FAIL on fill/empty/r2r/channels/clock_tap_sinks 1936 = C-TAP-LOAD, expected for macro type). CTS: 6 core taps clk_c0..c5 landed on u_c/u_ha/u_hb clk, FF read on 4_cts.odb (read-only STA, E8 unit oth-ubuntu-1170350-1795807732, evidence epyc8:/srv/opentallas-scratch2/claude/s81-int-r3-xtap/read_A/read.{ff,tt}.log): half->c hold FF 0 negative on all 77 endpoints per view, worst +42.87 (e13e, otag[2]->r_t_a[2]) and +32.94 (e13w), vs'


def test_pass_result_mentioning_fail_is_not_a_failure():
    """regression d60241b01e6d: S81-INT-R3-XTAP PASS result quoting 'AUTO-GEOM FAIL' (expected) was relayed as WAITER-FAIL."""
    ln = q(1, "S81-INT-R3-XTAP", XTAP_TEXT, to="S81-INT-R3", cc="COORD")
    assert "FAIL" in XTAP_TEXT[:R.WINDOW]
    assert R.classify(XTAP_TEXT) == "UNKNOWN"
    assert R.parse(ln) is None


def test_explicit_verdict_decides():
    assert R.parse(q(1, "L", "verdict=FAIL: G0 17")) and R.parse(q(1, "L", "status: failed, see log"))
    assert R.parse(q(1, "L", "all good verdict=PASS but AUTO-GEOM FAIL expected")) is None
    assert R.parse(q(1, "L", "x", tag="RESULT-FAIL")) and R.parse(q(1, "L", "FAIL everywhere", tag="RESULT-PASS")) is None
    assert R.classify("class_id=C-X FAIL: bind") == "FAIL" and R.classify("clean run") == "PASS"


def test_whole_token_verdict_not_substring():
    """regression 5da0b183b934: 'FAIL-CLASS 8070467972 verdict CLOSED-SUPERSEDED' was relayed as WAITER-FAIL."""
    closed = "FAIL-CLASS 8070467972 verdict CLOSED-SUPERSEDED. Cause: old run; no further action applies."
    assert R.classify(closed) != "FAIL" and R.parse(q(1, "HEAD-INT-R3", closed)) is None
    for neg in ("CLOSED-SUPERSEDED the old run", "NOT-FAILED-X on this row", "SUPERSEDED-FAIL-OVER done", "FAILURE-CLASS closed", "REFUSAL-LOG ok"):
        assert R.classify(neg) != "FAIL", neg
        assert R.parse(q(1, "L", neg)) is None, neg
    for pos in ("FAIL: bind", "FAILED bind", "REFUSE: x", "REFUSED x", "Traceback (most recent call last)", "class_id=C-X FAIL: bind",
                "FAIL", "did NOT pass", "verdict=FAIL: G0"):
        assert R.classify(pos) == "FAIL", pos
        assert R.parse(q(1, "L", pos)), pos
    assert R.parse(q(1, "L", "anything", tag="RESULT-FAIL"))
