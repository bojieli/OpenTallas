"""FLOW-FLEET-R2: run-item interim result.json records say RUNNING, never FAIL (waiters took 'stage src_manifest, verdict FAIL' for a failure)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as KW      # noqa: E402


def test_interim_record_is_running_with_stage_kept():
    res = {"stage": "src_manifest", "verdict": "FAIL", "src_manifest": {"hash": "h"}}
    r = KW.interim_record(res)
    assert r["verdict"] == "RUNNING" and r["stage"] == "src_manifest" and r["src_manifest"] == {"hash": "h"}
    assert res["verdict"] == "FAIL"                      # the live res keeps the fail-by-default, so an exit that sets nothing still reads FAIL


def test_final_verdicts_are_untouched():
    assert KW.interim_record({"stage": "geom", "verdict": "PASS"})["verdict"] == "PASS"


def test_ended_unit_with_running_record_is_a_fail_at_that_stage():
    r = KW.ended_unit_result({"stage": "gen", "verdict": "RUNNING"})
    assert r["verdict"] == "FAIL" and r["stage"] == "gen" and "ended while RUNNING" in r["tail"]
    assert KW.ended_unit_result({"stage": "geom", "verdict": "PASS"})["verdict"] == "PASS"
