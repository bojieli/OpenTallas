"""HOLD-FLOW-R 11-16 (lever 4): the post-CTS probe warns, never fails, when the CTS hold-buffer count jumps 2x or more."""
import json
import os
import subprocess
import sys
import time

import autopilot as A


def probe(kit):
    a = {"kit": str(kit), "since": time.time() - 3600, "goal": "route"}
    r = subprocess.run([sys.executable, "-I", "-c", A.PROBE_CLASSIFY, json.dumps(a)], capture_output=True, text=True, timeout=60)
    line = next((ln for ln in r.stdout.splitlines() if ln.startswith("AP_JSON ")), None)
    assert line, (r.stdout[-300:], r.stderr[-300:])
    return json.loads(line[8:]), r.stderr


def kit(tmp_path, counts, age=0):
    k = tmp_path / "kit"
    d = k / "run/logs/asap7/x/base"
    d.mkdir(parents=True, exist_ok=True)
    (k / "config.mk").write_text("export X = 1\n")
    f = d / "4_1_cts.log"
    f.write_text("".join(f"[INFO RSZ-0032] Inserted {n} hold buffers.\n" for n in counts))
    t = time.time() - age
    os.utime(f, (t, t))
    return k


def test_first_run_has_no_baseline_and_no_warning(tmp_path):
    c, err = probe(kit(tmp_path, [2001, 2001, 483]))
    assert c["cts_hold"] == {"current": 4485, "previous": None} and "cts_hold_jump" not in c and "WARN" not in err


def test_next_form_with_2x_is_flagged_but_not_a_failure(tmp_path):
    k = kit(tmp_path, [3000], age=100)
    probe(k)
    kit(tmp_path, [2001, 2001, 2001, 483, 2001, 2001, 2001, 2001], age=0)      # 16,494-style jump
    c, err = probe(k)
    assert c["cts_hold"]["previous"] == 3000 and "OT_CTS_HOLD_JUMP FLAG" in c["cts_hold_jump"] and "WARN" in err
    assert "cts_hold_error" not in c
    cls, kind, why = A.classify(c, {"exit": 0})
    assert "cts_hold" not in why                      # a warning line, never a classification input


def test_reprobing_the_same_run_does_not_compare_it_with_itself(tmp_path):
    k = kit(tmp_path, [3000], age=100)
    probe(k)
    kit(tmp_path, [9000], age=0)
    probe(k)
    c, _ = probe(k)
    assert c["cts_hold"]["previous"] == 3000 and "cts_hold_jump" in c


def test_small_kit_below_the_floor_is_quiet(tmp_path):
    k = kit(tmp_path, [30], age=100)
    probe(k)
    kit(tmp_path, [150], age=0)
    c, _ = probe(k)
    assert "cts_hold_jump" not in c
