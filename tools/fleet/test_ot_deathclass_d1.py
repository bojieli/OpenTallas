"""FABLE-FLOW-0230 D1 (28 of 85 DIED posts said nothing): NOT-RUN with a named reason, EMIT / compare bind errors, FAIL_route make exits and a
"verdict": "FAIL" json each get a class; nothing matched is NO-PATTERN with the last non-ot-run line, never a bare post."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ot_deathclass as DC      # noqa: E402


def cls(rc, t):
    return DC.classify(rc, "", t, 100)


def test_not_run_with_a_reason_is_not_ssh_drop():
    c, cause = cls(78, "ot-run: NOT-RUN disk-ETA hold: epyc9 scratch2 projected under the floor in 2.1 h\n")
    assert c == "NOT-RUN" and "disk-ETA" in cause
    assert cls(78, "ot-run: REFUSED (ISOLATION step 3): lane job names input paths outside its --dir\n")[0] == "NOT-RUN"
    assert cls(78, "ot-run: NOT-RUN SSH probe exit 255 on epyc8\n")[0] == "SSH-DROP"


def test_rc78_without_log_does_not_infer_ssh_transport_failure():
    c, cause = DC.classify(78, "--hosts epyc8 --max-wait 3600", "", 3623)
    assert c == "NO-PATTERN" and "no log" in cause
    c, cause = cls(78, "NOT-RUN requeue budget exhausted after 3600 s")
    assert c == "NOT-RUN" and "budget exhausted" in cause


def test_bind_emit_and_compare():
    assert cls(1, "elab done\nEMIT relay_depth u_x: 1 row matched no internal sink\n")[0] == "BIND-FAIL"
    assert cls(1, "compare FAIL (361869 mismatched)\n")[0] == "BIND-FAIL"


def test_route_make_exit():
    t = "[ERROR DPL-0036] Detailed placement failed.\nmake: *** [Makefile:612: results/asap7/x/base/5_1_grt.odb] Error 1\n"
    c, cause = cls(2, t)
    assert c == "ROUTE-FAIL"
    assert cls(1, "touch /k/FAIL_route\n")[0] == "ROUTE-FAIL"


def test_verdict_json_fail():
    assert cls(1, '{\n "verdict": "FAIL",\n "reason": "hold_ff -12 ps"\n}\n')[0] == "VERDICT-FAIL"


def test_nothing_matched_is_no_pattern_with_last_line():
    c, cause = cls(5, "step a\nlast real line\not-run: RAN on epyc9 (unit x): exit 5\n")
    assert c == "NO-PATTERN" and cause.startswith("last real line")
