"""ROUTEFAIL-CAUSE 11-23: a FAILED post is one line and carries class, first error line and log path."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import autopilot as A  # noqa: E402
import fail_cause as F  # noqa: E402


def job(**k):
    return dict({"id": "ab12cd34ef56", "unit": "ap-ab12cd34ef56-a1", "die": "s81", "type": "t", "src": "main@x", "lane": "KIT-WAVE-1",
                 "path": "/srv/s/items/t/gen/t", "host": "epyc2", "client_log": "/c/a1.log", "kind": "route-make-fail",
                 "reasons": "FAIL_route make exit 2 (see run_route.log)"}, **k)


def test_make_exit_gets_stage_error_and_log():
    j = job(first_error='4_1_cts.log: Error: cts.tcl, 89 can\'t read "tb_cdirect": no such variable', first_error_log="epyc2:/k/run/logs/4_1_cts.log")
    assert F.cause(j, "AP_START 1 u\nmake[1]: *** [Makefile:548: do-4_1_cts] Error 1\n") == ("flow-script", j["first_error"], j["first_error_log"])


def test_sigkill_is_mem_kill_not_caught_rsz():
    j = job(first_error="5_1_grt.log: [ERROR RSZ-0060] Max buffer count reached.")
    cls, line, _ = F.cause(j, "make[1]: *** [Makefile:585: do-5_1_grt] Error 247\nFAIL_route make exit 2 (see run_route.log)\n")
    assert cls == "mem-kill" and "Error 247" in line


def test_client_log_classes():
    for text, cls in (("OSError: [Errno 28] No space left on device\n", "disk-full"),
                      ("NOT-RUN every requested host is draining: epyc9 DRAINING (128 of 250 GB scratch free)\n", "not-run"),
                      ("Error: global_route.tcl, 196 DPL-0036\n", "legalize"),
                      ("[ERROR DRT-0073] No access point for u/clk\n", "pin-access"),
                      ("FAIL_POSTPLACE PLACE-SETUP-STOP wns -900 ps < -300 ps\n", "place-setup"),
                      ("Traceback\nRuntimeError: reentrant call\not-job: signal 15: stopping the command\n", "stopped"),
                      ("[ERROR GRT-0116] Global routing finished with congestion.\n", "grt-congestion")):
        assert F.cause(job(kind="flow-error", reasons="exit 1"), "AP_START 1 u\n" + text)[0] == cls, text


def test_previous_attempt_is_not_the_cause():
    assert F.client_error("AP_START 1 u\nError: old.tcl, 1 x\nAP_RC=2\nAP_START 2 u\nError: new.tcl, 2 y\n") == "Error: new.tcl, 2 y"


def test_orphan_names_autopilot_cancel():
    hub = ("2026-11-18 18:39:56 PST AUTOPILOT: KIT-WAVE GRT-ARM CANCEL s81/t@5 units ['ap-ab12cd34ef56-a1'] containers [none]: STRUCT-STOP\n"
           "2026-11-18 18:42:36 PST AUTOPILOT: CLASSIFY ab12cd34ef56 s81/t -> CRASH (infra-orphan): client lost\n")
    cls, line, _ = F.cause(job(kind="infra-orphan", reasons="client lost, kit logs idle 3.3 h"), "", hub)
    assert cls == "cancelled" and "GRT-ARM CANCEL" in line
    # another job's cancel, or a path that is only a prefix, is not this job's sender
    assert F.cause(job(kind="infra-orphan", reasons="client lost"), "", hub.replace("ab12cd34ef56", "ffffffffffff"))[0] != "cancelled"
    assert F.stop_sender(job(), "", "x signal 15 from pid 1 (ot-run --cancel-dir /srv/s/items/t/gen/t_b)") == ""
    assert F.stop_sender(job(), "", "x signal 15 from pid 1 (ot-run --cancel-dir /srv/s/items/t/gen/t; invoked by tick)")


def test_refused_host_before_the_run_is_no_cause():
    t = "AP_START 1 u\nNOT-RUN on epyc2: ot-heavy exit 75 (ot-run status 75)\nmake[1]: *** [Makefile:585: do-5_1_grt] Error 1\not-run: RAN on epyc8 (unit oth-1): exit 2\n"
    assert F.client_error(t) == "make[1]: *** [Makefile:585: do-5_1_grt] Error 1"
    hook = "Error: global_route.tcl, 195 pin-register mean unavailable -- sign-off would be NOT RUN"
    assert F.classify_line(hook) == "flow-script"


def test_unknown_says_so():
    assert F.cause(job(), "nothing")[:2] == ("unclassified", "")


def test_notice_is_one_line(tmp_path, monkeypatch):
    out = []
    monkeypatch.setattr(A, "coord_append", lambda rel, line: out.append((rel, line)))
    monkeypatch.setattr(A, "COORD", tmp_path)
    (tmp_path / "lanes").mkdir()
    (tmp_path / "lanes" / "KIT-WAVE-1.md").write_text("")
    p = tmp_path / "a1.log"
    p.write_text("AP_START 1 u\n[ERROR DRT-0073] No access point for u/clk\nAP_RC=2\n")
    A.failed_notice(job(kind="flow-error", reasons="tail line 1\n  tail line 2", client_log=str(p)), "CRASH", "epyc2")
    assert len(out) == 2
    for _, l in out:
        assert "\n" not in l and "cause pin-access: [ERROR DRT-0073] No access point for u/clk" in l and f"log {p}" in l
        assert " | kit epyc2:/srv/s/items/t/gen/t src main@x | review " in l
