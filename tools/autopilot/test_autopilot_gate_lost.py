"""Distinguish design stops, missing gate results and measured gate failures."""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

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



def test_postplace_setup_stop_in_fresh_route_log(tmp_path):
    stop = "FAIL_POSTPLACE PLACE-SETUP-STOP wns -48290.74 ps < -300 ps"
    k = kit_with_marker(tmp_path)
    (k / "FAIL_POSTCTS").unlink()
    runlog = k / "run_route.log"
    runlog.write_text("make: Nothing to be done for 'place'.\n" + stop + "\n")
    c = probe(k, time.time() - 600)
    assert A.classify(c, {"exit": 6}) == ("STRUCTURAL", "place-setup-stop", stop)
    old = time.time() - 7200
    os.utime(runlog, (old, old))
    assert "place_setup_stop" not in probe(k, time.time() - 600)



def test_sealed_place_stop_requires_current_completed_client_log():
    unit = "ap-3d8d9a0d2252-a1"
    stop = "FAIL_POSTPLACE PLACE-SETUP-STOP wns -162224.15 ps < -300 ps (TT, post-place; routing cannot close it)"
    log = (f"AP_START 1795252041 {unit}\n{stop}\n"
           "ot-job: command exit 6\n"
           "ot-run: RAN on localhost (unit oth-ubuntu-274016-1795252047): exit 6\n"
           "ot-run-sealed: copy-back localhost -> epyc7 rc 0\nAP_RC=6\n")
    client = A.parse_client_log(log, unit=unit, started=1795252040)
    assert client["return_hosts"] == ["epyc7"]
    assert A.classify({}, client) == ("STRUCTURAL", "place-setup-stop", stop)
    assert "place_setup_stop" not in A.parse_client_log(log, unit="ap-other-a1", started=1795252040)
    assert "place_setup_stop" not in A.parse_client_log(log, unit=unit, started=1795252200)
    assert "place_setup_stop" not in A.parse_client_log(log.replace("AP_RC=6", "AP_RC=2"), unit=unit)
    assert "place_setup_stop" not in A.parse_client_log(log + f"AP_START 1795252241 {unit}\n", unit=unit)



def test_probe_prefers_fresh_copy_back_evidence(monkeypatch):
    paths = {
        "epyc7": {"exists": True, "place_setup_stop": "fresh stop"},
        "epyc9": {"exists": True, "last_log_mtime": 99990},
        "localhost": {"exists": False},
    }
    monkeypatch.setattr(A, "rpy", lambda host, _probe, _args: paths[host].copy())
    job = {"host": "epyc9", "ran_on": "localhost", "return_hosts": ["epyc7"],
           "goal": "route", "path": "/kit", "started": 100000}
    assert A.probe_job(job)["probe_host"] == "epyc7"
    paths["epyc7"] = {"error": "host unavailable"}
    assert A.probe_job(job)["probe_host"] == "epyc9"



def test_current_place_pass_overrides_copied_failure_marker(tmp_path):
    stop = "FAIL_POSTPLACE PLACE-SETUP-STOP wns -94428.62 ps < -300 ps"
    k = kit_with_marker(tmp_path, marker=stop)
    runlog = k / "run_route.log"
    runlog.write_text("OT_POSTPLACE_SETUP_STOP pass\n[ERROR DPL-0033] later legalizer failure\n")
    c = probe(k, time.time() - 600)
    assert "place_setup_stop" not in c
    assert "FAIL_POSTCTS" not in c
    assert A.classify(c, {"exit": 2})[:2] == ("CRASH", "flow-error")
    (k / "FAIL_POSTCTS").write_text(stop + "\nFF structural hold gate: WNS -100 ps")
    (k / "postcts_gate_tt.json").write_text('{"verdict": "FAIL"}')
    (k / "postcts_gate_TT.log").write_text("post-CTS hold WNS -100 FAIL\n")
    c = probe(k, time.time() - 600)
    assert A.classify(c, {"exit": 4})[:2] == ("STRUCTURAL", "post-cts-hold")


def test_new_place_receipt_overrides_marker_when_route_log_was_not_returned(tmp_path):
    k = kit_with_marker(tmp_path, marker="FAIL_POSTPLACE PLACE-SETUP-STOP wns -94428.62 ps < -300 ps")
    (k / "place_setup_stop.json").write_text('{"stopped": false, "wns": -197.86}')
    assert "place_setup_stop" not in probe(k, time.time() - 600)


# Retained epyc2 5_1_grt.log, AP 031c5184d5c9. Unrelated progress lines omitted.
CAUGHT_RSZ_THEN_DPL = """[WARNING RSZ-0064] Unable to repair all hold checks within margin.
[INFO RSZ-0032] Inserted 201 hold buffers.
[ERROR RSZ-0060] Max buffer count reached.
OT_HB4PAD: after hold repair the design holds 6326 HB4xp67 cells
OT_HOLD_GUARD_GRT chunk 1: hold ws 34.95 (+33.80) tns 0.0 viol 0, +201 buffers (cap 200), 2883 s
OT_HOLD_SETUP_GUARD stop: worst setup -179.88 < min(before 6.65, floor -42); hold ws 34.95
OT_HOLD_GUARD_GRT: chunk buffer caps reached (RSZ-0060 caught per chunk); continuing on the repaired design
OT_HOLD_BUDGET added 201 logic_cells 177068 pct 0.11 budget 10 hold_ws 34.95 margin 40 OK
OT_GRT_NONPORT restored exact FF SDC (port hold remains visible)
OT_GRT_NONPORT begin native_ff input_ports=5951 excluded_output_ports=0
 wire186267
[ERROR DPL-0033] detailed placement checks failed during check placement.
Error: global_route.tcl, 196 DPL-0033
Elapsed time: 4:02:08.09[h:]min:sec. CPU time: user 17523.51 sys 639.04 (125%). Peak memory: 15491204KB.
"""


def test_grt_terminal_dpl_after_proven_caught_rsz(tmp_path):
    k = kit_with_marker(tmp_path)
    (k / "FAIL_POSTCTS").unlink()
    stage = k / "run/logs/asap7/x/base/5_1_grt.log"
    stage.write_text(CAUGHT_RSZ_THEN_DPL)
    old_marker = "FAIL_route make exit 2: 5_1_grt.log: [ERROR RSZ-0060] Max buffer count reached.\n"
    expected = "FAIL_route make exit 2: 5_1_grt.log: [ERROR DPL-0033] detailed placement checks failed during check placement."
    marker = k / "FAIL_route"
    marker.write_text(old_marker)
    receipt = probe(k, time.time() - 600)
    assert A.classify(receipt, {"exit": 2}) == ("CRASH", "route-make-fail", expected)
    assert receipt["first_error"].startswith("5_1_grt.log: [ERROR DPL-0033]")

    # Exercise the exact emitted runner diagnostic branch against the same stage file.
    marker.unlink()
    (k / "kit_resume.py").write_bytes(Path(A.KR.__file__).read_bytes())
    source = (Path(A.__file__).resolve().parents[1] / "die_plan/gen_phys.py").read_text()
    start = source.index('if [ $rc != 0 ] && ! ls "$K"/FAIL_*')
    end = source.index("# Route success alone is not sign-off.", start)
    runner = source[start:end]
    run = subprocess.run(["bash", "-c", "K=$1; rc=2; GOAL=route\n" + runner, "runner", str(k)],
                         check=True, capture_output=True, text=True, timeout=30)
    assert run.stdout.strip() == marker.read_text().strip() == expected


def test_grt_terminal_dpl_does_not_replace_uncaught_or_old_failure(tmp_path):
    k = kit_with_marker(tmp_path)
    (k / "FAIL_POSTCTS").unlink()
    old_marker = "FAIL_route make exit 2: 5_1_grt.log: [ERROR RSZ-0060] Max buffer count reached."
    (k / "FAIL_route").write_text(old_marker + "\n")
    stage = k / "run/logs/asap7/x/base/5_1_grt.log"
    for text in (CAUGHT_RSZ_THEN_DPL.replace("OT_HOLD_GUARD_GRT chunk 1:", "unrelated chunk 1:"),
                 CAUGHT_RSZ_THEN_DPL.replace("continuing on the repaired design", "repair ended"),
                 CAUGHT_RSZ_THEN_DPL + "[ERROR GRT-9999] later terminal failure\n"):
        stage.write_text(text)
        receipt = probe(k, time.time() - 600)
        assert "grt_caught_dpl" not in receipt
        assert A.classify(receipt, {"exit": 2}) == ("CRASH", "route-make-fail", old_marker)
    stage.write_text(CAUGHT_RSZ_THEN_DPL)
    old = time.time() - 7200
    os.utime(stage, (old, old))
    assert "grt_caught_dpl" not in probe(k, time.time() - 600)


def test_failed_sealed_return_keeps_exact_worker_grt_overflow():
    unit = "ap-6b0d31f1a8c9-a1"
    start = 1795360482
    error = "[ERROR GRT-0116] Global routing finished with congestion. Check the congestion regions in the DRC Viewer."
    log = (
        f"AP_START {start} {unit}\n"
        f"FAIL_route make exit 2: 5_1_grt.log: {error}\n"
        "ot-job: command exit 2\n"
        "ot-run: RAN on localhost (unit oth-ubuntu-4018231-1795360490): exit 2\n"
        "tar: physical_completion: Cannot change mode: Operation not permitted\n"
        "ot-run-sealed: copy-back localhost -> epyc2 rc 2\n"
        "AP_RC=2\n"
    )
    client = A.parse_client_log(log, unit=unit, started=start)
    assert A.classify({}, client) == ("FAIL", "grt-overflow", error)
    assert A.classify({"oom": "memcg OOM"}, client) == ("CRASH", "infra-oom", "memcg OOM")

    for changed in (
        log.replace(unit, "ap-other-a1"),
        log.replace("5_1_grt.log", "5_2_route.log"),
        log.replace("copy-back localhost -> epyc2 rc 2", "copy-back localhost -> epyc2 rc 0"),
        log.replace("AP_RC=2", "AP_RC=98"),
        log.replace(f"AP_START {start}", f"AP_START {start + 121}"),
    ):
        assert "grt_overflow_return" not in A.parse_client_log(changed, unit=unit, started=start)
