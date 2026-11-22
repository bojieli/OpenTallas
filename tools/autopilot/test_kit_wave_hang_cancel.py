"""FABLE-FLOW-0000 F2 (FLOW-FLEET-R1 11-22): HANG = no new output for 90 min in place/CTS/GRT while CPU grows (report, then cancel);
a manual `ot-run --cancel` is CANCELLED with no free INFRA retry unless --reason infra."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as KW  # noqa: E402

NOW = 1_800_000_000.0


def test_hang_reports_then_cancels_on_the_same_frozen_log():
    rec = {"stage": "place"}
    w = {"log": NOW - 95 * 60}
    k, why = KW.hang_judge(rec, w, NOW)
    assert k == "report" and why.startswith("HANG: stage place: no new log output for 95 min")
    rec["hang_reported"] = [NOW, w["log"]]
    assert KW.hang_judge(rec, w, NOW + 10 * 60)[0] is None            # inside the report window
    assert KW.hang_judge(rec, w, NOW + 31 * 60)[0] == "cancel"
    w2 = {"log": NOW + 5 * 60 - 95 * 60 + 60}                          # new output after the report: a fresh report, never a cancel
    assert KW.hang_judge(rec, w2, NOW + 31 * 60)[0] != "cancel"


def test_hang_only_in_route_stages_and_after_90_min():
    assert KW.hang_judge({"stage": "gen"}, {"log": NOW - 300 * 60}, NOW)[0] is None
    assert KW.hang_judge({"stage": "kit_rtl"}, {"log": NOW - 300 * 60}, NOW)[0] is None
    assert KW.hang_judge({"stage": "place"}, {"log": NOW - 80 * 60}, NOW)[0] is None
    assert KW.hang_judge({"stage": "place"}, {"log": NOW - 300 * 60}, NOW, hub_newest=NOW - 60)[0] is None   # hub log grew
    assert KW.hang_judge({"stage": "place"}, {"log": NOW - 300 * 60}, NOW, minutes=0)[0] is None              # option off


def test_manual_cancel_reason():
    assert KW.manual_cancel_reason("x\not-run: OT-RUN-CANCEL reason=design (ot-run --cancel: ...)\nexit 143") == "design"
    assert KW.manual_cancel_reason("ot-run: OT-RUN-CANCEL reason=infra (ot-run --cancel)") == "infra"
    assert KW.manual_cancel_reason("command exit 143") is None


def test_manual_cancel_is_not_infra():
    assert KW.is_infra_fail({"reason": "rc 143 OT-RUN-CANCEL reason=hang"}) is False
    assert KW.is_infra_fail({"reason": "rc 143 OT-RUN-CANCEL reason=infra"}) is True
    assert KW.is_infra_fail({"reason": "rc 143 earlyoom"}) is True


def test_wiring():
    src = (Path(__file__).resolve().parent / "kit_wave.py").read_text()
    assert 'rec.update(status="CANCELLED", **{"class": "MANUAL-CANCEL"}' in src
    assert 'out.append((key, "HANG-REPORT"' in src and 'if kind == "HANG-REPORT":' in src
