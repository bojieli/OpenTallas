import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import autopilot as AP


def test_enospc_is_an_infra_crash_that_resubmits():
    cls, kind, why = AP.classify({"runlog_tail": "write error\nmkdir: cannot create directory: No space left on device\n", "goal": "route"}, {"exit": 1})
    assert (cls, kind) == ("CRASH", "infra-disk") and "No space left" in why
    assert "infra-disk" in AP.INFRA_KINDS
    cls2, kind2, _ = AP.classify({"runlog_tail": "segfault in drt", "goal": "route"}, {"exit": 1})
    assert kind2 != "infra-disk"


def test_stage_submit_declares_the_measured_disk(tmp_path, monkeypatch):
    import json, time
    monkeypatch.setattr(AP, "AP_DIR", tmp_path)
    assert AP.stage_disk_args() == []
    (tmp_path / "kit_peak_gb.json").write_text(json.dumps({"p90_gb": 12.2, "n": 9, "at": time.time()}))
    assert AP.stage_disk_args() == ["--disk", "13"]
    (tmp_path / "kit_peak_gb.json").write_text(json.dumps({"p90_gb": 1.0, "n": 9, "at": time.time()}))
    assert AP.stage_disk_args() == ["--disk", "3"]
    (tmp_path / "kit_peak_gb.json").write_text(json.dumps({"p90_gb": 50, "n": 2, "at": time.time()}))
    assert AP.stage_disk_args() == []
