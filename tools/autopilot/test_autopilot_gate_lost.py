"""Distinguish design stops, missing gate results and measured gate failures."""
import json
import os
import subprocess
import sys
import time

import autopilot as A


def probe(kit, since):
    a = {"kit": str(kit), "since": since, "goal": "route"}
    r = subprocess.run([sys.executable, "-I", "-c", A.PROBE_CLASSIFY, json.dumps(a)], capture_output=True, text=True, timeout=60)
    line = next((ln for ln in r.stdout.splitlines() if ln.startswith("AP_JSON ")), None)
    assert line, (r.stdout[-300:], r.stderr[-300:])
    return json.loads(line[8:])


def kit_with_marker(tmp_path, marker="legacy grt gate: [Errno 2] No such file or directory: '/work/postcts_gate_tt.json'"):
    k = tmp_path / "kit"
    (k / "run/logs/asap7/x/base").mkdir(parents=True)
    (k / "FAIL_POSTCTS").write_text(marker)
    (k / "config.mk").write_text("export X = 1\n")
    return k


def test_missing_gate_json_and_log_is_gate_lost(tmp_path):
    k = kit_with_marker(tmp_path)
    c = probe(k, time.time() - 600)
    assert "postcts_gate_tt.json missing" in c.get("gate_lost", "")
    cls, kind, why = A.classify(c, {"exit": 1})
    assert (cls, kind) == ("CRASH", "infra-gate-lost") and "gate lost" in why
    assert kind not in A.INFRA_KINDS
    assert not A.is_earlyoom_kill(why)
    assert A.classify(dict(c, oom="make Error 137"), {"exit": 2})[:2] == ("CRASH", "infra-oom")


def test_stale_gate_files_are_gate_lost(tmp_path):
    k = kit_with_marker(tmp_path)
    (k / "postcts_gate_tt.json").write_text('{"verdict": "FAIL"}')
    (k / "postcts_gate_TT.log").write_text("hold WNS -12 FAIL\n")
    old = time.time() - 7200
    for f in ("postcts_gate_tt.json", "postcts_gate_TT.log"):
        os.utime(k / f, (old, old))
    c = probe(k, time.time() - 600)
    assert "older than this run" in c.get("gate_lost", "")


def test_truncated_gate_log_is_gate_lost(tmp_path):
    k = kit_with_marker(tmp_path)
    (k / "postcts_gate_tt.json").write_text('{"verdict": "FAIL"}')
    (k / "postcts_gate_TT.log").write_text("[INFO] reading liberty\n[INFO] link design\n")
    assert "truncated" in probe(k, time.time() - 600).get("gate_lost", "")


def test_real_gate_verdict_stays_structural(tmp_path):
    k = kit_with_marker(tmp_path, marker="TT hold gate failed: hold WNS -40 ps")
    (k / "postcts_gate_tt.json").write_text('{"verdict": "FAIL"}')
    (k / "postcts_gate_TT.log").write_text("post-CTS hold WNS -40.1 FAIL\n")
    c = probe(k, time.time() - 600)
    assert not c.get("gate_lost")
    assert A.classify(c, {"exit": 1})[:2] == ("STRUCTURAL", "post-cts-hold")


def test_postplace_setup_stop_precedes_missing_cts_gate(tmp_path):
    import kit_wave as KW

    stop = "FAIL_POSTPLACE PLACE-SETUP-STOP wns -7704.00 ps < -300 ps (TT, post-place) start=u_rrl/Q end=u_ft/D"
    k = kit_with_marker(tmp_path, marker=stop + "\n" + "trailing diagnostics " * 50)
    c = probe(k, time.time() - 600)
    assert c["place_setup_stop"] == stop
    assert "gate_lost" not in c
    cls, kind, why = A.classify(c, {"exit": 6})
    assert (cls, kind, why) == ("STRUCTURAL", "place-setup-stop", stop)
    assert KW.queue_class({"status": "DONE-STRUCTURAL", "kind": kind, "reasons": why}) == ("place", "FAIL", "PLAN", stop)
