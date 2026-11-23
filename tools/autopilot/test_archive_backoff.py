"""FLOW-HEALTH-1 11-15 (FABLE-FLOW-2000 d): ARCHIVE FAILED was retried every tick (243x on one job); replay of its log line"""
import autopilot as AP

LINE = ("probe rc 1: Traceback (most recent call last):\n  File \"<stdin>\", line 14, in <module>\nFileNotFoundError: [Errno 2] No such file or directory: "
        "'/srv/opentallas-scratch3/claude/kw43/x/attempt_3/gen/hd_spn_esh'")


def test_permanent_error_backs_off_from_the_third_failure_and_posts_once():
    j = {"id": "3054c87a89d6"}
    posts = [AP.archive_backoff(j, LINE, now=1000 + i) for i in range(6)]
    assert posts == [False, False, True, False, False, False]
    assert not AP.archive_due(j, now=1000 + 5)                      # backed off
    assert AP.archive_due(j, now=1000 + 7 * 3600)                   # retried again after at most 6 h
    assert j["archive_fail_n"] == 6


def test_transient_error_backs_off_but_never_posts():
    j = {"id": "x"}
    assert [AP.archive_backoff(j, "ssh transport failure", now=10) for _ in range(5)] == [False] * 5
    assert not AP.archive_due(j, now=11)


def test_first_two_failures_retry_next_tick():
    j = {}
    AP.archive_backoff(j, LINE, now=5)
    AP.archive_backoff(j, LINE, now=6)
    assert AP.archive_due(j, now=7)


def test_already_reported_permanent_archive_error_becomes_terminal(monkeypatch):
    def unexpected(*args, **kwargs):
        raise AssertionError("terminal historic archive should neither probe nor post again")

    for name in ("rpy", "coord_append", "resolve_provenance"):
        monkeypatch.setattr(AP, name, unexpected)
    j = {"id": "3054c87a89d6", "status": "SIGNED", "archive_posted": 100,
         "archive_fail_n": 39, "archive_fail_err": LINE, "archive_retry_at": 9e10,
         "history": [["2026-11-14 02:05:05 PST", "SIGNED", "original signoff"]]}
    AP.archive({"jobs": {j["id"]: j}}, j)
    assert j["status"] == "SIGNED-NOT-ARCHIVED"
    assert j["archive_posted"] == 100
    assert [entry[1] for entry in j["history"]] == ["SIGNED", "SIGNED-NOT-ARCHIVED"]

    transient = dict(j, status="SIGNED", archive_fail_err="ssh transport failure")
    AP.archive({"jobs": {transient["id"]: transient}}, transient)
    assert transient["status"] == "SIGNED"
