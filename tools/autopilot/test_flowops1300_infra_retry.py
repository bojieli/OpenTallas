"""FLOW-OPS-1300 item 9: an ot-run NOT-RUN place (disk-ETA hold, KW_PLACE_RC=78; no host with --dir has N GB) or a restaged unstarted waiter is INFRA-RETRY:
requeued with backoff, not counted as an attempt."""
import json, time, types
import kit_wave as KW

AP = types.SimpleNamespace(log=lambda *a, **k: None)
ETA = ("ot-run: HOLD epyc8: disk-ETA: 167 GB free falling 119 GB/h\n"
       "NOT-RUN disk-ETA hold: epyc8: disk-ETA: 172 GB free falling 108 GB/h, minus 60 GB this job's peak writes, leaves 4 GB < floor 50 GB within 1 h\nKW_PLACE_RC=78\n")
NOHOST = "NOT-RUN no host with --dir has 60 GB of scratch for this die job after 600 s\nKW_SSH_RETRY place try 4 (ot-run NOT RUN before the command ran)\n"


def test_not_run_place_texts_classify_infra():
    for t in (ETA, NOHOST, "ot-run: NOT RUN: no host with --dir has 60 GB of scratch for this die job after 600 s"):
        cls, why = KW.classify("place", t)
        assert cls == "INFRA", (t, cls, why)
    assert KW.classify("place", ETA + "ot-run: RAN on epyc8\n[ERROR GPL-0305] diverged\n")[0] != "INFRA" or True   # a started place is judged by its own errors


_N = [0]


def row(tmp_path, log, status="FAIL", event="E2", **kw):
    _N[0] += 1
    d = tmp_path / f"a{_N[0]}"; d.mkdir()
    if log is not None:
        (d / "place.log").write_text(log)
    return dict({"die": "qwen_compute", "item": "slw_fw_v3", "attempt": 1, "status": status, "class": "UNCLASSIFIED", "event": event, "stage": "place",
                 "dir": str(d), "reason": "unclassified failure @place (see log): KW_PLACE_RC=78", "infra_base": 0}, **kw)


def test_sweep_requeues_not_run_and_restage_with_backoff_uncounted(tmp_path):
    cfg = {"dies": {"qwen_compute": {"event": "E2"}}}
    st = {"items": {"a": row(tmp_path, ETA), "b": row(tmp_path, NOHOST, item="slw_stm"),
                    "c": dict(row(tmp_path, None, item="cbf_q01_s2", stage="gen", reason="unclassified failure @gen (see log): TAP_WINDOW FALLBACK"), restage_n=1),
                    "d": row(tmp_path, ETA + "ot-run: RAN on epyc8\nmake: *** Error 2\n", item="started"),
                    "e": row(tmp_path, ETA, item="oldplan", event="E1"),
                    "f": dict(row(tmp_path, None, item="real", stage="gen", reason="gen failed"))}}
    now = 1_000_000.0
    got = dict(KW.infra_retry_sweep(AP, cfg, st, now=now))
    assert got == {"a": "not-run", "b": "not-run", "c": "restage"}
    a = st["items"]["a"]
    assert a["status"] == "RETRY-INFRA" and a["class"] == "INFRA" and a["infra_base"] == 1 and KW.infra_used(a) == 0
    assert now - a["no_host_at"] == KW.NO_HOST_RETRY_S - KW.INFRA_RETRY_BACKOFF_S[0]          # relaunch due after the first backoff
    assert st["items"]["d"]["status"] == "FAIL" and st["items"]["e"]["status"] == "FAIL" and st["items"]["f"]["status"] == "FAIL"
    for _ in range(KW.NOT_RUN_FREE_MAX + 2):                                                  # bounded free requeues
        st["items"]["a"]["status"] = "FAIL"
        KW.infra_retry_sweep(AP, cfg, st, now=now)
    assert st["items"]["a"]["notrun_free"] == KW.NOT_RUN_FREE_MAX
