"""WF-1 11-14 (OWNER: delete the conservative limits): core_tap_reach is advisory in kit_preflight.check()."""
import kit_preflight as KP


def test_far_core_tap_is_reported_but_never_fails(tmp_path, monkeypatch):
    k = tmp_path / "kit"
    k.mkdir()
    monkeypatch.setattr(KP, "core_tap_reach", lambda kit, limit=None: ["core tap clk_c4 is 382 um from its core u_x (limit 300): one unbuffered clock wire"])
    rec = KP.check(k)
    row = rec["checks"]["core_tap_reach"]
    assert row["verdict"] == "PASS" and row["errors"] == [] and "382" in row["advisory"][0]
    assert not [i for i in rec["issues"] if i.startswith("core_tap_reach")]


def test_core_tap_reach_exception_is_advisory_too(tmp_path, monkeypatch):
    k = tmp_path / "kit"
    k.mkdir()

    def boom(kit, limit=None):
        raise ValueError("no pins")
    monkeypatch.setattr(KP, "core_tap_reach", boom)
    rec = KP.check(k)
    assert rec["checks"]["core_tap_reach"]["verdict"] == "PASS" and "unreadable" in rec["checks"]["core_tap_reach"]["advisory"][0]


def test_core_tap_reach_function_itself_still_reports_rows():
    # the measurement stays (advisory text), only the verdict is gone
    assert hasattr(KP, "core_tap_reach_rows") and hasattr(KP, "core_tap_reach")
