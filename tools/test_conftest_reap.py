"""FLOW-HEALTH-1 11-15 (FABLE-FLOW-1600): the conftest fixture reaps the detached lec_async watchers a test starts"""
import os
import subprocess
import sys

import conftest as C


def test_detached_watcher_is_found_and_reaped(tmp_path):
    k = tmp_path / "lec_async.sh"
    k.write_text("#!/bin/bash\nsleep 300\n")
    # the same shape lec_async.sh start leaves: setsid nohup bash <script> watch <kit>, parent gone
    subprocess.Popen(["setsid", "nohup", "bash", str(k), "watch", str(tmp_path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     stdin=subprocess.DEVNULL, start_new_session=True)
    for _ in range(50):
        if C.session_lec_watchers():
            break
        import time; time.sleep(0.1)
    assert C.session_lec_watchers(), "marker not inherited by the detached watcher"
    assert C.reap_lec_watchers() == []
    assert C.session_lec_watchers() == []


def test_other_sessions_are_untouched(tmp_path):
    k = tmp_path / "lec_async.sh"
    k.write_text("#!/bin/bash\nsleep 5\n")
    p = subprocess.Popen(["bash", str(k), "watch", str(tmp_path)], env=dict(os.environ, OT_TEST_WATCH_SESSION="pytest-other"),
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        assert C.session_lec_watchers() == []
        assert C.reap_lec_watchers() == []
        assert p.poll() is None
    finally:
        p.kill()
        p.wait()
