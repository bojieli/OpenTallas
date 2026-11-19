import os, sys, time
sys.path.insert(0, os.path.dirname(__file__))
import kit_wave as K


def test_slow_host_is_skipped_others_kept_and_runs_in_parallel():
    def fn(h, a):
        if h == "slow":
            time.sleep(5)
        else:
            time.sleep(0.3)
        return h.upper()
    t = time.time()
    r = K.parallel_probe({"a": 1, "b": 2, "c": 3, "slow": 4}, fn, budget=1.0)
    assert r == {"a": "A", "b": "B", "c": "C"}
    assert time.time() - t < 2.5


def test_raising_probe_is_skipped():
    def fn(h, a):
        if h == "bad":
            raise RuntimeError("x")
        return 1
    assert K.parallel_probe({"bad": 0, "ok": 0}, fn, budget=1) == {"ok": 1}
