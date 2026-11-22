"""WAVE-COPYBACK-1115 (FABLE-PD-PLACE-0830 class A): a place that finished RC=0 on a host ot-run chose (INPUT HOLD, no copy-back record)
is probed there, an RC=0 place with no odb is INFRA (uncharged, reason never the GRTM banner), and a resume sees the RAN host.
    python3 -m pytest -q tools/autopilot/test_kit_wave_copyback.py"""
import json
import tempfile
from pathlib import Path

import kit_wave as KW

LOG = """ot-run: INPUT HOLD: spec inputs exist only on intel1, epyc2, epyc7, epyc8, epyc9, epyc10; candidates epyc10 -> intel1, epyc2, epyc7, epyc8, epyc9, epyc10
ot-run: RAN on epyc7 (unit oth-ubuntu-4088679-1794755995): exit 1
ot-run: RAN on epyc8 (unit oth-ubuntu-3200640-1794756003): exit 0
KW_PLACE_RC=0
"""
BANNER = "GRTM mode edge_outline (OT_GRT_TRANSITION_MODE)\n"


def test_ran_ok_host_last_exit_zero():
    assert KW.ran_ok_host(LOG) == "epyc8"
    assert KW.ran_ok_host("ot-run: RAN on epyc7 (unit u): exit 1\n") == ""
    assert KW.ran_ok_host("ot-run: RAN on localhost: exit 0\n", "intel2") == "intel2"
    assert KW.ran_ok_host("") == ""


def test_copy_back_hosts_ran_host_first_without_record():
    assert KW.copy_back_hosts(LOG, "epyc10", "intel2") == ["epyc8", "epyc10"]
    assert KW.copy_back_hosts("no ot-run line", "epyc10") == ["epyc10"]
    assert KW.copy_back_hosts(LOG.replace("epyc8", "epyc10"), "epyc10") == ["epyc10"]


def test_copy_back_hosts_record_stays_authoritative():
    txt = LOG + "ot-run-sealed: copy-back epyc8 -> epyc7 rc 0\n"
    assert KW.copy_back_hosts(txt, "epyc10") == ["epyc7", "epyc8", "epyc10"]
    assert KW.copy_back_host(txt, "epyc8") == "epyc7"


def test_spill_terminal_destination_precedes_execution_and_gen_hosts():
    txt = ("ot-run: RAN on epyc10 (unit oth-ubuntu-3520614-1795360035): exit 0\n"
           "ot-run: SPILL: outputs copied back epyc10 -> epyc2; RAN on epyc10: exit 0\n"
           "ot-run: SPILL: dropped the stage copy /scratch/kit on epyc10\n")
    assert KW.copy_back_hosts(txt, "epyc9", "intel2") == ["epyc2", "epyc10", "epyc9"]


def test_rc0_no_odb_is_uncharged_infra_without_banner():
    stage_text = BANNER + "Error: plan outline utilization 0.4\n" + LOG
    cls, why = KW.classify("place", stage_text)
    assert cls == "INFRA" and KW.is_place_no_odb(why)
    assert "edge_outline" not in why and "outline" not in why.split("@")[1] and "GRTM" not in why
    cls2, _ = KW.classify("place", BANNER + "[ERROR PDN-0123] bad\nKW_PLACE_RC=1\n")
    assert cls2 == "PLAN"                                           # a real RC!=0 place keeps its verdicts
    assert KW.classify("place", "x\nKW_PLACE_NO_ODB t: RC=0, no 3_place.odb on a\n")[0] == "INFRA"
    assert KW.classify("geom", LOG)[0] != "INFRA" or "RC=0" not in KW.classify("geom", LOG)[1]


def test_free_place_no_odb_resets_infra_budget_and_is_bounded():
    rec = dict(attempt=28, infra_base=0, status="FAIL", reason=KW.PLACE_NO_ODB_WHY + " @place: x")
    assert KW.infra_used(rec) == 28
    assert KW.free_place_no_odb(rec) and rec["status"] == "RETRY-INFRA" and KW.infra_used(rec) == 0
    for _ in range(KW.COPYBACK_FREE_MAX):
        KW.free_place_no_odb(rec)
    assert rec["copyback_free"] == KW.COPYBACK_FREE_MAX
    rec["attempt"] = 40
    assert not KW.free_place_no_odb(rec) and KW.infra_used(rec) == 40 - rec["infra_base"]
    assert not KW.free_place_no_odb(dict(attempt=3, reason="PLAN geometry"))


def test_reclassify_rejudges_recent_false_fail(tmp_path=None):
    d = Path(tempfile.mkdtemp())
    (d / "place.log").write_text(BANNER + LOG)
    (d / "result.json").write_text(json.dumps({"stage": "place", "verdict": "FAIL", "tail": BANNER + LOG, "errors": "outline"}))
    import time
    rec = dict(status="FAIL", stage="place", dir=str(d), attempt=14, infra_base=0, updated=time.time(),
               **{"class": "PLAN"}, reason="plan geometry / site @place: GRTM mode edge_outline")
    old = dict(rec, updated=time.time() - 72 * 3600)
    st = {"items": {"k": rec, "o": old}}
    ch = KW.reclassify(st, write=True, log=lambda *_: None)
    assert len(ch) == 2
    assert st["items"]["k"]["status"] == "RETRY-INFRA" and st["items"]["k"]["class"] == "INFRA" and KW.infra_used(st["items"]["k"]) == 0
    assert st["items"]["o"]["status"] == "FAIL" and st["items"]["o"]["class"] == "INFRA"     # relabelled, not relaunched


class _AP:
    HUB_NAME = "intel2"


def test_resume_source_adds_the_ran_host():
    d = Path(tempfile.mkdtemp())
    (d / "place.log").write_text(LOG)
    (d / "gen.log").write_text("")
    (d / "spec.json").write_text(json.dumps({"work": "/w", "gen_host": "epyc10"}))
    out = KW.resume_source(_AP, {"dir": str(d), "item": "t", "attempt": 14, "kind": "type", "class": "INFRA"})
    assert out["candidates"] == [["epyc10", "/w/gen/t"], ["epyc8", "/w/gen/t"]]


def test_rejudge_place_nodb_each_tick_once_per_attempt():
    import time
    d = Path(tempfile.mkdtemp())
    (d / "place.log").write_text(BANNER + LOG)
    rec = dict(status="FAIL", stage="place", dir=str(d), attempt=9, infra_base=0, updated=time.time(),
               **{"class": "PLAN"}, reason="plan geometry / site @place: GRTM")
    st = {"items": {"k": rec}}
    assert KW.rejudge_place_nodb(st) == ["k"]
    assert rec["status"] == "RETRY-INFRA" and rec["class"] == "INFRA" and KW.infra_used(rec) == 0
    rec["status"] = "FAIL"                                     # same attempt: not judged twice
    assert KW.rejudge_place_nodb(st) == []
    rec["attempt"] = 10                                        # a new attempt that false-fails again is judged again
    assert KW.rejudge_place_nodb(st) == ["k"]
    (d / "place.log").write_text("KW_PLACE_RC=1\n")
    rec.update(status="FAIL", attempt=11)
    assert KW.rejudge_place_nodb(st) == [] and rec["status"] == "FAIL"
