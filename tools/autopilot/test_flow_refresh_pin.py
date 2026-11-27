"""CONFOUND-CTL 11-27 (HEAD-INT-R3): private-spec --pin-flow-refresh keeps an A/B probe off the moving rt/current."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as KW  # noqa: E402

OWN_RT = Path(KW.__file__).resolve().parents[2]


def test_flow_refresh_root_default_and_pinned():
    assert KW.flow_refresh_root({}, "/x/launch") == (KW.RT_CURRENT, False)
    assert KW.flow_refresh_root({"flow_refresh_pin": False}, "/x/launch") == (KW.RT_CURRENT, False)
    assert KW.flow_refresh_root({"flow_refresh_pin": True}, "/x/launch") == ("/x/launch", True)
    assert KW.flow_refresh_root({"flow_refresh_pin": True}, None) == (KW.RT_CURRENT, False)


def test_the_stage_refresh_uses_the_root_helper():
    src = Path(KW.__file__).read_text()
    i = src.index("def flow_refresh(stage):")
    body = src[i:src.index("\n    def ", i + 10)]
    assert "_rtc, _pinned = flow_refresh_root(sp, tsrc)" in body and "KIT_FLOW_REFRESH PINNED" in body
    assert body.index("flow_refresh_root(sp, tsrc)") < body.index("--rt {q(_rtc)}")


def test_pin_driver_refusal():
    assert KW.pin_driver_refusal({}) == ""
    assert "without tools_rt" in KW.pin_driver_refusal({"flow_refresh_pin": True})
    assert KW.pin_driver_refusal({"flow_refresh_pin": True, "tools_rt": str(OWN_RT)}) == ""
    assert "run it with /elsewhere/rt" in KW.pin_driver_refusal({"flow_refresh_pin": True, "tools_rt": "/elsewhere/rt"})


def test_runitem_driver_keeps_its_own_file_for_a_pinned_spec(tmp_path):
    ctl = tmp_path / "ctl"
    ctl.mkdir()
    (ctl / "kit_wave.py").write_text("# other driver\n")
    own = Path(KW.__file__).resolve()
    for pin, want in ((False, (ctl / "kit_wave.py").resolve()), (True, own)):
        sp = tmp_path / f"spec_{pin}.json"
        sp.write_text(json.dumps({"private": {"lane": "X"}, "flow_refresh_pin": pin}))
        assert KW.runitem_driver(str(sp), env={"OT_CONTROL_ROOT": str(ctl)}) == want


def test_control_root_is_off_while_pinned(tmp_path, monkeypatch):
    ctl = tmp_path / "ctl"
    ctl.mkdir()
    (ctl / "kit_wave.py").write_text("# other driver\n")
    assert KW.control_root(env={"OT_CONTROL_ROOT": str(ctl)}) == ctl.resolve()
    monkeypatch.setattr(KW, "_PIN_CONTROL", [True])
    assert KW.control_root(env={"OT_CONTROL_ROOT": str(ctl)}) is None


def test_pinned_run_item_with_a_foreign_driver_is_refused_with_a_result(tmp_path, monkeypatch):
    monkeypatch.setattr(KW, "_PIN_CONTROL", [])
    sp = tmp_path / "spec.json"
    sp.write_text(json.dumps({"private": {"lane": "X"}, "die": "d", "item": "t", "flow_refresh_pin": True, "tools_rt": "/elsewhere/rt"}))
    assert KW._run_item(str(sp)) == 2
    r = json.loads((tmp_path / "result.json").read_text())
    assert r["verdict"] == "FAIL" and r["stage"] == "pin" and "elsewhere" in r["tail"]
    assert KW._PIN_CONTROL == [True]                        # set from the spec on entry


def test_a_refusal_keeps_a_prior_pass_record(tmp_path):
    sp = tmp_path / "spec.json"
    sp.write_text(json.dumps({"private": {"lane": "X"}, "flow_refresh_pin": True, "tools_rt": "/elsewhere/rt"}))
    (tmp_path / "result.json").write_text(json.dumps({"verdict": "PASS", "stage": "geom"}))
    assert KW._run_item(str(sp)) == 2
    assert json.loads((tmp_path / "result.json").read_text())["verdict"] == "PASS"


def test_pin_control_is_reset_for_an_unpinned_spec(tmp_path, monkeypatch):
    monkeypatch.setattr(KW, "_PIN_CONTROL", [True])
    monkeypatch.setattr(KW, "pin_driver_refusal", lambda sp, own=None: "stop")      # stop right after the entry reset
    sp = tmp_path / "spec.json"
    sp.write_text(json.dumps({"private": {"lane": "X"}}))
    assert KW._run_item(str(sp)) == 2 and KW._PIN_CONTROL == []


def test_pinned_goal_and_refit_guards_are_in_the_pipeline():
    src = Path(KW.__file__).read_text()
    assert KW.PIN_GOALS == ("place", "geom")
    i = src.index("chain_goal = prior[\"goal\"] if resume_reviewed else chain_goal_of(sp, goal)")
    assert "chain_goal not in PIN_GOALS" in src[i:i + 300]
    j = src.index('if rc and os.environ.get("OT_BIND_RT", "1") != "0" and sp.get("flow_refresh_pin"):')
    assert j < src.index('if rc and os.environ.get("OT_BIND_RT", "1") != "0":\n') and 'return fail("pin"' in src[j:j + 300]


def test_private_spec_help_lists_the_flag():
    import subprocess
    out = subprocess.run([sys.executable, "-I", KW.__file__, "private-spec", "--help"], capture_output=True, text=True, timeout=120)
    assert out.returncode == 0 and "--pin-flow-refresh" in out.stdout, out.stderr[-500:]


def test_input_skip_has_the_pin():
    assert "flow_refresh_pin" in KW.INPUT_SKIP
